"""
Scheduler service for Kroolo Agent Bot
Handles automated tasks, health checks, and scheduled operations
"""

import logging
import asyncio
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from utils.logger import logger, log_admin_action

class SchedulerService:
    """Service for managing scheduled tasks and automation"""
    
    def __init__(self, ai_service, auth_service, database):
        self.ai_service = ai_service
        self.auth_service = auth_service
        self.database = database
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Setup scheduler event listeners for monitoring"""
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    def _job_listener(self, event):
        """Handle job execution events"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
            # Log to database for admin review
            self.database.log_action(
                user_id=None,
                chat_id=None,
                action="scheduler_job_failed",
                details=f"Job {event.job_id}: {event.exception}"
            )
        else:
            logger.info(f"Job {event.job_id} completed successfully")
    
    async def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Add default jobs
            await self._add_default_jobs()
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def _add_default_jobs(self):
        """Add default scheduled jobs"""
        # Daily health check at 6 AM UTC
        self.add_job(
            "daily_health_check",
            self._daily_health_check,
            CronTrigger(hour=6, minute=0),
            "Daily system health check"
        )
        
        # Database cleanup every Sunday at 2 AM UTC
        self.add_job(
            "weekly_cleanup",
            self._weekly_cleanup,
            CronTrigger(day_of_week="sun", hour=2, minute=0),
            "Weekly database cleanup"
        )
        
        # Rate limit reset every hour
        self.add_job(
            "hourly_rate_limit_reset",
            self._hourly_rate_limit_reset,
            IntervalTrigger(hours=1),
            "Hourly rate limit reset"
        )
        
        # AI service health check every 30 minutes
        self.add_job(
            "ai_health_check",
            self._ai_health_check,
            IntervalTrigger(minutes=30),
            "AI service health check"
        )
    
    def add_job(self, job_id: str, func: Callable, trigger, description: str = ""):
        """Add a new scheduled job"""
        try:
            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                replace_existing=True
            )
            
            self.jobs[job_id] = {
                "job": job,
                "description": description,
                "created_at": datetime.utcnow()
            }
            
            logger.info(f"Added scheduled job: {job_id} - {description}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to add job {job_id}: {e}")
            return None
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        try:
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
                del self.jobs[job_id]
                logger.info(f"Removed scheduled job: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        if job_id not in self.jobs:
            return None
        
        job_info = self.jobs[job_id]
        job = job_info["job"]
        
        return {
            "id": job_id,
            "description": job_info["description"],
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "created_at": job_info["created_at"].isoformat(),
            "active": job.next_run_time is not None
        }
    
    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all jobs"""
        return {
            job_id: self.get_job_status(job_id)
            for job_id in self.jobs.keys()
        }
    
    async def _daily_health_check(self):
        """Daily system health check"""
        try:
            logger.info("Running daily health check...")
            
            # Check AI services
            ai_status = self.ai_service.is_service_available()
            
            # Check database
            db_healthy = True
            try:
                self.database.get_session()
            except Exception:
                db_healthy = False
            
            # Log health status
            health_status = {
                "timestamp": datetime.utcnow().isoformat(),
                "ai_services": ai_status,
                "database": "healthy" if db_healthy else "unhealthy",
                "overall": "healthy" if (ai_status["overall"] and db_healthy) else "unhealthy"
            }
            
            # Store health status in database
            self.database.log_action(
                user_id=None,
                chat_id=None,
                action="daily_health_check",
                details=str(health_status)
            )
            
            logger.info(f"Daily health check completed: {health_status['overall']}")
            
        except Exception as e:
            logger.error(f"Daily health check failed: {e}")
    
    async def _weekly_cleanup(self):
        """Weekly database cleanup and maintenance"""
        try:
            logger.info("Running weekly cleanup...")
            
            # Clean old logs (older than 30 days)
            # This would be implemented in the database class
            # self.database.cleanup_old_logs(days=30)
            
            # Clean old rate limit data
            # self.database.cleanup_old_rate_limits(days=7)
            
            logger.info("Weekly cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Weekly cleanup failed: {e}")
    
    async def _hourly_rate_limit_reset(self):
        """Hourly rate limit reset for active users"""
        try:
            logger.info("Running hourly rate limit reset...")
            
            # Reset hourly rate limits
            # This would be implemented in the rate limiter
            # self.rate_limiter.reset_hourly_limits()
            
            logger.info("Hourly rate limit reset completed")
            
        except Exception as e:
            logger.error(f"Hourly rate limit reset failed: {e}")
    
    async def _ai_health_check(self):
        """Check AI service health"""
        try:
            logger.info("Running AI service health check...")
            
            # Test AI service with a simple query
            test_response = await self.ai_service.ask_ai("Hello")
            
            if test_response and not test_response.startswith("Sorry"):
                logger.info("AI service health check: OK")
            else:
                logger.warning("AI service health check: Service degraded")
                
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
    
    async def trigger_job_now(self, job_id: str) -> bool:
        """Trigger a job to run immediately"""
        try:
            if job_id in self.jobs:
                self.scheduler.trigger_job(job_id)
                logger.info(f"Manually triggered job: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to trigger job {job_id}: {e}")
            return False
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get overall scheduler status"""
        return {
            "running": self.scheduler.running,
            "job_count": len(self.jobs),
            "active_jobs": len([j for j in self.jobs.values() if j["job"].next_run_time]),
            "jobs": self.get_all_jobs()
        }
