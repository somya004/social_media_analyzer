import re
from dataclasses import dataclass, field
from typing import Optional
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Matches standard watch URLs, short URLs, and embed URLs
_VIDEO_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})"
)

_YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": False,
}


# Exceptions

class YouTubeExtractionError(Exception):
    """Base error for all YouTube service failures."""


class InvalidYouTubeURL(YouTubeExtractionError):
    """URL did not contain a recognisable video ID."""


class VideoNotAvailable(YouTubeExtractionError):
    """Video is private, deleted, or region-blocked."""


class TranscriptNotAvailable(YouTubeExtractionError):
    """Transcript is disabled or does not exist for this video."""


class MetadataFetchError(YouTubeExtractionError):
    """yt-dlp could not retrieve metadata."""


# Return types

@dataclass
class TranscriptSegment:
    text: str
    start: float   # seconds from video start
    duration: float


@dataclass
class TranscriptData:
    full_text: str
    segments: list[TranscriptSegment]
    language: str


@dataclass
class VideoMetadataRaw:
    video_id: str
    title: str
    creator: str
    upload_date: str       # YYYY-MM-DD
    duration: int          # seconds
    views: int
    likes: Optional[int]   # None when YouTube hides the count
    description: str
    hashtags: list[str]
    thumbnail_url: str


@dataclass
class VideoData:
    metadata: VideoMetadataRaw
    transcript: TranscriptData


# Service

class YouTubeService:

    def extract_video_id(self, url: str) -> str:
        """
        Parse the 11-character video ID from any standard YouTube URL form.
        Raises InvalidYouTubeURL if nothing matches.
        """
        url = url.strip()
        match = _VIDEO_ID_RE.search(url)
        if not match:
            raise InvalidYouTubeURL(f"Cannot extract video ID from: {url!r}")
        return match.group(1)

    def get_metadata(self, url: str) -> VideoMetadataRaw:
        """
        Fetch video metadata via yt-dlp.
        Raises MetadataFetchError or VideoNotAvailable on failure.
        """
        video_id = self.extract_video_id(url)
        logger.info("fetching metadata  video_id=%s", video_id)

        try:
            with YoutubeDL(_YDL_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as exc:
            msg = str(exc).lower()
            if "private" in msg or "unavailable" in msg or "removed" in msg:
                raise VideoNotAvailable(f"Video {video_id} is not accessible") from exc
            raise MetadataFetchError(f"yt-dlp failed for {video_id}: {exc}") from exc
        except ExtractorError as exc:
            raise MetadataFetchError(f"Extractor error for {video_id}: {exc}") from exc

        if info is None:
            raise MetadataFetchError(f"yt-dlp returned no data for {video_id}")

        hashtags = self._extract_hashtags(
            info.get("description") or "",
            info.get("tags") or [],
        )

        upload_date = self._format_date(info.get("upload_date") or "")

        return VideoMetadataRaw(
            video_id=video_id,
            title=info.get("title") or "",
            creator=info.get("uploader") or info.get("channel") or "",
            upload_date=upload_date,
            duration=int(info.get("duration") or 0),
            views=int(info.get("view_count") or 0),
            # like_count is None when YouTube hides it; keep None rather than 0
            likes=info.get("like_count"),
            description=(info.get("description") or "")[:2000],  # cap length
            hashtags=hashtags,
            thumbnail_url=info.get("thumbnail") or "",
        )

    def get_transcript(self, video_id: str) -> TranscriptData:
        logger.info("fetching transcript  video_id=%s", video_id)

        url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB"],
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            subtitles = info.get("subtitles") or {}
            auto_captions = info.get("automatic_captions") or {}

            caption_sources = (
                subtitles.get("en")
                or auto_captions.get("en")
                or subtitles.get("en-US")
                or auto_captions.get("en-US")
                or subtitles.get("en-GB")
                or auto_captions.get("en-GB")
                or []
            )

            if not caption_sources:
                raise TranscriptNotAvailable(f"No English transcript found for {video_id}")

            caption_url = None
            for source in caption_sources:
                if source.get("ext") in {"vtt", "srv3"}:
                    caption_url = source.get("url")
                    break

            if not caption_url:
                caption_url = caption_sources[0].get("url")

            import requests
            response = requests.get(caption_url, timeout=20)
            response.raise_for_status()

            lines = []
            seen = set()

            for line in response.text.splitlines():
                line = line.strip()

                if not line:
                    continue
                if line.startswith("WEBVTT"):
                    continue
                if "-->" in line:
                    continue
                if line.isdigit():
                    continue
                if line.startswith(("Kind:", "Language:")):
                    continue

                line = re.sub(r"<[^>]+>", "", line)
                line = line.replace("&amp;", "&")

                if line and line not in seen:
                    seen.add(line)
                    lines.append(line)

            segments = [
                TranscriptSegment(text=line, start=0, duration=0)
                for line in lines
            ]

            return TranscriptData(
                full_text=" ".join(lines),
                segments=segments,
                language="en",
            )

        except Exception as exc:
            logger.warning(
                "transcript unavailable  video_id=%s  reason=%s",
                video_id,
                exc,
            )
            return TranscriptData(full_text="", segments=[], language="")

    def get_video_data(self, url: str) -> VideoData:
        """
        Main entry point. Returns metadata + transcript for a YouTube URL.

        If the transcript cannot be fetched the data is still returned with
        an empty TranscriptData so downstream callers can decide how to handle
        the missing content rather than failing entirely.
        """
        metadata = self.get_metadata(url)

        try:
            transcript = self.get_transcript(metadata.video_id)
        except TranscriptNotAvailable as exc:
            logger.warning("transcript unavailable  video_id=%s  reason=%s", metadata.video_id, exc)
            transcript = TranscriptData(full_text="", segments=[], language="")
        except VideoNotAvailable:
            raise  # propagate — metadata succeeded but video disappeared between calls

        logger.info(
            "extraction complete  video_id=%s  transcript_chars=%d  hashtags=%d",
            metadata.video_id,
            len(transcript.full_text),
            len(metadata.hashtags),
        )
        return VideoData(metadata=metadata, transcript=transcript)

     # Private helpers
    
    def _pick_transcript(self, transcript_list, video_id: str):
        """
        Return the best available transcript in preference order:
          1. Manual English
          2. Auto-generated English
          3. Any manually created transcript
          4. Any auto-generated transcript
        """
        try:
            return transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        except NoTranscriptFound:
            pass

        try:
            return transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
        except NoTranscriptFound:
            pass

        # Fall back to whatever is available, translated to English if needed
        available = list(transcript_list)
        if not available:
            raise TranscriptNotAvailable(f"No transcripts at all for {video_id}")

        transcript = available[0]
        if transcript.is_translatable:
            try:
                return transcript.translate("en")
            except Exception:
                pass  # translation failed, return as-is

        return transcript

    def _extract_hashtags(self, description: str, tags: list[str]) -> list[str]:
        """
        Combine hashtags from the description text and the tags list.
        Deduplicates and normalises to lowercase.
        """
        found: set[str] = set()

        # Tags from yt-dlp metadata
        for tag in tags:
            clean = tag.strip().lower()
            if clean:
                found.add(f"#{clean}" if not clean.startswith("#") else clean)

        # Inline hashtags from description body
        for match in re.finditer(r"#(\w+)", description):
            found.add(f"#{match.group(1).lower()}")

        return sorted(found)

    def _format_date(self, raw: str) -> str:
        """Convert yt-dlp's YYYYMMDD string to YYYY-MM-DD."""
        if len(raw) == 8 and raw.isdigit():
            return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        return raw
