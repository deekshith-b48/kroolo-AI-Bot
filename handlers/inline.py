"""
Inline query handler for Kroolo Agent Bot
Provides helpful inline suggestions and directs users to use /ask command
"""

import logging
import hashlib
from typing import List, Optional
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from services.ai_service import AIService
from utils.logger import log_user_action

logger = logging.getLogger(__name__)

class InlineQueryHandler:
    """Handles inline queries for the bot"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
    
    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline queries from users"""
        query = update.inline_query.query.strip()
        user = update.inline_query.from_user
        
        # Log the inline query
        if user:
            log_user_action(user.id, 0, "inline_query", query)
        
        # If no query, show help
        if not query:
            await self._show_inline_help(update)
            return
        
        try:
            # Generate results based on query type
            results = await self._generate_inline_results(query, user)
            
            # Answer the inline query
            await update.inline_query.answer(
                results=results,
                cache_time=30,  # Cache for 30 seconds
                switch_pm_text="Ask me directly",
                switch_pm_parameter="start"
            )
            
        except Exception as e:
            logger.error(f"Error handling inline query: {e}")
            # Fallback to simple result
            fallback_result = InlineQueryResultArticle(
                id="error",
                title="Error processing query",
                input_message_content=InputTextMessageContent(
                    "❌ Sorry, I encountered an error processing your query. Please try again or use /ask command."
                )
            )
            await update.inline_query.answer([fallback_result], cache_time=1)
    
    async def _generate_inline_results(self, query: str, user) -> List[InlineQueryResultArticle]:
        """Generate inline query results optimized for groups and topic threads"""
        results = []
        
        # Generate unique ID for this query
        query_hash = hashlib.md5(f"{user.id}:{query}".encode()).hexdigest()[:8]
        
        # Main AI response result - optimized for groups
        ask_result = InlineQueryResultArticle(
            id=f"ask_{query_hash}",
            title=f"🤖 Ask AI: {query[:50]}{'...' if len(query) > 50 else ''}",
            description="Get AI response directly in chat",
            input_message_content=InputTextMessageContent(
                f"🤖 **AI Response to:** {query}\n\n_Processing your question..._\n\n/ask {query}",
                parse_mode=ParseMode.MARKDOWN
            ),
            thumb_url="https://img.icons8.com/color/48/000000/robot.png"
        )
        results.append(ask_result)
        
        # Quick AI summary for groups
        summary_result = InlineQueryResultArticle(
            id=f"summary_{query_hash}",
            title=f"📋 Quick Summary: {query[:40]}{'...' if len(query) > 40 else ''}",
            description="Get a brief AI summary for group discussion",
            input_message_content=InputTextMessageContent(
                f"📋 **Quick Summary Request:** {query}\n\n/ask summarize: {query}",
                parse_mode=ParseMode.MARKDOWN
            ),
            thumb_url="https://img.icons8.com/color/48/000000/summary.png"
        )
        results.append(summary_result)
        
        # Topic management for groups
        topic_result = InlineQueryResultArticle(
            id=f"topic_{query_hash}",
            title=f"🎯 Set Topic: {query[:40]}{'...' if len(query) > 40 else ''}",
            description="Set as community discussion topic",
            input_message_content=InputTextMessageContent(
                f"🎯 **New Topic Set:** {query}\n\n/topic {query}",
                parse_mode=ParseMode.MARKDOWN
            ),
            thumb_url="https://img.icons8.com/color/48/000000/topic.png"
        )
        results.append(topic_result)
        
        # Community engagement options
        engagement_actions = [
            {
                "id": f"news_{query_hash}",
                "title": f"📰 News about: {query[:35]}{'...' if len(query) > 35 else ''}",
                "description": "Get latest news on this topic",
                "text": f"📰 **Latest News:** {query}\n\n/news {query}",
                "thumb_url": "https://img.icons8.com/color/48/000000/news.png"
            },
            {
                "id": f"quiz_{query_hash}",
                "title": f"🧩 Quiz about: {query[:35]}{'...' if len(query) > 35 else ''}",
                "description": "Create a quiz for group engagement",
                "text": f"🧩 **Quiz Time:** {query}\n\n/quiz {query}",
                "thumb_url": "https://img.icons8.com/color/48/000000/quiz.png"
            },
            {
                "id": f"fact_{query_hash}",
                "title": f"💡 Fun Fact: {query[:35]}{'...' if len(query) > 35 else ''}",
                "description": "Share an interesting fact",
                "text": f"💡 **Fun Fact about:** {query}\n\n/funfact {query}",
                "thumb_url": "https://img.icons8.com/color/48/000000/idea.png"
            }
        ]
        
        # Add engagement actions to results
        for action in engagement_actions:
            result = InlineQueryResultArticle(
                id=action["id"],
                title=action["title"],
                description=action["description"],
                input_message_content=InputTextMessageContent(
                    action["text"],
                    parse_mode=ParseMode.MARKDOWN
                ),
                thumb_url=action["thumb_url"]
            )
            results.append(result)
        
        # Help option
        help_result = InlineQueryResultArticle(
            id=f"help_{query_hash}",
            title="❓ Get Help & Commands",
            description="Show all available bot commands",
            input_message_content=InputTextMessageContent(
                "❓ **Getting Help**\n\nUse /help to see all available commands and features.",
                parse_mode=ParseMode.MARKDOWN
            ),
            thumb_url="https://img.icons8.com/color/48/000000/help.png"
        )
        results.append(help_result)
        
        return results
    
    async def _show_inline_help(self, update: Update):
        """Show help for inline queries"""
        help_results = [
            InlineQueryResultArticle(
                id="help_1",
                title="🤖 How to use Kroolo Agent Bot",
                description="Learn how to use the bot commands",
                input_message_content=InputTextMessageContent(
                    "**How to use Kroolo Agent Bot:**\n\n"
                    "**Commands:**\n"
                    "• `/start` - Start the bot\n"
                    "• `/help` - Show help\n"
                    "• `/ask <question>` - Ask AI\n"
                    "• `/topic <name>` - Set topic\n"
                    "• `/status` - Bot status (admin)\n"
                    "• `/admin_help` - Admin commands\n\n"
                    "**Inline Usage:**\n"
                    "Type your question to get quick suggestions and use `/ask` for full responses."
                ),
                thumb_url="https://img.icons8.com/color/48/000000/help.png"
            ),
            InlineQueryResultArticle(
                id="help_2",
                title="📝 Quick Commands",
                description="Common bot commands",
                input_message_content=InputTextMessageContent(
                    "**Quick Commands:**\n\n"
                    "• `/start` - Start the bot\n"
                    "• `/help` - Show help\n"
                    "• `/ask <question>` - Ask AI\n"
                    "• `/topic <name>` - Set topic\n"
                    "• `/status` - Bot status (admin)\n"
                    "• `/admin_help` - Admin commands"
                ),
                thumb_url="https://img.icons8.com/color/48/000000/command.png"
            )
        ]
        
        await update.inline_query.answer(
            results=help_results,
            cache_time=300,  # Cache help for 5 minutes
            switch_pm_text="Start bot",
            switch_pm_parameter="start"
        )
    
    async def handle_chosen_inline_result(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when user selects an inline result"""
        user = update.chosen_inline_result.from_user
        query = update.chosen_inline_result.query
        result_id = update.chosen_inline_result.result_id
        
        # Log the chosen result
        if user:
            log_user_action(user.id, 0, "chose_inline_result", f"result_id: {result_id}, query: {query}")
        
        # You can add additional logic here for tracking popular inline queries
        # or providing follow-up actions based on the chosen result
