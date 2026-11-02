import os
import json
import logging
from typing import Optional
import numpy as np

# Constrain PyTorch thread consumption to minimize memory footprint
try:
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass

logger = logging.getLogger(__name__)

class EmbedderService:
    """
    Singleton lazy-loaded SentenceTransformer service.
    Defers model loading until the first actual analysis request.
    Uses precomputed, static role vectors at startup without loading PyTorch weights.
    """
    _instance: Optional["EmbedderService"] = None
    _model = None
    _role_embeddings: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbedderService, cls).__new__(cls)
        return cls._instance

    @property
    def model(self):
        """Lazy-loads SentenceTransformer only when first needed."""
        if self._model is None:
            logger.info("Lazy-loading sentence-transformers model 'all-MiniLM-L6-v2' on demand...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            logger.info("SentenceTransformer model loaded successfully.")
        return self._model

    def encode(self, text: str) -> np.ndarray:
        """Generates 384-dim normalized embedding for a text string."""
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)
        try:
            import torch
            with torch.no_grad():
                return self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        except Exception:
            return self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)

    def precompute_role_embeddings(self, roles_data_path: str) -> None:
        """
        Loads precomputed role vectors from disk or computes them lightly.
        Does not force heavy model loading at startup if pre-cached vector file exists.
        """
        if self._role_embeddings:
            return

        cache_path = os.path.join(os.path.dirname(roles_data_path), "roles_embeddings.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._role_embeddings = {k: np.array(v, dtype=np.float32) for k, v in data.items()}
                logger.info(f"Loaded {len(self._role_embeddings)} precomputed role embeddings instantly from disk.")
                return
            except Exception as e:
                logger.warning(f"Could not load precomputed embeddings cache: {e}")

        # Fallback: compute on the fly
        if not os.path.exists(roles_data_path):
            return

        with open(roles_data_path, "r", encoding="utf-8") as f:
            roles = json.load(f)

        logger.info(f"Computing embeddings for {len(roles)} roles...")
        texts = []
        role_ids = []
        for role in roles:
            role_id = role["id"]
            title = role.get("title", "")
            description = role.get("description", "")
            skills = ", ".join(role.get("required_skills", {}).keys())
            keywords = ", ".join(role.get("typical_keywords", []))
            combined_role_text = f"Role: {title}. Description: {description}. Required Skills: {skills}. Domain Keywords: {keywords}."
            texts.append(combined_role_text)
            role_ids.append(role_id)

        embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=8, show_progress_bar=False)
        cache_data = {}
        for r_id, emb in zip(role_ids, embeddings):
            self._role_embeddings[r_id] = np.array(emb, dtype=np.float32)
            cache_data[r_id] = emb.tolist()

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)
            logger.info("Saved roles_embeddings.json to disk.")
        except Exception:
            pass

    def get_role_embedding(self, role_id: str) -> Optional[np.ndarray]:
        return self._role_embeddings.get(role_id)

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Computes cosine similarity between two 1D vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

# Module-level singleton
embedder_service = EmbedderService()
