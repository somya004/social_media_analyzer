import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.services.chunking_service import TextChunk
from app.services.embedding_service import EmbeddingService
from app.core.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStoreService:

    def __init__(self) -> None:
        self._settings = get_settings()
        self._embedder = EmbeddingService()
        self._client: chromadb.ClientAPI | None = None

    # ---------------------------------------------------------------------- #
    # Client + collection
    # ---------------------------------------------------------------------- #

    def _get_client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self._settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def create_collection(self) -> chromadb.Collection:
        client = self._get_client()
        collection = client.get_or_create_collection(
            name=self._settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "collection ready  name=%s  count=%d",
            self._settings.chroma_collection_name,
            collection.count(),
        )
        return collection

    def reset_collection(self) -> None:
        client = self._get_client()
        name = self._settings.chroma_collection_name
        try:
            client.delete_collection(name)
            logger.info("collection deleted  name=%s", name)
        except Exception:
            pass  # didn't exist; nothing to do
        client.create_collection(name, metadata={"hnsw:space": "cosine"})
        logger.info("collection recreated  name=%s", name)

    def get_collection_count(self) -> int:
        return self.create_collection().count()

    # ---------------------------------------------------------------------- #
    # Write
    # ---------------------------------------------------------------------- #

    def add_chunks(self, chunks: list[TextChunk]) -> None:
        if not chunks:
            return

        collection = self.create_collection()
        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_texts(texts)

        ids = [c.chunk_id for c in chunks]
        metadatas = [self._build_metadata(c) for c in chunks]

        # Chroma has a hard limit of 41_665 items per add call; batch to be safe.
        batch_size = 500
        for i in range(0, len(chunks), batch_size):
            batch_slice = slice(i, i + batch_size)
            collection.add(
                ids=ids[batch_slice],
                embeddings=embeddings[batch_slice],
                documents=texts[batch_slice],
                metadatas=metadatas[batch_slice],
            )

        logger.info(
            "stored chunks  count=%d  collection=%s",
            len(chunks),
            self._settings.chroma_collection_name,
        )

    # ---------------------------------------------------------------------- #
    # Read
    # ---------------------------------------------------------------------- #

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        collection = self.create_collection()
        query_embedding = self._embedder.embed_query(query)

        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": min(k, collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if filters:
            kwargs["where"] = filters

        results = collection.query(**kwargs)

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        # Chroma returns cosine distance (0=identical, 2=opposite).
        # Convert to similarity score in [0, 1].
        distances = results["distances"][0]

        return [
            {
                "text": doc,
                "metadata": meta,
                "score": round(1 - (dist / 2), 4),
            }
            for doc, meta, dist in zip(docs, metas, distances)
        ]

    # ---------------------------------------------------------------------- #
    # Helpers
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _build_metadata(chunk: TextChunk) -> dict:
        # Chroma metadata values must be str, int, float, or bool.
        # Pull promoted fields out of chunk.metadata for indexed filtering.
        m = chunk.metadata

        def _str(v) -> str:
            return str(v) if v is not None else ""

        def _float_or_none(v) -> float | None:
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        base = {
            "chunk_id": chunk.chunk_id,
            "video_id": chunk.video_id,
            "source": chunk.source,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "title": _str(m.get("title")),
            "creator": _str(m.get("creator")),
            "upload_date": _str(m.get("upload_date")),
        }

        engagement_rate = _float_or_none(m.get("engagement_rate"))
        if engagement_rate is not None:
            base["engagement_rate"] = engagement_rate

        return base
