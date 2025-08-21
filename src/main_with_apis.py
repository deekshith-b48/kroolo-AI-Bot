"""
Main application entry point for the Kroolo AI Bot with complete API surface.
Integrates all Phase 4 API routes and Phase 5 database schemas.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from src.core.agent_manager import agent_manager
from src.core.telegram_client import telegram_client
from src.core.content_scheduler import content_scheduler
from src.core.metrics_collector import metrics_collector
from src.core.rag_service import rag_service
from src.core.rate_limiter import rate_limiter
from src.database.session import init_database

# Import all API routers
from src.api.telegram import router as telegram_router
from src.api.internal import router as internal_router
from src.api.admin import router as admin_router
from src.api.rag import router as rag_router
from src.api.scheduler import router as scheduler_router
from src.api.connectors import router as connectors_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Kroolo AI Bot with complete API surface...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("✅ Database initialized")
        
        # Initialize core services
        await agent_manager.initialize()
        logger.info("✅ Agent manager initialized")
        
        await telegram_client.initialize()
        logger.info("✅ Telegram client initialized")
        
        await content_scheduler.initialize(telegram_client, agent_manager)
        logger.info("✅ Content scheduler initialized")
        
        await metrics_collector.initialize()
        logger.info("✅ Metrics collector initialized")
        
        await rag_service.initialize()
        logger.info("✅ RAG service initialized")
        
        await rate_limiter.initialize()
        logger.info("✅ Rate limiter initialized")
        
        logger.info("🚀 Kroolo AI Bot started successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Kroolo AI Bot...")
        
        try:
            await content_scheduler.shutdown()
            logger.info("✅ Content scheduler shutdown")
            
            # Close other services as needed
            logger.info("✅ Kroolo AI Bot shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title="Kroolo AI Bot",
    description="A comprehensive multi-agent Telegram bot with AI capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Add all API routers
app.include_router(telegram_router)
app.include_router(internal_router)
app.include_router(admin_router)
app.include_router(rag_router)
app.include_router(scheduler_router)
app.include_router(connectors_router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Record error metrics
    await metrics_collector.record_error({
        "error_type": "unhandled_exception",
        "error_message": str(exc),
        "endpoint": str(request.url),
        "method": request.method
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": str(asyncio.get_event_loop().time())
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Kroolo AI Bot",
        "version": "1.0.0",
        "status": "running",
        "description": "Multi-agent Telegram bot with AI capabilities",
        "api_documentation": {
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "available_apis": {
            "telegram": "/v1/telegram/*",
            "internal": "/internal/v1/*",
            "admin": "/v1/admin/*",
            "rag": "/v1/rag/*",
            "scheduler": "/v1/scheduler/*",
            "connectors": "/v1/connectors/*"
        },
        "health_checks": {
            "overall": "/health",
            "telegram": "/v1/telegram/health",
            "internal": "/internal/v1/health",
            "admin": "/v1/admin/health",
            "rag": "/v1/rag/health",
            "scheduler": "/v1/scheduler/health",
            "connectors": "/v1/connectors/health"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check for all services."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": str(asyncio.get_event_loop().time()),
            "services": {}
        }
        
        # Check each service
        try:
            agent_health = await agent_manager.health_check()
            health_status["services"]["agent_manager"] = agent_health
        except Exception as e:
            health_status["services"]["agent_manager"] = {"status": "error", "error": str(e)}
        
        try:
            telegram_health = await telegram_client.health_check()
            health_status["services"]["telegram_client"] = telegram_health
        except Exception as e:
            health_status["services"]["telegram_client"] = {"status": "error", "error": str(e)}
        
        try:
            scheduler_health = await content_scheduler.health_check()
            health_status["services"]["content_scheduler"] = scheduler_health
        except Exception as e:
            health_status["services"]["content_scheduler"] = {"status": "error", "error": str(e)}
        
        try:
            metrics_health = await metrics_collector.health_check()
            health_status["services"]["metrics_collector"] = metrics_health
        except Exception as e:
            health_status["services"]["metrics_collector"] = {"status": "error", "error": str(e)}
        
        try:
            rag_health = await rag_service.health_check()
            health_status["services"]["rag_service"] = rag_health
        except Exception as e:
            health_status["services"]["rag_service"] = {"status": "error", "error": str(e)}
        
        try:
            rate_limiter_health = await rate_limiter.health_check()
            health_status["services"]["rate_limiter"] = rate_limiter_health
        except Exception as e:
            health_status["services"]["rate_limiter"] = {"status": "error", "error": str(e)}
        
        # Determine overall status
        unhealthy_services = [
            service for service, status in health_status["services"].items()
            if status.get("status") not in ["healthy", "degraded"]
        ]
        
        if unhealthy_services:
            health_status["status"] = "unhealthy"
            health_status["unhealthy_services"] = unhealthy_services
        elif any(status.get("status") == "degraded" for status in health_status["services"].values()):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "timestamp": str(asyncio.get_event_loop().time()),
            "error": str(e)
        }

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        prometheus_metrics = await metrics_collector.get_prometheus_metrics()
        return prometheus_metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

# System status endpoint
@app.get("/status")
async def system_status():
    """Detailed system status information."""
    try:
        # Get metrics
        metrics_data = await metrics_collector.get_metrics(include_history=False)
        
        # Get health status
        health_data = await health_check()
        
        return {
            "system": {
                "name": "Kroolo AI Bot",
                "version": "1.0.0",
                "uptime": "calculated_uptime",  # Would calculate actual uptime
                "environment": settings.environment
            },
            "health": health_data,
            "metrics": {
                "messages_processed": metrics_data.get("message_metrics", {}).get("total_messages", 0),
                "responses_generated": metrics_data.get("response_metrics", {}).get("total_responses", 0),
                "errors_encountered": metrics_data.get("error_metrics", {}).get("total_errors", 0),
                "active_agents": len(agent_manager.agent_configs) if agent_manager.agent_configs else 0
            },
            "configuration": {
                "telegram_bot_configured": bool(settings.telegram_bot_token),
                "openai_configured": bool(settings.openai_api_key),
                "database_configured": bool(settings.database_url),
                "redis_configured": bool(settings.redis_url),
                "qdrant_configured": bool(settings.qdrant_url)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

# Ready endpoint for Kubernetes readiness probes
@app.get("/ready")
async def ready():
    """Readiness probe endpoint."""
    try:
        # Check if all critical services are ready
        health = await health_check()
        
        if health["status"] in ["healthy", "degraded"]:
            return {"status": "ready", "timestamp": str(asyncio.get_event_loop().time())}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

# Live endpoint for Kubernetes liveness probes
@app.get("/live")
async def live():
    """Liveness probe endpoint."""
    return {"status": "alive", "timestamp": str(asyncio.get_event_loop().time())}

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "src.main_with_apis:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False,
        log_level="info"
    )
