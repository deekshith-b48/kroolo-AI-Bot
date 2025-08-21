"""
Base agent class that provides common functionality for all AI agents.
Implements message processing, context management, and safety checks.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

from ..core.telegram_client import TelegramClient
from ..core.rag_service import RAGService
from ..core.safety_checker import SafetyChecker
from ..core.context_manager import ContextManager
from ..utils.formatter import MessageFormatter

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, config: Any):
        self.config = config
        self.agent_type = self._get_agent_type()
        self.handle = getattr(config, 'handle', 'UnknownAgent')
        self.name = getattr(config, 'name', 'Unknown Agent')
        self.persona = getattr(config, 'persona', '')
        self.tone = getattr(config, 'tone', 'neutral')
        self.capabilities = getattr(config, 'capabilities', [])
        self.guardrails = getattr(config, 'guardrails', [])
        self.safety_level = getattr(config, 'safety_level', 'standard')
        
        # Services
        self.telegram_client = TelegramClient()
        self.rag_service = RAGService()
        self.safety_checker = SafetyChecker()
        self.context_manager = ContextManager()
        self.formatter = MessageFormatter()
        
        # State
        self.is_active = True
        self.last_activity = datetime.now()
        self.message_count = 0
        
        logger.info(f"Initialized agent: {self.handle} ({self.agent_type})")
    
    def _get_agent_type(self) -> str:
        """Get the agent type based on class name."""
        class_name = self.__class__.__name__.lower()
        if 'news' in class_name:
            return 'news'
        elif 'quiz' in class_name:
            return 'quiz'
        elif 'debate' in class_name:
            return 'debate'
        elif 'fun' in class_name:
            return 'fun'
        else:
            return 'persona'
    
    async def process_message(self, message_info: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message and generate a response."""
        try:
            # Update activity
            self.last_activity = datetime.now()
            self.message_count += 1
            
            # Extract message details
            chat_id = message_info.get('chat_id')
            user_id = message_info.get('user_id')
            text = message_info.get('text', '')
            
            # Safety check
            safety_result = await self._check_safety(text, context)
            if not safety_result['safe']:
                return await self._handle_unsafe_content(safety_result, context)
            
            # Prepare agent context
            agent_context = await self._prepare_agent_context(message_info, context)
            
            # Generate response
            response = await self._generate_response(message_info, agent_context)
            
            # Format response
            formatted_response = await self._format_response(response, context)
            
            # Send response
            sent_message = await self._send_response(chat_id, formatted_response, context)
            
            # Update context
            await self._update_context(chat_id, user_id, text, response, context)
            
            return {
                'success': True,
                'response': formatted_response,
                'message_id': sent_message.get('message_id'),
                'context_updated': True
            }
            
        except Exception as e:
            logger.error(f"Error processing message in {self.handle}: {e}")
            return await self._handle_error(e, context)
    
    async def _check_safety(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if content is safe to process."""
        try:
            safety_result = await self.safety_checker.check_content(
                text=text,
                agent_config=self.config,
                context=context
            )
            return safety_result
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            # Default to safe if check fails
            return {'safe': True, 'confidence': 0.5, 'flags': []}
    
    async def _handle_unsafe_content(self, safety_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle content that fails safety checks."""
        flags = safety_result.get('flags', [])
        
        if 'harmful_content' in flags:
            response = "I cannot engage with that type of content. Please keep our conversation respectful and constructive."
        elif 'personal_advice' in flags:
            response = "I'm not qualified to give personal advice. Please consult with appropriate professionals for such matters."
        else:
            response = "I'm unable to process that request. Please rephrase or ask something else."
        
        return {
            'success': False,
            'response': response,
            'reason': 'safety_check_failed',
            'flags': flags
        }
    
    async def _prepare_agent_context(self, message_info: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context specific to this agent."""
        agent_context = {
            'agent_name': self.name,
            'agent_handle': self.handle,
            'agent_persona': self.persona,
            'agent_tone': self.tone,
            'agent_capabilities': self.capabilities,
            'user_message': message_info.get('text', ''),
            'chat_context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add RAG context if available
        if 'rag.retrieve' in self.capabilities:
            try:
                rag_context = await self.rag_service.get_relevant_context(
                    query=message_info.get('text', ''),
                    chat_id=message_info.get('chat_id'),
                    limit=5
                )
                agent_context['rag_context'] = rag_context
            except Exception as e:
                logger.warning(f"Failed to get RAG context: {e}")
        
        return agent_context
    
    @abstractmethod
    async def _generate_response(self, message_info: Dict[str, Any], agent_context: Dict[str, Any]) -> str:
        """Generate a response based on the message and context."""
        pass
    
    async def _format_response(self, response: str, context: Dict[str, Any]) -> str:
        """Format the response for Telegram."""
        try:
            formatted = await self.formatter.format_message(
                text=response,
                agent_tone=self.tone,
                chat_type=context.get('chat_type', 'group'),
                include_emoji=context.get('include_emoji', True)
            )
            return formatted
        except Exception as e:
            logger.error(f"Formatting failed: {e}")
            return response
    
    async def _send_response(self, chat_id: int, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send the response to Telegram."""
        try:
            # Check if response is too long
            if len(response) > 4096:
                # Split into multiple messages
                messages = self._split_long_message(response)
                sent_messages = []
                
                for i, message_part in enumerate(messages):
                    sent_msg = await self.telegram_client.send_message(
                        chat_id=chat_id,
                        text=message_part,
                        parse_mode='Markdown'
                    )
                    sent_messages.append(sent_msg)
                    
                    # Add delay between messages to avoid rate limiting
                    if i < len(messages) - 1:
                        await asyncio.sleep(0.5)
                
                return sent_messages[-1] if sent_messages else {}
            else:
                # Send single message
                return await self.telegram_client.send_message(
                    chat_id=chat_id,
                    text=response,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
            raise
    
    def _split_long_message(self, text: str, max_length: int = 4000) -> List[str]:
        """Split a long message into smaller parts."""
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Split by sentences to maintain readability
        sentences = text.split('. ')
        
        for sentence in sentences:
            if len(current_part + sentence + '. ') <= max_length:
                current_part += sentence + '. '
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = sentence + '. '
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    async def _update_context(self, chat_id: int, user_id: int, user_message: str, 
                            agent_response: str, context: Dict[str, Any]):
        """Update conversation context."""
        try:
            await self.context_manager.update_context(
                chat_id=chat_id,
                user_id=user_id,
                user_message=user_message,
                agent_response=agent_response,
                agent_handle=self.handle,
                context=context
            )
        except Exception as e:
            logger.warning(f"Failed to update context: {e}")
    
    async def _handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors during message processing."""
        error_message = f"I encountered an error while processing your request. Please try again later."
        
        # Log detailed error for debugging
        logger.error(f"Agent {self.handle} error: {str(error)}", exc_info=True)
        
        return {
            'success': False,
            'response': error_message,
            'error': str(error),
            'error_type': type(error).__name__
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the agent."""
        try:
            # Check basic functionality
            health_status = {
                'status': 'healthy',
                'agent': self.handle,
                'type': self.agent_type,
                'active': self.is_active,
                'last_activity': self.last_activity.isoformat(),
                'message_count': self.message_count,
                'capabilities': self.capabilities
            }
            
            # Check if agent can generate responses
            test_context = {
                'agent_name': self.name,
                'agent_persona': self.persona,
                'test_mode': True
            }
            
            try:
                test_response = await self._generate_response(
                    {'text': 'Hello, this is a health check.'},
                    test_context
                )
                health_status['response_generation'] = 'working'
                health_status['test_response_length'] = len(test_response)
            except Exception as e:
                health_status['response_generation'] = 'failed'
                health_status['response_error'] = str(e)
                health_status['status'] = 'degraded'
            
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent': self.handle,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities."""
        return self.capabilities.copy()
    
    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of agent configuration."""
        return {
            'handle': self.handle,
            'name': self.name,
            'type': self.agent_type,
            'tone': self.tone,
            'capabilities': self.capabilities,
            'guardrails': self.guardrails,
            'safety_level': self.safety_level,
            'active': self.is_active
        }
