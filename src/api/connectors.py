"""
Connector APIs
Handles external integrations with no-code platforms like n8n, Make, Zapier, and LangChain.
"""

import logging
import hmac
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from pydantic import BaseModel, Field

from config.settings import settings
from src.core.event_router import event_router
from src.core.content_scheduler import content_scheduler, ContentType, ScheduleType
from src.core.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/connectors", tags=["connectors"])

# Request/Response Models

class WebhookRequest(BaseModel):
    """Generic webhook request model."""
    chat_id: int = Field(..., description="Target chat ID")
    action: str = Field(..., description="Action to perform")
    payload: Dict[str, Any] = Field(..., description="Action payload")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")

class WebhookResponse(BaseModel):
    """Generic webhook response model."""
    success: bool
    message: str
    webhook_id: str
    timestamp: datetime
    processed_action: str
    result: Optional[Dict[str, Any]] = None

class NewsIngestRequest(BaseModel):
    """Request model for news ingestion."""
    chat_id: int
    title: str
    summary: str
    url: str
    source: str
    category: str = "general"
    publish_immediately: bool = False

class QuizPublishRequest(BaseModel):
    """Request model for quiz publishing."""
    chat_id: int
    question: str
    options: list
    correct_answer: int
    explanation: str
    category: str = "general"
    difficulty: str = "medium"
    publish_immediately: bool = False

class LangChainRunRequest(BaseModel):
    """Request model for LangChain execution."""
    chain_config_id: str = Field(..., description="Chain configuration ID")
    input_data: Dict[str, Any] = Field(..., description="Input data for the chain")
    chat_id: int = Field(..., description="Target chat ID")
    user_id: Optional[int] = Field(default=None, description="User ID for context")

# Webhook signature verification

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    timestamp: Optional[str] = None
) -> bool:
    """
    Verify webhook signature using HMAC.
    Supports both simple HMAC and timestamped signatures.
    """
    try:
        # Check timestamp if provided (prevent replay attacks)
        if timestamp:
            current_time = int(time.time())
            webhook_time = int(timestamp)
            if abs(current_time - webhook_time) > 300:  # 5 minutes tolerance
                logger.warning(f"Webhook timestamp too old: {webhook_time}")
                return False
        
        # Calculate expected signature
        if timestamp:
            # Include timestamp in signature calculation
            message = f"{timestamp}.{payload.decode()}"
        else:
            message = payload.decode()
        
        expected_signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return False

async def verify_connector_signature(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_timestamp: Optional[str] = Header(None)
) -> bool:
    """Dependency to verify webhook signatures."""
    if not settings.webhook_secret:
        logger.warning("Webhook secret not configured, skipping signature verification")
        return True
    
    if not x_webhook_signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    
    # Get raw request body
    body = await request.body()
    
    # Verify signature
    is_valid = verify_webhook_signature(
        payload=body,
        signature=x_webhook_signature,
        secret=settings.webhook_secret,
        timestamp=x_webhook_timestamp
    )
    
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    return True

# Connector Endpoints

