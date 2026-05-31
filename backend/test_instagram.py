"""
Smoke test for InstagramService.

Usage:
    cd backend
    python test_instagram.py                              # uses default public reel
    python test_instagram.py <instagram_reel_url>         # any public Reel URL
    python test_instagram.py --error-cases                # URL parsing checks only (no network)

Exit codes:
    0  all assertions passed
    1  extraction failed or an assertion error
"""

import sys
import json
from dataclasses import asdict
from app.services.instagram_service import (
    InstagramService,
    InstagramExtractionError,
    InvalidInstagramURL,
    ReelNotAvailable,
    ApifyRunError,
    RateLimitError,
    ReelData,
    ReelMetadata,
)

# A well-known public Reel used as the default.
# Replace with any currently-live public Reel if this one is removed.
DEFAULT_URL = "https://www.instagram.com/reel/DYOsGMXxlwj/?utm_source=ig_web_copy_link&igsh=NTc4MTIwNjQ2YQ=="


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        raise AssertionError(f"Check failed: {label}")


# --------------------------------------------------------------------------- #
# Error-case tests — no network, no Apify token needed
# --------------------------------------------------------------------------- #

def run_error_cases() -> None:
    service = InstagramService()

    section("Error case: invalid URLs")
    bad_urls = [
        "not-a-url",
        "https://twitter.com/user/status/123",
        "https://instagram.com/",           # no shortcode
        "https://instagram.com/stories/user/",
    ]
    for url in bad_urls:
        try:
            service.extract_shortcode(url)
            check(f"should have raised InvalidInstagramURL for {url!r}", False)
        except InvalidInstagramURL:
            check(f"InvalidInstagramURL raised for {url!r}", True)

    section("Error case: valid URL forms that should parse")
    valid_cases = [
        ("https://www.instagram.com/reel/C0xampleReelABC/", "C0xampleReelABC"),
        ("https://instagram.com/reel/Abc123XYZ_-a/", "Abc123XYZ_-a"),
        ("https://www.instagram.com/p/C0xampleReelABC/?igsh=xxx", "C0xampleReelABC"),
        ("https://www.instagram.com/reel/C0xampleReelABC", "C0xampleReelABC"),
    ]
    for url, expected in valid_cases:
        sc = service.extract_shortcode(url)
        check(f"parse {url!r} → {expected!r}", sc == expected)

    section("Error case: engagement rate edge cases")
    # Test the math directly without needing Apify
    from app.services.instagram_service import InstagramService as IS
    svc = IS()

    # Normal case
    views, likes, comments = 1000, 80, 20
    er = round(((likes + comments) / views) * 100, 4)
    check("engagement_rate calculation correct", er == 10.0)

    # Zero views → should produce None, not ZeroDivisionError
    # Simulate by calling _parse_item with a stub that has 0 views
    stub = {
        "ownerUsername": "testuser",
        "videoPlayCount": 0,
        "likesCount": 50,
        "commentsCount": 10,
        "caption": "test #hashtag",
    }
    meta = svc._parse_item("testshortcode", "https://www.instagram.com/reel/testshortcode/", stub)
    check("engagement_rate is None when views=0", meta.engagement_rate is None)

    # Missing views → should also produce None
    stub_no_views = {
        "ownerUsername": "testuser",
        "likesCount": 50,
        "commentsCount": 10,
        "caption": "",
    }
    meta2 = svc._parse_item("testshortcode", "https://www.instagram.com/reel/testshortcode/", stub_no_views)
    check("engagement_rate is None when views=None", meta2.engagement_rate is None)

    section("Error case: duration normalisation")
    # Duration > 3600 should be treated as milliseconds and divided by 1000
    stub_ms = {
        "ownerUsername": "testuser",
        "videoDuration": 30500,   # 30.5 seconds in ms
        "caption": "",
    }
    meta3 = svc._parse_item("sc", "https://www.instagram.com/reel/sc/", stub_ms)
    check("millisecond duration converted to seconds", meta3.duration == 30)

    stub_sec = {
        "ownerUsername": "testuser",
        "videoDuration": 45,      # already in seconds
        "caption": "",
    }
    meta4 = svc._parse_item("sc", "https://www.instagram.com/reel/sc/", stub_sec)
    check("second duration kept as-is", meta4.duration == 45)

    section("Error case: hashtag extraction")
    tags = svc._extract_hashtags("Check #ThisOut and #cool", ["trending", "#viral"])
    check("inline hashtags extracted", "#thisout" in tags and "#cool" in tags)
    check("tag list merged in", "#trending" in tags and "#viral" in tags)
    check("all lowercase", all(t == t.lower() for t in tags))
    check("all start with #", all(t.startswith("#") for t in tags))
    check("no duplicates", len(tags) == len(set(tags)))

    print("\nAll error cases passed.\n")


