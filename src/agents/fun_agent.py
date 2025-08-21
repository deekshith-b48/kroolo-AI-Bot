"""
Fun agent for entertainment and humor content.
Handles jokes, fun facts, and entertaining content.
"""

import asyncio
import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from .base_agent import BaseAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class FunAgent(BaseAgent):
    """Agent for handling entertainment and humor content."""
    
    def __init__(self, config):
        super().__init__(config)
        self.agent_type = 'fun'
        
        # Fun content settings
        self.content_types = getattr(config, 'content_types', ['joke', 'fact', 'riddle', 'story', 'meme'])
        self.categories = getattr(config, 'categories', ['humor', 'science', 'history', 'technology', 'random'])
        self.max_daily_usage = getattr(config, 'max_daily_usage', 5)
        self.cooldown_hours = getattr(config, 'cooldown_hours', 24)
        
        # Content tracking
        self.daily_usage = {}  # chat_id -> usage_count
        self.last_usage = {}  # chat_id -> last_usage_time
        self.user_ratings = {}  # content_id -> ratings
        
        # Content database (in production, this would come from a database)
        self.content_database = self._initialize_content_database()
        
        logger.info(f"Initialized fun agent with {len(self.content_database)} content items across {len(self.content_types)} types")
    
    async def _generate_response(self, message_info: Dict[str, Any], agent_context: Dict[str, Any]) -> str:
        """Generate fun content response."""
        try:
            user_message = message_info.get('text', '').lower()
            chat_id = message_info.get('chat_id')
            user_id = message_info.get('user_id')
            
            # Parse user intent
            if 'joke' in user_message or 'funny' in user_message:
                return await self._get_joke(chat_id, user_id)
            elif 'fact' in user_message or 'interesting' in user_message:
                return await self._get_fun_fact(chat_id, user_id)
            elif 'riddle' in user_message or 'puzzle' in user_message:
                return await self._get_riddle(chat_id, user_id)
            elif 'story' in user_message or 'tale' in user_message:
                return await self._get_story(chat_id, user_id)
            elif 'meme' in user_message or 'humor' in user_message:
                return await self._get_meme_content(chat_id, user_id)
            elif 'random' in user_message or 'surprise' in user_message:
                return await self._get_random_content(chat_id, user_id)
            elif 'rate' in user_message or 'feedback' in user_message:
                return await self._process_rating(chat_id, user_id, user_message)
            elif 'help' in user_message or 'commands' in user_message:
                return self._show_fun_help()
            else:
                return await self._offer_fun_content(chat_id)
                
        except Exception as e:
            logger.error(f"Error generating fun content response: {e}")
            return self._get_fallback_response()
    
    async def _get_joke(self, chat_id: int, user_id: int) -> str:
        """Get a random joke."""
        try:
            if not await self._can_use_content(chat_id):
                return self._get_cooldown_message(chat_id)
            
            # Get jokes from database
            jokes = [item for item in self.content_database if item['type'] == 'joke']
            if not jokes:
                return "I'm all out of jokes right now! Try asking for a fun fact instead."
            
            # Select random joke
            joke = random.choice(jokes)
            
            # Record usage
            await self._record_usage(chat_id, user_id, joke['id'])
            
            # Format joke response
            response = f"😄 **Here's a joke for you:**\n\n"
            response += f"{joke['content']}\n\n"
            
            if joke.get('punchline'):
                response += f"🎭 **Punchline:** {joke['punchline']}\n\n"
            
            response += f"💡 *Rate this joke with 'rate {joke['id']} [1-5]'*"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting joke: {e}")
            return "I'm having trouble telling jokes right now. Please try again later."
    
    async def _get_fun_fact(self, chat_id: int, user_id: int) -> str:
        """Get a random fun fact."""
        try:
            if not await self._can_use_content(chat_id):
                return self._get_cooldown_message(chat_id)
            
            # Get facts from database
            facts = [item for item in self.content_database if item['type'] == 'fact']
            if not facts:
                return "I'm all out of fun facts right now! Try asking for a joke instead."
            
            # Select random fact
            fact = random.choice(facts)
            
            # Record usage
            await self._record_usage(chat_id, user_id, fact['id'])
            
            # Format fact response
            response = f"🧠 **Fun Fact:**\n\n"
            response += f"{fact['content']}\n\n"
            
            if fact.get('source'):
                response += f"📚 *Source: {fact['source']}*\n\n"
            
            if fact.get('category'):
                response += f"🏷️ Category: {fact['category']}\n\n"
            
            response += f"💡 *Rate this fact with 'rate {fact['id']} [1-5]'*"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting fun fact: {e}")
            return "I'm having trouble sharing fun facts right now. Please try again later."
    
    async def _get_riddle(self, chat_id: int, user_id: int) -> str:
        """Get a random riddle."""
        try:
            if not await self._can_use_content(chat_id):
                return self._get_cooldown_message(chat_id)
            
            # Get riddles from database
            riddles = [item for item in self.content_database if item['type'] == 'riddle']
            if not riddles:
                return "I'm all out of riddles right now! Try asking for a joke instead."
            
            # Select random riddle
            riddle = random.choice(riddles)
            
            # Record usage
            await self._record_usage(chat_id, user_id, riddle['id'])
            
            # Format riddle response
            response = f"🤔 **Here's a riddle for you:**\n\n"
            response += f"{riddle['content']}\n\n"
            
            response += f"💭 *Think about it...*\n\n"
            
            # Don't show answer immediately - let user think
            response += f"💡 *Ask me 'answer {riddle['id']}' when you're ready for the solution!*"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting riddle: {e}")
            return "I'm having trouble sharing riddles right now. Please try again later."
    
    async def _get_story(self, chat_id: int, user_id: int) -> str:
        """Get a random short story."""
        try:
            if not await self._can_use_content(chat_id):
                return self._get_cooldown_message(chat_id)
            
            # Get stories from database
            stories = [item for item in self.content_database if item['type'] == 'story']
            if not stories:
                return "I'm all out of stories right now! Try asking for a joke instead."
            
            # Select random story
            story = random.choice(stories)
            
            # Record usage
            await self._record_usage(chat_id, user_id, story['id'])
            
            # Format story response
            response = f"📖 **Here's a story for you:**\n\n"
            response += f"{story['content']}\n\n"
            
            if story.get('moral'):
                response += f"💡 **Moral:** {story['moral']}\n\n"
            
            if story.get('category'):
                response += f"🏷️ Category: {story['category']}\n\n"
            
            response += f"💡 *Rate this story with 'rate {story['id']} [1-5]'*"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting story: {e}")
            return "I'm having trouble sharing stories right now. Please try again later."
    
    async def _get_meme_content(self, chat_id: int, user_id: int) -> str:
        """Get meme-style content."""
        try:
            if not await self._can_use_content(chat_id):
                return self._get_cooldown_message(chat_id)
            
            # Get meme content from database
            memes = [item for item in self.content_database if item['type'] == 'meme']
            if not memes:
                return "I'm all out of meme content right now! Try asking for a joke instead."
            
            # Select random meme content
            meme = random.choice(memes)
            
            # Record usage
            await self._record_usage(chat_id, user_id, meme['id'])
            
            # Format meme response
            response = f"🎭 **Meme Content:**\n\n"
            response += f"{meme['content']}\n\n"
            
            if meme.get('caption'):
                response += f"💬 **Caption:** {meme['caption']}\n\n"
            
            response += f"💡 *Rate this content with 'rate {meme['id']} [1-5]'*"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting meme content: {e}")
            return "I'm having trouble sharing meme content right now. Please try again later."
    
    async def _get_random_content(self, chat_id: int, user_id: int) -> str:
        """Get random fun content of any type."""
        try:
            if not await self._can_use_content(chat_id):
                return self._get_cooldown_message(chat_id)
            
            # Select random content
            content = random.choice(self.content_database)
            
            # Record usage
            await self._record_usage(chat_id, user_id, content['id'])
            
            # Format based on content type
            if content['type'] == 'joke':
                return await self._get_joke(chat_id, user_id)
            elif content['type'] == 'fact':
                return await self._get_fun_fact(chat_id, user_id)
            elif content['type'] == 'riddle':
                return await self._get_riddle(chat_id, user_id)
            elif content['type'] == 'story':
                return await self._get_story(chat_id, user_id)
            elif content['type'] == 'meme':
                return await self._get_meme_content(chat_id, user_id)
            else:
                return await self._get_fun_fact(chat_id, user_id)  # Fallback
                
        except Exception as e:
            logger.error(f"Error getting random content: {e}")
            return "I'm having trouble getting random content right now. Please try again later."
    
    async def _process_rating(self, chat_id: int, user_id: int, user_message: str) -> str:
        """Process user rating for content."""
        try:
            # Parse rating command: "rate [content_id] [rating]"
            parts = user_message.split()
            if len(parts) < 3:
                return "Please use the format: 'rate [content_id] [rating]' where rating is 1-5"
            
            try:
                content_id = parts[1]
                rating = int(parts[2])
                if rating < 1 or rating > 5:
                    return "Rating must be between 1 and 5"
            except ValueError:
                return "Rating must be a number between 1 and 5"
            
            # Record rating
            if content_id not in self.user_ratings:
                self.user_ratings[content_id] = []
            
            # Check if user already rated this content
            existing_rating = next(
                (r for r in self.user_ratings[content_id] if r['user_id'] == user_id),
                None
            )
            
            if existing_rating:
                existing_rating['rating'] = rating
                existing_rating['timestamp'] = datetime.now()
                response = f"✅ **Rating updated!** You rated content {content_id} as {rating}/5"
            else:
                rating_data = {
                    'user_id': user_id,
                    'rating': rating,
                    'timestamp': datetime.now()
                }
                self.user_ratings[content_id].append(rating_data)
                response = f"⭐ **Rating recorded!** You rated content {content_id} as {rating}/5"
            
            # Calculate average rating
            ratings = self.user_ratings[content_id]
            if ratings:
                avg_rating = sum(r['rating'] for r in ratings) / len(ratings)
                response += f"\n📊 Average rating: {avg_rating:.1f}/5 ({len(ratings)} ratings)"
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing rating: {e}")
            return "I'm having trouble processing your rating. Please try again."
    
    async def _can_use_content(self, chat_id: int) -> bool:
        """Check if content can be used in this chat."""
        current_time = datetime.now()
        
        # Check daily usage limit
        if chat_id in self.daily_usage:
            last_reset = self.daily_usage[chat_id].get('reset_date')
            if last_reset and (current_time - last_reset).days >= 1:
                # Reset daily usage
                self.daily_usage[chat_id] = {
                    'count': 0,
                    'reset_date': current_time
                }
            
            if self.daily_usage[chat_id]['count'] >= self.max_daily_usage:
                return False
        
        # Check cooldown
        if chat_id in self.last_usage:
            time_since_last = current_time - self.last_usage[chat_id]
            if time_since_last.total_seconds() < (self.cooldown_hours * 3600):
                return False
        
        return True
    
    def _get_cooldown_message(self, chat_id: int) -> str:
        """Get cooldown message when content cannot be used."""
        if chat_id in self.daily_usage and self.daily_usage[chat_id]['count'] >= self.max_daily_usage:
            return f"🚫 **Daily limit reached!** You've used {self.max_daily_usage} fun content items today. Come back tomorrow for more!"
        
        if chat_id in self.last_usage:
            time_since_last = datetime.now() - self.last_usage[chat_id]
            hours_remaining = max(0, self.cooldown_hours - (time_since_last.total_seconds() / 3600))
            return f"⏳ **Cooldown active!** Please wait {hours_remaining:.1f} more hours before requesting more fun content."
        
        return "🚫 **Content temporarily unavailable.** Please try again later."
    
    async def _record_usage(self, chat_id: int, user_id: int, content_id: str):
        """Record content usage for tracking."""
        current_time = datetime.now()
        
        # Update daily usage
        if chat_id not in self.daily_usage:
            self.daily_usage[chat_id] = {
                'count': 0,
                'reset_date': current_time
            }
        
        self.daily_usage[chat_id]['count'] += 1
        
        # Update last usage time
        self.last_usage[chat_id] = current_time
        
        # Update content usage count
        for content in self.content_database:
            if content['id'] == content_id:
                content['total_uses'] = content.get('total_uses', 0) + 1
                break
    
    def _show_fun_help(self) -> str:
        """Show fun content help and commands."""
        response = f"🎭 **Fun Content Help**\n\n"
        response += f"**Available Content Types:**\n"
        response += f"• 😄 Jokes - Humorous content\n"
        response += f"• 🧠 Fun Facts - Interesting information\n"
        response += f"• 🤔 Riddles - Brain teasers\n"
        response += f"• 📖 Stories - Short tales\n"
        response += f"• 🎭 Memes - Humorous content\n\n"
        
        response += f"**Commands:**\n"
        response += f"• 'joke' - Get a random joke\n"
        response += f"• 'fact' - Get a fun fact\n"
        response += f"• 'riddle' - Get a riddle\n"
        response += f"• 'story' - Get a short story\n"
        response += f"• 'meme' - Get meme content\n"
        response += f"• 'random' - Get random content\n"
        response += f"• 'rate [id] [1-5]' - Rate content\n"
        response += f"• 'help' - Show this help\n\n"
        
        response += f"**Limits:**\n"
        response += f"• Daily limit: {self.max_daily_usage} items\n"
        response += f"• Cooldown: {self.cooldown_hours} hours between uses\n\n"
        
        response += f"💡 **Tip:** Just ask for what you want! (e.g., 'tell me a joke')"
        
        return response
    
    async def _offer_fun_content(self, chat_id: int) -> str:
        """Offer fun content options."""
        response = f"🎭 **Fun & Entertainment!**\n\n"
        response += f"I have lots of entertaining content for you:\n\n"
        response += f"😄 **Jokes** - Laugh out loud humor\n"
        response += f"🧠 **Fun Facts** - Mind-blowing information\n"
        response += f"🤔 **Riddles** - Test your brain power\n"
        response += f"📖 **Stories** - Engaging short tales\n"
        response += f"🎭 **Memes** - Internet humor\n\n"
        
        response += f"**Just ask for what you want:**\n"
        response += f"• 'Tell me a joke'\n"
        response += f"• 'Share a fun fact'\n"
        response += f"• 'Give me a riddle'\n"
        response += f"• 'Tell me a story'\n"
        response += f"• 'Show me something funny'\n\n"
        
        response += f"🎯 **Or use commands:** /joke, /fact, /riddle, /story, /meme"
        
        return response
    
    def _initialize_content_database(self) -> List[Dict[str, Any]]:
        """Initialize the content database with sample content."""
        return [
            # Jokes
            {
                'id': 'joke_001',
                'type': 'joke',
                'content': 'Why did the AI go to therapy?',
                'punchline': 'Because it had too many processing issues!',
                'category': 'humor',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'joke_002',
                'type': 'joke',
                'content': 'What do you call a computer that sings?',
                'punchline': 'A Dell!',
                'category': 'humor',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'joke_003',
                'type': 'joke',
                'content': 'Why did the programmer quit his job?',
                'punchline': 'Because he didn\'t get arrays!',
                'category': 'humor',
                'total_uses': 0,
                'average_rating': 0.0
            },
            
            # Fun Facts
            {
                'id': 'fact_001',
                'type': 'fact',
                'content': 'Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible!',
                'source': 'Scientific research',
                'category': 'science',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'fact_002',
                'type': 'fact',
                'content': 'A day on Venus is longer than its year. Venus takes 243 Earth days to rotate on its axis but only 225 Earth days to orbit the Sun.',
                'source': 'NASA',
                'category': 'science',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'fact_003',
                'type': 'fact',
                'content': 'The shortest war in history lasted only 38 minutes. It was between Britain and Zanzibar on August 27, 1896.',
                'source': 'Historical records',
                'category': 'history',
                'total_uses': 0,
                'average_rating': 0.0
            },
            
            # Riddles
            {
                'id': 'riddle_001',
                'type': 'riddle',
                'content': 'I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?',
                'answer': 'An echo',
                'category': 'logic',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'riddle_002',
                'type': 'riddle',
                'content': 'What has keys, but no locks; space, but no room; and you can enter, but not go in?',
                'answer': 'A keyboard',
                'category': 'technology',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'riddle_003',
                'type': 'riddle',
                'content': 'The more you take, the more you leave behind. What am I?',
                'answer': 'Footsteps',
                'category': 'logic',
                'total_uses': 0,
                'average_rating': 0.0
            },
            
            # Stories
            {
                'id': 'story_001',
                'type': 'story',
                'content': 'A young programmer was struggling with a bug that had been eluding them for days. Frustrated, they decided to take a walk. As they strolled through the park, watching children play, they suddenly realized the solution: sometimes the simplest approach is the best. They rushed back to their computer and implemented the fix in just a few lines of code.',
                'moral': 'Sometimes stepping away from a problem helps you see the solution more clearly.',
                'category': 'technology',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'story_002',
                'type': 'story',
                'content': 'In a small village, there was a wise old AI researcher who was known for solving impossible problems. One day, a young student asked, "How do you know when an AI is truly intelligent?" The researcher smiled and said, "When it asks questions that make you question your own intelligence."',
                'moral': 'True intelligence is not about having all the answers, but about asking the right questions.',
                'category': 'philosophy',
                'total_uses': 0,
                'average_rating': 0.0
            },
            
            # Memes
            {
                'id': 'meme_001',
                'type': 'meme',
                'content': 'When you finally fix that bug at 3 AM',
                'caption': 'The satisfaction is real! 😅',
                'category': 'humor',
                'total_uses': 0,
                'average_rating': 0.0
            },
            {
                'id': 'meme_002',
                'type': 'meme',
                'content': 'Me: I\'ll just check one thing quickly\nAlso me: *3 hours later*',
                'caption': 'Time flies when you\'re coding! ⏰',
                'category': 'humor',
                'total_uses': 0,
                'average_rating': 0.0
            }
        ]
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when fun content generation fails."""
        fallback_responses = [
            "I'm having trouble with the fun content right now. Please try again in a few minutes.",
            "The entertainment service is temporarily unavailable. Please check back later.",
            "I can't share fun content at the moment. Please try again soon.",
            "There seems to be a technical issue with the fun system. Please try again later."
        ]
        
        import random
        return random.choice(fallback_responses)
    
    async def process_special_command(self, command: str, message_info: Dict[str, Any]) -> str:
        """Process special fun content commands."""
        command_lower = command.lower()
        chat_id = message_info.get('chat_id')
        user_id = message_info.get('user_id')
        
        if command_lower in ['/joke', '/funny']:
            return await self._get_joke(chat_id, user_id)
        elif command_lower in ['/fact', '/interesting']:
            return await self._get_fun_fact(chat_id, user_id)
        elif command_lower in ['/riddle', '/puzzle']:
            return await self._get_riddle(chat_id, user_id)
        elif command_lower in ['/story', '/tale']:
            return await self._get_story(chat_id, user_id)
        elif command_lower in ['/meme', '/humor']:
            return await self._get_meme_content(chat_id, user_id)
        elif command_lower in ['/random', '/surprise']:
            return await self._get_random_content(chat_id, user_id)
        elif command_lower in ['/help', '/commands']:
            return self._show_fun_help()
        else:
            return "I don't recognize that fun command. Try /joke, /fact, /riddle, /story, or /help."
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the fun agent."""
        try:
            # Basic health check
            health_status = await super().health_check()
            
            # Fun content-specific checks
            fun_status = {
                'content_types': self.content_types,
                'categories': self.categories,
                'content_database_size': len(self.content_database),
                'max_daily_usage': self.max_daily_usage,
                'cooldown_hours': self.cooldown_hours,
                'active_chats': len(self.daily_usage),
                'total_ratings': len(self.user_ratings)
            }
            
            health_status['fun_specific'] = fun_status
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent': self.handle,
                'error': str(e),
                'error_type': type(e).__name__
            }
