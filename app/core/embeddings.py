"""
app/core/embeddings.py
──────────────────────
Singleton HuggingFace embedding model.

The model is loaded ONCE when this module is first imported and reused
across all requests. This avoids reloading a ~90MB model on every
upload/query call, which would be catastrophically slow.
"""

import logging
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings
from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load and cache the HuggingFace sentence-transformer embedding model.
    
    The @lru_cache(maxsize=1) decorator ensures this function is executed
    only once per process lifetime — subsequent calls return the cached instance.

    Returns:
        HuggingFaceEmbeddings: The shared embedding model instance.
    """
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
    model = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("Embedding model loaded and cached successfully.")
    return model
