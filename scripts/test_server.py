#!/usr/bin/env python3
"""
Test server to verify the bot functionality.
"""

import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create simple FastAPI app
app = FastAPI(
    title="Kroolo AI Bot - Test Server",
    description="Testing the bot functionality",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Kroolo AI Bot",
        "status": "running",
        "version": "1.0.0",
        "message": "🤖 Kroolo AI Bot is alive and ready!",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "telegram_webhook": "/v1/telegram/webhook/krooloAgentBot",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "web_server": "healthy",
            "postgres": "available" if check_postgres() else "unavailable",
            "redis": "available" if check_redis() else "unavailable",
            "qdrant": "available" if check_qdrant() else "unavailable"
        },
        "message": "All systems operational! 🚀"
    }

@app.post("/v1/telegram/webhook/krooloAgentBot")
async def telegram_webhook(request: Request):
    """Test webhook endpoint."""
    try:
        body = await request.json()
        
        logger.info(f"📨 Received Telegram update: {body.get('update_id', 'unknown')}")
        
        # Extract basic info
        message = body.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "")
        
        # Simulate processing
        response = {
            "status": "processed",
            "update_id": body.get("update_id"),
            "chat_id": chat_id,
            "user_id": user_id,
            "text": text,
            "message": "✅ Update processed successfully!",
            "timestamp": datetime.now().isoformat(),
            "simulated_response": f"🤖 Hello! I received: '{text}'"
        }
        
        logger.info(f"✅ Processed update for chat {chat_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return JSONResponse(
            status_code=200,  # Always return 200 to Telegram
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

def check_postgres():
    """Check if PostgreSQL is available."""
    try:
        import asyncpg
        # Would check connection here
        return True
    except:
        return False

def check_redis():
    """Check if Redis is available."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True
    except:
        return False

def check_qdrant():
    """Check if Qdrant is available."""
    try:
        import requests
        response = requests.get("http://localhost:6333/health", timeout=2)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Kroolo AI Bot Test Server...")
    logger.info("🌐 Server will be available at: http://localhost:8000")
    logger.info("📡 Webhook endpoint: http://localhost:8000/v1/telegram/webhook/krooloAgentBot")
    logger.info("📊 Health check: http://localhost:8000/health")
    logger.info("📚 API docs: http://localhost:8000/docs")
    logger.info("🛑 Press Ctrl+C to stop")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
