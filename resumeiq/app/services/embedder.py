import os
import json
import logging
from typing import Optional
import torch
from sentence_transformers import SentenceTransformer
import numpy as np

# Constrain PyTorch thread consumption to minimize memory footprint
torch.set_num_threads(1)
try:
    torch.set_num_interop_threads(1)
except Exception:
    pass

logger = logging.getLogger(__name__)

class EmbedderService:
    """
    Singleton lazy-loaded SentenceTransformer service.
    Caches model and precomputed role embeddings to optimize inference time and memory.
    """
    _instance: Optional["EmbedderService"] = None
    _model: Optional[SentenceTransformer] = None
    _role_embeddings: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbedderService, cls).__new__(cls)
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Lazy-loading sentence-transformers model 'all-MiniLM-L6-v2'...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            logger.info("SentenceTransformer model loaded successfully.")
        return self._model

    def encode(self, text: str) -> np.ndarray:
        """Generates 384-dim normalized embedding for a text string."""
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)
        with torch.no_grad():
            return self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)

    def precompute_role_embeddings(self, roles_data_path: str) -> None:
        """
        Precomputes and caches role embeddings at application startup.
        Combines title, description, and required skills for a rich representation.
        """
        if self._role_embeddings:
            return  # Already precomputed
            
        if not os.path.exists(roles_data_path):
            logger.warning(f"Roles file not found at {roles_data_path}, skipping precomputation.")
            return

        with open(roles_data_path, "r", encoding="utf-8") as f:
            roles = json.load(f)

        logger.info(f"Precomputing embeddings for {len(roles)} roles...")
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

        # Batch encode in a single pass to save CPU and peak RAM
        with torch.no_grad():
            embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=8, show_progress_bar=False)
            for r_id, emb in zip(role_ids, embeddings):
                self._role_embeddings[r_id] = emb

        logger.info(f"Precomputed {len(self._role_embeddings)} role embeddings successfully.")

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
