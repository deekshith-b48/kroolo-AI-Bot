"""
Community Engagement Commands for Kroolo Agent Bot
Handles news, quizzes, fun facts, and scheduled posts
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from services.community_engagement import CommunityEngagementService
from services.auth import AuthService
from utils.logger import log_user_action, log_admin_action

logger = logging.getLogger(__name__)

class CommunityEngagementCommands:
    """Handles community engagement commands"""
    
    def __init__(self, engagement_service: CommunityEngagementService, auth_service: AuthService):
        self.engagement_service = engagement_service
        self.auth_service = auth_service
    
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command - fetch and display AI news"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        try:
            # Log action
            if user:
                log_user_action(user.id, chat_id, "news", "requested AI news")
            
            # Fetch AI news
            articles = await self.engagement_service.fetch_ai_news(limit=5)
            
            if not articles:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ **News Unavailable**\n\nUnable to fetch AI news at the moment. Please try again later.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Format news message
            news_text = "📰 **Latest AI News**\n\n"
            for i, article in enumerate(articles, 1):
                news_text += f"**{i}. {article['title']}**\n"
                if article.get('summary'):
                    news_text += f"{article['summary']}\n"
                news_text += f"🔗 [Read More]({article['link']})\n"
                news_text += f"📅 {article.get('published', 'Unknown date')}\n\n"
            
            news_text += "💡 *Use `/setnews HH:MM` to schedule daily news updates*"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=news_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in news command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error fetching news**\n\nPlease try again later or contact support."
            )
    
    async def quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /quiz command - start a quiz"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        try:
            # Log action
            if user:
                log_user_action(user.id, chat_id, "quiz", "started quiz")
            
            # Get random quiz
            quiz = self.engagement_service.get_random_quiz()
            
            # Create inline keyboard for options
            keyboard = []
            for option in quiz["options"]:
                keyboard.append([InlineKeyboardButton(option, callback_data=f"quiz_{option}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Store correct answer in user data for callback handling
            context.user_data["quiz_answer"] = quiz["correct_answer"]
            context.user_data["quiz_explanation"] = quiz["explanation"]
            
            quiz_text = (
                f"🧠 **AI Quiz Time!**\n\n"
                f"**Question:** {quiz['question']}\n\n"
                f"**Options:**\n"
                f"• A) {quiz['options'][0]}\n"
                f"• B) {quiz['options'][1]}\n"
                f"• C) {quiz['options'][2]}\n"
                f"• D) {quiz['options'][3]}\n\n"
                f"*Click an option to answer and earn points!*"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=quiz_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in quiz command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error starting quiz**\n\nPlease try again later."
            )
    
    async def funfact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /funfact command - display random AI fun fact"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        try:
            # Log action
            if user:
                log_user_action(user.id, chat_id, "funfact", "requested fun fact")
            
            # Get random fun fact
            fun_fact = self.engagement_service.get_random_fun_fact()
            
            fun_fact_text = (
                f"🎭 **AI Fun Fact**\n\n"
                f"{fun_fact}\n\n"
                f"💡 *Use `/setfunfact HH:MM` to schedule daily fun facts*"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=fun_fact_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error in funfact command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error getting fun fact**\n\nPlease try again later."
            )
    
    async def joke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /joke command - display random tech/AI joke"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        try:
            # Log action
            if user:
                log_user_action(user.id, chat_id, "joke", "requested joke")
            
            # Get random joke
            joke = self.engagement_service.get_random_joke()
            
            joke_text = (
                f"😄 **Tech Joke of the Day**\n\n"
                f"{joke}\n\n"
                f"🎭 *Use `/setjoke HH:MM` to schedule daily jokes*"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=joke_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error in joke command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error getting joke**\n\nPlease try again later."
            )
    
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /leaderboard command - show quiz leaderboard"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        try:
            # Log action
            if user:
                log_user_action(user.id, chat_id, "leaderboard", "viewed leaderboard")
            
            # Get leaderboard
            leaderboard = self.engagement_service.get_leaderboard(limit=10)
            
            if not leaderboard:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🏆 **Quiz Leaderboard**\n\nNo quiz scores yet! Be the first to take a quiz with `/quiz`"
                )
                return
            
            # Format leaderboard
            leaderboard_text = "🏆 **Quiz Leaderboard**\n\n"
            
            for entry in leaderboard:
                rank_emoji = "🥇" if entry["rank"] == 1 else "🥈" if entry["rank"] == 2 else "🥉" if entry["rank"] == 3 else f"{entry['rank']}."
                leaderboard_text += (
                    f"{rank_emoji} **{entry['username']}**\n"
                    f"   📊 {entry['points']} points • "
                    f"✅ {entry['correct_answers']}/{entry['total_questions']} "
                    f"({entry['accuracy']}%)\n\n"
                )
            
            leaderboard_text += "🎯 *Take a quiz with `/quiz` to climb the leaderboard!*"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=leaderboard_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error loading leaderboard**\n\nPlease try again later."
            )
    
    async def mystats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mystats command - show user's quiz statistics"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if not user:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **User not found**\n\nPlease try again."
            )
            return
        
        try:
            # Log action
            log_user_action(user.id, chat_id, "mystats", "viewed personal stats")
            
            # Get user stats
            stats = self.engagement_service.get_user_stats(user.id)
            
            if "error" in stats:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ **Error loading stats**\n\nPlease try again later."
                )
                return
            
            stats_text = (
                f"📊 **Your Quiz Statistics**\n\n"
                f"👤 **User:** {user.first_name or 'Unknown'}\n"
                f"🏆 **Rank:** {stats['rank']}\n"
                f"💎 **Total Points:** {stats['points']}\n"
                f"✅ **Correct Answers:** {stats['correct_answers']}\n"
                f"❓ **Total Questions:** {stats['total_questions']}\n"
                f"📈 **Accuracy:** {stats['accuracy']}%\n"
                f"📅 **Last Quiz:** {stats['last_quiz_date'] or 'Never'}\n\n"
                f"🎯 *Take more quizzes with `/quiz` to improve your stats!*"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=stats_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error in mystats command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error loading stats**\n\nPlease try again later."
            )
    
    async def setnews_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setnews command - schedule daily news (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        # Check if user is admin
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied**\n\nThis command is for administrators only."
            )
            return
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/setnews HH:MM [timezone]`\n\n"
                     "**Examples:**\n"
                     "• `/setnews 09:00` - Schedule news at 9 AM UTC\n"
                     "• `/setnews 15:30 EST` - Schedule news at 3:30 PM EST\n\n"
                     "**Available timezones:** UTC, EST, PST, GMT, etc."
            )
            return
        
        try:
            time_str = args[0]
            timezone = args[1] if len(args) > 1 else "UTC"
            
            # Schedule the job
            result = self.engagement_service.schedule_job(
                "news", chat_id, time_str, timezone, user.id
            )
            
            if result["success"]:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **{result['message']}**\n\n"
                         f"📰 Daily AI news will be posted at {result['time']} {result['timezone']}\n\n"
                         f"🛑 Use `/stopnews` to cancel this schedule"
                )
                
                # Log admin action
                log_admin_action(user.id, "setnews", chat_id, f"scheduled at {time_str} {timezone}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Error:** {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in setnews command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error scheduling news**\n\nPlease check the time format and try again."
            )
    
    async def stopnews_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stopnews command - stop scheduled news (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Check if user is admin
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied**\n\nThis command is for administrators only."
            )
            return
        
        try:
            # Stop the news schedule
            result = self.engagement_service.unschedule_job("news", chat_id)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🛑 **{result['message']}**\n\n"
                     f"📰 Daily news updates have been stopped.\n\n"
                     f"🔄 Use `/setnews HH:MM` to schedule again"
            )
            
            # Log admin action
            log_admin_action(user.id, "stopnews", chat_id, "stopped news schedule")
            
        except Exception as e:
            logger.error(f"Error in stopnews command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error stopping news**\n\nPlease try again later."
            )
    
    async def setquiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setquiz command - schedule daily quiz (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        # Check if user is admin
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied**\n\nThis command is for administrators only."
            )
            return
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/setquiz HH:MM [timezone]`\n\n"
                     "**Examples:**\n"
                     "• `/setquiz 20:00` - Schedule quiz at 8 PM UTC\n"
                     "• `/setquiz 18:30 EST` - Schedule quiz at 6:30 PM EST"
            )
            return
        
        try:
            time_str = args[0]
            timezone = args[1] if len(args) > 1 else "UTC"
            
            # Schedule the job
            result = self.engagement_service.schedule_job(
                "quiz", chat_id, time_str, timezone, user.id
            )
            
            if result["success"]:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **{result['message']}**\n\n"
                         f"🧠 Daily AI quiz will be posted at {result['time']} {result['timezone']}\n\n"
                         f"🛑 Use `/stopquiz` to cancel this schedule"
                )
                
                # Log admin action
                log_admin_action(user.id, "setquiz", chat_id, f"scheduled at {time_str} {timezone}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Error:** {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in setquiz command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error scheduling quiz**\n\nPlease check the time format and try again."
            )
    
    async def stopquiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stopquiz command - stop scheduled quiz (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Check if user is admin
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied**\n\nThis command is for administrators only."
            )
            return
        
        try:
            # Stop the quiz schedule
            result = self.engagement_service.unschedule_job("quiz", chat_id)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🛑 **{result['message']}**\n\n"
                     f"🧠 Daily quiz updates have been stopped.\n\n"
                     f"🔄 Use `/setquiz HH:MM` to schedule again"
            )
            
            # Log admin action
            log_admin_action(user.id, "stopquiz", chat_id, "stopped quiz schedule")
            
        except Exception as e:
            logger.error(f"Error in stopquiz command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error stopping quiz**\n\nPlease try again later."
            )
    
    async def setfunfact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setfunfact command - schedule daily fun fact (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        # Check if user is admin
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied**\n\nThis command is for administrators only."
            )
            return
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/setfunfact HH:MM [timezone]`\n\n"
                     "**Examples:**\n"
                     "• `/setfunfact 15:00` - Schedule fun fact at 3 PM UTC\n"
                     "• `/setfunfact 12:30 EST` - Schedule fun fact at 12:30 PM EST"
            )
            return
        
        try:
            time_str = args[0]
            timezone = args[1] if len(args) > 1 else "UTC"
            
            # Schedule the job
            result = self.engagement_service.schedule_job(
                "funfact", chat_id, time_str, timezone, user.id
            )
            
            if result["success"]:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **{result['message']}**\n\n"
                         f"🎭 Daily AI fun fact will be posted at {result['time']} {result['timezone']}\n\n"
                         f"🛑 Use `/stopfunfact` to cancel this schedule"
                )
                
                # Log admin action
                log_admin_action(user.id, "setfunfact", chat_id, f"scheduled at {time_str} {timezone}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Error:** {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in setfunfact command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error scheduling fun fact**\n\nPlease check the time format and try again."
            )
    
    async def stopfunfact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stopfunfact command - stop scheduled fun fact (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Check if user is admin
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied**\n\nThis command is for administrators only."
            )
            return
        
        try:
            # Stop the fun fact schedule
            result = self.engagement_service.unschedule_job("funfact", chat_id)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🛑 **{result['message']}**\n\n"
                     f"🎭 Daily fun fact updates have been stopped.\n\n"
                     f"🔄 Use `/setfunfact HH:MM` to schedule again"
            )
            
            # Log admin action
            log_admin_action(user.id, "stopfunfact", chat_id, "stopped fun fact schedule")
            
        except Exception as e:
            logger.error(f"Error in stopfunfact command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error stopping fun fact**\n\nPlease try again later."
            )
    
    async def listjobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listjobs command - show all scheduled jobs (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Check if user is admin
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied**\n\nThis command is for administrators only."
            )
            return
        
        try:
            # Get scheduled jobs
            jobs = self.engagement_service.get_scheduled_jobs(chat_id)
            
            if not jobs:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="📅 **Scheduled Jobs**\n\nNo active schedules found.\n\n"
                         "**Available commands:**\n"
                         "• `/setnews HH:MM` - Schedule daily news\n"
                         "• `/setquiz HH:MM` - Schedule daily quiz\n"
                         "• `/setfunfact HH:MM` - Schedule daily fun fact"
                )
                return
            
            # Format jobs list
            jobs_text = "📅 **Active Schedules**\n\n"
            
            for job in jobs:
                job_type_emoji = {
                    "news": "📰",
                    "quiz": "🧠",
                    "funfact": "🎭"
                }.get(job["type"], "📋")
                
                jobs_text += (
                    f"{job_type_emoji} **{job['type'].title()}**\n"
                    f"   ⏰ {job['time']} {job['timezone']}\n"
                    f"   📅 Created: {job['created']}\n\n"
                )
            
            jobs_text += "🛑 **Stop commands:**\n"
            jobs_text += "• `/stopnews` - Stop news schedule\n"
            jobs_text += "• `/stopquiz` - Stop quiz schedule\n"
            jobs_text += "• `/stopfunfact` - Stop fun fact schedule"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=jobs_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log admin action
            log_admin_action(user.id, "listjobs", chat_id, "viewed scheduled jobs")
            
        except Exception as e:
            logger.error(f"Error in listjobs command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error loading schedules**\n\nPlease try again later."
            )
    
    async def handle_quiz_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quiz answer callbacks"""
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat.id
        
        try:
            # Extract the selected answer
            selected_answer = query.data.replace("quiz_", "")
            
            # Get the correct answer from user data
            correct_answer = context.user_data.get("quiz_answer")
            explanation = context.user_data.get("quiz_explanation")
            
            if not correct_answer:
                await query.answer("❌ Quiz session expired. Please start a new quiz with /quiz")
                return
            
            # Check if answer is correct
            is_correct = selected_answer == correct_answer
            
            # Record the answer
            result = self.engagement_service.record_quiz_answer(
                user.id, user.username or f"User_{user.id}", is_correct
            )
            
            if result["success"]:
                # Create response message
                if is_correct:
                    response_text = (
                        f"✅ **Correct Answer!**\n\n"
                        f"🎯 You selected: {selected_answer}\n"
                        f"💎 **+{result['points_earned']} points earned!**\n"
                        f"📊 Total points: {result['total_points']}\n\n"
                        f"💡 **Explanation:** {explanation}\n\n"
                        f"🏆 Check your rank with `/mystats`"
                    )
                else:
                    response_text = (
                        f"❌ **Wrong Answer**\n\n"
                        f"🎯 You selected: {selected_answer}\n"
                        f"✅ Correct answer: {correct_answer}\n"
                        f"💎 No points earned\n"
                        f"📊 Total points: {result['total_points']}\n\n"
                        f"💡 **Explanation:** {explanation}\n\n"
                        f"🎯 Try again with `/quiz`"
                    )
                
                # Answer the callback query
                await query.answer()
                
                # Edit the message to show the result
                await query.edit_message_text(
                    text=response_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Log the action
                log_user_action(user.id, chat_id, "quiz_answer", f"answered: {selected_answer}, correct: {is_correct}")
                
            else:
                await query.answer("❌ Error recording answer. Please try again.")
                
        except Exception as e:
            logger.error(f"Error handling quiz callback: {e}")
            await query.answer("❌ Error processing answer. Please try again.")
    
    async def help_engagement_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help_engagement command - show community engagement help"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        help_text = (
            "🎯 **Community Engagement Commands**\n\n"
            "**📰 News & Updates:**\n"
            "• `/news` - Get latest AI news\n"
            "• `/setnews HH:MM` - Schedule daily news (Admin)\n"
            "• `/stopnews` - Stop news schedule (Admin)\n\n"
            "**🧠 Quiz System:**\n"
            "• `/quiz` - Start an AI quiz\n"
            "• `/leaderboard` - View top scorers\n"
            "• `/mystats` - Your quiz statistics\n"
            "• `/setquiz HH:MM` - Schedule daily quiz (Admin)\n"
            "• `/stopquiz` - Stop quiz schedule (Admin)\n\n"
            "**🎭 Fun & Entertainment:**\n"
            "• `/funfact` - Random AI fun fact\n"
            "• `/joke` - Tech/AI joke\n"
            "• `/setfunfact HH:MM` - Schedule daily fun fact (Admin)\n"
            "• `/stopfunfact` - Stop fun fact schedule (Admin)\n\n"
            "**⚙️ Admin Management:**\n"
            "• `/listjobs` - View all scheduled jobs (Admin)\n\n"
            "**💡 Tips:**\n"
            "• Use HH:MM format for scheduling (e.g., 09:00, 20:30)\n"
            "• Add timezone for specific regions (e.g., EST, PST, GMT)\n"
            "• Quiz points accumulate over time\n"
            "• All schedules are chat-specific"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=help_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Log action
        if user:
            log_user_action(user.id, chat_id, "help_engagement", "viewed engagement help")
