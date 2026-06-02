from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.vector_store_service import VectorStoreService
from app.services.memory_service import MemoryService
from app.core.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are an analyst that answers questions strictly from provided transcript excerpts.

Rules:
- Answer only from the CONTEXT block below. Do not use prior knowledge.
- If the context does not contain enough evidence to answer, say exactly:
  "The available transcript data does not contain enough evidence to answer this question."
- Keep answers concise and factual.
- When referencing content, indicate whether it came from YouTube or Instagram.\
"""

CONTEXT_TEMPLATE = """\
CONTEXT (retrieved transcript excerpts):
{context}

CONVERSATION HISTORY:
{history}

QUESTION: {question}\
"""


def _excerpt(text: str, max_len: int = 120) -> str:
    text = text.strip()
    return text[:max_len] + "…" if len(text) > max_len else text


class RAGService:

    def __init__(self) -> None:
        self._settings = get_settings()
        self._vector_store = VectorStoreService()
        self._memory = MemoryService()

    def answer_question(
        self,
        question: str,
        session_id: str | None = None,
        filters: dict | None = None,
        k: int = 5,
    ) -> dict:
        if not question.strip():
            raise ValueError("question cannot be empty")

        session_id = self._memory.get_or_create(session_id)
        logger.info(
            "rag query  session=%s  question=%.80s  filters=%s",
            session_id, question, filters,
        )

        chunks = self._vector_store.similarity_search(question, k=k, filters=filters)
        if not chunks:
            logger.warning(
                "no chunks retrieved  session=%s  question=%.80s",
                session_id, question,
            )

        context_block = self._build_context_block(chunks)
        history_block = self._memory.format_history_for_prompt(session_id)

        prompt = CONTEXT_TEMPLATE.format(
            context=context_block or "(no relevant excerpts found)",
            history=history_block or "(no prior conversation)",
            question=question,
        )

        model = self._get_model()
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]

        logger.debug("invoking llm  session=%s", session_id)
        response = model.invoke(messages)
        answer: str = response.content.strip()

        self._memory.add_turn(session_id, "user", question)
        self._memory.add_turn(session_id, "assistant", answer)

        sources = [
            {
                "video_id": c["metadata"].get("video_id", ""),
                "source": c["metadata"].get("source", ""),
                "chunk_id": c["metadata"].get("chunk_id", ""),
                "title": c["metadata"].get("title", ""),
                "evidence": _excerpt(c["text"]),
                "score": c.get("score", 0.0),
            }
            for c in chunks
        ]

        logger.info(
            "rag answer  session=%s  sources=%d  answer_chars=%d",
            session_id, len(sources), len(answer),
        )

        return {
            "answer": answer,
            "sources": sources,
            "session_id": session_id,
        }

    def _get_model(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=self._settings.gemini_model,
            google_api_key=self._settings.gemini_api_key,
        )
        
    @staticmethod
    def _build_context_block(chunks: list[dict]) -> str:
        parts = []
        for i, chunk in enumerate(chunks, 1):
            m = chunk["metadata"]
            source = m.get("source", "unknown").upper()
            title = m.get("title", "")
            creator = m.get("creator", "")
            label = source
            if title:
                label += f" — {title}"
            if creator:
                label += f" by {creator}"
            parts.append(f"[{i}] {label}\n{chunk['text'].strip()}")
        return "\n\n".join(parts)
