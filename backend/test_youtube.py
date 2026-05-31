"""
Quick smoke test for YouTubeService.
Run from the backend/ directory:
    python test_youtube.py [youtube_url]
"""

import sys
import json
from dataclasses import asdict
from app.services.youtube_service import (
    YouTubeService,
    YouTubeExtractionError,
    InvalidYouTubeURL,
    VideoNotAvailable,
    TranscriptNotAvailable,
)

DEFAULT_URL = "https://www.youtube.com/watch?v=5MuIMqhT8DM"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    service = YouTubeService()

    print(f"\nExtracting: {url}\n{'-' * 60}")

    try:
        data = service.get_video_data(url)
    except InvalidYouTubeURL as exc:
        print(f"[InvalidYouTubeURL] {exc}")
        sys.exit(1)
    except VideoNotAvailable as exc:
        print(f"[VideoNotAvailable] {exc}")
        sys.exit(1)
    except YouTubeExtractionError as exc:
        print(f"[ExtractionError] {exc}")
        sys.exit(1)

    m = data.metadata
    t = data.transcript

    print("METADATA")
    print(f"  video_id    : {m.video_id}")
    print(f"  title       : {m.title}")
    print(f"  creator     : {m.creator}")
    print(f"  upload_date : {m.upload_date}")
    print(f"  duration    : {m.duration}s")
    print(f"  views       : {m.views:,}")
    print(f"  likes       : {m.likes if m.likes is not None else 'hidden'}")
    print(f"  hashtags    : {m.hashtags}")
    print(f"  description : {m.description[:120]}{'...' if len(m.description) > 120 else ''}")

    print("\nTRANSCRIPT")
    print(f"  language    : {t.language or 'n/a'}")
    print(f"  segments    : {len(t.segments)}")
    print(f"  total chars : {len(t.full_text):,}")
    if t.segments:
        first = t.segments[0]
        print(f"  first seg   : [{first.start:.1f}s] {first.text!r}")

    print("\nFULL STRUCTURE (truncated)")
    doc = asdict(data)
    doc["transcript"]["full_text"] = doc["transcript"]["full_text"][:200] + "..."
    doc["transcript"]["segments"] = doc["transcript"]["segments"][:2]
    print(json.dumps(doc, indent=2))


if __name__ == "__main__":
    main()
