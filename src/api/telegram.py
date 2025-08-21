"""
Telegram Webhook API Implementation
Handles incoming Telegram updates with proper validation and normalization.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from pydantic import BaseModel, Field

from config.settings import settings
from src.core.security import verify_telegram_signature, sanitize_input
from src.core.rate_limiter import rate_limiter
from src.core.event_router import event_router
from src.core.metrics_collector import metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])

class TelegramUpdate(BaseModel):
    """Pydantic model for Telegram update validation."""
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

class NormalizedEvent(BaseModel):
    """Normalized event structure for internal processing."""
    idempotency_key: str = Field(..., description="Unique key for deduplication")
    update_id: int
    chat_id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    text: Optional[str] = None
    entities: Optional[list] = None
    message_type: str
    timestamp: str
    reply_to_message_id: Optional[int] = None
    raw: Dict[str, Any] = Field(..., description="Original Telegram update")

def extract_message_data(update: TelegramUpdate) -> Optional[Dict[str, Any]]:
    """Extract message data from various update types."""
    message_sources = [
        update.message,
        update.edited_message,
        update.channel_post,
        update.edited_channel_post
    ]
    
    for message in message_sources:
        if message:
            return message
    
    # Handle callback queries
    if update.callback_query:
        return {
            "message_id": update.callback_query.get("id"),
            "chat": update.callback_query.get("message", {}).get("chat", {}),
            "from": update.callback_query.get("from", {}),
            "text": update.callback_query.get("data", ""),
            "date": int(time.time()),
            "callback_query": True
        }
    
    return None

def normalize_update(update: TelegramUpdate) -> Optional[NormalizedEvent]:
    """Convert raw Telegram update to normalized event."""
    try:
        message = extract_message_data(update)
        if not message:
            logger.warning(f"No extractable message from update {update.update_id}")
            return None
        
        chat = message.get("chat", {})
        user = message.get("from", {})
        
        chat_id = chat.get("id")
        user_id = user.get("id")
        
        if not chat_id:
            logger.warning(f"No chat_id in update {update.update_id}")
            return None
        
        # Create idempotency key
        idempotency_key = f"telegram:{chat_id}:{update.update_id}"
        
        # Determine message type
        message_type = "text"
        if message.get("photo"):
            message_type = "photo"
        elif message.get("document"):
            message_type = "document"
        elif message.get("voice"):
            message_type = "voice"
        elif message.get("video"):
            message_type = "video"
        elif message.get("sticker"):
            message_type = "sticker"
        elif message.get("poll"):
            message_type = "poll"
        elif message.get("callback_query"):
            message_type = "callback_query"
        
        # Extract and sanitize text
        text = message.get("text", "")
        if text:
            text = sanitize_input(text, max_length=4096)
        
        # Create normalized event
        normalized_event = NormalizedEvent(
            idempotency_key=idempotency_key,
            update_id=update.update_id,
            chat_id=chat_id,
            user_id=user_id,
            username=user.get("username"),
            text=text,
            entities=message.get("entities", []),
            message_type=message_type,
            timestamp=datetime.now().isoformat(),
            reply_to_message_id=message.get("reply_to_message", {}).get("message_id"),
            raw=update.dict()
        )
        
        return normalized_event
        
    except Exception as e:
        logger.error(f"Failed to normalize update {update.update_id}: {e}")
        return None

@router.post("/webhook/krooloAgentBot")
async def telegram_webhook(
    request: Request,
    update_data: TelegramUpdate,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Main Telegram webhook endpoint.
    
    Accepts raw Telegram updates, validates, normalizes, and enqueues for processing.
    Returns 200 OK immediately to prevent Telegram retries.
    """
    start_time = time.time()
    
    try:
        # Verify webhook signature
        if not await verify_telegram_signature(request, x_telegram_bot_api_secret_token):
            await metrics_collector.record_error({
                "error_type": "webhook_auth_failed",
                "chat_id": None,
                "user_id": None
            })
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Normalize the update
        normalized_event = normalize_update(update_data)
        if not normalized_event:
            logger.warning(f"Could not normalize update {update_data.update_id}")
            return {"status": "ignored", "reason": "unnormalizable_update"}
        
        # Check rate limits
        message_info = {
            "user_id": normalized_event.user_id,
            "chat_id": normalized_event.chat_id,
            "message_type": normalized_event.message_type
        }
        
        if not await rate_limiter.check_rate_limit(message_info):
            await metrics_collector.record_rate_limit({
                "limit_type": "webhook",
                "user_id": normalized_event.user_id,
                "chat_id": normalized_event.chat_id
            })
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Record message metrics
        await metrics_collector.record_message({
            "message_type": normalized_event.message_type,
            "chat_type": "group" if normalized_event.chat_id < 0 else "private",
            "chat_id": normalized_event.chat_id,
            "user_id": normalized_event.user_id
        })
        
        # Route the message for processing
        await event_router.route_message(normalized_event.dict())
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        logger.info(
            f"Webhook processed update {update_data.update_id} "
            f"for chat {normalized_event.chat_id} in {processing_time:.3f}s"
        )
        
        return {
            "status": "ok",
            "update_id": update_data.update_id,
            "processing_time_ms": round(processing_time * 1000, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error for update {update_data.update_id}: {e}")
        await metrics_collector.record_error({
            "error_type": "webhook_processing_error",
            "chat_id": getattr(normalized_event, 'chat_id', None) if 'normalized_event' in locals() else None,
            "user_id": getattr(normalized_event, 'user_id', None) if 'normalized_event' in locals() else None
        })
        
        # Return 200 to prevent Telegram retries for our internal errors
        return {
            "status": "error",
            "error": "internal_processing_error",
            "update_id": update_data.update_id
        }

@router.get("/webhook/info")
async def webhook_info():
    """Get webhook configuration information."""
    return {
        "webhook_url": settings.telegram_webhook_url,
        "bot_username": settings.telegram_bot_username or "krooloAgentBot",
        "status": "active"
    }

@router.delete("/webhook")
async def delete_webhook():
    """Delete webhook configuration."""
    # This would typically call Telegram's deleteWebhook API
    return {"status": "webhook_deleted"}

@router.get("/health")
async def webhook_health():
    """Health check endpoint for the webhook service."""
    return {
        "status": "healthy",
        "service": "telegram_webhook",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