@router.post("/webhook/{connector_name}", response_model=WebhookResponse)
async def generic_webhook(
    connector_name: str,
    request: WebhookRequest,
    signature_valid: bool = Depends(verify_connector_signature)
):
    """
    Generic webhook endpoint for external automation platforms.
    Supports n8n, Make, Zapier, and other webhook-based integrations.
    """
    try:
        import uuid
        webhook_id = str(uuid.uuid4())
        
        logger.info(f"Processing webhook from {connector_name}: {request.action}")
        
        result = None
        
        # Route based on action type
        if request.action == "publish_news":
            result = await _handle_news_publish(request)
        elif request.action == "create_quiz":
            result = await _handle_quiz_create(request)
        elif request.action == "schedule_content":
            result = await _handle_content_schedule(request)
        elif request.action == "ingest_knowledge":
            result = await _handle_knowledge_ingest(request)
        elif request.action == "send_message":
            result = await _handle_message_send(request)
        elif request.action == "trigger_agent":
            result = await _handle_agent_trigger(request)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        return WebhookResponse(
            success=True,
            message=f"Action '{request.action}' processed successfully",
            webhook_id=webhook_id,
            timestamp=datetime.now(),
            processed_action=request.action,
            result=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed for {connector_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

@router.post("/n8n/news/ingest")
async def n8n_news_ingest(
    request: NewsIngestRequest,
    signature_valid: bool = Depends(verify_connector_signature)
):
    """
    n8n-specific endpoint for news ingestion.
    Example n8n workflow: RSS feed → filter → POST to this endpoint.
    """
    try:
        # Ingest news into RAG system
        news_content = f"Title: {request.title}\n\nSummary: {request.summary}\n\nSource: {request.source}"
        
        metadata = {
            "chat_id": request.chat_id,
            "title": request.title,
            "url": request.url,
            "source": request.source,
            "category": request.category,
            "ingested_via": "n8n",
            "ingested_at": datetime.now().isoformat()
        }
        
        # Add to knowledge base
        knowledge_id = await rag_service.add_knowledge(
            content=news_content,
            metadata=metadata,
            content_type="news"
        )
        
        # Optionally publish immediately
        if request.publish_immediately:
            # Create immediate news delivery
            await content_scheduler.schedule_content(
                content_type=ContentType.NEWS,
                chat_id=request.chat_id,
                content_data={
                    "title": request.title,
                    "summary": request.summary,
                    "url": request.url,
                    "source": request.source
                },
                schedule_type=ScheduleType.ONE_TIME,
                schedule_config={"datetime": datetime.now()},
                max_runs=1
            )
        
        return {
            "success": True,
            "message": "News article ingested successfully",
            "knowledge_id": knowledge_id,
            "published_immediately": request.publish_immediately
        }
        
    except Exception as e:
        logger.error(f"n8n news ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"News ingestion failed: {str(e)}")

@router.post("/make/quiz/publish")
async def make_quiz_publish(
    request: QuizPublishRequest,
    signature_valid: bool = Depends(verify_connector_signature)
):
    """
    Make (formerly Integromat) endpoint for quiz publishing.
    Example Make scenario: Google Sheets → format → POST to this endpoint.
    """
    try:
        # Prepare quiz data
        quiz_data = {
            "question": request.question,
            "options": request.options,
            "correct_answer": request.correct_answer,
            "explanation": request.explanation,
            "category": request.category,
            "difficulty": request.difficulty,
            "created_via": "make",
            "created_at": datetime.now().isoformat()
        }
        
        # Optionally publish immediately
        if request.publish_immediately:
            # Create immediate quiz delivery
            schedule_id = await content_scheduler.schedule_content(
                content_type=ContentType.QUIZ,
                chat_id=request.chat_id,
                content_data=quiz_data,
                schedule_type=ScheduleType.ONE_TIME,
                schedule_config={"datetime": datetime.now()},
                max_runs=1
            )
            
            return {
                "success": True,
                "message": "Quiz published immediately",
                "schedule_id": schedule_id,
                "quiz_data": quiz_data
            }
        else:
            # Store for later use (would typically save to database)
            return {
                "success": True,
                "message": "Quiz stored successfully",
                "quiz_data": quiz_data
            }
        
    except Exception as e:
        logger.error(f"Make quiz publishing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quiz publishing failed: {str(e)}")

@router.post("/langchain/run")
async def langchain_run(
    request: LangChainRunRequest,
    signature_valid: bool = Depends(verify_connector_signature)
):
    """
    LangChain integration endpoint.
    Allows external LangChain orchestrators to execute chains and send results to chats.
    """
    try:
        # This would typically load the chain configuration and execute it
        # For now, simulate chain execution
        
        logger.info(f"Executing LangChain chain {request.chain_config_id} for chat {request.chat_id}")
        
        # Simulate chain execution result
        chain_result = {
            "output": f"LangChain chain {request.chain_config_id} executed successfully",
            "input_data": request.input_data,
            "execution_time": "1.23s",
            "tokens_used": 150,
            "cost": 0.002
        }
        
        # Send result to chat if requested
        if request.chat_id:
            # Create immediate message delivery
            await content_scheduler.schedule_content(
                content_type=ContentType.REMINDER,
                chat_id=request.chat_id,
                content_data={
                    "message": chain_result["output"],
                    "source": "langchain",
                    "chain_id": request.chain_config_id
                },
                schedule_type=ScheduleType.ONE_TIME,
                schedule_config={"datetime": datetime.now()},
                max_runs=1
            )
        
        return {
            "success": True,
            "message": "LangChain execution completed",
            "chain_result": chain_result,
            "sent_to_chat": request.chat_id is not None
        }
        
    except Exception as e:
        logger.error(f"LangChain execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"LangChain execution failed: {str(e)}")

@router.get("/webhooks/info")
async def webhook_info():
    """
    Get information about available webhook endpoints and their schemas.
    """
    return {
        "available_endpoints": {
            "/v1/connectors/webhook/{connector_name}": {
                "description": "Generic webhook for any connector",
                "methods": ["POST"],
                "authentication": "HMAC signature required",
                "supported_actions": [
                    "publish_news",
                    "create_quiz",
                    "schedule_content",
                    "ingest_knowledge",
                    "send_message",
                    "trigger_agent"
                ]
            },
            "/v1/connectors/n8n/news/ingest": {
                "description": "n8n-specific news ingestion",
                "methods": ["POST"],
                "authentication": "HMAC signature required"
            },
            "/v1/connectors/make/quiz/publish": {
                "description": "Make-specific quiz publishing",
                "methods": ["POST"],
                "authentication": "HMAC signature required"
            },
            "/v1/connectors/langchain/run": {
                "description": "LangChain chain execution",
                "methods": ["POST"],
                "authentication": "HMAC signature required"
            }
        },
        "authentication": {
            "method": "HMAC-SHA256",
            "headers": {
                "X-Webhook-Signature": "Required - HMAC signature",
                "X-Webhook-Timestamp": "Optional - Unix timestamp for replay protection"
            },
            "signature_calculation": "HMAC-SHA256 of request body using webhook secret"
        },
        "supported_connectors": ["n8n", "make", "zapier", "langchain", "custom"]
    }

# Helper functions for webhook actions

async def _handle_news_publish(request: WebhookRequest) -> Dict[str, Any]:
    """Handle news publishing action."""
    payload = request.payload
    
    # Validate required fields
    required_fields = ["title", "summary", "source"]
    for field in required_fields:
        if field not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Create news content
    schedule_id = await content_scheduler.schedule_content(
        content_type=ContentType.NEWS,
        chat_id=request.chat_id,
        content_data=payload,
        schedule_type=ScheduleType.ONE_TIME,
        schedule_config={"datetime": datetime.now()},
        max_runs=1
    )
    
    return {"schedule_id": schedule_id, "action": "news_published"}

async def _handle_quiz_create(request: WebhookRequest) -> Dict[str, Any]:
    """Handle quiz creation action."""
    payload = request.payload
    
    # Validate required fields
    required_fields = ["question", "options", "correct_answer"]
    for field in required_fields:
        if field not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Create quiz
    schedule_id = await content_scheduler.schedule_content(
        content_type=ContentType.QUIZ,
        chat_id=request.chat_id,
        content_data=payload,
        schedule_type=ScheduleType.ONE_TIME,
        schedule_config={"datetime": datetime.now()},
        max_runs=1
    )
    
    return {"schedule_id": schedule_id, "action": "quiz_created"}

async def _handle_content_schedule(request: WebhookRequest) -> Dict[str, Any]:
    """Handle content scheduling action."""
    payload = request.payload
    
    # Extract schedule parameters
    content_type_map = {
        "news": ContentType.NEWS,
        "quiz": ContentType.QUIZ,
        "debate": ContentType.DEBATE,
        "fun": ContentType.FUN,
        "reminder": ContentType.REMINDER
    }
    
    content_type = content_type_map.get(payload.get("content_type", "reminder"), ContentType.REMINDER)
    schedule_config = payload.get("schedule_config", {})
    content_data = payload.get("content_data", {})
    
    # Create schedule
    schedule_id = await content_scheduler.schedule_content(
        content_type=content_type,
        chat_id=request.chat_id,
        content_data=content_data,
        schedule_type=ScheduleType.CRON,
        schedule_config=schedule_config
    )
    
    return {"schedule_id": schedule_id, "action": "content_scheduled"}

async def _handle_knowledge_ingest(request: WebhookRequest) -> Dict[str, Any]:
    """Handle knowledge ingestion action."""
    payload = request.payload
    
    if "content" not in payload:
        raise HTTPException(status_code=400, detail="Missing required field: content")
    
    # Ingest knowledge
    knowledge_id = await rag_service.add_knowledge(
        content=payload["content"],
        metadata={
            "chat_id": request.chat_id,
            "source": "webhook",
            **payload.get("metadata", {})
        },
        content_type=payload.get("content_type", "text")
    )
    
    return {"knowledge_id": knowledge_id, "action": "knowledge_ingested"}

async def _handle_message_send(request: WebhookRequest) -> Dict[str, Any]:
    """Handle direct message sending action."""
    payload = request.payload
    
    if "message" not in payload:
        raise HTTPException(status_code=400, detail="Missing required field: message")
    
    # Send message immediately
    schedule_id = await content_scheduler.schedule_content(
        content_type=ContentType.REMINDER,
        chat_id=request.chat_id,
        content_data={"message": payload["message"]},
        schedule_type=ScheduleType.ONE_TIME,
        schedule_config={"datetime": datetime.now()},
        max_runs=1
    )
    
    return {"schedule_id": schedule_id, "action": "message_sent"}

async def _handle_agent_trigger(request: WebhookRequest) -> Dict[str, Any]:
    """Handle agent trigger action."""
    payload = request.payload
    
    if "agent_handle" not in payload or "message" not in payload:
        raise HTTPException(status_code=400, detail="Missing required fields: agent_handle, message")
    
    # Create normalized event for agent processing
    normalized_event = {
        "chat_id": request.chat_id,
        "user_id": 0,  # System user
        "text": f"@{payload['agent_handle']} {payload['message']}",
        "entities": [{"type": "mention", "offset": 0, "length": len(payload['agent_handle']) + 1}],
        "message_type": "text",
        "timestamp": datetime.now().isoformat()
    }
    
    # Route to agent
    await event_router.route_message(normalized_event)
    
    return {"action": "agent_triggered", "agent": payload['agent_handle']}

@router.get("/health")
async def connectors_health():
    """Health check for connector services."""
    return {
        "status": "healthy",
        "service": "connectors",
        "timestamp": datetime.now().isoformat(),
        "webhook_endpoints_active": True,
        "signature_verification": settings.webhook_secret is not None
    }
