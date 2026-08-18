from typing import List
try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False
    SentenceTransformer = None

from app.core.config import settings

class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        if not HAS_ST:
            return None
        if cls._model is None:
            cls._model = SentenceTransformer(
                settings.EMBEDDING_MODEL_NAME,
                device=settings.EMBEDDING_DEVICE
            )
        return cls._model

    @classmethod
    def embed_text(cls, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * 384
        model = cls.get_model()
        if model is None:
            # Deterministic fallback embedding if sentence-transformers not installed
            hash_val = sum(ord(c) for c in text)
            return [float((hash_val * (i + 1)) % 100) / 100.0 for i in range(384)]
        vector = model.encode(text, convert_to_numpy=True).tolist()
        return [float(x) for x in vector]

    @classmethod
    def embed_batch(cls, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = cls.get_model()
        vectors = model.encode(texts, convert_to_numpy=True).tolist()
        return [[float(x) for x in vec] for vec in vectors]