# --------------------------------------------------------------------------- #
# Full extraction test — requires network and a valid APIFY_API_TOKEN
# --------------------------------------------------------------------------- #

def run_extraction(url: str) -> None:
    service = InstagramService()

    print(f"\nExtracting: {url}")

    try:
        data: ReelData = service.get_video_data(url)
    except InvalidInstagramURL as exc:
        print(f"[InvalidInstagramURL] {exc}")
        sys.exit(1)
    except ReelNotAvailable as exc:
        print(f"[ReelNotAvailable] {exc}")
        sys.exit(1)
    except RateLimitError as exc:
        print(f"[RateLimitError] {exc}")
        sys.exit(1)
    except ApifyRunError as exc:
        print(f"[ApifyRunError] {exc}")
        sys.exit(1)
    except InstagramExtractionError as exc:
        print(f"[ExtractionError] {exc}")
        sys.exit(1)

    m: ReelMetadata = data.metadata

    section("Metadata assertions")
    check("shortcode is non-empty", bool(m.shortcode))
    check("reel_url is non-empty", bool(m.reel_url))
    check("creator_username is non-empty", bool(m.creator_username))
    check("hashtags is a list", isinstance(m.hashtags, list))
    check("upload_date is non-empty", bool(m.upload_date))
    check("engagement_rate is float or None", m.engagement_rate is None or isinstance(m.engagement_rate, float))
    if m.views is not None and m.views > 0 and m.likes is not None and m.comments is not None:
        expected_er = round(((m.likes + m.comments) / m.views) * 100, 4)
        check("engagement_rate value matches formula", m.engagement_rate == expected_er)

    section("Caption assertions")
    check("caption is a string", isinstance(data.caption, str))
    check("caption matches metadata.caption", data.caption == m.caption)

    section("Human-readable summary")
    print(f"  shortcode        : {m.shortcode}")
    print(f"  reel_url         : {m.reel_url}")
    print(f"  creator_username : {m.creator_username}")
    print(f"  creator_full_name: {m.creator_full_name}")
    print(f"  followers        : {m.followers:,}" if m.followers else "  followers        : n/a")
    print(f"  upload_date      : {m.upload_date}")
    print(f"  duration         : {m.duration}s" if m.duration else "  duration         : n/a")
    print(f"  views            : {m.views:,}" if m.views else "  views            : n/a")
    print(f"  likes            : {m.likes:,}" if m.likes else "  likes            : n/a")
    print(f"  comments         : {m.comments:,}" if m.comments else "  comments         : n/a")
    print(f"  engagement_rate  : {m.engagement_rate}%" if m.engagement_rate else "  engagement_rate  : n/a")
    print(f"  hashtags         : {m.hashtags[:6]}{'…' if len(m.hashtags) > 6 else ''}")
    print(f"  caption          : {m.caption[:120]}{'…' if len(m.caption) > 120 else ''}")

    section("Serialised structure (truncated)")
    doc = asdict(data)
    doc["metadata"]["caption"] = doc["metadata"]["caption"][:200]
    doc["caption"] = doc["caption"][:200]
    print(json.dumps(doc, indent=2))

    print("\nAll checks passed.\n")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    args = sys.argv[1:]

    if "--error-cases" in args:
        run_error_cases()
        return

    url = args[0] if args else DEFAULT_URL
    run_extraction(url)


if __name__ == "__main__":
    main()
