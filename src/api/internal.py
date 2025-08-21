"""
Internal Microservice APIs
Handles communication between internal services like normalizer, router, and agents.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.core.event_router import event_router
from src.core.intent_classifier import intent_classifier, Intent
from src.core.agent_manager import agent_manager
from src.core.rag_service import rag_service
from src.core.metrics_collector import metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/v1", tags=["internal"])

# Request/Response Models

class NormalizeRequest(BaseModel):
    """Request model for message normalization."""
    raw_update: Dict[str, Any]

class NormalizeResponse(BaseModel):
    """Response model for message normalization."""
    normalized_event: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class RouteRequest(BaseModel):
    """Request model for message routing."""
    chat_id: int
    user_id: Optional[int] = None
    text: str
    entities: List[Dict[str, Any]] = []
    message_type: str = "text"

class RouteResponse(BaseModel):
    """Response model for message routing."""
    route: str
    agent_id: Optional[str] = None
    agent_handle: Optional[str] = None
    intent: str
    confidence: float
    route_reason: str

class AgentInvokeRequest(BaseModel):
    """Request model for agent invocation."""
    chat_id: int
    user_id: int
    message: str
    context_refs: List[str] = []
    request_meta: Dict[str, Any] = {}

class AgentInvokeResponse(BaseModel):
    """Response model for agent invocation."""
    reply_text: str
    reply_format: str = "markdown"
    sources: List[str] = []
    safety_flags: List[str] = []
    processing_time_ms: float
    agent_id: str
    success: bool

class DeliveryRequest(BaseModel):
    """Request model for message delivery."""
    chat_id: int
    text: str
    reply_to_message_id: Optional[int] = None
    parse_mode: str = "MarkdownV2"
    inline_keyboard: Optional[List[List[str]]] = None
    disable_web_page_preview: bool = True

class DeliveryResponse(BaseModel):
    """Response model for message delivery."""
    telegram_message_id: int
    timestamp: str
    success: bool
    error: Optional[str] = None

# Internal API Endpoints

@router.post("/ingest/normalize", response_model=NormalizeResponse)
async def normalize_message(request: NormalizeRequest):
    """
    Normalize a raw Telegram update into standard schema.
    Used by webhook gateway for message preprocessing.
    """
    try:
        start_time = time.time()
        
        # Extract message from raw update
        raw_update = request.raw_update
        
        # This would typically be handled by the webhook directly
        # but providing API for testing and debugging
        normalized_event = {
            "update_id": raw_update.get("update_id"),
            "chat_id": raw_update.get("message", {}).get("chat", {}).get("id"),
            "user_id": raw_update.get("message", {}).get("from", {}).get("id"),
            "text": raw_update.get("message", {}).get("text", ""),
            "entities": raw_update.get("message", {}).get("entities", []),
            "message_type": "text",
            "timestamp": datetime.now().isoformat(),
            "raw": raw_update
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return NormalizeResponse(
            normalized_event=normalized_event,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Normalization failed: {e}")
        return NormalizeResponse(
            normalized_event={},
            success=False,
            error=str(e)
        )

@router.post("/router/route", response_model=RouteResponse)
async def route_message(request: RouteRequest):
    """
    Determine routing for a normalized message.
    Returns which agent or service should handle the message.
    """
    try:
        # Classify intent
        intent = await intent_classifier.classify_intent(request.text)
        
        # Determine routing based on message content
        route = "unknown"
        agent_id = None
        agent_handle = None
        confidence = 0.5
        route_reason = "default"
        
        # Check for mentions
        mentions = []
        for entity in request.entities:
            if entity.get("type") == "mention":
                mention_text = request.text[entity["offset"]:entity["offset"] + entity["length"]]
                mentions.append(mention_text)
        
        if mentions:
            # Route to mentioned agent
            for mention in mentions:
                agent_handle = mention.lstrip("@")
                agent = await agent_manager.get_agent(agent_handle)
                if agent:
                    route = "agent"
                    agent_id = agent.id if hasattr(agent, 'id') else agent_handle
                    confidence = 0.9
                    route_reason = f"explicit_mention:{mention}"
                    break
        
        # Check for slash commands
        elif request.text.startswith("/"):
            command = request.text.split()[0].lower()
            if command == "/quiz":
                route = "quiz"
                agent_handle = "quizmaster"
                confidence = 0.95
                route_reason = "slash_command:/quiz"
            elif command == "/news":
                route = "news"
                agent_handle = "newsreporter"
                confidence = 0.95
                route_reason = "slash_command:/news"
            elif command == "/debate":
                route = "debate"
                agent_handle = "debatebot"
                confidence = 0.95
                route_reason = "slash_command:/debate"
            elif command == "/help":
                route = "help"
                confidence = 0.95
                route_reason = "slash_command:/help"
        
        # Route based on intent classification
        else:
            if intent == Intent.NEWS:
                route = "news"
                agent_handle = "newsreporter"
                confidence = 0.8
                route_reason = "intent_classification:news"
            elif intent == Intent.QUIZ:
                route = "quiz"
                agent_handle = "quizmaster"
                confidence = 0.8
                route_reason = "intent_classification:quiz"
            elif intent == Intent.DEBATE:
                route = "debate"
                agent_handle = "debatebot"
                confidence = 0.8
                route_reason = "intent_classification:debate"
            elif intent == Intent.FUN:
                route = "fun"
                agent_handle = "funagent"
                confidence = 0.8
                route_reason = "intent_classification:fun"
            elif intent == Intent.PERSONA_CHAT:
                route = "persona"
                agent_handle = "alanturing"
                confidence = 0.7
                route_reason = "intent_classification:persona"
            else:
                route = "default"
                agent_handle = "alanturing"  # Default to persona agent
                confidence = 0.5
                route_reason = "fallback_to_default"
        
        return RouteResponse(
            route=route,
            agent_id=agent_id,
            agent_handle=agent_handle,
            intent=intent.value,
            confidence=confidence,
            route_reason=route_reason
        )
        
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")

@router.post("/agents/{agent_id}/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(agent_id: str, request: AgentInvokeRequest):
    """
    Invoke a specific agent to process a message.
    Returns the agent's response with metadata.
    """
    try:
        start_time = time.time()
        
        # Get agent instance
        agent = await agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Prepare message info
        message_info = {
            "chat_id": request.chat_id,
            "user_id": request.user_id,
            "text": request.message,
            "message_type": "text"
        }
        
        # Prepare agent context
        agent_context = {
            "user_history": [],
            "chat_context": [],
            "agent_memory": {},
            "context_refs": request.context_refs,
            "request_meta": request.request_meta
        }
        
        # Process message through agent
        result = await agent.process_message(message_info, agent_context)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Record agent response metrics
        await metrics_collector.record_agent_response(
            {"agent_type": agent.agent_type, "handle": agent_id},
            {
                "response_time": processing_time / 1000,
                "response_size": len(result.get("response", "")),
                "success": result.get("success", False)
            }
        )
        
        return AgentInvokeResponse(
            reply_text=result.get("response", ""),
            reply_format=result.get("format", "markdown"),
            sources=result.get("sources", []),
            safety_flags=result.get("safety_flags", []),
            processing_time_ms=processing_time,
            agent_id=agent_id,
            success=result.get("success", False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent invocation failed for {agent_id}: {e}")
        await metrics_collector.record_error({
            "error_type": "agent_invocation_failed",
            "agent_type": agent_id,
            "chat_id": request.chat_id,
            "user_id": request.user_id
        })
        raise HTTPException(status_code=500, detail=f"Agent invocation failed: {str(e)}")

@router.post("/delivery/send", response_model=DeliveryResponse)
async def send_message(request: DeliveryRequest):
    """
    Send a message via Telegram API with proper formatting and error handling.
    """
    try:
        from src.core.telegram_client import telegram_client
        
        # Prepare message data
        message_data = {
            "chat_id": request.chat_id,
            "text": request.text,
            "parse_mode": request.parse_mode,
            "disable_web_page_preview": request.disable_web_page_preview
        }
        
        if request.reply_to_message_id:
            message_data["reply_to_message_id"] = request.reply_to_message_id
        
        if request.inline_keyboard:
            # Convert to Telegram inline keyboard format
            keyboard = {
                "inline_keyboard": [
                    [{"text": button, "callback_data": button} for button in row]
                    for row in request.inline_keyboard
                ]
            }
            message_data["reply_markup"] = keyboard
        
        # Send message
        result = await telegram_client.send_message(**message_data)
        
        return DeliveryResponse(
            telegram_message_id=result.get("message_id", 0),
            timestamp=datetime.now().isoformat(),
            success=True
        )
        
    except Exception as e:
        logger.error(f"Message delivery failed: {e}")
        return DeliveryResponse(
            telegram_message_id=0,
            timestamp=datetime.now().isoformat(),
            success=False,
            error=str(e)
        )

@router.get("/health")
async def internal_health():
    """Health check for internal services."""
    try:
        # Check component health
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "event_router": "healthy",
                "intent_classifier": "healthy",
                "agent_manager": "healthy",
                "rag_service": "healthy" if rag_service.is_initialized else "degraded",
                "metrics_collector": "healthy" if metrics_collector.is_initialized else "degraded"
            }
        }
        
        # Check if any components are unhealthy
        unhealthy_components = [
            comp for comp, status in health_status["components"].items()
            if status not in ["healthy", "degraded"]
        ]
        
        if unhealthy_components:
            health_status["status"] = "unhealthy"
            health_status["unhealthy_components"] = unhealthy_components
        elif any(status == "degraded" for status in health_status["components"].values()):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
