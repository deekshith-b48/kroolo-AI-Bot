"""
Inline query handler for Kroolo Agent Bot
Handles @krooloAgentBot <query> inline queries
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
        chat_id = update.inline_query.chat_type if hasattr(update.inline_query, 'chat_type') else 'private'
        
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
        """Generate inline query results"""
        results = []
        
        # Generate unique ID for this query
        query_hash = hashlib.md5(f"{user.id}:{query}".encode()).hexdigest()[:8]
        
        # Main AI response result
        try:
            # For inline queries, we'll provide a quick response without calling AI
            # This prevents abuse and ensures fast response times
            ai_result = InlineQueryResultArticle(
                id=f"ai_{query_hash}",
                title=f"🤖 AI Response: {query[:50]}{'...' if len(query) > 50 else ''}",
                description="Get AI-powered answer to your question",
                input_message_content=InputTextMessageContent(
                    f"🔍 **Query:** {query}\n\n"
                    f"💡 **AI Response:**\n"
                    f"Use `/ask {query}` for a detailed AI response.\n\n"
                    f"*Inline queries provide quick previews. Use /ask for full responses.*",
                    parse_mode=ParseMode.MARKDOWN
                ),
                thumb_url="https://img.icons8.com/color/48/000000/robot.png"
            )
            results.append(ai_result)
            
        except Exception as e:
            logger.error(f"Error generating AI result: {e}")
        
        # Quick action results
        quick_actions = [
            {
                "id": f"ask_{query_hash}",
                "title": f"📝 Ask AI: {query[:40]}{'...' if len(query) > 40 else ''}",
                "description": "Send as /ask command",
                "text": f"/ask {query}",
                "thumb_url": "https://img.icons8.com/color/48/000000/chat.png"
            },
            {
                "id": f"topic_{query_hash}",
                "title": f"🎯 Set Topic: {query[:40]}{'...' if len(query) > 40 else ''}",
                "description": "Set as community topic",
                "text": f"/topic {query}",
                "thumb_url": "https://img.icons8.com/color/48/000000/topic.png"
            }
        ]
        
        for action in quick_actions:
            result = InlineQueryResultArticle(
                id=action["id"],
                title=action["title"],
                description=action["description"],
                input_message_content=InputTextMessageContent(action["text"]),
                thumb_url=action["thumb_url"]
            )
            results.append(result)
        
        # Add contextual suggestions based on query type
        contextual_results = await self._generate_contextual_results(query, query_hash)
        results.extend(contextual_results)
        
        return results
    
    async def _generate_contextual_results(self, query: str, query_hash: str) -> List[InlineQueryResultArticle]:
        """Generate contextual results based on query content"""
        results = []
        
        # Detect query type and provide relevant suggestions
        query_lower = query.lower()
        
        # Technical/Programming queries
        if any(word in query_lower for word in ["code", "programming", "python", "javascript", "api", "bug", "error"]):
            results.append(InlineQueryResultArticle(
                id=f"tech_{query_hash}",
                title="💻 Technical Support",
                description="Get programming help and code examples",
                input_message_content=InputTextMessageContent(
                    f"🔧 **Technical Query:** {query}\n\n"
                    f"I can help with:\n"
                    f"• Code review and debugging\n"
                    f"• API documentation\n"
                    f"• Best practices\n\n"
                    f"Use `/ask {query}` for detailed technical assistance."
                ),
                thumb_url="https://img.icons8.com/color/48/000000/code.png"
            ))
        
        # Business/Analytics queries
        elif any(word in query_lower for word in ["business", "analytics", "data", "report", "sales", "marketing", "strategy"]):
            results.append(InlineQueryResultArticle(
                id=f"business_{query_hash}",
                title="📊 Business Insights",
                description="Get business analysis and insights",
                input_message_content=InputTextMessageContent(
                    f"📈 **Business Query:** {query}\n\n"
                    f"I can help with:\n"
                    f"• Market analysis\n"
                    f"• Data interpretation\n"
                    f"• Strategy recommendations\n\n"
                    f"Use `/ask {query}` for comprehensive business insights."
                ),
                thumb_url="https://img.icons8.com/color/48/000000/business.png"
            ))
        
        # Creative/Content queries
        elif any(word in query_lower for word in ["write", "content", "creative", "story", "article", "blog", "social"]):
            results.append(InlineQueryResultArticle(
                id=f"creative_{query_hash}",
                title="✍️ Content Creation",
                description="Get creative writing help and ideas",
                input_message_content=InputTextMessageContent(
                    f"🎨 **Creative Query:** {query}\n\n"
                    f"I can help with:\n"
                    f"• Content ideas and outlines\n"
                    f"• Writing assistance\n"
                    f"• Creative brainstorming\n\n"
                    f"Use `/ask {query}` for detailed creative support."
                ),
                thumb_url="https://img.icons8.com/color/48/000000/creative.png"
            ))
        
        # Learning/Education queries
        elif any(word in query_lower for word in ["learn", "study", "education", "tutorial", "explain", "how to", "what is"]):
            results.append(InlineQueryResultArticle(
                id=f"learn_{query_hash}",
                title="📚 Learning Assistant",
                description="Get educational explanations and tutorials",
                input_message_content=InputTextMessageContent(
                    f"🎓 **Learning Query:** {query}\n\n"
                    f"I can help with:\n"
                    f"• Concept explanations\n"
                    f"• Step-by-step tutorials\n"
                    f"• Learning resources\n\n"
                    f"Use `/ask {query}` for comprehensive learning support."
                ),
                thumb_url="https://img.icons8.com/color/48/000000/graduation-cap.png"
            ))
        
        # General knowledge queries
        else:
            results.append(InlineQueryResultArticle(
                id=f"general_{query_hash}",
                title="🌐 General Knowledge",
                description="Get information and answers",
                input_message_content=InputTextMessageContent(
                    f"🔍 **Query:** {query}\n\n"
                    f"I can help with:\n"
                    f"• Information and facts\n"
                    f"• Problem solving\n"
                    f"• Research assistance\n\n"
                    f"Use `/ask {query}` for detailed answers."
                ),
                thumb_url="https://img.icons8.com/color/48/000000/search.png"
            ))
        
        return results
    
    async def _show_inline_help(self, update: Update):
        """Show help for inline queries"""
        help_results = [
            InlineQueryResultArticle(
                id="help_1",
                title="🤖 How to use @krooloAgentBot",
                description="Learn how to use inline queries",
                input_message_content=InputTextMessageContent(
                    "**How to use @krooloAgentBot inline queries:**\n\n"
                    "1. Type `@krooloAgentBot` followed by your question\n"
                    "2. Select from the suggested results\n"
                    "3. Choose to send as message or use quick commands\n\n"
                    "**Examples:**\n"
                    "• `@krooloAgentBot explain AI`\n"
                    "• `@krooloAgentBot python tutorial`\n"
                    "• `@krooloAgentBot business strategy`\n\n"
                    "**Commands:**\n"
                    "• `/ask <question>` - Get detailed AI response\n"
                    "• `/topic <name>` - Set community topic\n"
                    "• `/help` - See all available commands"
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
