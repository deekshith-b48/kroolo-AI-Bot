"""
Workflow management and approval system for the Kroolo AI Bot.
Handles automation workflows, approvals, and external integrations.
"""

import logging
import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.core.admin_auth import admin_auth, AdminAuthError, InsufficientPermissionError
from src.models.admin import (
    BotWorkflow, WorkflowStatus, PendingApproval, AuditAction,
    Permissions
)
from src.database.session import get_db_session
from src.core.telegram_client import TelegramClient
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class WorkflowExecution:
    """Workflow execution result."""
    success: bool
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    status_code: Optional[int] = None


class WorkflowManager:
    """Manages bot workflows and automation integrations."""
    
    def __init__(self, telegram_client: TelegramClient):
        self.telegram_client = telegram_client
        self.session: Optional[aiohttp.ClientSession] = None
        self.workflow_cache = {}  # Cache for active workflows
        self.execution_queue = asyncio.Queue()
        self.worker_tasks = []
        
    async def initialize(self):
        """Initialize the workflow manager."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Workflow manager initialized")
            
            # Start worker tasks
            for i in range(3):  # 3 concurrent workers
                task = asyncio.create_task(self._workflow_worker(f"worker-{i}"))
                self.worker_tasks.append(task)
            
            # Load active workflows into cache
            await self._load_active_workflows()
    
    async def shutdown(self):
        """Shutdown the workflow manager."""
        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Close HTTP session
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Workflow manager shutdown")
    
    async def _load_active_workflows(self):
        """Load active workflows into cache."""
        try:
            async with get_db_session() as session:
                workflows = session.query(BotWorkflow).filter(
                    BotWorkflow.is_active == True,
                    BotWorkflow.status == WorkflowStatus.ACTIVE
                ).all()
                
                self.workflow_cache = {
                    workflow.name: workflow for workflow in workflows
                }
                
                logger.info(f"Loaded {len(workflows)} active workflows")
                
        except Exception as e:
            logger.error(f"Failed to load active workflows: {e}")
    
    async def _workflow_worker(self, worker_name: str):
        """Worker task to process workflow executions."""
        logger.info(f"Workflow worker {worker_name} started")
        
        try:
            while True:
                # Get workflow execution from queue
                execution_data = await self.execution_queue.get()
                
                try:
                    await self._execute_workflow_internal(execution_data)
                except Exception as e:
                    logger.error(f"Worker {worker_name} execution failed: {e}")
                finally:
                    self.execution_queue.task_done()
                    
        except asyncio.CancelledError:
            logger.info(f"Workflow worker {worker_name} cancelled")
        except Exception as e:
            logger.error(f"Workflow worker {worker_name} error: {e}")
    
    async def add_workflow(self, admin_id: int, name: str, endpoint_url: str,
                          description: Optional[str] = None, trigger_command: Optional[str] = None,
                          method: str = "POST", headers: Optional[Dict[str, str]] = None,
                          payload_template: Optional[Dict[str, Any]] = None) -> BotWorkflow:
        """Add a new workflow."""
        if not await admin_auth.has_permission(admin_id, Permissions.ADD_WORKFLOW):
            raise InsufficientPermissionError("No permission to add workflows")
        
        async with get_db_session() as session:
            admin_user = await admin_auth.get_admin_user(admin_id)
            
            # Check if workflow already exists
            existing = session.query(BotWorkflow).filter(
                BotWorkflow.name == name
            ).first()
            
            if existing:
                raise ValueError(f"Workflow '{name}' already exists")
            
            # Validate URL
            if not (endpoint_url.startswith('http://') or endpoint_url.startswith('https://')):
                raise ValueError("Invalid URL format")
            
            # Create workflow
            workflow = BotWorkflow(
                name=name,
                description=description,
                endpoint_url=endpoint_url,
                trigger_command=trigger_command,
                method=method.upper(),
                headers=headers or {},
                payload_template=payload_template or {},
                created_by_id=admin_user.id,
                status=WorkflowStatus.PENDING
            )
            
            session.add(workflow)
            session.commit()
            session.refresh(workflow)
            
            # Log action
            await admin_auth.log_admin_action(
                admin_id, AuditAction.WORKFLOW_ADDED,
                details={
                    "name": name,
                    "url": endpoint_url,
                    "trigger": trigger_command,
                    "method": method
                }
            )
            
            # Create pending approval
            approval = PendingApproval(
                request_type="workflow_approval",
                request_data={
                    "workflow_id": workflow.id,
                    "workflow_name": name,
                    "action": "approve_workflow"
                },
                requested_by_id=admin_id,
                expires_at=datetime.now() + timedelta(days=7)
            )
            session.add(approval)
            session.commit()
            
            logger.info(f"Workflow '{name}' added by admin {admin_id}")
            return workflow
    
    async def approve_workflow(self, admin_id: int, workflow_id: int) -> bool:
        """Approve a pending workflow."""
        if not await admin_auth.has_permission(admin_id, Permissions.APPROVE_WORKFLOW):
            raise InsufficientPermissionError("No permission to approve workflows")
        
        async with get_db_session() as session:
            workflow = session.query(BotWorkflow).filter(
                BotWorkflow.id == workflow_id,
                BotWorkflow.status == WorkflowStatus.PENDING
            ).first()
            
            if not workflow:
                return False
            
            # Update workflow status
            workflow.status = WorkflowStatus.APPROVED
            workflow.is_active = True
            workflow.approved_by_id = (await admin_auth.get_admin_user(admin_id)).id
            
            # Update pending approval
            approval = session.query(PendingApproval).filter(
                PendingApproval.request_type == "workflow_approval",
                PendingApproval.request_data.contains({"workflow_id": workflow_id}),
                PendingApproval.status == "pending"
            ).first()
            
            if approval:
                approval.status = "approved"
                approval.reviewed_by_id = (await admin_auth.get_admin_user(admin_id)).id
            
            session.commit()
            
            # Add to cache
            self.workflow_cache[workflow.name] = workflow
            
            # Log action
            await admin_auth.log_admin_action(
                admin_id, AuditAction.WORKFLOW_ENABLED,
                details={"workflow_id": workflow_id, "name": workflow.name}
            )
            
            logger.info(f"Workflow '{workflow.name}' approved by admin {admin_id}")
            return True
    
    async def reject_workflow(self, admin_id: int, workflow_id: int, reason: Optional[str] = None) -> bool:
        """Reject a pending workflow."""
        if not await admin_auth.has_permission(admin_id, Permissions.APPROVE_WORKFLOW):
            raise InsufficientPermissionError("No permission to reject workflows")
        
        async with get_db_session() as session:
            workflow = session.query(BotWorkflow).filter(
                BotWorkflow.id == workflow_id,
                BotWorkflow.status == WorkflowStatus.PENDING
            ).first()
            
            if not workflow:
                return False
            
            # Update workflow status
            workflow.status = WorkflowStatus.REJECTED
            
            # Update pending approval
            approval = session.query(PendingApproval).filter(
                PendingApproval.request_type == "workflow_approval",
                PendingApproval.request_data.contains({"workflow_id": workflow_id}),
                PendingApproval.status == "pending"
            ).first()
            
            if approval:
                approval.status = "rejected"
                approval.reviewed_by_id = (await admin_auth.get_admin_user(admin_id)).id
                approval.review_message = reason
            
            session.commit()
            
            logger.info(f"Workflow '{workflow.name}' rejected by admin {admin_id}")
            return True
    
    async def toggle_workflow(self, admin_id: int, workflow_name: str) -> bool:
        """Toggle workflow active status."""
        if not await admin_auth.has_permission(admin_id, Permissions.TOGGLE_WORKFLOW):
            raise InsufficientPermissionError("No permission to toggle workflows")
        
        async with get_db_session() as session:
            workflow = session.query(BotWorkflow).filter(
                BotWorkflow.name == workflow_name
            ).first()
            
            if not workflow:
                return False
            
            # Toggle status
            workflow.is_active = not workflow.is_active
            workflow.status = WorkflowStatus.ACTIVE if workflow.is_active else WorkflowStatus.INACTIVE
            session.commit()
            
            # Update cache
            if workflow.is_active:
                self.workflow_cache[workflow_name] = workflow
            else:
                self.workflow_cache.pop(workflow_name, None)
            
            # Log action
            action = AuditAction.WORKFLOW_ENABLED if workflow.is_active else AuditAction.WORKFLOW_DISABLED
            await admin_auth.log_admin_action(
                admin_id, action,
                details={"name": workflow_name, "active": workflow.is_active}
            )
            
            status = "enabled" if workflow.is_active else "disabled"
            logger.info(f"Workflow '{workflow_name}' {status} by admin {admin_id}")
            return True
    
    async def remove_workflow(self, admin_id: int, workflow_name: str) -> bool:
        """Remove a workflow."""
        if not await admin_auth.has_permission(admin_id, Permissions.REMOVE_WORKFLOW):
            raise InsufficientPermissionError("No permission to remove workflows")
        
        async with get_db_session() as session:
            workflow = session.query(BotWorkflow).filter(
                BotWorkflow.name == workflow_name
            ).first()
            
            if not workflow:
                return False
            
            # Remove from cache
            self.workflow_cache.pop(workflow_name, None)
            
            # Delete workflow
            session.delete(workflow)
            session.commit()
            
            # Log action
            await admin_auth.log_admin_action(
                admin_id, AuditAction.WORKFLOW_REMOVED,
                details={"name": workflow_name}
            )
            
            logger.info(f"Workflow '{workflow_name}' removed by admin {admin_id}")
            return True
    
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any],
                             user_id: Optional[int] = None, chat_id: Optional[int] = None) -> WorkflowExecution:
        """Execute a workflow asynchronously."""
        if workflow_name not in self.workflow_cache:
            return WorkflowExecution(
                success=False,
                error_message=f"Workflow '{workflow_name}' not found or inactive"
            )
        
        # Add to execution queue
        execution_data = {
            "workflow_name": workflow_name,
            "input_data": input_data,
            "user_id": user_id,
            "chat_id": chat_id,
            "timestamp": datetime.now()
        }
        
        await self.execution_queue.put(execution_data)
        
        return WorkflowExecution(
            success=True,
            response_data={"status": "queued", "workflow": workflow_name}
        )
    
    async def _execute_workflow_internal(self, execution_data: Dict[str, Any]) -> WorkflowExecution:
        """Internal workflow execution."""
        workflow_name = execution_data["workflow_name"]
        input_data = execution_data["input_data"]
        user_id = execution_data.get("user_id")
        chat_id = execution_data.get("chat_id")
        
        workflow = self.workflow_cache.get(workflow_name)
        if not workflow:
            logger.error(f"Workflow '{workflow_name}' not in cache")
            return WorkflowExecution(
                success=False,
                error_message="Workflow not found in cache"
            )
        
        start_time = datetime.now()
        
        try:
            # Prepare payload
            payload = workflow.payload_template.copy()
            payload.update({
                "input": input_data,
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": start_time.isoformat()
            })
            
            # Prepare headers
            headers = workflow.headers.copy()
            headers.setdefault("Content-Type", "application/json")
            headers.setdefault("User-Agent", f"Kroolo-AI-Bot/{settings.app_version}")
            
            # Make HTTP request
            async with self.session.request(
                method=workflow.method,
                url=workflow.endpoint_url,
                json=payload,
                headers=headers
            ) as response:
                execution_time = (datetime.now() - start_time).total_seconds()
                response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                
                # Update execution stats
                await self._update_workflow_stats(workflow.id, True, execution_time)
                
                if response.status < 400:
                    logger.info(f"Workflow '{workflow_name}' executed successfully in {execution_time:.2f}s")
                    return WorkflowExecution(
                        success=True,
                        response_data=response_data,
                        execution_time=execution_time,
                        status_code=response.status
                    )
                else:
                    logger.error(f"Workflow '{workflow_name}' failed with status {response.status}")
                    return WorkflowExecution(
                        success=False,
                        error_message=f"HTTP {response.status}: {response_data}",
                        execution_time=execution_time,
                        status_code=response.status
                    )
                    
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_workflow_stats(workflow.id, False, execution_time)
            logger.error(f"Workflow '{workflow_name}' timed out")
            return WorkflowExecution(
                success=False,
                error_message="Workflow execution timed out",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_workflow_stats(workflow.id, False, execution_time)
            logger.error(f"Workflow '{workflow_name}' execution error: {e}")
            return WorkflowExecution(
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _update_workflow_stats(self, workflow_id: int, success: bool, execution_time: float):
        """Update workflow execution statistics."""
        try:
            async with get_db_session() as session:
                workflow = session.query(BotWorkflow).filter(
                    BotWorkflow.id == workflow_id
                ).first()
                
                if workflow:
                    workflow.execution_count += 1
                    workflow.last_executed = datetime.now()
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update workflow stats: {e}")
    
    async def get_workflow_by_trigger(self, trigger_command: str) -> Optional[BotWorkflow]:
        """Get workflow by trigger command."""
        for workflow in self.workflow_cache.values():
            if workflow.trigger_command == trigger_command:
                return workflow
        return None
    
    async def get_pending_approvals(self, admin_id: int) -> List[PendingApproval]:
        """Get pending workflow approvals."""
        if not await admin_auth.has_permission(admin_id, Permissions.APPROVE_WORKFLOW):
            raise InsufficientPermissionError("No permission to view approvals")
        
        async with get_db_session() as session:
            approvals = session.query(PendingApproval).filter(
                PendingApproval.request_type == "workflow_approval",
                PendingApproval.status == "pending",
                PendingApproval.expires_at > datetime.now()
            ).order_by(PendingApproval.created_at).all()
            
            return approvals
    
    async def list_workflows(self, admin_id: int, include_inactive: bool = False) -> List[BotWorkflow]:
        """List all workflows."""
        if not await admin_auth.is_admin(admin_id):
            raise AdminAuthError("Admin privileges required")
        
        async with get_db_session() as session:
            query = session.query(BotWorkflow)
            
            if not include_inactive:
                query = query.filter(BotWorkflow.is_active == True)
            
            workflows = query.order_by(BotWorkflow.status, BotWorkflow.name).all()
            return workflows
    
    async def get_workflow_stats(self, admin_id: int) -> Dict[str, Any]:
        """Get workflow statistics."""
        if not await admin_auth.has_permission(admin_id, Permissions.VIEW_ANALYTICS):
            raise InsufficientPermissionError("No permission to view analytics")
        
        async with get_db_session() as session:
            total_workflows = session.query(BotWorkflow).count()
            active_workflows = session.query(BotWorkflow).filter(BotWorkflow.is_active == True).count()
            pending_workflows = session.query(BotWorkflow).filter(BotWorkflow.status == WorkflowStatus.PENDING).count()
            
            # Get execution stats
            total_executions = session.query(BotWorkflow).with_entities(
                session.query(BotWorkflow.execution_count).label('total')
            ).scalar() or 0
            
            return {
                "total_workflows": total_workflows,
                "active_workflows": active_workflows,
                "pending_workflows": pending_workflows,
                "total_executions": total_executions,
                "queue_size": self.execution_queue.qsize()
            }


# Global workflow manager instance
workflow_manager = None


def get_workflow_manager(telegram_client: TelegramClient) -> WorkflowManager:
    """Get global workflow manager instance."""
    global workflow_manager
    if workflow_manager is None:
        workflow_manager = WorkflowManager(telegram_client)
    return workflow_manager
