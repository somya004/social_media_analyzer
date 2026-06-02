import re
from dataclasses import dataclass
from typing import Optional

from apify_client import ApifyClient

try:
    from apify_client.errors import ApifyApiError
except ModuleNotFoundError:
    ApifyApiError = Exception

from app.core.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# apify/instagram-reel-scraper is the standard public actor for Reels.
_ACTOR_ID = "apify/instagram-scraper"

# Matches /reel/<shortcode>/ and /p/<shortcode>/ URL forms.
_SHORTCODE_RE = re.compile(r"instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)")


# Exceptions

class InstagramExtractionError(Exception):
    """Base for all Instagram service failures."""


class InvalidInstagramURL(InstagramExtractionError):
    """URL did not contain a recognisable Reel shortcode."""


class ReelNotAvailable(InstagramExtractionError):
    """Reel is private, deleted, or otherwise inaccessible."""


class ApifyRunError(InstagramExtractionError):
    """Apify actor run failed or returned no results."""


class RateLimitError(InstagramExtractionError):
    """Apify or Instagram rate limit was hit."""


# Return types

@dataclass
class ReelMetadata:
    shortcode: str
    reel_url: str
    creator_username: str
    creator_full_name: str
    followers: Optional[int]
    caption: str
    hashtags: list[str]
    upload_date: str           # ISO 8601 string as returned by Apify
    views: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    duration: Optional[int]    # seconds; None if Apify omits it
    thumbnail_url: str
    engagement_rate: Optional[float]  # ((likes + comments) / views) * 100


@dataclass
class ReelData:
    metadata: ReelMetadata
    caption: str               # primary text content, used downstream as "transcript"


# Service

class InstagramService:

    def __init__(self) -> None:
        self._settings = get_settings()

    def extract_shortcode(self, url: str) -> str:
        url = url.strip()
        match = _SHORTCODE_RE.search(url)
        if not match:
            raise InvalidInstagramURL(f"Cannot extract shortcode from: {url!r}")
        return match.group(1)

    def get_metadata(self, url: str) -> ReelMetadata:
        shortcode = self.extract_shortcode(url)
        logger.info("fetching reel  shortcode=%s", shortcode)

        raw = self._run_actor(url)
        return self._parse_item(shortcode, url, raw)

    def get_video_data(self, url: str) -> ReelData:
        """Main entry point. Returns metadata and caption text."""
        metadata = self.get_metadata(url)

        logger.info(
            "extraction complete  shortcode=%s  creator=%s  views=%s  engagement=%.2f%%",
            metadata.shortcode,
            metadata.creator_username,
            metadata.views,
            metadata.engagement_rate or 0.0,
        )

        return ReelData(metadata=metadata, caption=metadata.caption)

     # Private helpers
    
    def _run_actor(self, url: str) -> dict:
        client = ApifyClient(self._settings.apify_api_token)

        try:
            run = client.actor(_ACTOR_ID).call(
                run_input={
                    "directUrls": [url],
                    "resultsLimit": 1,
                    "resultsType": "posts",
                },
            )
        except ApifyApiError as exc:
            status = getattr(exc, "status_code", None)
            if status == 429:
                raise RateLimitError("Apify rate limit reached") from exc
            raise ApifyRunError(f"Apify API error: {exc}") from exc
        except Exception as exc:
            raise ApifyRunError(f"Unexpected error starting Apify actor: {exc}") from exc

        if run is None:
            raise ApifyRunError("Apify actor run returned None")

        dataset_id = getattr(run, "default_dataset_id", None)

        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId")

        if not dataset_id:
            raise ApifyRunError("Apify run did not produce a dataset")
        try:
            items = list(client.dataset(dataset_id).iterate_items())
        except ApifyApiError as exc:
            raise ApifyRunError(f"Failed to read Apify dataset: {exc}") from exc

        if not items:
            raise ReelNotAvailable(f"Apify returned no items for URL: {url}")

        return items[0]

    def _parse_item(self, shortcode: str, url: str, item: dict) -> ReelMetadata:
        # Private or deleted reels come back as a stub with no owner data.
        if not item.get("ownerUsername") and not item.get("ownerId"):
            raise ReelNotAvailable(
                f"Reel {shortcode!r} appears to be private or deleted"
            )

        views = self._int_or_none(item.get("videoPlayCount") or item.get("videoViewCount"))
        likes = self._int_or_none(item.get("likesCount"))
        comments = self._int_or_none(item.get("commentsCount"))

        engagement_rate: Optional[float] = None
        if views and views > 0 and likes is not None and comments is not None:
            engagement_rate = round(((likes + comments) / views) * 100, 4)

        caption: str = item.get("caption") or ""
        hashtags = self._extract_hashtags(
            caption,
            item.get("hashtags") or [],
        )

        # Apify may return the duration in seconds or milliseconds depending on
        # the actor version; values over 3600 are almost certainly milliseconds.
        raw_duration = self._int_or_none(item.get("videoDuration"))
        if raw_duration is not None and raw_duration > 3600:
            raw_duration = raw_duration // 1000

        upload_date = item.get("timestamp") or item.get("takenAtTimestamp") or ""

        return ReelMetadata(
            shortcode=shortcode,
            reel_url=item.get("url") or url,
            creator_username=item.get("ownerUsername") or "",
            creator_full_name=item.get("ownerFullName") or "",
            followers=self._int_or_none(item.get("ownerFollowersCount")),
            caption=caption,
            hashtags=hashtags,
            upload_date=upload_date,
            views=views,
            likes=likes,
            comments=comments,
            duration=raw_duration,
            thumbnail_url=item.get("displayUrl") or item.get("thumbnailUrl") or "",
            engagement_rate=engagement_rate,
        )

    @staticmethod
    def _extract_hashtags(caption: str, tag_list: list) -> list[str]:
        found: set[str] = set()

        for tag in tag_list:
            clean = str(tag).strip().lower()
            if clean:
                found.add(clean if clean.startswith("#") else f"#{clean}")

        for match in re.finditer(r"#(\w+)", caption):
            found.add(f"#{match.group(1).lower()}")

        return sorted(found)

    @staticmethod
    def _int_or_none(value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
