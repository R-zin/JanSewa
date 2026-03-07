from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.logging_middleware import LoggingMiddleware
from app.core.metrics_middleware import MetricsMiddleware
from app.api.v1.router import api_router

# Configure structured logging with PII sanitization
setup_logging(
    log_level=getattr(settings, 'LOG_LEVEL', 'INFO'),
    log_dir=getattr(settings, 'LOG_DIR', 'logs'),
    enable_console=True,
    enable_file=True,
    enable_json=True,
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Government Services Assistant API")
    yield
    logger.info("Shutting down Government Services Assistant API")


app = FastAPI(
    title="Government Services Assistant API",
    description="AI-powered assistant for government services",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics middleware (before logging to capture all requests)
app.add_middleware(MetricsMiddleware)

# Logging middleware
app.add_middleware(LoggingMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "government-services-assistant"}
