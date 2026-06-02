from dataclasses import asdict
from app.services.youtube_service import YouTubeService, YouTubeExtractionError
from app.services.instagram_service import InstagramService, InstagramExtractionError
from app.services.chunking_service import TranscriptChunker
from app.services.vector_store_service import VectorStoreService
from app.utils.logging import get_logger

logger = get_logger(__name__)

_CHUNK_SIZE = 700
_CHUNK_OVERLAP = 120


class AnalysisError(Exception):
    """Raised when an analysis step fails in a way the route should surface as 4xx/5xx."""
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


class AnalysisService:

    def __init__(self) -> None:
        self._yt = YouTubeService()
        self._ig = InstagramService()
        self._chunker = TranscriptChunker(chunk_size=_CHUNK_SIZE, overlap=_CHUNK_OVERLAP)
        self._store = VectorStoreService()

    # Public interface
    
    def analyze_youtube(self, url: str, video_id: str = "A") -> dict:
        logger.info("analyze_youtube  url=%s  video_id=%s", url, video_id)

        try:
            data = self._yt.get_video_data(url)
        except YouTubeExtractionError as exc:
            raise AnalysisError(str(exc), status_code=422) from exc
        except Exception as exc:
            logger.exception("unexpected error during YouTube extraction  url=%s", url)
            raise AnalysisError(
                f"YouTube extraction failed unexpectedly: {exc}", status_code=500
            ) from exc

        text = data.transcript.full_text.strip()
        chunk_count = 0

        if text:
            chunk_meta = self._build_yt_chunk_meta(data, video_id)
            chunks = self._chunker.chunk_text(
                text=text,
                video_id=video_id,
                source="youtube",
                metadata=chunk_meta,
            )
            try:
                self._store.add_chunks(chunks)
                chunk_count = len(chunks)
            except Exception as exc:
                logger.exception("vector store write failed  video_id=%s", video_id)
                raise AnalysisError(
                    f"Failed to store YouTube chunks: {exc}", status_code=500
                ) from exc
        else:
            logger.warning("empty transcript  video_id=%s  url=%s", video_id, url)

        m = data.metadata
        return {
            "video_id": video_id,
            "source": "youtube",
            "title": m.title,
            "creator": m.creator,
            "upload_date": m.upload_date,
            "duration": m.duration,
            "views": m.views,
            "likes": m.likes,
            "hashtags": m.hashtags,
            "thumbnail_url": m.thumbnail_url,
            "transcript_chars": len(text),
            "chunks_stored": chunk_count,
            "transcript_available": bool(text),
        }

    def analyze_instagram(self, url: str, video_id: str = "B") -> dict:
        logger.info("analyze_instagram  url=%s  video_id=%s", url, video_id)

        try:
            data = self._ig.get_video_data(url)
        except InstagramExtractionError as exc:
            raise AnalysisError(str(exc), status_code=422) from exc
        except Exception as exc:
            logger.exception("unexpected error during Instagram extraction  url=%s", url)
            raise AnalysisError(
                f"Instagram extraction failed unexpectedly: {exc}", status_code=500
            ) from exc

        text = data.caption.strip()
        chunk_count = 0

        if text:
            chunk_meta = self._build_ig_chunk_meta(data, video_id)
            chunks = self._chunker.chunk_text(
                text=text,
                video_id=video_id,
                source="instagram",
                metadata=chunk_meta,
            )
            try:
                self._store.add_chunks(chunks)
                chunk_count = len(chunks)
            except Exception as exc:
                logger.exception("vector store write failed  video_id=%s", video_id)
                raise AnalysisError(
                    f"Failed to store Instagram chunks: {exc}", status_code=500
                ) from exc
        else:
            logger.warning("empty caption  video_id=%s  url=%s", video_id, url)

        m = data.metadata
        return {
            "video_id": video_id,
            "source": "instagram",
            "shortcode": m.shortcode,
            "creator": m.creator_username,
            "creator_full_name": m.creator_full_name,
            "followers": m.followers,
            "upload_date": m.upload_date,
            "duration": m.duration,
            "views": m.views,
            "likes": m.likes,
            "comments": m.comments,
            "engagement_rate": m.engagement_rate,
            "hashtags": m.hashtags,
            "thumbnail_url": m.thumbnail_url,
            "caption_chars": len(text),
            "chunks_stored": chunk_count,
            "caption_available": bool(text),
        }

    def analyze_pair(self, youtube_url: str, instagram_url: str) -> dict:
        logger.info(
            "analyze_pair  youtube=%s  instagram=%s",
            youtube_url, instagram_url,
        )
        youtube_result = self.analyze_youtube(youtube_url, video_id="A")
        instagram_result = self.analyze_instagram(instagram_url, video_id="B")
        return {
            "youtube": youtube_result,
            "instagram": instagram_result,
        }

     # Metadata helpers
   
    @staticmethod
    def _build_yt_chunk_meta(data, video_id: str) -> dict:
        m = data.metadata
        return {
            "video_id": video_id,
            "source": "youtube",
            "title": m.title,
            "creator": m.creator,
            "upload_date": m.upload_date,
            "views": m.views,
            "likes": m.likes,
            "engagement_rate": None,
        }

    @staticmethod
    def _build_ig_chunk_meta(data, video_id: str) -> dict:
        m = data.metadata
        return {
            "video_id": video_id,
            "source": "instagram",
            "title": m.shortcode,
            "creator": m.creator_username,
            "upload_date": m.upload_date,
            "views": m.views,
            "likes": m.likes,
            "engagement_rate": m.engagement_rate,
        }
