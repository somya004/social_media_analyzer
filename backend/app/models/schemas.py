from pydantic import BaseModel, field_validator
from typing import Optional, List, Any


# YouTube extraction output

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
    duration: int
    views: int
    likes: Optional[int]
    description: str
    hashtags: List[str]
    thumbnail_url: str


class YouTubeVideoSchema(BaseModel):
    metadata: YouTubeMetadataSchema
    transcript: TranscriptSchema


# Instagram extraction output

class InstagramMetadataSchema(BaseModel):
    shortcode: str
    reel_url: str
    creator_username: str
    creator_full_name: str
    followers: Optional[int]
    caption: str
    hashtags: List[str]
    upload_date: str
    views: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    duration: Optional[int]
    thumbnail_url: str
    engagement_rate: Optional[float]


class InstagramReelSchema(BaseModel):
    metadata: InstagramMetadataSchema
    caption: str


# Shared engagement metadata (API responses)

class VideoMetadata(BaseModel):
    title: Optional[str] = None
    creator: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    followers: Optional[int] = None
    hashtags: List[str] = []
    duration: Optional[int] = None
    upload_date: Optional[str] = None
    engagement_rate: Optional[float] = None
    thumbnail_url: Optional[str] = None


# /analyze

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
    source: str
    url: str
    transcript: str
    metadata: VideoMetadata


class AnalyzeResponse(BaseModel):
    session_id: str
    youtube: VideoMetadata
    instagram: VideoMetadata


# /chat — streaming (routes.py) uses these for validation

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    citations: List["Citation"] = []


# RAG output

class SourceCitation(BaseModel):
    video_id: str
    source: str          # "youtube" | "instagram"
    chunk_id: str
    title: str
    evidence: str        # excerpt from the matched chunk
    score: float


class RAGResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    session_id: str


# /chat legacy citation shape (used by streaming stub in routes.py)

class Citation(BaseModel):
    source: str
    title: Optional[str] = None
    excerpt: str
    relevance_score: float


# Internal

class EmbeddedChunk(BaseModel):
    text: str
    embedding: List[float]
    source: str
    metadata: dict[str, Any] = {}
