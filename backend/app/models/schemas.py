from pydantic import BaseModel, field_validator
from typing import Optional, List, Any


# --------------------------------------------------------------------------- #
# YouTube extraction output — mirrors YouTubeService dataclasses
# --------------------------------------------------------------------------- #

class TranscriptSegmentSchema(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptSchema(BaseModel):
    full_text: str
    segments: List[TranscriptSegmentSchema]
    language: str


class YouTubeMetadataSchema(BaseModel):
    video_id: str
    title: str
    creator: str
    upload_date: str
    duration: int              # seconds
    views: int
    likes: Optional[int]       # None when YouTube hides the count
    description: str
    hashtags: List[str]
    thumbnail_url: str


class YouTubeVideoSchema(BaseModel):
    metadata: YouTubeMetadataSchema
    transcript: TranscriptSchema


# --------------------------------------------------------------------------- #
# Shared engagement metadata (used in API responses for both sources)
# --------------------------------------------------------------------------- #

class VideoMetadata(BaseModel):
    title: Optional[str] = None
    creator: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    followers: Optional[int] = None
    hashtags: List[str] = []
    duration: Optional[int] = None          # seconds
    upload_date: Optional[str] = None       # YYYY-MM-DD
    engagement_rate: Optional[float] = None # percentage
    thumbnail_url: Optional[str] = None


# --------------------------------------------------------------------------- #
# /analyze
# --------------------------------------------------------------------------- #

class AnalyzeRequest(BaseModel):
    youtube_url: str
    instagram_url: str

    @field_validator("youtube_url")
    @classmethod
    def must_be_youtube(cls, v: str) -> str:
        if "youtube.com" not in v and "youtu.be" not in v:
            raise ValueError("youtube_url does not look like a YouTube URL")
        return v

    @field_validator("instagram_url")
    @classmethod
    def must_be_instagram(cls, v: str) -> str:
        if "instagram.com" not in v:
            raise ValueError("instagram_url does not look like an Instagram URL")
        return v


class VideoInput(BaseModel):
    """Normalised single-source video ready for embedding."""
    source: str          # "youtube" | "instagram"
    url: str
    transcript: str
    metadata: VideoMetadata


class AnalyzeResponse(BaseModel):
    session_id: str
    youtube: VideoMetadata
    instagram: VideoMetadata


# --------------------------------------------------------------------------- #
# /chat
# --------------------------------------------------------------------------- #

class Citation(BaseModel):
    source: str
    title: Optional[str] = None
    excerpt: str
    relevance_score: float


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = []


# --------------------------------------------------------------------------- #
# Internal embedding
# --------------------------------------------------------------------------- #

class EmbeddedChunk(BaseModel):
    text: str
    embedding: List[float]
    source: str
    metadata: dict[str, Any] = {}
