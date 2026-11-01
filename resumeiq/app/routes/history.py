import logging
from flask import Blueprint, jsonify, request

from ..services.firebase_service import firebase_service, require_auth

logger = logging.getLogger(__name__)
history_bp = Blueprint("history", __name__)

@history_bp.route("/analyses", methods=["GET"])
@require_auth
def list_analyses():
    """Lists past analyses for the authenticated user."""
    current_user = getattr(request, "current_user", {"uid": "guest_demo"})
    uid = current_user.get("uid", "guest_demo")
    analyses = firebase_service.get_user_analyses(uid)
    return jsonify({
        "analyses": analyses,
        "total_count": len(analyses)
    }), 200

@history_bp.route("/analyses/<analysis_id>", methods=["GET"])
@require_auth
def get_analysis(analysis_id: str):
    """Retrieves a single historical analysis."""
    current_user = getattr(request, "current_user", {"uid": "guest_demo"})
    uid = current_user.get("uid", "guest_demo")
    record = firebase_service.get_analysis_by_id(uid, analysis_id)
    if not record:
        return jsonify({"error": "Not Found", "message": f"Analysis '{analysis_id}' not found."}), 404
    return jsonify(record), 200

@history_bp.route("/analyses/<analysis_id>", methods=["DELETE"])
@require_auth
def delete_analysis(analysis_id: str):
    """Deletes an analysis record."""
    current_user = getattr(request, "current_user", {"uid": "guest_demo"})
    uid = current_user.get("uid", "guest_demo")
    success = firebase_service.delete_analysis(uid, analysis_id)
    if success:
        return jsonify({"success": True, "message": "Analysis deleted successfully."}), 200
    return jsonify({"error": "Not Found", "message": "Failed to delete record."}), 404

