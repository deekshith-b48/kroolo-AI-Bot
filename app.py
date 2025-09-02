"""
Kroolo Agent Bot - Basic API Server
The actual bot runs via kroolo_bot.py using long-polling.
This file provides simple health/status endpoints for Railway deployment.
"""

import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create simple FastAPI app for health checks
app = FastAPI(title="Kroolo Agent Bot API", version="1.0.0")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Kroolo Agent Bot API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "kroolo-agent-bot"}

@app.get("/status")
async def status():
    """Status endpoint"""
        return {
        "status": "running",
        "mode": "long-polling",
        "bot_file": "kroolo_bot.py"
    }

# Simple validation without complex imports
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("Warning: TELEGRAM_BOT_TOKEN not set. Bot will not function properly.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))