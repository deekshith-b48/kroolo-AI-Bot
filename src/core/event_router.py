"""
Event router for intelligently routing messages to appropriate agents.
Uses content analysis and intent classification to determine the best agent for each message.
Includes admin command handling and workflow integration.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from .intent_classifier import IntentClassifier
from .agent_manager import AgentManager
from .content_analyzer import ContentAnalyzer
from .admin_auth import admin_auth
from .admin_commands import get_admin_commands
from .admin_panels import get_admin_panels
from .workflow_manager import get_workflow_manager
from .community_manager import get_community_manager
from .telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be routed."""
    COMMAND = "command"
    MENTION = "mention"
    QUESTION = "question"
    STATEMENT = "statement"
    CALLBACK = "callback"
    INLINE_QUERY = "inline_query"
    ADMIN_COMMAND = "admin_command"


class Intent(Enum):
    """User intent classification."""
    NEWS = "news"
    QUIZ = "quiz"
    DEBATE = "debate"
    FUN = "fun"
    PERSONA_CHAT = "persona_chat"
    MODERATION = "moderation"
    ADMIN = "admin"
    HELP = "help"
    WORKFLOW = "workflow"
    UNKNOWN = "unknown"


class EventRouter:
    """Routes incoming messages to appropriate agents based on content and intent."""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.agent_manager = AgentManager()
        self.content_analyzer = ContentAnalyzer()
        self.telegram_client = TelegramClient()
        
        # Initialize admin system components
        self.admin_commands = None
        self.admin_panels = None
        self.workflow_manager = None
        self.community_manager = None
        
        # Command patterns
        self.command_patterns = {
            r'/news\s+(.*)': Intent.NEWS,
            r'/quiz\s*(.*)': Intent.QUIZ,
            r'/debate\s+(.*)': Intent.DEBATE,
            r'/fun\s*(.*)': Intent.FUN,
            r'/help\s*(.*)': Intent.HELP,
            r'/config\s*(.*)': Intent.ADMIN,
            r'/agents\s*(.*)': Intent.HELP,
            r'/rules\s*(.*)': Intent.HELP,
        }
        
        # Admin command patterns
        self.admin_command_patterns = {
            r'/admin_help\s*(.*)': Intent.ADMIN,
            r'/status\s*(.*)': Intent.ADMIN,
            r'/promote\s+(.*)': Intent.ADMIN,
            r'/demote\s+(.*)': Intent.ADMIN,
            r'/ban\s+(.*)': Intent.ADMIN,
            r'/unban\s+(.*)': Intent.ADMIN,
            r'/mute\s+(.*)': Intent.ADMIN,
            r'/unmute\s+(.*)': Intent.ADMIN,
            r'/listadmins\s*(.*)': Intent.ADMIN,
            r'/addworkflow\s+(.*)': Intent.ADMIN,
            r'/removeworkflow\s+(.*)': Intent.ADMIN,
            r'/listworkflows\s*(.*)': Intent.ADMIN,
            r'/toggleworkflow\s+(.*)': Intent.ADMIN,
            r'/approvals\s*(.*)': Intent.ADMIN,
            r'/approve\s+(.*)': Intent.ADMIN,
            r'/reject\s+(.*)': Intent.ADMIN,
            r'/reload\s*(.*)': Intent.ADMIN,
            r'/logs\s*(.*)': Intent.ADMIN,
            r'/analytics\s*(.*)': Intent.ADMIN,
            r'/admin_panel\s*(.*)': Intent.ADMIN,
        }
        
        # Mention patterns
        self.mention_pattern = r'@(\w+)'
    
    async def initialize(self):
        """Initialize the event router with admin components."""
        await self.telegram_client.initialize()
        
        # Initialize admin system components
        self.admin_commands = get_admin_commands(self.telegram_client)
        self.admin_panels = get_admin_panels(self.telegram_client)
        self.workflow_manager = get_workflow_manager(self.telegram_client)
        self.community_manager = get_community_manager(self.telegram_client)
        
        # Initialize workflow manager
        await self.workflow_manager.initialize()
        
        logger.info("Event router initialized with admin system")
        
    async def route_update(self, update: Any, message_info: Dict[str, Any]) -> Dict[str, Any]:
        """Route an incoming update to the appropriate handler."""
        try:
            user_id = message_info.get("user_id")
            chat_id = message_info.get("chat_id")
            
            # Check if user is banned
            if user_id and await admin_auth.is_user_banned(user_id):
                return {
                    "routed": True,
                    "blocked": True,
                    "reason": "User is banned"
                }
            
            # Check if user is muted in this chat
            if user_id and chat_id and await admin_auth.is_user_muted(user_id, chat_id):
                return {
                    "routed": True,
                    "blocked": True,
                    "reason": "User is muted in this chat"
                }
            
            # Determine message type
            message_type = self._classify_message_type(message_info)
            
            # Handle callback queries (inline keyboard responses)
            if message_type == MessageType.CALLBACK:
                return await self._handle_callback_query(message_info)
            
            # Extract intent
            intent = await self._extract_intent(message_info, message_type)
            
            # Handle admin commands
            if intent == Intent.ADMIN or message_type == MessageType.ADMIN_COMMAND:
                return await self._handle_admin_command(message_info)
            
            # Check community settings and command permissions
            if chat_id and message_type == MessageType.COMMAND:
                text = message_info.get("text", "")
                command = text.split()[0].lstrip('/') if text.startswith('/') else ""
                
                if not await self.community_manager.is_command_allowed(chat_id, command):
                    return {
                        "routed": True,
                        "blocked": True,
                        "reason": f"Command '{command}' is not allowed in this community"
                    }
            
            # Check for workflow triggers
            if message_type == MessageType.COMMAND:
                workflow_result = await self._check_workflow_trigger(message_info)
                if workflow_result:
                    return workflow_result
            
            # Select appropriate agent
            agent = await self._select_agent(message_info, intent, message_type)
            
            # Route to agent
            if agent:
                result = await self._route_to_agent(agent, message_info, intent)
                return {
                    "routed": True,
                    "agent": agent.handle,
                    "intent": intent.value,
                    "result": result
                }
            else:
                # Default handling
                result = await self._handle_default(message_info, intent)
                return {
                    "routed": False,
                    "intent": intent.value,
                    "result": result
                }
                
        except Exception as e:
            logger.error(f"Error routing update: {e}")
            return {
                "routed": False,
                "error": str(e),
                "fallback": True
            }
    
    def _classify_message_type(self, message_info: Dict[str, Any]) -> MessageType:
        """Classify the type of message."""
        if message_info.get("type") == "callback_query":
            return MessageType.CALLBACK
        elif message_info.get("type") == "inline_query":
            return MessageType.INLINE_QUERY
        
        text = message_info.get("text", "")
        
        # Check for admin commands first
        if text.startswith('/'):
            for pattern in self.admin_command_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    return MessageType.ADMIN_COMMAND
            return MessageType.COMMAND
        
        # Check for mentions
        if re.search(self.mention_pattern, text):
            return MessageType.MENTION
        
        # Check for questions
        if self._is_question(text):
            return MessageType.QUESTION
        
        return MessageType.STATEMENT
    
    def _is_question(self, text: str) -> bool:
        """Check if text is a question."""
        question_indicators = ['?', 'what', 'how', 'why', 'when', 'where', 'who', 'which']
        text_lower = text.lower().strip()
        
        return (text_lower.endswith('?') or 
                any(indicator in text_lower for indicator in question_indicators))
    
    async def _extract_intent(self, message_info: Dict[str, Any], message_type: MessageType) -> Intent:
        """Extract user intent from message."""
        text = message_info.get("text", "")
        
        # Handle admin commands
        if message_type == MessageType.ADMIN_COMMAND:
            return Intent.ADMIN
        
        # Handle regular commands
        elif message_type == MessageType.COMMAND:
            for pattern, intent in self.command_patterns.items():
                if re.match(pattern, text, re.IGNORECASE):
                    return intent
            
            # Check if it's a workflow trigger
            if self.workflow_manager:
                workflow = await self.workflow_manager.get_workflow_by_trigger(text.split()[0])
                if workflow:
                    return Intent.WORKFLOW
        
        # Handle mentions
        elif message_type == MessageType.MENTION:
            mention = re.search(self.mention_pattern, text)
            if mention:
                agent_handle = mention.group(1)
                agent = await self.agent_manager.get_agent_by_handle(agent_handle)
                if agent:
                    return Intent.PERSONA_CHAT
        
        # Use ML-based intent classification for other cases
        if text:
            return await self.intent_classifier.classify_intent(text)
        
        return Intent.UNKNOWN
    
    async def _select_agent(self, message_info: Dict[str, Any], intent: Intent, message_type: MessageType) -> Optional[Any]:
        """Select the most appropriate agent for the message."""
        chat_id = message_info.get("chat_id")
        
        # Get available agents for this chat
        available_agents = await self.agent_manager.get_available_agents(chat_id)
        
        if not available_agents:
            return None
        
        # Handle explicit mentions
        if message_type == MessageType.MENTION:
            mention = re.search(self.mention_pattern, message_info.get("text", ""))
            if mention:
                agent_handle = mention.group(1)
                return await self.agent_manager.get_agent_by_handle(agent_handle)
        
        # Handle commands with specific intent
        if message_type == MessageType.COMMAND:
            if intent == Intent.NEWS:
                return await self.agent_manager.get_agent_by_type("news")
            elif intent == Intent.QUIZ:
                return await self.agent_manager.get_agent_by_type("quiz")
            elif intent == Intent.DEBATE:
                return await self.agent_manager.get_agent_by_type("debate")
            elif intent == Intent.FUN:
                return await self.agent_manager.get_agent_by_type("fun")
        
        # Intent-based routing
        if intent == Intent.NEWS:
            return await self.agent_manager.get_agent_by_type("news")
        elif intent == Intent.QUIZ:
            return await self.agent_manager.get_agent_by_type("quiz")
        elif intent == Intent.DEBATE:
            return await self.agent_manager.get_agent_by_type("debate")
        elif intent == Intent.FUN:
            return await self.agent_manager.get_agent_by_type("fun")
        elif intent == Intent.PERSONA_CHAT:
            # Use default persona agent
            return await self.agent_manager.get_default_agent(chat_id)
        
        # Fallback to default agent
        return await self.agent_manager.get_default_agent(chat_id)
    
    async def _route_to_agent(self, agent: Any, message_info: Dict[str, Any], intent: Intent) -> Dict[str, Any]:
        """Route message to a specific agent."""
        try:
            # Prepare context for agent
            context = await self._prepare_context(message_info, intent)
            
            # Get agent response
            response = await agent.process_message(message_info, context)
            
            return {
                "agent_id": agent.id,
                "agent_name": agent.name,
                "response": response,
                "context_used": context
            }
            
        except Exception as e:
            logger.error(f"Error routing to agent {agent.handle}: {e}")
            return {
                "error": str(e),
                "fallback_response": "I'm having trouble processing that right now. Please try again later."
            }
    
    async def _handle_default(self, message_info: Dict[str, Any], intent: Intent) -> Dict[str, Any]:
        """Handle messages that couldn't be routed to a specific agent."""
        return {
            "response": "I'm not sure how to handle that. Try mentioning a specific agent like @AlanTuring or use /help for available commands.",
            "suggested_agents": await self._get_suggested_agents(intent)
        }
    
    async def _prepare_context(self, message_info: Dict[str, Any], intent: Intent) -> Dict[str, Any]:
        """Prepare context information for the agent."""
        context = {
            "chat_id": message_info.get("chat_id"),
            "user_id": message_info.get("user_id"),
            "message_type": message_info.get("type"),
            "intent": intent.value,
            "timestamp": message_info.get("timestamp"),
            "chat_type": message_info.get("chat_type"),
            "is_private": message_info.get("is_private", False)
        }
        
        # Add content analysis if available
        if message_info.get("text"):
            content_analysis = await self.content_analyzer.analyze_content(message_info["text"])
            context["content_analysis"] = content_analysis
        
        return context
    
    async def _get_suggested_agents(self, intent: Intent) -> List[str]:
        """Get suggested agents based on intent."""
        if intent == Intent.NEWS:
            return ["@AIReporter"]
        elif intent == Intent.QUIZ:
            return ["@QuizMaster"]
        elif intent == Intent.DEBATE:
            return ["@DebateBot", "@OldAI", "@NewAI"]
        elif intent == Intent.FUN:
            return ["@FunFact"]
        else:
            return ["@AlanTuring", "@PersonaHubBot"]
    
    async def _handle_admin_command(self, message_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle admin commands."""
        try:
            user_id = message_info.get("user_id")
            chat_id = message_info.get("chat_id")
            text = message_info.get("text", "")
            message_id = message_info.get("message_id")
            
            # Parse command and arguments
            parts = text.split()
            command = parts[0].lstrip('/') if parts else ""
            args = parts[1:] if len(parts) > 1 else []
            
            # Execute admin command
            result = await self.admin_commands.handle_command(
                user_id=user_id,
                chat_id=chat_id,
                command=command,
                args=args,
                message_id=message_id
            )
            
            # Send response
            if result.success:
                response_data = await self.telegram_client.send_message(
                    chat_id=chat_id,
                    text=result.message,
                    parse_mode="Markdown",
                    reply_markup={"inline_keyboard": result.inline_keyboard} if result.inline_keyboard else None
                )
            else:
                response_data = await self.telegram_client.send_message(
                    chat_id=chat_id,
                    text=result.message,
                    parse_mode="Markdown"
                )
            
            return {
                "routed": True,
                "handler": "admin_command",
                "command": command,
                "success": result.success,
                "response": response_data
            }
            
        except Exception as e:
            logger.error(f"Error handling admin command: {e}")
            
            # Send error message
            try:
                await self.telegram_client.send_message(
                    chat_id=message_info.get("chat_id"),
                    text=f"❌ Admin command failed: {str(e)}",
                    parse_mode="Markdown"
                )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
            
            return {
                "routed": True,
                "handler": "admin_command",
                "error": str(e),
                "success": False
            }
    
    async def _handle_callback_query(self, message_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle callback queries from inline keyboards."""
        try:
            user_id = message_info.get("user_id")
            chat_id = message_info.get("chat_id")
            callback_data = message_info.get("data", "")
            message_id = message_info.get("message_id")
            
            # Extract callback query ID for answering
            callback_query_id = message_info.get("callback_query_id", "")
            
            # Check if it's an admin callback
            if callback_data.startswith("admin:") or callback_data.startswith("workflow:"):
                result = await self.admin_panels.handle_callback(
                    user_id=user_id,
                    chat_id=chat_id,
                    callback_data=callback_data,
                    message_id=message_id,
                    callback_query_id=callback_query_id
                )
                
                return {
                    "routed": True,
                    "handler": "admin_callback",
                    "callback_data": callback_data,
                    "success": result.get("success", False),
                    "result": result
                }
            
            # Handle other callback queries (agent-specific, etc.)
            # This would route to appropriate agent callback handlers
            return {
                "routed": False,
                "handler": "callback_query",
                "callback_data": callback_data,
                "message": "Callback not handled by admin system"
            }
            
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            
            # Answer callback query with error
            try:
                await self.telegram_client.answer_callback_query(
                    callback_query_id=message_info.get("callback_query_id", ""),
                    text="❌ Action failed",
                    show_alert=True
                )
            except Exception as answer_error:
                logger.error(f"Failed to answer callback query: {answer_error}")
            
            return {
                "routed": True,
                "handler": "callback_query",
                "error": str(e),
                "success": False
            }
    
    async def _check_workflow_trigger(self, message_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if message triggers a workflow."""
        try:
            text = message_info.get("text", "")
            if not text.startswith('/'):
                return None
            
            trigger_command = text.split()[0]
            workflow = await self.workflow_manager.get_workflow_by_trigger(trigger_command)
            
            if workflow:
                # Extract input data from message
                parts = text.split()[1:] if len(text.split()) > 1 else []
                input_data = {
                    "command": trigger_command,
                    "args": parts,
                    "message_text": text,
                    "user_name": message_info.get("username", "Unknown")
                }
                
                # Execute workflow
                result = await self.workflow_manager.execute_workflow(
                    workflow_name=workflow.name,
                    input_data=input_data,
                    user_id=message_info.get("user_id"),
                    chat_id=message_info.get("chat_id")
                )
                
                # Send response
                if result.success:
                    response_text = f"🤖 Workflow '{workflow.name}' executed successfully"
                    if result.response_data:
                        response_text += f"\n\nResult: {result.response_data}"
                else:
                    response_text = f"❌ Workflow '{workflow.name}' failed: {result.error_message}"
                
                await self.telegram_client.send_message(
                    chat_id=message_info.get("chat_id"),
                    text=response_text,
                    parse_mode="Markdown"
                )
                
                return {
                    "routed": True,
                    "handler": "workflow",
                    "workflow_name": workflow.name,
                    "success": result.success,
                    "result": result
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking workflow trigger: {e}")
            return None
    
    async def shutdown(self):
        """Shutdown the event router."""
        if self.workflow_manager:
            await self.workflow_manager.shutdown()
        
        if self.telegram_client:
            await self.telegram_client.shutdown()
        
        logger.info("Event router shutdown completed")


# Global event router instance
event_router = EventRouter()
