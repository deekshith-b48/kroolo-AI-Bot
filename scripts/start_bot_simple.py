#!/usr/bin/env python3
"""
Simple bot startup script for testing functionality.
Starts the bot with minimal configuration.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def start_simple_bot():
    """Start the bot with minimal configuration for testing."""
    try:
        logger.info("🚀 Starting Kroolo AI Bot (Simple Mode)...")
        
        # Import the main FastAPI app
        from src.main_with_apis import app
        
        logger.info("✅ FastAPI app imported successfully")
        
        # Start uvicorn server
        import uvicorn
        
        logger.info("🌐 Starting web server on http://localhost:8000")
        logger.info("📡 Webhook endpoint: http://localhost:8000/v1/telegram/webhook/krooloAgentBot")
        logger.info("📊 Health check: http://localhost:8000/health")
        logger.info("📚 API docs: http://localhost:8000/docs")
        
        # Run the server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(start_simple_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
