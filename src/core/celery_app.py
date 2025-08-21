"""
Celery application for background task processing.
Handles content scheduling, news aggregation, and other asynchronous operations.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

try:
    from celery import Celery
    from celery.schedules import crontab
    from celery.utils.log import get_task_logger
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logging.warning("Celery not available. Background processing will be limited.")

from config.settings import settings

logger = logging.getLogger(__name__)

# Create Celery app
if CELERY_AVAILABLE:
    celery_app = Celery(
        'kroolo_bot',
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            'src.core.celery_app',
            'src.core.content_scheduler'
        ]
    )
    
    # Configure Celery
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        result_expires=3600,  # 1 hour
        beat_schedule={
            'fetch-news-every-hour': {
                'task': 'src.core.celery_app.fetch_news_task',
                'schedule': crontab(minute=0, hour='*'),
                'args': (),
            },
            'generate-daily-quiz': {
                'task': 'src.core.celery_app.generate_daily_quiz_task',
                'schedule': crontab(minute=0, hour=9),  # 9 AM daily
                'args': (),
            },
            'cleanup-old-content': {
                'task': 'src.core.celery_app.cleanup_old_content_task',
                'schedule': crontab(minute=0, hour=2),  # 2 AM daily
                'args': (),
            },
            'update-rag-embeddings': {
                'task': 'src.core.celery_app.update_rag_embeddings_task',
                'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
                'args': (),
            },
        }
    )
    
    # Set up logging
    celery_logger = get_task_logger(__name__)
else:
    celery_app = None
    celery_logger = logger


# Task definitions
if CELERY_AVAILABLE:
    @celery_app.task(bind=True, name='fetch-news-task')
    def fetch_news_task(self):
        """Fetch news from RSS feeds and update the database."""
        try:
            celery_logger.info("Starting news fetch task")
            
            # This would integrate with the news agent
            # For now, just log the task
            result = {
                'status': 'success',
                'message': 'News fetch completed',
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"News fetch task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"News fetch task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='generate-daily-quiz-task')
    def generate_daily_quiz_task(self):
        """Generate daily quiz questions."""
        try:
            celery_logger.info("Starting daily quiz generation task")
            
            # This would integrate with the quiz agent
            # For now, just log the task
            result = {
                'status': 'success',
                'message': 'Daily quiz generation completed',
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"Daily quiz generation task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"Daily quiz generation task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='cleanup-old-content-task')
    def cleanup_old_content_task(self):
        """Clean up old content and expired data."""
        try:
            celery_logger.info("Starting content cleanup task")
            
            # This would clean up old content, expired sessions, etc.
            # For now, just log the task
            result = {
                'status': 'success',
                'message': 'Content cleanup completed',
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"Content cleanup task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"Content cleanup task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='update-rag-embeddings-task')
    def update_rag_embeddings_task(self):
        """Update RAG embeddings and optimize the vector database."""
        try:
            celery_logger.info("Starting RAG embeddings update task")
            
            # This would update embeddings, optimize the vector database
            # For now, just log the task
            result = {
                'status': 'success',
                'message': 'RAG embeddings update completed',
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"RAG embeddings update task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"RAG embeddings update task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='send-scheduled-content-task')
    def send_scheduled_content_task(self, chat_id: int, content_type: str, 
                                  content_data: Dict[str, Any]):
        """Send scheduled content to a specific chat."""
        try:
            celery_logger.info(f"Starting scheduled content task for chat {chat_id}")
            
            # This would send the scheduled content via Telegram
            # For now, just log the task
            result = {
                'status': 'success',
                'message': f'Scheduled content sent to chat {chat_id}',
                'chat_id': chat_id,
                'content_type': content_type,
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"Scheduled content task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"Scheduled content task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'chat_id': chat_id,
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='process-user-feedback-task')
    def process_user_feedback_task(self, user_id: int, feedback_data: Dict[str, Any]):
        """Process user feedback asynchronously."""
        try:
            celery_logger.info(f"Starting user feedback processing task for user {user_id}")
            
            # This would process user feedback, update ratings, etc.
            # For now, just log the task
            result = {
                'status': 'success',
                'message': f'User feedback processed for user {user_id}',
                'user_id': user_id,
                'feedback_data': feedback_data,
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"User feedback processing task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"User feedback processing task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='generate-content-summary-task')
    def generate_content_summary_task(self, content_type: str, content_ids: List[str]):
        """Generate summaries for multiple content items."""
        try:
            celery_logger.info(f"Starting content summary generation task for {content_type}")
            
            # This would generate AI summaries for content
            # For now, just log the task
            result = {
                'status': 'success',
                'message': f'Content summary generation completed for {content_type}',
                'content_type': content_type,
                'content_ids': content_ids,
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"Content summary generation task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"Content summary generation task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'content_type': content_type,
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='moderate-content-task')
    def moderate_content_task(self, content_id: str, content_text: str, 
                            content_type: str, user_id: int):
        """Moderate content for safety and compliance."""
        try:
            celery_logger.info(f"Starting content moderation task for {content_id}")
            
            # This would use AI moderation to check content
            # For now, just log the task
            result = {
                'status': 'success',
                'message': f'Content moderation completed for {content_id}',
                'content_id': content_id,
                'moderation_result': 'passed',
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"Content moderation task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"Content moderation task failed: {e}")
            self.retry(countdown=60, max_retries=3)
            return {
                'status': 'error',
                'error': str(e),
                'content_id': content_id,
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='backup-database-task')
    def backup_database_task(self):
        """Create database backup."""
        try:
            celery_logger.info("Starting database backup task")
            
            # This would create database backups
            # For now, just log the task
            result = {
                'status': 'success',
                'message': 'Database backup completed',
                'backup_size': '0 MB',
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"Database backup task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"Database backup task failed: {e}")
            self.retry(countdown=300, max_retries=2)  # Retry after 5 minutes
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @celery_app.task(bind=True, name='health-check-task')
    def health_check_task(self):
        """Perform system health check."""
        try:
            celery_logger.info("Starting health check task")
            
            # This would check various system components
            # For now, just log the task
            result = {
                'status': 'success',
                'message': 'Health check completed',
                'system_status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
            celery_logger.info(f"Health check task completed: {result}")
            return result
            
        except Exception as e:
            celery_logger.error(f"Health check task failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


class CeleryManager:
    """Manager for Celery operations."""
    
    def __init__(self):
        self.app = celery_app
        self.is_available = CELERY_AVAILABLE
        
        if self.is_available:
            logger.info("Celery manager initialized")
        else:
            logger.warning("Celery not available. Background processing will be limited.")
    
    async def schedule_content_delivery(self, chat_id: int, content_type: str, 
                                      content_data: Dict[str, Any], 
                                      delivery_time: datetime) -> str:
        """Schedule content delivery for a specific time."""
        if not self.is_available:
            logger.warning("Celery not available. Cannot schedule content delivery.")
            return None
        
        try:
            # Calculate delay until delivery time
            now = datetime.now()
            if delivery_time <= now:
                delay = 0
            else:
                delay = int((delivery_time - now).total_seconds())
            
            # Schedule the task
            task = send_scheduled_content_task.apply_async(
                args=[chat_id, content_type, content_data],
                countdown=delay
            )
            
            logger.info(f"Scheduled content delivery for chat {chat_id} at {delivery_time}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to schedule content delivery: {e}")
            return None
    
    async def process_feedback_async(self, user_id: int, feedback_data: Dict[str, Any]):
        """Process user feedback asynchronously."""
        if not self.is_available:
            logger.warning("Celery not available. Cannot process feedback asynchronously.")
            return None
        
        try:
            task = process_user_feedback_task.delay(user_id, feedback_data)
            logger.info(f"Feedback processing queued for user {user_id}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to queue feedback processing: {e}")
            return None
    
    async def generate_content_summary_async(self, content_type: str, content_ids: List[str]):
        """Generate content summaries asynchronously."""
        if not self.is_available:
            logger.warning("Celery not available. Cannot generate summaries asynchronously.")
            return None
        
        try:
            task = generate_content_summary_task.delay(content_type, content_ids)
            logger.info(f"Content summary generation queued for {content_type}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to queue content summary generation: {e}")
            return None
    
    async def moderate_content_async(self, content_id: str, content_text: str, 
                                   content_type: str, user_id: int):
        """Moderate content asynchronously."""
        if not self.is_available:
            logger.warning("Celery not available. Cannot moderate content asynchronously.")
            return None
        
        try:
            task = moderate_content_task.delay(content_id, content_text, content_type, user_id)
            logger.info(f"Content moderation queued for {content_id}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to queue content moderation: {e}")
            return None
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a Celery task."""
        if not self.is_available:
            return {"error": "Celery not available"}
        
        try:
            task_result = self.app.AsyncResult(task_id)
            
            status_info = {
                'task_id': task_id,
                'status': task_result.status,
                'ready': task_result.ready(),
                'successful': task_result.successful(),
                'failed': task_result.failed()
            }
            
            if task_result.ready():
                if task_result.successful():
                    status_info['result'] = task_result.result
                else:
                    status_info['error'] = str(task_result.info)
            
            return status_info
            
        except Exception as e:
            return {
                'error': str(e),
                'task_id': task_id
            }
    
    async def get_worker_stats(self) -> Dict[str, Any]:
        """Get Celery worker statistics."""
        if not self.is_available:
            return {"error": "Celery not available"}
        
        try:
            # Get active workers
            active_workers = self.app.control.inspect().active()
            registered_workers = self.app.control.inspect().registered()
            
            stats = {
                'active_workers': len(active_workers) if active_workers else 0,
                'registered_workers': len(registered_workers) if registered_workers else 0,
                'worker_details': {}
            }
            
            if active_workers:
                for worker_name, tasks in active_workers.items():
                    stats['worker_details'][worker_name] = {
                        'active_tasks': len(tasks),
                        'status': 'active'
                    }
            
            if registered_workers:
                for worker_name, worker_info in registered_workers.items():
                    if worker_name not in stats['worker_details']:
                        stats['worker_details'][worker_name] = {
                            'active_tasks': 0,
                            'status': 'registered'
                        }
            
            return stats
            
        except Exception as e:
            return {
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Celery system."""
        try:
            if not self.is_available:
                return {
                    'status': 'not_available',
                    'message': 'Celery is not available'
                }
            
            # Check worker status
            worker_stats = await self.get_worker_stats()
            
            # Check if any workers are active
            if worker_stats.get('active_workers', 0) > 0:
                status = 'healthy'
            elif worker_stats.get('registered_workers', 0) > 0:
                status = 'degraded'
            else:
                status = 'unhealthy'
            
            health_status = {
                'status': status,
                'celery_available': True,
                'worker_stats': worker_stats,
                'scheduled_tasks': len(self.app.conf.beat_schedule) if self.app.conf.beat_schedule else 0
            }
            
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'celery_available': self.is_available,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    async def shutdown(self):
        """Shutdown the Celery manager."""
        try:
            if self.is_available:
                # Cancel all pending tasks
                self.app.control.purge()
                logger.info("Celery manager shutdown")
        except Exception as e:
            logger.error(f"Error during Celery manager shutdown: {e}")


# Global Celery manager instance
celery_manager = CeleryManager()
