import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid

try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logging.warning("Celery not available. Content scheduling will be limited.")

logger = logging.getLogger(__name__)

class ContentType(Enum):
    """Types of content that can be scheduled."""
    NEWS = "news"
    QUIZ = "quiz"
    DEBATE = "debate"
    FUN = "fun"
    REMINDER = "reminder"
    ANNOUNCEMENT = "announcement"
    DAILY_DIGEST = "daily_digest"
    WEEKLY_SUMMARY = "weekly_summary"

class ScheduleType(Enum):
    """Types of scheduling."""
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    INTERVAL = "interval"
    CRON = "cron"

@dataclass
class ContentSchedule:
    """Content schedule configuration."""
    id: str
    content_type: ContentType
    chat_id: int
    content_data: Dict[str, Any]
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    is_active: bool = True
    created_at: datetime = None
    next_run: datetime = None
    last_run: datetime = None
    run_count: int = 0
    max_runs: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

class ContentScheduler:
    """Manages content scheduling and delivery."""
    
    def __init__(self):
        self.is_initialized = False
        self.schedules: Dict[str, ContentSchedule] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.telegram_client = None
        self.agent_manager = None
        
        # Schedule templates
        self.schedule_templates = {
            "daily_morning": {
                "type": ScheduleType.CRON,
                "config": {"hour": 9, "minute": 0},
                "description": "Daily at 9:00 AM"
            },
            "daily_evening": {
                "type": ScheduleType.CRON,
                "config": {"hour": 18, "minute": 0},
                "description": "Daily at 6:00 PM"
            },
            "weekly_monday": {
                "type": ScheduleType.CRON,
                "config": {"day_of_week": 1, "hour": 10, "minute": 0},
                "description": "Every Monday at 10:00 AM"
            },
            "hourly": {
                "type": ScheduleType.INTERVAL,
                "config": {"hours": 1},
                "description": "Every hour"
            },
            "every_15_minutes": {
                "type": ScheduleType.INTERVAL,
                "config": {"minutes": 15},
                "description": "Every 15 minutes"
            }
        }
    
    async def initialize(self, telegram_client=None, agent_manager=None):
        """Initialize the content scheduler."""
        try:
            self.telegram_client = telegram_client
            self.agent_manager = agent_manager
            
            # Start the main scheduler loop
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            self.is_initialized = True
            logger.info("Content scheduler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize content scheduler: {e}")
            raise
    
    async def schedule_content(
        self,
        content_type: ContentType,
        chat_id: int,
        content_data: Dict[str, Any],
        schedule_type: ScheduleType,
        schedule_config: Dict[str, Any],
        max_runs: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule content for delivery."""
        try:
            schedule_id = str(uuid.uuid4())
            
            # Calculate next run time
            next_run = self._calculate_next_run(schedule_type, schedule_config)
            
            schedule = ContentSchedule(
                id=schedule_id,
                content_type=content_type,
                chat_id=chat_id,
                content_data=content_data,
                schedule_type=schedule_type,
                schedule_config=schedule_config,
                next_run=next_run,
                max_runs=max_runs,
                metadata=metadata or {}
            )
            
            self.schedules[schedule_id] = schedule
            
            logger.info(f"Scheduled {content_type.value} content for chat {chat_id} at {next_run}")
            
            return schedule_id
        
        except Exception as e:
            logger.error(f"Failed to schedule content: {e}")
            raise
    
    async def schedule_from_template(
        self,
        template_name: str,
        content_type: ContentType,
        chat_id: int,
        content_data: Dict[str, Any],
        **kwargs
    ) -> str:
        """Schedule content using a predefined template."""
        if template_name not in self.schedule_templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = self.schedule_templates[template_name]
        
        return await self.schedule_content(
            content_type=content_type,
            chat_id=chat_id,
            content_data=content_data,
            schedule_type=template["type"],
            schedule_config=template["config"],
            **kwargs
        )
    
    async def schedule_news_digest(
        self,
        chat_id: int,
        schedule_time: str = "daily_morning",
        categories: Optional[List[str]] = None
    ) -> str:
        """Schedule a daily news digest."""
        content_data = {
            "action": "send_news_digest",
            "categories": categories or ["general", "technology", "science"],
            "max_articles": 5,
            "include_summary": True
        }
        
        return await self.schedule_from_template(
            schedule_time,
            ContentType.NEWS,
            chat_id,
            content_data
        )
    
    async def schedule_daily_quiz(
        self,
        chat_id: int,
        schedule_time: str = "daily_morning",
        difficulty: str = "medium"
    ) -> str:
        """Schedule a daily quiz."""
        content_data = {
            "action": "send_daily_quiz",
            "difficulty": difficulty,
            "category": "general",
            "max_questions": 3
        }
        
        return await self.schedule_from_template(
            schedule_time,
            ContentType.QUIZ,
            chat_id,
            content_data
        )
    
    async def schedule_debate_topic(
        self,
        chat_id: int,
        schedule_time: str = "weekly_monday",
        topic_category: str = "technology"
    ) -> str:
        """Schedule a weekly debate topic."""
        content_data = {
            "action": "start_debate",
            "topic_category": topic_category,
            "max_participants": 4,
            "max_turns": 6
        }
        
        return await self.schedule_from_template(
            schedule_time,
            ContentType.DEBATE,
            chat_id,
            content_data
        )
    
    async def schedule_fun_content(
        self,
        chat_id: int,
        schedule_time: str = "every_15_minutes",
        content_types: Optional[List[str]] = None
    ) -> str:
        """Schedule fun content delivery."""
        content_data = {
            "action": "send_fun_content",
            "content_types": content_types or ["joke", "fact", "riddle"],
            "max_content": 2
        }
        
        return await self.schedule_from_template(
            schedule_time,
            ContentType.FUN,
            chat_id,
            content_data
        )
    
    async def cancel_scheduled_content(self, schedule_id: str) -> bool:
        """Cancel a scheduled content delivery."""
        try:
            if schedule_id in self.schedules:
                schedule = self.schedules[schedule_id]
                schedule.is_active = False
                
                # Cancel running task if exists
                if schedule_id in self.running_tasks:
                    self.running_tasks[schedule_id].cancel()
                    del self.running_tasks[schedule_id]
                
                logger.info(f"Cancelled scheduled content: {schedule_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to cancel scheduled content: {e}")
            return False
    
    async def get_scheduled_content(
        self,
        chat_id: Optional[int] = None,
        content_type: Optional[ContentType] = None,
        active_only: bool = True
    ) -> List[ContentSchedule]:
        """Get scheduled content matching criteria."""
        try:
            schedules = list(self.schedules.values())
            
            if chat_id is not None:
                schedules = [s for s in schedules if s.chat_id == chat_id]
            
            if content_type is not None:
                schedules = [s for s in schedules if s.content_type == content_type]
            
            if active_only:
                schedules = [s for s in schedules if s.is_active]
            
            return schedules
        
        except Exception as e:
            logger.error(f"Failed to get scheduled content: {e}")
            return []
    
    async def update_schedule(
        self,
        schedule_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a schedule configuration."""
        try:
            if schedule_id not in self.schedules:
                return False
            
            schedule = self.schedules[schedule_id]
            
            # Update allowed fields
            allowed_fields = [
                "content_data", "schedule_config", "is_active",
                "max_runs", "metadata"
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(schedule, field, value)
            
            # Recalculate next run if schedule config changed
            if "schedule_config" in updates:
                schedule.next_run = self._calculate_next_run(
                    schedule.schedule_type,
                    schedule.schedule_config
                )
            
            logger.info(f"Updated schedule: {schedule_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update schedule: {e}")
            return False
    
    def _calculate_next_run(
        self,
        schedule_type: ScheduleType,
        schedule_config: Dict[str, Any]
    ) -> datetime:
        """Calculate the next run time for a schedule."""
        now = datetime.now()
        
        if schedule_type == ScheduleType.ONE_TIME:
            # One-time schedule
            if "datetime" in schedule_config:
                return schedule_config["datetime"]
            else:
                return now + timedelta(minutes=1)
        
        elif schedule_type == ScheduleType.INTERVAL:
            # Interval-based schedule
            interval = schedule_config.get("interval", 60)  # Default 1 minute
            return now + timedelta(seconds=interval)
        
        elif schedule_type == ScheduleType.CRON:
            # Cron-like schedule
            return self._calculate_cron_next_run(schedule_config)
        
        elif schedule_type == ScheduleType.RECURRING:
            # Recurring schedule
            return self._calculate_recurring_next_run(schedule_config)
        
        else:
            # Default to 1 minute from now
            return now + timedelta(minutes=1)
    
    def _calculate_cron_next_run(self, config: Dict[str, Any]) -> datetime:
        """Calculate next run time for cron-like schedules."""
        now = datetime.now()
        
        # Simple cron implementation
        hour = config.get("hour", now.hour)
        minute = config.get("minute", now.minute)
        day_of_week = config.get("day_of_week")
        
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if day_of_week is not None:
            # Adjust to next occurrence of the specified day
            days_ahead = day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
        
        # If the time has passed today, move to next occurrence
        if next_run <= now:
            if day_of_week is not None:
                next_run += timedelta(days=7)
            else:
                next_run += timedelta(days=1)
        
        return next_run
    
    def _calculate_recurring_next_run(self, config: Dict[str, Any]) -> datetime:
        """Calculate next run time for recurring schedules."""
        now = datetime.now()
        
        # Simple recurring implementation
        days = config.get("days", [])
        time_str = config.get("time", "09:00")
        
        if not days:
            return now + timedelta(days=1)
        
        # Parse time
        try:
            hour, minute = map(int, time_str.split(":"))
        except:
            hour, minute = 9, 0
        
        # Find next occurrence
        for day_offset in range(8):  # Check next 7 days
            check_date = now + timedelta(days=day_offset)
            if check_date.weekday() in days:
                next_run = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run > now:
                    return next_run
        
        return now + timedelta(days=1)
    
    async def _scheduler_loop(self):
        """Main scheduler loop that checks and executes scheduled content."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                now = datetime.now()
                schedules_to_run = []
                
                # Find schedules that need to run
                for schedule in self.schedules.values():
                    if not schedule.is_active:
                        continue
                    
                    if schedule.next_run and schedule.next_run <= now:
                        # Check if we've exceeded max runs
                        if schedule.max_runs and schedule.run_count >= schedule.max_runs:
                            schedule.is_active = False
                            continue
                        
                        schedules_to_run.append(schedule)
                
                # Execute schedules
                for schedule in schedules_to_run:
                    await self._execute_schedule(schedule)
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _execute_schedule(self, schedule: ContentSchedule):
        """Execute a scheduled content delivery."""
        try:
            logger.info(f"Executing scheduled content: {schedule.id}")
            
            # Create and start execution task
            task = asyncio.create_task(
                self._execute_content_delivery(schedule)
            )
            
            self.running_tasks[schedule.id] = task
            
            # Wait for completion
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Content delivery cancelled: {schedule.id}")
                return
            finally:
                # Clean up task reference
                if schedule.id in self.running_tasks:
                    del self.running_tasks[schedule.id]
            
            # Update schedule
            schedule.last_run = datetime.now()
            schedule.run_count += 1
            
            # Calculate next run time
            if schedule.is_active:
                schedule.next_run = self._calculate_next_run(
                    schedule.schedule_type,
                    schedule.schedule_config
                )
            
            logger.info(f"Completed scheduled content: {schedule.id}")
        
        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule.id}: {e}")
    
    async def _execute_content_delivery(self, schedule: ContentSchedule):
        """Execute the actual content delivery."""
        try:
            content_type = schedule.content_type
            chat_id = schedule.chat_id
            content_data = schedule.content_data
            
            if content_type == ContentType.NEWS:
                await self._deliver_news_content(chat_id, content_data)
            elif content_type == ContentType.QUIZ:
                await self._deliver_quiz_content(chat_id, content_data)
            elif content_type == ContentType.DEBATE:
                await self._deliver_debate_content(chat_id, content_data)
            elif content_type == ContentType.FUN:
                await self._deliver_fun_content(chat_id, content_data)
            elif content_type == ContentType.REMINDER:
                await self._deliver_reminder(chat_id, content_data)
            elif content_type == ContentType.ANNOUNCEMENT:
                await self._deliver_announcement(chat_id, content_data)
            else:
                logger.warning(f"Unknown content type: {content_type}")
        
        except Exception as e:
            logger.error(f"Failed to deliver content: {e}")
            raise
    
    async def _deliver_news_content(self, chat_id: int, content_data: Dict[str, Any]):
        """Deliver news content."""
        if not self.agent_manager:
            logger.warning("Agent manager not available for news delivery")
            return
        
        try:
            news_agent = await self.agent_manager.get_agent("newsreporter")
            if news_agent:
                # Generate news content
                message_info = {
                    "chat_id": chat_id,
                    "text": "Daily news digest",
                    "user_id": 0  # System user
                }
                
                agent_context = {
                    "user_history": [],
                    "chat_context": [],
                    "agent_memory": {}
                }
                
                response = await news_agent.process_message(message_info, agent_context)
                
                if response.get("success") and self.telegram_client:
                    await self.telegram_client.send_message(
                        chat_id=chat_id,
                        text=response["response"]
                    )
        
        except Exception as e:
            logger.error(f"Failed to deliver news content: {e}")
    
    async def _deliver_quiz_content(self, chat_id: int, content_data: Dict[str, Any]):
        """Deliver quiz content."""
        if not self.agent_manager:
            logger.warning("Agent manager not available for quiz delivery")
            return
        
        try:
            quiz_agent = await self.agent_manager.get_agent("quizmaster")
            if quiz_agent:
                # Generate quiz content
                message_info = {
                    "chat_id": chat_id,
                    "text": "Daily quiz",
                    "user_id": 0  # System user
                }
                
                agent_context = {
                    "user_history": [],
                    "chat_context": [],
                    "agent_memory": {}
                }
                
                response = await quiz_agent.process_message(message_info, agent_context)
                
                if response.get("success") and self.telegram_client:
                    await self.telegram_client.send_message(
                        chat_id=chat_id,
                        text=response["response"]
                    )
        
        except Exception as e:
            logger.error(f"Failed to deliver quiz content: {e}")
    
    async def _deliver_debate_content(self, chat_id: int, content_data: Dict[str, Any]):
        """Deliver debate content."""
        if not self.agent_manager:
            logger.warning("Agent manager not available for debate delivery")
            return
        
        try:
            debate_agent = await self.agent_manager.get_agent("debatebot")
            if debate_agent:
                # Generate debate content
                message_info = {
                    "chat_id": chat_id,
                    "text": "Weekly debate topic",
                    "user_id": 0  # System user
                }
                
                agent_context = {
                    "user_history": [],
                    "chat_context": [],
                    "agent_memory": {}
                }
                
                response = await debate_agent.process_message(message_info, agent_context)
                
                if response.get("success") and self.telegram_client:
                    await self.telegram_client.send_message(
                        chat_id=chat_id,
                        text=response["response"]
                    )
        
        except Exception as e:
            logger.error(f"Failed to deliver debate content: {e}")
    
    async def _deliver_fun_content(self, chat_id: int, content_data: Dict[str, Any]):
        """Deliver fun content."""
        if not self.agent_manager:
            logger.warning("Agent manager not available for fun content delivery")
            return
        
        try:
            fun_agent = await self.agent_manager.get_agent("funagent")
            if fun_agent:
                # Generate fun content
                message_info = {
                    "chat_id": chat_id,
                    "text": "Fun content",
                    "user_id": 0  # System user
                }
                
                agent_context = {
                    "user_history": [],
                    "chat_context": [],
                    "agent_memory": {}
                }
                
                response = await fun_agent.process_message(message_info, agent_context)
                
                if response.get("success") and self.telegram_client:
                    await self.telegram_client.send_message(
                        chat_id=chat_id,
                        text=response["response"]
                    )
        
        except Exception as e:
            logger.error(f"Failed to deliver fun content: {e}")
    
    async def _deliver_reminder(self, chat_id: int, content_data: Dict[str, Any]):
        """Deliver a reminder message."""
        if not self.telegram_client:
            logger.warning("Telegram client not available for reminder delivery")
            return
        
        try:
            message = content_data.get("message", "Reminder!")
            await self.telegram_client.send_message(
                chat_id=chat_id,
                text=f"⏰ {message}"
            )
        
        except Exception as e:
            logger.error(f"Failed to deliver reminder: {e}")
    
    async def _deliver_announcement(self, chat_id: int, content_data: Dict[str, Any]):
        """Deliver an announcement message."""
        if not self.telegram_client:
            logger.warning("Telegram client not available for announcement delivery")
            return
        
        try:
            message = content_data.get("message", "Announcement")
            title = content_data.get("title", "📢 Announcement")
            
            full_message = f"{title}\n\n{message}"
            await self.telegram_client.send_message(
                chat_id=chat_id,
                text=full_message
            )
        
        except Exception as e:
            logger.error(f"Failed to deliver announcement: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check content scheduler health."""
        try:
            active_schedules = [s for s in self.schedules.values() if s.is_active]
            running_tasks = len(self.running_tasks)
            
            return {
                "status": "healthy" if self.is_initialized else "unhealthy",
                "is_initialized": self.is_initialized,
                "total_schedules": len(self.schedules),
                "active_schedules": len(active_schedules),
                "running_tasks": running_tasks,
                "next_scheduled_run": min([s.next_run for s in active_schedules]) if active_schedules else None,
                "celery_available": CELERY_AVAILABLE
            }
        except Exception as e:
            logger.error(f"Failed to check content scheduler health: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def shutdown(self):
        """Shutdown the content scheduler."""
        try:
            # Cancel scheduler task
            if self.scheduler_task:
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel all running tasks
            for task in self.running_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.running_tasks:
                await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
            
            logger.info("Content scheduler shutdown complete")
        
        except Exception as e:
            logger.error(f"Error during content scheduler shutdown: {e}")

# Global instance
content_scheduler = ContentScheduler()
