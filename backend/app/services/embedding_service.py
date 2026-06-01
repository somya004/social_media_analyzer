from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_model(model_name: str) -> SentenceTransformer:
    logger.info("loading embedding model  name=%s", model_name)
    model = SentenceTransformer(model_name)
    logger.info("embedding model loaded  name=%s", model_name)
    return model


class EmbeddingService:

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def _model(self) -> SentenceTransformer:
        return _load_model(self._settings.embedding_model)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        logger.debug("embedding  count=%d", len(texts))
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        # BGE models produce better retrieval results when the query is
        # prefixed this way — it's part of the model's intended usage.
        prefixed = f"Represent this sentence for searching relevant passages: {query}"
        vectors = self._model.encode(
            [prefixed],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors[0].tolist()
