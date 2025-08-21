"""
Main application entry point for the Kroolo AI Bot.
Initializes all services and starts the FastAPI server.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from core.webhook import app as webhook_app
from core.agent_manager import AgentManager
from core.telegram_client import TelegramClient
from core.scheduler import ContentScheduler
from core.monitoring import MetricsCollector
from database.session import init_database
from utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
agent_manager: AgentManager = None
telegram_client: TelegramClient = None
content_scheduler: ContentScheduler = None
metrics_collector: MetricsCollector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent_manager, telegram_client, content_scheduler, metrics_collector
    
    # Startup
    logger.info("Starting Kroolo AI Bot...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Initialize services
        agent_manager = AgentManager()
        await agent_manager.initialize()
        logger.info("Agent manager initialized")
        
        telegram_client = TelegramClient()
        await telegram_client.initialize()
        logger.info("Telegram client initialized")
        
        content_scheduler = ContentScheduler()
        await content_scheduler.initialize()
        logger.info("Content scheduler initialized")
        
        metrics_collector = MetricsCollector()
        await metrics_collector.initialize()
        logger.info("Metrics collector initialized")
        
        # Set webhook
        if settings.environment == "production":
            await telegram_client.set_webhook(settings.telegram_webhook_url)
            logger.info("Webhook set successfully")
        
        logger.info("Kroolo AI Bot started successfully!")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Kroolo AI Bot...")
    
    try:
        if content_scheduler:
            await content_scheduler.shutdown()
        
        if telegram_client:
            await telegram_client.shutdown()
        
        if metrics_collector:
            await metrics_collector.shutdown()
        
        logger.info("Shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Kroolo AI Bot",
    description="Multi-agent Telegram bot with AI personas, news, quizzes, and debates",
    version=settings.app_version,
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

# Include webhook routes
app.include_router(webhook_app, prefix="/webhook", tags=["webhook"])

# Include admin API routes
from src.api.admin import router as admin_router
app.include_router(admin_router, tags=["admin"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Kroolo AI Bot",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {}
    }
    
    try:
        # Check agent manager
        if agent_manager:
            agent_status = agent_manager.get_agent_status()
            health_status["services"]["agent_manager"] = {
                "status": "healthy" if agent_status["initialized"] else "unhealthy",
                "total_agents": agent_status["total_agents"]
            }
        else:
            health_status["services"]["agent_manager"] = {"status": "not_initialized"}
        
        # Check telegram client
        if telegram_client:
            telegram_health = await telegram_client.health_check()
            health_status["services"]["telegram_client"] = telegram_health
        else:
            health_status["services"]["telegram_client"] = {"status": "not_initialized"}
        
        # Check content scheduler
        if content_scheduler:
            scheduler_health = await content_scheduler.health_check()
            health_status["services"]["content_scheduler"] = scheduler_health
        else:
            health_status["services"]["content_scheduler"] = {"status": "not_initialized"}
        
        # Check metrics collector
        if metrics_collector:
            metrics_health = await metrics_collector.health_check()
            health_status["services"]["metrics_collector"] = metrics_health
        else:
            health_status["services"]["metrics_collector"] = {"status": "not_initialized"}
        
        # Overall status
        all_healthy = all(
            service.get("status") == "healthy" 
            for service in health_status["services"].values()
        )
        
        if not all_healthy:
            health_status["status"] = "degraded"
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status


@app.get("/status")
async def status():
    """Get detailed system status."""
    if not agent_manager:
        return {"error": "Agent manager not initialized"}
    
    return {
        "agents": agent_manager.get_agent_status(),
        "telegram": await telegram_client.get_status() if telegram_client else None,
        "scheduler": await content_scheduler.get_status() if content_scheduler else None,
        "metrics": await metrics_collector.get_status() if metrics_collector else None
    }


@app.get("/agents")
async def list_agents():
    """List all available agents."""
    if not agent_manager:
        return {"error": "Agent manager not initialized"}
    
    agents = []
    for handle, agent in agent_manager._agents.items():
        agents.append(agent.get_config_summary())
    
    return {"agents": agents}


@app.post("/agents/{handle}/reload")
async def reload_agent(handle: str):
    """Reload a specific agent configuration."""
    if not agent_manager:
        return {"error": "Agent manager not initialized"}
    
    success = await agent_manager.reload_agent(handle)
    return {"success": success, "agent": handle}


@app.post("/agents/reload")
async def reload_all_agents():
    """Reload all agent configurations."""
    if not agent_manager:
        return {"error": "Agent manager not initialized"}
    
    success = await agent_manager.reload_all_agents()
    return {"success": success}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
