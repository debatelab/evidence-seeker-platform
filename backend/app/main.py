from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys
import uvicorn
import logging

# Suppress the bcrypt version warning from passlib
logging.getLogger("passlib").setLevel(logging.ERROR)

from app.core.config import settings
from app.core.database import create_tables
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.evidence_seekers import router as evidence_seekers_router
from app.api.documents import router as documents_router
from app.api.permissions import router as permissions_router
from app.api.embeddings import router as embeddings_router
from app.api.search import router as search_router
from app.api.config import router as config_router
from app.api.progress import router as progress_router


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    # Configure Loguru
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Create FastAPI app
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description="Evidence Seeker Platform API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add trusted host middleware
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"]
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
        logging.error(f"{request}: {exc_str}")
        content = {"status_code": 10422, "message": exc_str, "data": None}
        return JSONResponse(
            content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    # Global exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # Include routers
    app.include_router(
        auth_router, prefix=settings.api_v1_prefix, tags=["Authentication"]
    )
    app.include_router(
        users_router, prefix=settings.api_v1_prefix + "/users", tags=["Users"]
    )
    app.include_router(
        evidence_seekers_router,
        prefix=settings.api_v1_prefix + "/evidence-seekers",
        tags=["Evidence Seekers"],
    )
    app.include_router(
        documents_router,
        prefix=settings.api_v1_prefix + "/documents",
        tags=["Documents"],
    )
    app.include_router(
        permissions_router,
        prefix=settings.api_v1_prefix + "/permissions",
        tags=["Permissions"],
    )
    app.include_router(
        embeddings_router,
        prefix=settings.api_v1_prefix + "/embeddings",
        tags=["Embeddings"],
    )
    app.include_router(
        search_router,
        prefix=settings.api_v1_prefix + "/search",
        tags=["Search"],
    )
    app.include_router(
        config_router,
        prefix=settings.api_v1_prefix + "/config",
        tags=["Configuration"],
    )
    app.include_router(
        progress_router,
        prefix=settings.api_v1_prefix + "/progress",
        tags=["Progress"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "version": settings.version}

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Welcome to Evidence Seeker Platform API",
            "version": settings.version,
            "docs": "/docs",
        }

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Application startup event"""
        logger.info("Starting Evidence Seeker Platform API")
        create_tables()
        logger.info("Database tables created/verified")

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event"""
        logger.info("Shutting down Evidence Seeker Platform API")

    return app


# Create the FastAPI app instance
app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
