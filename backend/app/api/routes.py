from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    AnalyzeYouTubeRequest,
    AnalyzeYouTubeResponse,
    AnalyzeInstagramRequest,
    AnalyzeInstagramResponse,
    AnalyzePairRequest,
    AnalyzePairResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.analysis_service import AnalysisService, AnalysisError
from app.services.rag_service import RAGService
from app.core.config import get_settings
from app.utils.logging import get_logger

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__, level=settings.log_level)

# One instance per worker process — services are stateless except for
# MemoryService inside RAGService, which is intentionally in-process.
_analysis = AnalysisService()
_rag = RAGService()


# Health

@router.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_model": settings.gemini_model,
        "embedding_model": settings.embedding_model,
        "chroma_collection": settings.chroma_collection_name,
        "debug": settings.debug,
    }


# Analysis
 
@router.post("/analyze/youtube", response_model=AnalyzeYouTubeResponse)
async def analyze_youtube(payload: AnalyzeYouTubeRequest):
    logger.info("POST /analyze/youtube  url=%s  video_id=%s", payload.url, payload.video_id)
    try:
        result = _analysis.analyze_youtube(payload.url, video_id=payload.video_id)
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return result


@router.post("/analyze/instagram", response_model=AnalyzeInstagramResponse)
async def analyze_instagram(payload: AnalyzeInstagramRequest):
    logger.info("POST /analyze/instagram  url=%s  video_id=%s", payload.url, payload.video_id)
    try:
        result = _analysis.analyze_instagram(payload.url, video_id=payload.video_id)
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return result


@router.post("/analyze/pair", response_model=AnalyzePairResponse)
async def analyze_pair(payload: AnalyzePairRequest):
    logger.info(
        "POST /analyze/pair  youtube=%s  instagram=%s",
        payload.youtube_url, payload.instagram_url,
    )
    try:
        result = _analysis.analyze_pair(payload.youtube_url, payload.instagram_url)
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return result


# Chat

@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    logger.info(
        "POST /chat  session=%s  question=%.80s",
        payload.session_id, payload.question,
    )
    try:
        result = _rag.answer_question(
            question=payload.question,
            session_id=payload.session_id,
            filters=payload.filters,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("RAG failure  session=%s", payload.session_id)
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")
    return result
