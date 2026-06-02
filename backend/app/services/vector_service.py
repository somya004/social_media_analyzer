import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.models.schemas import EmbeddedChunk
from app.core.config import settings


def _get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def store(chunks: list[EmbeddedChunk]) -> str:
    session_id = str(uuid.uuid4())
    client = _get_client()
    collection = client.get_or_create_collection(session_id)

    collection.add(
        ids=[str(uuid.uuid4()) for _ in chunks],
        embeddings=[c.embedding for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
    )

    return session_id


def query(session_id: str, embedding: list[float], n_results: int = 5) -> list[dict]:
    client = _get_client()
    collection = client.get_collection(session_id)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {"text": doc, "metadata": meta, "score": 1 - dist}
        for doc, meta, dist in zip(docs, metas, distances)
    ]
