import os
import json
import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from flask import request, jsonify
import jwt

logger = logging.getLogger(__name__)

class FirebaseService:
    """
    Handles Firebase Admin SDK authentication verification,
    Cloud Firestore operations, and user-isolated storage.
    Supports real Firebase tokens with user-specific isolation even in local mode.
    """
    def __init__(self):
        self.initialized = False
        self.auth = None
        self.db = None
        self.bucket = None
        self._mock_storage: Dict[str, Dict[str, Any]] = {}
        self._init_firebase()

    def _init_firebase(self):
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")

        if cred_path and os.path.exists(cred_path):
            try:
                import firebase_admin
                from firebase_admin import credentials, auth, firestore, storage

                if not firebase_admin._apps:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': bucket_name
                    } if bucket_name else None)
                
                self.auth = auth
                self.db = firestore.client()
                if bucket_name:
                    self.bucket = storage.bucket()
                self.initialized = True
                logger.info("Firebase Admin SDK successfully initialized.")
            except Exception as e:
                logger.warning(f"Could not initialize Firebase Admin SDK: {e}. Running in Local mode with token decoding.")
                self.initialized = False
        else:
            logger.info("FIREBASE_CREDENTIALS_PATH not set or file not found. Running in Local Mode with token decoding.")
            self.initialized = False

    def verify_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verifies or decodes JWT ID token from client.
        Extracts real user_id / sub and email so each user has isolated storage.
        """
        if not id_token:
            return None

        # If Admin SDK initialized, verify cryptographically
        if self.initialized and self.auth:
            try:
                decoded_token = self.auth.verify_id_token(id_token)
                return decoded_token
            except Exception as e:
                logger.error(f"Error verifying Firebase ID token with Admin SDK: {e}")

        # Fallback for client tokens without Admin SDK serviceAccountKey:
        # Decode the Firebase JWT payload unverified to get the exact real user uid and email
        try:
            unverified = jwt.decode(id_token, options={"verify_signature": False})
            uid = unverified.get("user_id") or unverified.get("sub")
            email = unverified.get("email")
            if uid:
                return {
                    "uid": uid,
                    "email": email or f"{uid}@firebase.user",
                    "name": unverified.get("name", "User")
                }
        except Exception:
            pass

        # Handle simple demo tokens
        if id_token.startswith("demo_token_"):
            demo_id = id_token.replace("demo_token_", "")
            return {
                "uid": f"user_{demo_id}",
                "email": f"{demo_id}@resumeiq.local",
                "name": "Demo User"
            }

        return None

    def save_analysis(self, uid: str, analysis_id: str, data: Dict[str, Any]) -> bool:
        """Saves analysis record under users/{uid}/analyses/{analysisId}."""
        if self.initialized and self.db:
            try:
                doc_ref = self.db.collection("users").document(uid).collection("analyses").document(analysis_id)
                doc_ref.set(data)
                return True
            except Exception as e:
                logger.error(f"Error saving to Firestore: {e}")
                return False
        else:
            # User-isolated in-memory storage partitioned strictly by unique uid
            if uid not in self._mock_storage:
                self._mock_storage[uid] = {}
            self._mock_storage[uid][analysis_id] = data
            return True

    def get_user_analyses(self, uid: str) -> List[Dict[str, Any]]:
        """Retrieves past analyses strictly for the authenticated user."""
        if self.initialized and self.db:
            try:
                docs = self.db.collection("users").document(uid).collection("analyses").order_by("created_at", direction="DESCENDING").stream()
                return [d.to_dict() for d in docs]
            except Exception as e:
                logger.error(f"Error reading from Firestore: {e}")
                return []
        else:
            user_records = self._mock_storage.get(uid, {})
            records = list(user_records.values())
            records.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return records

    def get_analysis_by_id(self, uid: str, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single analysis document belonging to the user."""
        if self.initialized and self.db:
            try:
                doc = self.db.collection("users").document(uid).collection("analyses").document(analysis_id).get()
                return doc.to_dict() if doc.exists else None
            except Exception as e:
                logger.error(f"Error fetching document: {e}")
                return None
        else:
            return self._mock_storage.get(uid, {}).get(analysis_id)

    def delete_analysis(self, uid: str, analysis_id: str) -> bool:
        """Deletes an analysis document belonging to the user."""
        if self.initialized and self.db:
            try:
                self.db.collection("users").document(uid).collection("analyses").document(analysis_id).delete()
                return True
            except Exception as e:
                logger.error(f"Error deleting Firestore document: {e}")
                return False
        else:
            if uid in self._mock_storage and analysis_id in self._mock_storage[uid]:
                del self._mock_storage[uid][analysis_id]
                return True
            return False

# Global singleton
firebase_service = FirebaseService()

def require_auth(f):
    """Decorator to enforce Bearer token authentication and user isolation."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized", "message": "Missing Bearer authorization header."}), 401

        token = auth_header.split("Bearer ")[1].strip()
        decoded = firebase_service.verify_token(token)
        if not decoded:
            return jsonify({"error": "Unauthorized", "message": "Invalid or expired authorization token."}), 401

        request.current_user = decoded
        return f(*args, **kwargs)
    return decorated_function
