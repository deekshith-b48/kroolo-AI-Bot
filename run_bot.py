#!/usr/bin/env python3
"""
Kroolo Agent Bot Startup Script
This script properly initializes the bot with polling for local development
"""

import asyncio
import uvicorn
from app import app, startup_event, shutdown_event

async def main():
    """Main startup function"""
    print("🚀 Starting Kroolo Agent Bot with polling...")
    
    # Run startup event
    await startup_event()
    
    # Start uvicorn server
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
