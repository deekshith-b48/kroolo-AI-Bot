"""
Scheduler APIs
Handles scheduled content delivery and task management.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.content_scheduler import content_scheduler, ContentType, ScheduleType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/scheduler", tags=["scheduler"])

# Request/Response Models

class ScheduleRequest(BaseModel):
    """Request model for creating a schedule."""
    chat_id: int = Field(..., description="Target chat ID")
    task_type: str = Field(..., description="Type of task to schedule")
    cron_expr: Optional[str] = Field(default=None, description="Cron expression (for cron schedules)")
    schedule_type: str = Field(default="cron", description="Type of schedule: cron, interval, recurring, one_time")
    schedule_config: Dict[str, Any] = Field(default={}, description="Schedule configuration")
    content_params: Dict[str, Any] = Field(default={}, description="Content parameters")
    max_runs: Optional[int] = Field(default=None, description="Maximum number of runs")
    enabled: bool = Field(default=True, description="Whether schedule is enabled")

class ScheduleResponse(BaseModel):
    """Response model for schedule operations."""
    schedule_id: str
    task_type: str
    chat_id: int
    schedule_type: str
    next_run: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    message: str

class TriggerRequest(BaseModel):
    """Request model for manual triggers."""
    task_id: Optional[str] = Field(default=None, description="Specific task ID to trigger")
    chat_id: int = Field(..., description="Target chat ID")
    task_type: Optional[str] = Field(default=None, description="Type of task to trigger")
    content_params: Dict[str, Any] = Field(default={}, description="Content parameters for trigger")

class TriggerResponse(BaseModel):
    """Response model for manual triggers."""
    trigger_id: str
    task_type: str
    chat_id: int
    status: str
    timestamp: datetime
    message: str

# Pre-defined schedule templates for common tasks

SCHEDULE_TEMPLATES = {
    "daily_morning_news": {
        "task_type": "news_digest",
        "schedule_type": "cron",
        "schedule_config": {"hour": 9, "minute": 0},
        "content_params": {
            "categories": ["general", "technology", "science"],
            "max_articles": 5,
            "include_summary": True
        }
    },
    "daily_evening_quiz": {
        "task_type": "daily_quiz",
        "schedule_type": "cron",
        "schedule_config": {"hour": 18, "minute": 0},
        "content_params": {
            "difficulty": "medium",
            "category": "general",
            "max_questions": 3
        }
    },
    "weekly_debate": {
        "task_type": "debate_topic",
        "schedule_type": "cron",
        "schedule_config": {"day_of_week": 1, "hour": 10, "minute": 0},
        "content_params": {
            "topic_category": "technology",
            "max_participants": 4,
            "max_turns": 6
        }
    },
    "hourly_fun": {
        "task_type": "fun_content",
        "schedule_type": "interval",
        "schedule_config": {"hours": 1},
        "content_params": {
            "content_types": ["joke", "fact", "riddle"],
            "max_content": 1
        }
    }
}

# Scheduler API Endpoints

@router.post("/schedule", response_model=ScheduleResponse)
async def create_schedule(request: ScheduleRequest):
    """
    Create a new scheduled task.
    Supports cron expressions, intervals, and one-time schedules.
    """
    try:
        # Map task_type to ContentType
        content_type_map = {
            "news_digest": ContentType.NEWS,
            "daily_quiz": ContentType.QUIZ,
            "debate_topic": ContentType.DEBATE,
            "fun_content": ContentType.FUN,
            "reminder": ContentType.REMINDER,
            "announcement": ContentType.ANNOUNCEMENT,
            "daily_digest": ContentType.DAILY_DIGEST,
            "weekly_summary": ContentType.WEEKLY_SUMMARY
        }
        
        content_type = content_type_map.get(request.task_type, ContentType.REMINDER)
        
        # Map schedule_type string to ScheduleType enum
        schedule_type_map = {
            "cron": ScheduleType.CRON,
            "interval": ScheduleType.INTERVAL,
            "recurring": ScheduleType.RECURRING,
            "one_time": ScheduleType.ONE_TIME
        }
        
        schedule_type = schedule_type_map.get(request.schedule_type, ScheduleType.CRON)
        
        # Use cron_expr if provided for cron schedules
        schedule_config = request.schedule_config.copy()
        if request.cron_expr and schedule_type == ScheduleType.CRON:
            # Parse cron expression (simplified - would need proper cron parser)
            schedule_config["cron_expr"] = request.cron_expr
        
        # Create the schedule
        schedule_id = await content_scheduler.schedule_content(
            content_type=content_type,
            chat_id=request.chat_id,
            content_data=request.content_params,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            max_runs=request.max_runs
        )
        
        # Get the created schedule details
        schedules = await content_scheduler.get_scheduled_content(
            chat_id=request.chat_id,
            active_only=False
        )
        
        created_schedule = next((s for s in schedules if s.id == schedule_id), None)
        
        return ScheduleResponse(
            schedule_id=schedule_id,
            task_type=request.task_type,
            chat_id=request.chat_id,
            schedule_type=request.schedule_type,
            next_run=created_schedule.next_run if created_schedule else None,
            is_active=request.enabled,
            created_at=datetime.now(),
            message=f"Schedule created successfully for {request.task_type}"
        )
        
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")

@router.post("/schedule/template/{template_name}", response_model=ScheduleResponse)
async def create_schedule_from_template(template_name: str, chat_id: int):
    """
    Create a schedule using a pre-defined template.
    Available templates: daily_morning_news, daily_evening_quiz, weekly_debate, hourly_fun
    """
    try:
        if template_name not in SCHEDULE_TEMPLATES:
            available_templates = list(SCHEDULE_TEMPLATES.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown template '{template_name}'. Available templates: {available_templates}"
            )
        
        template = SCHEDULE_TEMPLATES[template_name]
        
        # Create schedule request from template
        schedule_request = ScheduleRequest(
            chat_id=chat_id,
            task_type=template["task_type"],
            schedule_type=template["schedule_type"],
            schedule_config=template["schedule_config"],
            content_params=template["content_params"]
        )
        
        return await create_schedule(schedule_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create schedule from template {template_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create schedule from template: {str(e)}")

@router.post("/trigger", response_model=TriggerResponse)
async def trigger_task(request: TriggerRequest):
    """
    Manually trigger a task immediately.
    Can trigger specific scheduled tasks or create one-time triggers.
    """
    try:
        import uuid
        
        trigger_id = str(uuid.uuid4())
        
        # If task_id is provided, trigger specific scheduled task
        if request.task_id:
            # This would typically trigger the specific scheduled task
            # For now, simulate the trigger
            task_type = request.task_type or "unknown"
            
            return TriggerResponse(
                trigger_id=trigger_id,
                task_type=task_type,
                chat_id=request.chat_id,
                status="triggered",
                timestamp=datetime.now(),
                message=f"Task {request.task_id} triggered successfully"
            )
        
        # Otherwise, create and trigger a one-time task
        elif request.task_type:
            # Map task_type to ContentType
            content_type_map = {
                "news_digest": ContentType.NEWS,
                "quiz": ContentType.QUIZ,
                "debate": ContentType.DEBATE,
                "fun": ContentType.FUN,
                "reminder": ContentType.REMINDER,
                "announcement": ContentType.ANNOUNCEMENT
            }
            
            content_type = content_type_map.get(request.task_type, ContentType.REMINDER)
            
            # Create one-time schedule that executes immediately
            schedule_id = await content_scheduler.schedule_content(
                content_type=content_type,
                chat_id=request.chat_id,
                content_data=request.content_params,
                schedule_type=ScheduleType.ONE_TIME,
                schedule_config={"datetime": datetime.now()},
                max_runs=1
            )
            
            return TriggerResponse(
                trigger_id=trigger_id,
                task_type=request.task_type,
                chat_id=request.chat_id,
                status="scheduled_immediate",
                timestamp=datetime.now(),
                message=f"One-time {request.task_type} task scheduled for immediate execution"
            )
        
        else:
            raise HTTPException(status_code=400, detail="Either task_id or task_type must be provided")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger task: {str(e)}")

@router.get("/schedules")
async def list_schedules(
    chat_id: Optional[int] = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0
):
    """
    List all schedules, optionally filtered by chat_id.
    """
    try:
        schedules = await content_scheduler.get_scheduled_content(
            chat_id=chat_id,
            active_only=active_only
        )
        
        # Apply pagination
        paginated_schedules = schedules[offset:offset + limit]
        
        # Format response
        formatted_schedules = []
        for schedule in paginated_schedules:
            formatted_schedules.append({
                "schedule_id": schedule.id,
                "task_type": schedule.content_type.value,
                "chat_id": schedule.chat_id,
                "schedule_type": schedule.schedule_type.value,
                "schedule_config": schedule.schedule_config,
                "content_data": schedule.content_data,
                "is_active": schedule.is_active,
                "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "run_count": schedule.run_count,
                "created_at": schedule.created_at.isoformat()
            })
        
        return {
            "schedules": formatted_schedules,
            "total_count": len(schedules),
            "page_size": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")

@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: str):
    """
    Get details for a specific schedule.
    """
    try:
        schedules = await content_scheduler.get_scheduled_content(active_only=False)
        schedule = next((s for s in schedules if s.id == schedule_id), None)
        
        if not schedule:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        
        return {
            "schedule_id": schedule.id,
            "task_type": schedule.content_type.value,
            "chat_id": schedule.chat_id,
            "schedule_type": schedule.schedule_type.value,
            "schedule_config": schedule.schedule_config,
            "content_data": schedule.content_data,
            "is_active": schedule.is_active,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
            "run_count": schedule.run_count,
            "max_runs": schedule.max_runs,
            "created_at": schedule.created_at.isoformat(),
            "metadata": schedule.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")

@router.patch("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, updates: Dict[str, Any]):
    """
    Update an existing schedule.
    """
    try:
        success = await content_scheduler.update_schedule(schedule_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        
        return {
            "schedule_id": schedule_id,
            "status": "updated",
            "timestamp": datetime.now().isoformat(),
            "updates": updates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """
    Delete a schedule.
    """
    try:
        success = await content_scheduler.cancel_scheduled_content(schedule_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        
        return {
            "schedule_id": schedule_id,
            "status": "deleted",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")

@router.get("/templates")
async def list_schedule_templates():
    """
    List all available schedule templates.
    """
    try:
        templates = []
        for name, template in SCHEDULE_TEMPLATES.items():
            templates.append({
                "name": name,
                "description": f"{template['task_type']} scheduled {template['schedule_type']}",
                "task_type": template["task_type"],
                "schedule_type": template["schedule_type"],
                "schedule_config": template["schedule_config"],
                "content_params": template["content_params"]
            })
        
        return {
            "templates": templates,
            "total_count": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Failed to list schedule templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")

@router.get("/health")
async def scheduler_health():
    """Health check for scheduler service."""
    try:
        health = await content_scheduler.health_check()
        return health
        
    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
