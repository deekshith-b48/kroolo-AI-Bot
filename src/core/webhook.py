"""
Webhook receiver for Telegram updates.
Handles incoming messages and routes them to appropriate handlers.
"""

import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from config.settings import settings
from .telegram_client import TelegramClient
from .event_router import EventRouter
from .rate_limiter import RateLimiter
from .security import verify_telegram_signature

logger = logging.getLogger(__name__)


class TelegramUpdate(BaseModel):
    """Telegram update model."""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None
    inline_query: Optional[Dict[str, Any]] = None
    chosen_inline_result: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None
    shipping_query: Optional[Dict[str, Any]] = None
    pre_checkout_query: Optional[Dict[str, Any]] = None
    poll: Optional[Dict[str, Any]] = None
    poll_answer: Optional[Dict[str, Any]] = None
    my_chat_member: Optional[Dict[str, Any]] = None
    chat_member: Optional[Dict[str, Any]] = None
    chat_join_request: Optional[Dict[str, Any]] = None


class WebhookReceiver:
    """Handles incoming Telegram webhook updates."""
    
    def __init__(self):
        self.telegram_client = TelegramClient()
        self.event_router = EventRouter()
        self.rate_limiter = RateLimiter()
        
    async def process_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Telegram update."""
        try:
            # Validate update structure
            update = TelegramUpdate(**update_data)
            
            # Extract message information
            message_info = self._extract_message_info(update)
            if not message_info:
                return {"status": "ignored", "reason": "no_message_content"}
            
            # Rate limiting check
            if not await self.rate_limiter.check_rate_limit(message_info):
                return {"status": "rate_limited", "reason": "too_many_requests"}
            
            # Route to appropriate handler
            result = await self.event_router.route_update(update, message_info)
            
            return {
                "status": "processed",
                "update_id": update.update_id,
                "result": result
            }
            
        except ValidationError as e:
            logger.error(f"Invalid update format: {e}")
            return {"status": "error", "reason": "invalid_format", "details": str(e)}
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return {"status": "error", "reason": "processing_error", "details": str(e)}
    
    def _extract_message_info(self, update: TelegramUpdate) -> Optional[Dict[str, Any]]:
        """Extract relevant message information from update."""
        if update.message:
            return {
                "type": "message",
                "chat_id": update.message.get("chat", {}).get("id"),
                "user_id": update.message.get("from", {}).get("id"),
                "text": update.message.get("text"),
                "message_id": update.message.get("message_id"),
                "chat_type": update.message.get("chat", {}).get("type"),
                "is_private": update.message.get("chat", {}).get("type") == "private"
            }
        elif update.callback_query:
            return {
                "type": "callback_query",
                "chat_id": update.callback_query.get("message", {}).get("chat", {}).get("id"),
                "user_id": update.callback_query.get("from", {}).get("id"),
                "data": update.callback_query.get("data"),
                "message_id": update.callback_query.get("message", {}).get("message_id")
            }
        elif update.inline_query:
            return {
                "type": "inline_query",
                "user_id": update.inline_query.get("from", {}).get("id"),
                "query": update.inline_query.get("query"),
                "inline_query_id": update.inline_query.get("id")
            }
        
        return None


# FastAPI app instance
app = FastAPI(
    title="Kroolo AI Bot Webhook",
    description="Webhook receiver for Telegram multi-agent bot",
    version="1.0.0"
)

# Global webhook receiver instance
webhook_receiver = WebhookReceiver()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "webhook_receiver"}


@app.post("/webhook")
async def webhook_handler(
    request: Request,
    signature: str = Depends(verify_telegram_signature)
):
    """Handle incoming Telegram webhook."""
    try:
        # Parse request body
        body = await request.body()
        update_data = json.loads(body)
        
        # Process update
        result = await webhook_receiver.process_update(update_data)
        
        # Return success response
        return JSONResponse(content=result, status_code=200)
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/webhook")
async def webhook_info():
    """Get webhook information."""
    return {
        "webhook_url": settings.telegram_webhook_url,
        "status": "active",
        "supported_updates": [
            "message", "edited_message", "channel_post", "edited_channel_post",
            "inline_query", "chosen_inline_result", "callback_query",
            "shipping_query", "pre_checkout_query", "poll", "poll_answer",
            "my_chat_member", "chat_member", "chat_join_request"
        ]
    }


@app.delete("/webhook")
async def delete_webhook():
    """Delete webhook (for testing purposes)."""
    try:
        result = await webhook_receiver.telegram_client.delete_webhook()
        return {"status": "deleted", "result": result}
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail="Error deleting webhook")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
