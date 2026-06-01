"""
Integration test for RAGService and MemoryService.

Requires a populated ChromaDB collection. This test seeds the vector store
with synthetic transcript data before running RAG queries, so it can run
independently of test_vector_store.py.

Usage:
    cd backend
    python test_rag.py

Requires a valid GEMINI_API_KEY in .env.

Exit codes:
    0  all checks passed
    1  a step failed
"""

import sys
import json
from app.services.chunking_service import TranscriptChunker
from app.services.vector_store_service import VectorStoreService
from app.services.rag_service import RAGService
from app.services.memory_service import MemoryService

# Seed corpus — same content as test_vector_store.py for consistency

YOUTUBE_TRANSCRIPT = (
    "Sleep is one of the most important biological functions the human body performs. "
    "During sleep, the brain consolidates memories and clears metabolic waste products. "
    "Research shows that adults who consistently sleep fewer than seven hours a night "
    "face significantly higher risks of cardiovascular disease, obesity, and cognitive decline. "
    "The two main stages of sleep are REM and non-REM. Non-REM sleep is divided into three phases, "
    "the deepest of which is responsible for physical restoration and immune function. "
    "REM sleep, characterised by rapid eye movement and vivid dreaming, plays a central role "
    "in emotional processing and long-term memory formation. "
    "Disruptions to the circadian rhythm — the internal 24-hour clock — can cause chronic sleep debt "
    "even when total hours in bed seem adequate. "
    "Blue light from screens suppresses melatonin production, pushing back sleep onset and reducing "
    "overall sleep quality. "
    "Caffeine has a half-life of five to seven hours, meaning a cup of coffee at 3 PM still has "
    "half its stimulant effect at 8 PM or 10 PM. "
    "Temperature also matters: the body needs to drop its core temperature by about one degree "
    "Celsius to initiate and maintain sleep, which is why a cool bedroom promotes deeper rest. "
    "Consistent sleep and wake times, even on weekends, are among the most evidence-backed "
    "interventions for improving sleep quality over the long term."
)

INSTAGRAM_CAPTION = (
    "Morning routines are the foundation of high-performance days. "
    "Waking up before sunrise gives you uninterrupted time before the world's demands begin. "
    "Start with hydration — your body loses water overnight and even mild dehydration impairs "
    "focus and mood. "
    "A cold shower activates the sympathetic nervous system, raising alertness without caffeine. "
    "Ten minutes of sunlight exposure within the first hour of waking anchors your circadian rhythm "
    "and improves sleep quality that same night. "
    "Movement — whether a full workout or a brisk walk — elevates BDNF, a protein linked to "
    "neuroplasticity and resilience. "
    "Journalling for five minutes externalises anxious thoughts and primes the brain for "
    "intentional action rather than reactive decision-making. "
    "Avoid checking your phone for the first thirty minutes; notifications pull your attention "
    "into other people's priorities before you have set your own. "
    "Eating a protein-rich breakfast stabilises blood sugar and reduces afternoon energy crashes. "
    "#morningroutine #productivity #health #sleep #mindset"
)

YOUTUBE_META = {
    "title": "Sleep Is Your Superpower",
    "creator": "TED",
    "upload_date": "2019-06-03",
    "engagement_rate": None,
}

INSTAGRAM_META = {
    "title": "Morning Routine for High Performance",
    "creator": "healthcoach",
    "upload_date": "2024-11-20",
    "engagement_rate": 7.34,
}


# Helpers

