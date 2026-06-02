"""
Tests for POST /api/chat/stream SSE endpoint.

No real Gemini, ChromaDB, or extraction calls are made. The RAGService
is patched to produce a predictable async stream.

Usage:
    cd backend
    python test_streaming.py

    # or with pytest:
    pytest test_streaming.py -v

Exit codes:
    0  all checks passed
    1  a check failed
"""

import sys
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock


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


def make_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def parse_sse_events(raw: bytes) -> list[dict]:
    """
    Parse a raw SSE byte stream into a list of {event, data} dicts.
    Handles multi-line blocks separated by blank lines.
    """
    events = []
    current: dict = {}
    for line in raw.decode().splitlines():
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            raw_data = line[len("data:"):].strip()
            try:
                current["data"] = json.loads(raw_data)
            except json.JSONDecodeError:
                current["data"] = raw_data
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


# Fake stream generator

FAKE_SESSION_ID = "stream-test-session-abc123"
FAKE_TOKENS = ["Sleep ", "improves ", "memory ", "consolidation."]
FAKE_SOURCES = [
    {
        "video_id": "A",
        "source": "youtube",
        "chunk_id": "chunk-xyz",
        "title": "Sleep Is Your Superpower",
        "evidence": "REM sleep plays a central role in memory formation.",
        "score": 0.91,
    }
]


async def fake_stream_answer(question, session_id=None, filters=None, k=5):
    """Mimics RAGService.stream_answer output without calling Gemini."""
    yield make_sse("start", {"session_id": FAKE_SESSION_ID})
    for token in FAKE_TOKENS:
        yield make_sse("token", {"token": token})
    yield make_sse("sources", {"sources": FAKE_SOURCES})
    yield make_sse("done", {"session_id": FAKE_SESSION_ID, "answer_chars": 35})


async def fake_stream_error(question, session_id=None, filters=None, k=5):
    """Mimics a stream that errors after the start event."""
    yield make_sse("start", {"session_id": FAKE_SESSION_ID})
    yield make_sse("error", {"message": "Retrieval failed: connection refused"})


# Client factory

def make_client():
    with (
        patch("app.services.analysis_service.YouTubeService"),
        patch("app.services.analysis_service.InstagramService"),
        patch("app.services.analysis_service.VectorStoreService"),
        patch("app.services.rag_service.VectorStoreService"),
        patch("app.services.rag_service.ChatGoogleGenerativeAI"),
    ):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)


# Tests
def test_stream_status_and_content_type(client) -> None:
    section("Test 1: HTTP 200 and content-type: text/event-stream")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = fake_stream_answer
        resp = client.post(
            "/api/chat/stream",
            json={"question": "What does the transcript say about sleep?"},
        )

    check("status 200", resp.status_code == 200)
    check(
        "content-type is text/event-stream",
        "text/event-stream" in resp.headers.get("content-type", ""),
    )
    print(f"  content-type: {resp.headers.get('content-type')}")


def test_stream_event_sequence(client) -> None:
    section("Test 2: Event sequence — start → token(s) → sources → done")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = fake_stream_answer
        resp = client.post(
            "/api/chat/stream",
            json={"question": "How does REM sleep affect memory?"},
        )

    events = parse_sse_events(resp.content)
    event_types = [e["event"] for e in events]

    print(f"  Events received: {event_types}")

    check("at least 4 events", len(events) >= 4)
    check("first event is 'start'", events[0]["event"] == "start")
    check("last event is 'done'", events[-1]["event"] == "done")
    check("has at least one 'token' event", "token" in event_types)
    check("has 'sources' event", "sources" in event_types)

    # Verify there is no 'error' event in a clean stream
    check("no error event in clean stream", "error" not in event_types)


def test_stream_start_event_payload(client) -> None:
    section("Test 3: 'start' event contains session_id")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = fake_stream_answer
        resp = client.post(
            "/api/chat/stream",
            json={"question": "Any question", "session_id": "my-session"},
        )

    events = parse_sse_events(resp.content)
    start = next(e for e in events if e["event"] == "start")

    check("start.data has session_id", "session_id" in start["data"])
    print(f"  start.session_id: {start['data']['session_id']}")


def test_stream_token_events(client) -> None:
    section("Test 4: 'token' events carry non-empty text")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = fake_stream_answer
        resp = client.post(
            "/api/chat/stream",
            json={"question": "What are the stages of sleep?"},
        )

    events = parse_sse_events(resp.content)
    token_events = [e for e in events if e["event"] == "token"]

    check("at least one token event", len(token_events) >= 1)
    check("every token has non-empty text",
          all(bool(e["data"].get("token", "").strip()) for e in token_events))

    reconstructed = "".join(e["data"]["token"] for e in token_events)
    check("reconstructed answer is non-empty", bool(reconstructed.strip()))
    print(f"  Token count    : {len(token_events)}")
    print(f"  Reconstructed  : {reconstructed!r}")


