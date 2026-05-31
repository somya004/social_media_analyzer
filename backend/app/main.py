from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.utils.logging import get_logger, configure_root

settings = get_settings()
configure_root(settings.log_level)
logger = get_logger(__name__, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup  debug=%s  gemini_model=%s  embedding_model=%s  chroma_dir=%s",
        settings.debug,
        settings.gemini_model,
        settings.embedding_model,
        settings.chroma_persist_dir,
    )
    yield
    logger.info("shutdown")


app = FastAPI(
    title="MediaRAG API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