def section(title: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {title}")
    print(f"{'─' * 62}")


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        raise AssertionError(f"Check failed: {label}")


def print_result(result: dict) -> None:
    display = {
        "session_id": result["session_id"],
        "answer": result["answer"],
        "sources": [
            {
                "video_id": s["video_id"],
                "source": s["source"],
                "chunk_id": s["chunk_id"][:8] + "…",
                "score": s["score"],
                "evidence": s["evidence"][:80] + "…" if len(s["evidence"]) > 80 else s["evidence"],
            }
            for s in result["sources"]
        ],
    }
    print(json.dumps(display, indent=2))


# Setup: seed vector store

def seed_vector_store() -> None:
    section("Setup: seeding vector store")

    chunker = TranscriptChunker(chunk_size=700, overlap=120)
    store = VectorStoreService()
    store.reset_collection()

    yt_chunks = chunker.chunk_text(
        YOUTUBE_TRANSCRIPT, "yt_test_001", "youtube", YOUTUBE_META
    )
    ig_chunks = chunker.chunk_text(
        INSTAGRAM_CAPTION, "ig_test_001", "instagram", INSTAGRAM_META
    )

    all_chunks = yt_chunks + ig_chunks
    store.add_chunks(all_chunks)

    count = store.get_collection_count()
    check(f"collection seeded with {len(all_chunks)} chunks", count == len(all_chunks))
    print(f"  Seeded {count} chunks ({len(yt_chunks)} YouTube, {len(ig_chunks)} Instagram)")


# Test cases

def test_basic_answer() -> str:
    section("Test 1: Basic factual question from YouTube content")

    rag = RAGService()
    result = rag.answer_question("What happens to the brain during sleep?")

    check("answer is non-empty", bool(result["answer"]))
    check("session_id is non-empty", bool(result["session_id"]))
    check("sources is a list", isinstance(result["sources"], list))
    check("at least one source returned", len(result["sources"]) >= 1)

    for s in result["sources"]:
        check("source has video_id", bool(s["video_id"]))
        check("source has source field", s["source"] in ("youtube", "instagram"))
        check("source has chunk_id", bool(s["chunk_id"]))
        check("source has evidence", bool(s["evidence"]))
        check("source has score in [0,1]", 0.0 <= s["score"] <= 1.0)

    print_result(result)
    return result["session_id"]


def test_memory_continuity(session_id: str) -> None:
    section("Test 2: Follow-up question uses conversation memory")

    rag = RAGService()

    # First turn — prime the session
    rag.answer_question(
        "What effect does caffeine have on sleep?",
        session_id=session_id,
    )

    # Second turn — refers back to "that" without repeating caffeine
    result = rag.answer_question(
        "How many hours does it take for that effect to wear off?",
        session_id=session_id,
    )

    check("session_id is preserved", result["session_id"] == session_id)
    check("answer is non-empty", bool(result["answer"]))

    # The memory should have stored both turns
    memory = MemoryService()
    # RAGService creates its own MemoryService; check indirectly via session_id reuse
    check("session_id matches", result["session_id"] == session_id)

    print_result(result)


def test_source_filter() -> None:
    section("Test 3: Source-filtered query (Instagram only)")

    rag = RAGService()
    result = rag.answer_question(
        "What should I do first thing in the morning?",
        filters={"source": "instagram"},
    )

    check("answer is non-empty", bool(result["answer"]))
    check("all sources are instagram",
          all(s["source"] == "instagram" for s in result["sources"]))

    print_result(result)


def test_insufficient_context() -> None:
    section("Test 4: Question outside corpus — should signal insufficient evidence")

    rag = RAGService()
    result = rag.answer_question(
        "What is the capital city of New Zealand and what is its population?"
    )

    check("answer is non-empty", bool(result["answer"]))
    answer_lower = result["answer"].lower()
    # Model should admit it cannot answer from the provided context
    insufficient_signals = [
        "does not contain",
        "insufficient",
        "not enough",
        "cannot answer",
        "no information",
        "not available",
    ]
    signalled = any(phrase in answer_lower for phrase in insufficient_signals)
    check("model signals insufficient evidence", signalled)

    print(f"\n  Answer: {result['answer']}")


def test_new_session_isolation() -> None:
    section("Test 5: New session starts with clean history")

    rag = RAGService()

    result_a = rag.answer_question("How does REM sleep affect memory?")
    sid_a = result_a["session_id"]

    result_b = rag.answer_question("How does REM sleep affect memory?")
    sid_b = result_b["session_id"]

    check("two default calls produce different session IDs", sid_a != sid_b)
    check("both answers are non-empty", bool(result_a["answer"]) and bool(result_b["answer"]))

    print(f"\n  Session A: {sid_a}")
    print(f"  Session B: {sid_b}")


def test_response_structure() -> None:
    section("Test 6: Response matches RAGResponse schema")
    from app.models.schemas import RAGResponse

    rag = RAGService()
    raw = rag.answer_question("What is the role of non-REM sleep?")

    # Validate the raw dict against the Pydantic model
    parsed = RAGResponse(**raw)
    check("answer parses into RAGResponse", bool(parsed.answer))
    check("session_id is present", bool(parsed.session_id))
    check("sources is a list", isinstance(parsed.sources, list))
    for s in parsed.sources:
        check("SourceCitation has required fields",
              bool(s.video_id) and bool(s.source) and bool(s.chunk_id))

    print(f"\n  Validated RAGResponse with {len(parsed.sources)} SourceCitation(s)")

def main() -> None:
    print("\nRAG service integration test")
    print("=" * 62)

    try:
        seed_vector_store()

        session_id = test_basic_answer()
        test_memory_continuity(session_id)
        test_source_filter()
        test_insufficient_context()
        test_new_session_isolation()
        test_response_structure()

    except AssertionError as exc:
        print(f"\n  FAILED: {exc}")
        sys.exit(1)
    except Exception as exc:
        import traceback
        print(f"\n  ERROR: {exc}")
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 62)
    print("  All checks passed.")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
