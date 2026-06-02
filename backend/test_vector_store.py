"""
Integration test for chunking, embedding, and vector storage.

Usage:
    cd backend
    python test_vector_store.py

Requires:
    - pip install -r requirements.txt
    - .env file with any values for GEMINI_API_KEY and APIFY_API_TOKEN
      (those services are not called by this test)

Exit codes:
    0  all assertions passed
    1  a step failed
"""

import sys
import json
from app.services.chunking_service import TranscriptChunker, TextChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService

# --------------------------------------------------------------------------- #
# Sample content — two sources, distinct topics so similarity search is meaningful
# --------------------------------------------------------------------------- #

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
    "The goal is not perfection but consistency — even a compressed fifteen-minute version of "
    "this routine beats having no intentional morning at all. "
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


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def section(title: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {title}")
    print(f"{'─' * 62}")


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        raise AssertionError(f"Check failed: {label}")


# --------------------------------------------------------------------------- #
# Test steps
# --------------------------------------------------------------------------- #

def test_chunking() -> tuple[list[TextChunk], list[TextChunk]]:
    section("Step 1: Chunking")
    chunker = TranscriptChunker(chunk_size=700, overlap=120)

    yt_chunks = chunker.chunk_text(
        text=YOUTUBE_TRANSCRIPT,
        video_id="yt_test_001",
        source="youtube",
        metadata=YOUTUBE_META,
    )
    ig_chunks = chunker.chunk_text(
        text=INSTAGRAM_CAPTION,
        video_id="ig_test_001",
        source="instagram",
        metadata=INSTAGRAM_META,
    )

    check("YouTube text produced chunks", len(yt_chunks) > 0)
    check("Instagram text produced chunks", len(ig_chunks) > 0)
    check("each chunk has a chunk_id", all(c.chunk_id for c in yt_chunks + ig_chunks))
    check("each chunk has non-empty text", all(c.text for c in yt_chunks + ig_chunks))
    check("start_char < end_char for all chunks", all(c.start_char < c.end_char for c in yt_chunks + ig_chunks))
    check("no chunk exceeds chunk_size + overlap", all(len(c.text) <= 820 for c in yt_chunks + ig_chunks))
    check("source field set correctly on yt", all(c.source == "youtube" for c in yt_chunks))
    check("source field set correctly on ig", all(c.source == "instagram" for c in ig_chunks))
    check("metadata preserved", yt_chunks[0].metadata.get("creator") == "TED")

    print(f"\n  YouTube  : {len(yt_chunks)} chunks")
    for c in yt_chunks:
        print(f"    [{c.start_char:>5} – {c.end_char:<5}]  {len(c.text):>4} chars  {c.text[:60]!r}…")
    print(f"\n  Instagram: {len(ig_chunks)} chunks")
    for c in ig_chunks:
        print(f"    [{c.start_char:>5} – {c.end_char:<5}]  {len(c.text):>4} chars  {c.text[:60]!r}…")

    return yt_chunks, ig_chunks


def test_embeddings(chunks: list[TextChunk]) -> None:
    section("Step 2: Embeddings")
    embedder = EmbeddingService()

    texts = [c.text for c in chunks[:3]]
    vectors = embedder.embed_texts(texts)

    check("returned one vector per text", len(vectors) == len(texts))
    check("vector is a list of floats", isinstance(vectors[0], list) and isinstance(vectors[0][0], float))
    check("vector dimension > 0", len(vectors[0]) > 0)

    # BGE-small-en-v1.5 produces 384-dimensional vectors
    check("BGE-small vector dimension is 384", len(vectors[0]) == 384)

    # Normalised vectors should have unit magnitude (sum of squares ≈ 1)
    magnitude = sum(v ** 2 for v in vectors[0]) ** 0.5
    check("embedding is unit-normalised", abs(magnitude - 1.0) < 1e-3)

    query_vec = embedder.embed_query("how does sleep affect memory?")
    check("query embedding is a list of floats", isinstance(query_vec, list))
    check("query embedding dimension matches", len(query_vec) == 384)

    print(f"\n  Embedded {len(texts)} texts")
    print(f"  Vector dimension : {len(vectors[0])}")
    print(f"  Sample magnitude : {magnitude:.6f}")


def test_vector_store(all_chunks: list[TextChunk]) -> None:
    section("Step 3: Vector store — ingest")
    store = VectorStoreService()

    # Start clean so the test is repeatable
    store.reset_collection()
    check("collection empty after reset", store.get_collection_count() == 0)

    store.add_chunks(all_chunks)
    count = store.get_collection_count()

    check("collection count > 0 after add", count > 0)
    check("collection count matches chunk count", count == len(all_chunks))

    print(f"\n  Stored {count} vectors")

    section("Step 4: Similarity search — broad query")
    results = store.similarity_search("sleep and memory consolidation", k=5)

    check("search returns at least 1 result", len(results) >= 1)
    check("each result has 'text' key", all("text" in r for r in results))
    check("each result has 'metadata' key", all("metadata" in r for r in results))
    check("each result has 'score' key", all("score" in r for r in results))
    check("scores are in [0, 1]", all(0.0 <= r["score"] <= 1.0 for r in results))
    check("metadata contains video_id", all(r["metadata"].get("video_id") for r in results))
    check("metadata contains source", all(r["metadata"].get("source") for r in results))
    check("metadata contains chunk_id", all(r["metadata"].get("chunk_id") for r in results))

    print(f"\n  Query   : 'sleep and memory consolidation'")
    print(f"  Results : {len(results)}")
    for i, r in enumerate(results, 1):
        m = r["metadata"]
        print(
            f"  [{i}] score={r['score']:.4f}  source={m['source']:10}  "
            f"video_id={m['video_id']:12}  {r['text'][:70]!r}…"
        )

    section("Step 5: Similarity search — source filter")
    ig_results = store.similarity_search(
        "morning routine and productivity",
        k=3,
        filters={"source": "instagram"},
    )

    check("filtered search returns results", len(ig_results) >= 1)
    check("all filtered results are instagram", all(r["metadata"]["source"] == "instagram" for r in ig_results))

    print(f"\n  Query   : 'morning routine and productivity'  filter: source=instagram")
    print(f"  Results : {len(ig_results)}")
    for i, r in enumerate(ig_results, 1):
        m = r["metadata"]
        print(
            f"  [{i}] score={r['score']:.4f}  creator={m['creator']:12}  "
            f"upload_date={m['upload_date']}  {r['text'][:70]!r}…"
        )

    section("Step 6: Metadata in results")
    top = results[0]["metadata"]
    print(f"\n  Top result metadata:")
    print(json.dumps(top, indent=4))

    check("engagement_rate present for instagram result" ,
          any(
              "engagement_rate" in r["metadata"]
              for r in ig_results
          ))


# Entry point

def main() -> None:
    print("\nVector store integration test")
    print("=" * 62)

    try:
        yt_chunks, ig_chunks = test_chunking()
        all_chunks = yt_chunks + ig_chunks

        test_embeddings(all_chunks)
        test_vector_store(all_chunks)

    except AssertionError as exc:
        print(f"\n  FAILED: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 62)
    print("  All checks passed.")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
