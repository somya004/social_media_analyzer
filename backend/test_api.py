"""
API route tests using FastAPI TestClient.

No real external calls are made. YouTubeService, InstagramService,
VectorStoreService, and RAGService are all patched at the service layer.

Usage:
    cd backend
    pytest test_api.py -v
    # or without pytest:
    python test_api.py
"""


import sys
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import app.services.analysis_service

# Shared fixtures


YOUTUBE_RESULT = {
    "video_id": "A",
    "source": "youtube",
    "title": "Test YouTube Video",
    "creator": "Test Creator",
    "upload_date": "2024-01-15",
    "duration": 600,
    "views": 500000,
    "likes": 12000,
    "hashtags": ["#test", "#video"],
    "thumbnail_url": "https://example.com/thumb.jpg",
    "transcript_chars": 4200,
    "chunks_stored": 7,
    "transcript_available": True,
}

INSTAGRAM_RESULT = {
    "video_id": "B",
    "source": "instagram",
    "shortcode": "TestCode123",
    "creator": "testcreator",
    "creator_full_name": "Test Creator",
    "followers": 85000,
    "upload_date": "2024-01-20T10:00:00.000Z",
    "duration": 30,
    "views": 220000,
    "likes": 18000,
    "comments": 340,
    "engagement_rate": 8.3364,
    "hashtags": ["#reel", "#test"],
    "thumbnail_url": "https://example.com/reel_thumb.jpg",
    "caption_chars": 480,
    "chunks_stored": 2,
    "caption_available": True,
}

RAG_RESULT = {
    "answer": "Based on the transcript, sleep improves memory consolidation.",
    "sources": [
        {
            "video_id": "A",
            "source": "youtube",
            "chunk_id": "abc123",
            "title": "Test YouTube Video",
            "evidence": "Sleep consolidates memories during REM phases.",
            "score": 0.87,
        }
    ],
    "session_id": "test-session-xyz",
}


# Helpers

def make_client():
    """
    Import and return a TestClient with AnalysisService and RAGService
    replaced by mocks. Import is deferred so patching happens before
    the module-level service instances in routes.py are created.
    """
    with (
        patch("app.services.analysis_service.YouTubeService"),
        patch("app.services.analysis_service.InstagramService"),
        patch("app.services.analysis_service.VectorStoreService"),
        patch("app.services.rag_service.VectorStoreService"),
        patch("app.services.rag_service.ChatGoogleGenerativeAI"),
    ):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)


def section(title: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {title}")
    print(f"{'─' * 62}")


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        raise AssertionError(f"Check failed: {label}")


# Tests

def test_health(client: TestClient) -> None:
    section("GET /api/health")
    resp = client.get("/api/health")
    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("status field is 'ok'", body.get("status") == "ok")
    check("gemini_model present", "gemini_model" in body)
    check("embedding_model present", "embedding_model" in body)
    check("chroma_collection present", "chroma_collection" in body)
    print(f"  Response: {json.dumps(body, indent=4)}")


def test_analyze_youtube_validation(client: TestClient) -> None:
    section("POST /api/analyze/youtube — input validation")

    # Missing url
    resp = client.post("/api/analyze/youtube", json={})
    check("missing url → 422", resp.status_code == 422)

    # Not a YouTube URL
    resp = client.post("/api/analyze/youtube", json={"url": "https://vimeo.com/123"})
    check("non-YouTube url → 422", resp.status_code == 422)

    # Empty video_id
    resp = client.post(
        "/api/analyze/youtube",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video_id": "  "},
    )
    check("blank video_id → 422", resp.status_code == 422)

    print("  All validation checks passed")


def test_analyze_youtube_success(client: TestClient) -> None:
    section("POST /api/analyze/youtube — success path")

    with patch("app.api.routes._analysis") as mock_svc:
        mock_svc.analyze_youtube.return_value = YOUTUBE_RESULT
        resp = client.post(
            "/api/analyze/youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video_id": "A"},
        )

    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("video_id is A", body["video_id"] == "A")
    check("source is youtube", body["source"] == "youtube")
    check("chunks_stored present", "chunks_stored" in body)
    check("transcript_available present", "transcript_available" in body)
    print(f"  Response: {json.dumps(body, indent=4)}")


def test_analyze_instagram_validation(client: TestClient) -> None:
    section("POST /api/analyze/instagram — input validation")

    resp = client.post("/api/analyze/instagram", json={})
    check("missing url → 422", resp.status_code == 422)

    resp = client.post("/api/analyze/instagram", json={"url": "https://tiktok.com/@user/video/123"})
    check("non-Instagram url → 422", resp.status_code == 422)

    resp = client.post(
        "/api/analyze/instagram",
        json={"url": "https://www.instagram.com/reel/TestCode123/", "video_id": ""},
    )
    check("empty video_id → 422", resp.status_code == 422)

    print("  All validation checks passed")


def test_analyze_instagram_success(client: TestClient) -> None:
    section("POST /api/analyze/instagram — success path")

    with patch("app.api.routes._analysis") as mock_svc:
        mock_svc.analyze_instagram.return_value = INSTAGRAM_RESULT
        resp = client.post(
            "/api/analyze/instagram",
            json={"url": "https://www.instagram.com/reel/TestCode123/", "video_id": "B"},
        )

    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("video_id is B", body["video_id"] == "B")
    check("source is instagram", body["source"] == "instagram")
    check("engagement_rate present", "engagement_rate" in body)
    check("caption_available present", "caption_available" in body)
    print(f"  Response: {json.dumps(body, indent=4)}")


