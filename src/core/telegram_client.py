"""
Telegram client for handling bot operations.
Manages webhooks, sends messages, and handles API interactions.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import aiohttp
import json

from config.settings import settings, BOT_TOKENS

logger = logging.getLogger(__name__)


class TelegramClient:
    """Client for Telegram Bot API operations."""
    
    def __init__(self):
        self.base_url = "https://api.telegram.org/bot"
        self.session: Optional[aiohttp.ClientSession] = None
        self.bot_tokens = BOT_TOKENS
        self.main_token = settings.telegram_bot_token
        self.rate_limit_delays = {}  # Track rate limit delays per chat
        
    async def initialize(self):
        """Initialize the HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Telegram client initialized")
    
    async def shutdown(self):
        """Shutdown the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Telegram client shutdown")
    
    async def _make_request(self, method: str, token: str, **params) -> Dict[str, Any]:
        """Make a request to the Telegram API."""
        if not self.session:
            await self.initialize()
        
        url = f"{self.base_url}{token}/{method}"
        
        try:
            async with self.session.post(url, json=params) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        return result.get('result', {})
                    else:
                        error_msg = result.get('description', 'Unknown error')
                        logger.error(f"Telegram API error: {error_msg}")
                        raise Exception(f"Telegram API error: {error_msg}")
                elif response.status == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, retry after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    # Retry once
                    async with self.session.post(url, json=params) as retry_response:
                        if retry_response.status == 200:
                            result = await retry_response.json()
                            if result.get('ok'):
                                return result.get('result', {})
                else:
                    error_text = await response.text()
                    logger.error(f"HTTP {response.status}: {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except asyncio.TimeoutError:
            logger.error("Telegram API request timeout")
            raise Exception("Telegram API request timeout")
        except Exception as e:
            logger.error(f"Telegram API request failed: {e}")
            raise
    
    async def set_webhook(self, url: str, token: str = None) -> bool:
        """Set webhook URL for the bot."""
        token = token or self.main_token
        
        try:
            result = await self._make_request(
                method="setWebhook",
                token=token,
                url=url,
                allowed_updates=[
                    "message", "edited_message", "channel_post", "edited_channel_post",
                    "inline_query", "chosen_inline_result", "callback_query",
                    "shipping_query", "pre_checkout_query", "poll", "poll_answer",
                    "my_chat_member", "chat_member", "chat_join_request"
                ]
            )
            logger.info(f"Webhook set successfully: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False
    
    async def delete_webhook(self, token: str = None) -> bool:
        """Delete webhook for the bot."""
        token = token or self.main_token
        
        try:
            result = await self._make_request(
                method="deleteWebhook",
                token=token
            )
            logger.info("Webhook deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False
    
    async def get_webhook_info(self, token: str = None) -> Dict[str, Any]:
        """Get current webhook information."""
        token = token or self.main_token
        
        try:
            result = await self._make_request(
                method="getWebhookInfo",
                token=token
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get webhook info: {e}")
            return {}
    
    async def send_message(self, chat_id: int, text: str, token: str = None, 
                          parse_mode: str = None, reply_to_message_id: int = None,
                          reply_markup: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a message to a chat."""
        token = token or self.main_token
        
        # Check rate limiting
        await self._check_rate_limit(chat_id, token)
        
        params = {
            "chat_id": chat_id,
            "text": text
        }
        
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_to_message_id:
            params["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        
        try:
            result = await self._make_request(
                method="sendMessage",
                token=token,
                **params
            )
            logger.debug(f"Message sent to chat {chat_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to send message to chat {chat_id}: {e}")
            raise
    
    async def send_poll(self, chat_id: int, question: str, options: List[str], 
                        token: str = None, is_anonymous: bool = False,
                        type: str = "quiz", correct_option_id: int = None,
                        explanation: str = None) -> Dict[str, Any]:
        """Send a poll to a chat."""
        token = token or self.main_token
        
        await self._check_rate_limit(chat_id, token)
        
        params = {
            "chat_id": chat_id,
            "question": question,
            "options": json.dumps(options),
            "is_anonymous": is_anonymous,
            "type": type
        }
        
        if correct_option_id is not None:
            params["correct_option_id"] = correct_option_id
        if explanation:
            params["explanation"] = explanation
        
        try:
            result = await self._make_request(
                method="sendPoll",
                token=token,
                **params
            )
            logger.debug(f"Poll sent to chat {chat_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to send poll to chat {chat_id}: {e}")
            raise
    
    async def edit_message(self, chat_id: int, message_id: int, text: str,
                          token: str = None, parse_mode: str = None,
                          reply_markup: Dict[str, Any] = None) -> Dict[str, Any]:
        """Edit an existing message."""
        token = token or self.main_token
        
        params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        
        try:
            result = await self._make_request(
                method="editMessageText",
                token=token,
                **params
            )
            logger.debug(f"Message {message_id} edited in chat {chat_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to edit message {message_id} in chat {chat_id}: {e}")
            raise
    
    async def delete_message(self, chat_id: int, message_id: int, token: str = None) -> bool:
        """Delete a message from a chat."""
        token = token or self.main_token
        
        try:
            result = await self._make_request(
                method="deleteMessage",
                token=token,
                chat_id=chat_id,
                message_id=message_id
            )
            logger.debug(f"Message {message_id} deleted from chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete message {message_id} from chat {chat_id}: {e}")
            return False
    
    async def answer_callback_query(self, callback_query_id: str, text: str = None,
                                   show_alert: bool = False, token: str = None) -> bool:
        """Answer a callback query."""
        token = token or self.main_token
        
        params = {
            "callback_query_id": callback_query_id
        }
        
        if text:
            params["text"] = text
        if show_alert:
            params["show_alert"] = show_alert
        
        try:
            result = await self._make_request(
                method="answerCallbackQuery",
                token=token,
                **params
            )
            return True
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}")
            return False
    
    async def get_chat_member(self, chat_id: int, user_id: int, token: str = None) -> Dict[str, Any]:
        """Get information about a chat member."""
        token = token or self.main_token
        
        try:
            result = await self._make_request(
                method="getChatMember",
                token=token,
                chat_id=chat_id,
                user_id=user_id
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get chat member info: {e}")
            return {}
    
    async def get_chat(self, chat_id: int, token: str = None) -> Dict[str, Any]:
        """Get information about a chat."""
        token = token or self.main_token
        
        try:
            result = await self._make_request(
                method="getChat",
                token=token,
                chat_id=chat_id
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get chat info: {e}")
            return {}
    
    async def _check_rate_limit(self, chat_id: int, token: str):
        """Check and handle rate limiting for a chat."""
        key = f"{token}:{chat_id}"
        current_time = datetime.now()
        
        if key in self.rate_limit_delays:
            last_delay = self.rate_limit_delays[key]
            time_since_last = (current_time - last_delay).total_seconds()
            
            # If we had a recent rate limit, add a small delay
            if time_since_last < 60:  # Within last minute
                await asyncio.sleep(0.1)  # 100ms delay
        
        # Update last delay time
        self.rate_limit_delays[key] = current_time
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the Telegram client."""
        try:
            # Test API connectivity
            me_info = await self._make_request(
                method="getMe",
                token=self.main_token
            )
            
            return {
                "status": "healthy",
                "bot_info": me_info,
                "webhook_info": await self.get_webhook_info(),
                "session_active": self.session is not None
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the Telegram client."""
        return {
            "main_token": self.main_token[:10] + "..." if self.main_token else None,
            "available_tokens": list(self.bot_tokens.keys()),
            "session_active": self.session is not None,
            "rate_limit_delays": len(self.rate_limit_delays)
        }
    
    def get_bot_token(self, bot_type: str = "main") -> Optional[str]:
        """Get bot token by type."""
        return self.bot_tokens.get(bot_type)
    
    def has_bot_token(self, bot_type: str) -> bool:
        """Check if a bot type has a token."""
        return bot_type in self.bot_tokens
