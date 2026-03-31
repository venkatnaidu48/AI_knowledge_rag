"""
Main FastAPI application entry point
Initializes and configures the RAG API server
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Callable

from config.settings import get_settings
from src.utils.logger import setup_logging, get_logger
from src.database.database import initialize_database, close_database_connection

# Setup logging early
setup_logging()
logger = get_logger(__name__)
settings = get_settings()


# ============ Lifespan Events ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    Docs: https://fastapi.tiangolo.com/advanced/events/
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database
    try:
        initialize_database()
        logger.info("[OK] Database initialized")
    except Exception as e:
        logger.error(f"[ERROR] Database initialization failed: {str(e)}")
        raise
    
    logger.info(f"{settings.APP_NAME} started successfully!")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    close_database_connection()
    logger.info("[OK] Database connections closed")
    logger.info(f"{settings.APP_NAME} shutdown complete")


# ============ Create FastAPI Application ============
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


# ============ Middleware Setup ============

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # In production, use specific hosts
)


# ============ Custom Exception Handlers ============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions
    """
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An internal server error occurred",
            "detail": str(exc) if settings.DEBUG else None,
        }
    )


# ============ Health Check Endpoint ============

@app.get("/health", tags=["Health"], summary="Health check")
async def health_check():
    """
    Health check endpoint
    Returns system status and availability
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Info"], summary="API Information")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "docs": "/docs",
        "api_docs": "/docs",
        "health": "/health",
    }


# ============ API Routes (To be implemented) ============

# Import and include routers here as we build them:
from src.api.routes.documents import router as documents_router
from src.api.routes.embeddings import router as embeddings_router
from src.api.routes.search import router as search_router
from src.api.routes.query import router as query_router
from src.api.routes.generation import router as generation_router
from src.api.routes.validation import router as validation_router

app.include_router(documents_router)
app.include_router(embeddings_router)
app.include_router(search_router)
app.include_router(query_router)
app.include_router(generation_router)
app.include_router(validation_router)


# ============ Logging Configuration ============

if __name__ != "__main__":
    logging.getLogger("uvicorn.access").disabled = False


# ============ Application Info ============

if settings.DEBUG:
    logger.debug(f"""
    ╔════════════════════════════════╗
    ║   RAG APPLICATION LOADED      ║
    ╚════════════════════════════════╝
    
    App Name:        {settings.APP_NAME}
    Version:         {settings.APP_VERSION}
    Environment:     {settings.ENVIRONMENT}
    Debug Mode:      {settings.DEBUG}
    
    Server Config:
    - Host: {settings.API_HOST}
    - Port: {settings.API_PORT}
    - Workers: {settings.API_WORKERS}
    
    Database: {settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL}
    Vector DB: {settings.FAISS_INDEX_PATH}
    
    API Docs: http://localhost:{settings.API_PORT}/docs
    """)