def test_analyze_pair_validation(client: TestClient) -> None:
    section("POST /api/analyze/pair — input validation")

    resp = client.post("/api/analyze/pair", json={})
    check("missing both urls → 422", resp.status_code == 422)

    resp = client.post(
        "/api/analyze/pair",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "instagram_url": "https://tiktok.com/@user/video/123",
        },
    )
    check("bad instagram_url → 422", resp.status_code == 422)

    resp = client.post(
        "/api/analyze/pair",
        json={
            "youtube_url": "https://vimeo.com/123",
            "instagram_url": "https://www.instagram.com/reel/TestCode123/",
        },
    )
    check("bad youtube_url → 422", resp.status_code == 422)

    print("  All validation checks passed")


def test_analyze_pair_success(client: TestClient) -> None:
    section("POST /api/analyze/pair — success path")

    pair_result = {"youtube": YOUTUBE_RESULT, "instagram": INSTAGRAM_RESULT}

    with patch("app.api.routes._analysis") as mock_svc:
        mock_svc.analyze_pair.return_value = pair_result
        resp = client.post(
            "/api/analyze/pair",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "instagram_url": "https://www.instagram.com/reel/TestCode123/",
            },
        )

    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("youtube key present", "youtube" in body)
    check("instagram key present", "instagram" in body)
    check("youtube.source is youtube", body["youtube"]["source"] == "youtube")
    check("instagram.source is instagram", body["instagram"]["source"] == "instagram")
    print(f"  youtube.chunks_stored: {body['youtube']['chunks_stored']}")
    print(f"  instagram.chunks_stored: {body['instagram']['chunks_stored']}")


def test_chat_validation(client: TestClient) -> None:
    section("POST /api/chat — input validation")

    resp = client.post("/api/chat", json={})
    check("missing question → 422", resp.status_code == 422)

    resp = client.post("/api/chat", json={"question": "   "})
    check("blank question → 422", resp.status_code == 422)

    print("  All validation checks passed")


def test_chat_success(client: TestClient) -> None:
    section("POST /api/chat — success path")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.answer_question.return_value = RAG_RESULT
        resp = client.post(
            "/api/chat",
            json={
                "question": "What does the transcript say about sleep?",
                "session_id": "test-session-xyz",
            },
        )

    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("answer present", bool(body.get("answer")))
    check("sources is a list", isinstance(body.get("sources"), list))
    check("session_id present", bool(body.get("session_id")))

    if body["sources"]:
        src = body["sources"][0]
        check("source has video_id", bool(src.get("video_id")))
        check("source has source field", bool(src.get("source")))
        check("source has chunk_id", bool(src.get("chunk_id")))
        check("source has evidence", bool(src.get("evidence")))
        check("score in [0,1]", 0.0 <= src.get("score", -1) <= 1.0)

    print(f"  Answer  : {body['answer']}")
    print(f"  Sources : {len(body['sources'])}")
    print(f"  Session : {body['session_id']}")


def test_chat_no_session(client: TestClient) -> None:
    section("POST /api/chat — session_id is optional")

    result_no_session = {**RAG_RESULT, "session_id": "new-auto-session"}

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.answer_question.return_value = result_no_session
        resp = client.post(
            "/api/chat",
            json={"question": "Tell me about the video content."},
        )

    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("session_id assigned", bool(body.get("session_id")))
    print(f"  Auto-assigned session_id: {body['session_id']}")


def test_analysis_error_propagation(client: TestClient) -> None:
    section("Error propagation — AnalysisError surfaces as HTTP error")
    from app.services.analysis_service import AnalysisError

    with patch("app.api.routes._analysis") as mock_svc:
        mock_svc.analyze_youtube.side_effect = AnalysisError(
            "Cannot extract video ID from: 'not-a-url'", status_code=422
        )
        resp = client.post(
            "/api/analyze/youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )

    check("AnalysisError 422 → HTTP 422", resp.status_code == 422)
    body = resp.json()
    check("detail message present", bool(body.get("detail")))
    print(f"  Error detail: {body['detail']}")


# Runner

def run_all() -> None:
    print("\nAPI route tests")
    print("=" * 62)

    client = make_client()

    tests = [
        test_health,
        test_analyze_youtube_validation,
        test_analyze_youtube_success,
        test_analyze_instagram_validation,
        test_analyze_instagram_success,
        test_analyze_pair_validation,
        test_analyze_pair_success,
        test_chat_validation,
        test_chat_success,
        test_chat_no_session,
        test_analysis_error_propagation,
    ]

    failed = 0
    for test_fn in tests:
        try:
            test_fn(client)
        except AssertionError as exc:
            print(f"\n  FAILED: {exc}")
            failed += 1
        except Exception as exc:
            import traceback
            print(f"\n  ERROR in {test_fn.__name__}: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 62)
    if failed:
        print(f"  {failed} test(s) FAILED.")
        sys.exit(1)
    else:
        print(f"  All {len(tests)} tests passed.")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    run_all()