def test_stream_sources_event(client) -> None:
    section("Test 5: 'sources' event contains citation list")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = fake_stream_answer
        resp = client.post(
            "/api/chat/stream",
            json={"question": "Tell me about sleep stages"},
        )

    events = parse_sse_events(resp.content)
    sources_event = next((e for e in events if e["event"] == "sources"), None)

    check("sources event present", sources_event is not None)
    sources = sources_event["data"]["sources"]
    check("sources is a list", isinstance(sources, list))
    check("at least one source", len(sources) >= 1)

    first = sources[0]
    check("source has video_id", bool(first.get("video_id")))
    check("source has source field", first.get("source") in ("youtube", "instagram"))
    check("source has chunk_id", bool(first.get("chunk_id")))
    check("source has evidence", bool(first.get("evidence")))
    check("source has score", "score" in first)

    print(f"  Sources: {len(sources)}")
    print(f"  First source: video_id={first['video_id']}  score={first['score']}")


def test_stream_done_event(client) -> None:
    section("Test 6: 'done' event is the final event and has session_id")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = fake_stream_answer
        resp = client.post(
            "/api/chat/stream",
            json={"question": "What is the role of melatonin in sleep?"},
        )

    events = parse_sse_events(resp.content)
    check("last event is 'done'", events[-1]["event"] == "done")

    done = events[-1]
    check("done.data has session_id", "session_id" in done["data"])
    check("done.data has answer_chars", "answer_chars" in done["data"])
    print(f"  done.session_id  : {done['data']['session_id']}")
    print(f"  done.answer_chars: {done['data']['answer_chars']}")


def test_stream_validation_error(client) -> None:
    section("Test 7: Empty question → 422 before stream starts")

    resp = client.post("/api/chat/stream", json={"question": "  "})
    check("blank question → 422", resp.status_code == 422)
    print(f"  detail: {resp.json().get('detail')}")


def test_stream_missing_question(client) -> None:
    section("Test 8: Missing question field → 422")

    resp = client.post("/api/chat/stream", json={})
    check("missing question → 422", resp.status_code == 422)


def test_stream_error_event(client) -> None:
    section("Test 9: Service error produces 'error' event in stream")

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = fake_stream_error
        resp = client.post(
            "/api/chat/stream",
            json={"question": "What does sleep do?"},
        )

    # The response itself is 200 because the stream started; the error
    # is communicated inside the event stream.
    check("status 200 (stream opened)", resp.status_code == 200)
    events = parse_sse_events(resp.content)
    event_types = [e["event"] for e in events]

    check("error event present", "error" in event_types)
    error_event = next(e for e in events if e["event"] == "error")
    check("error has message", bool(error_event["data"].get("message")))
    print(f"  error.message: {error_event['data']['message']}")


def test_stream_session_id_forwarded(client) -> None:
    section("Test 10: Provided session_id is forwarded to stream_answer")

    call_args = {}

    async def capturing_stream(question, session_id=None, filters=None, k=5):
        call_args["session_id"] = session_id
        async for event in fake_stream_answer(question, session_id, filters, k):
            yield event

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.stream_answer = capturing_stream
        client.post(
            "/api/chat/stream",
            json={"question": "Any question", "session_id": "forwarded-session-123"},
        )

    check("session_id forwarded correctly", call_args.get("session_id") == "forwarded-session-123")
    print(f"  Forwarded session_id: {call_args.get('session_id')}")


def test_non_streaming_chat_still_works(client) -> None:
    section("Test 11: POST /chat (non-streaming) still returns JSON")

    rag_result = {
        "answer": "Sleep consolidates memory.",
        "sources": [],
        "session_id": "non-stream-session",
    }

    with patch("app.api.routes._rag") as mock_rag:
        mock_rag.answer_question.return_value = rag_result
        resp = client.post(
            "/api/chat",
            json={"question": "What does sleep do for memory?"},
        )

    check("status 200", resp.status_code == 200)
    body = resp.json()
    check("answer present", bool(body.get("answer")))
    check("session_id present", bool(body.get("session_id")))
    check("content-type is application/json",
          "application/json" in resp.headers.get("content-type", ""))
    print(f"  answer    : {body['answer']}")
    print(f"  session_id: {body['session_id']}")


# Runner
def run_all() -> None:
    print("\nStreaming endpoint tests")
    print("=" * 62)

    client = make_client()

    tests = [
        test_stream_status_and_content_type,
        test_stream_event_sequence,
        test_stream_start_event_payload,
        test_stream_token_events,
        test_stream_sources_event,
        test_stream_done_event,
        test_stream_validation_error,
        test_stream_missing_question,
        test_stream_error_event,
        test_stream_session_id_forwarded,
        test_non_streaming_chat_still_works,
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
