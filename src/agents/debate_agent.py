"""
Debate agent for AI debates and discussions.
Handles debate orchestration, turn management, and summaries.
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


class DebateAgent(BaseAgent):
    """Agent for handling AI debates and discussions."""
    
    def __init__(self, config):
        super().__init__(config)
        self.agent_type = 'debate'
        
        # Debate-specific settings
        self.debate_topics = getattr(config, 'debate_topics', [
            "Should AI development be regulated?",
            "Is automation good for society?",
            "Should social media be more strictly controlled?",
            "Is remote work better than office work?",
            "Should education be more technology-focused?"
        ])
        self.max_turns = getattr(config, 'max_turns', 10)
        self.turn_duration = getattr(config, 'turn_duration', 300)  # 5 minutes
        self.allow_audience_participation = getattr(config, 'allow_audience_participation', True)
        
        # Active debates tracking
        self.active_debates = {}  # chat_id -> debate_data
        self.debate_history = {}  # debate_id -> completed_debate
        
        # Debate participants (AI agents)
        self.available_participants = [
            "AlanTuring", "NewsReporter", "DebateBot", "PersonaHubBot"
        ]
        
        logger.info(f"Initialized debate agent with {len(self.debate_topics)} debate topics")
    
    async def _generate_response(self, message_info: Dict[str, Any], agent_context: Dict[str, Any]) -> str:
        """Generate debate-related response."""
        try:
            user_message = message_info.get('text', '').lower()
            chat_id = message_info.get('chat_id')
            user_id = message_info.get('user_id')
            
            # Parse user intent
            if 'start' in user_message or 'begin' in user_message or 'new' in user_message:
                return await self._start_new_debate(chat_id, user_id)
            elif 'join' in user_message or 'participate' in user_message:
                return await self._join_debate(chat_id, user_id)
            elif 'vote' in user_message or 'opinion' in user_message:
                return await self._process_audience_participation(chat_id, user_id, user_message)
            elif 'status' in user_message or 'progress' in user_message:
                return await self._show_debate_status(chat_id)
            elif 'summary' in user_message or 'conclusion' in user_message:
                return await self._show_debate_summary(chat_id)
            elif 'topics' in user_message or 'subjects' in user_message:
                return self._show_available_topics()
            elif 'help' in user_message or 'rules' in user_message:
                return self._show_debate_help()
            else:
                return await self._offer_debate(chat_id)
                
        except Exception as e:
            logger.error(f"Error generating debate response: {e}")
            return self._get_fallback_response()
    
    async def _start_new_debate(self, chat_id: int, user_id: int) -> str:
        """Start a new debate in the chat."""
        try:
            # Check if there's already an active debate
            if chat_id in self.active_debates:
                active_debate = self.active_debates[chat_id]
                if active_debate['status'] == 'active':
                    return "There's already an active debate in this chat! Please finish it first or ask me to cancel it."
            
            # Create new debate
            debate_data = await self._create_debate(chat_id, user_id)
            self.active_debates[chat_id] = debate_data
            
            # Start the debate process
            asyncio.create_task(self._run_debate(chat_id))
            
            # Format debate presentation
            response = self._format_debate_start(debate_data)
            
            logger.info(f"Started new debate in chat {chat_id} on topic: {debate_data['topic']}")
            return response
            
        except Exception as e:
            logger.error(f"Error starting debate: {e}")
            return "I'm having trouble starting a debate right now. Please try again later."
    
    async def _create_debate(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """Create a new debate structure."""
        # Select random topic
        topic = random.choice(self.debate_topics)
        
        # Select participants (2-3 AI agents)
        num_participants = random.randint(2, 3)
        participants = random.sample(self.available_participants, num_participants)
        
        # Create debate structure
        debate_data = {
            'debate_id': f"debate_{chat_id}_{int(datetime.now().timestamp())}",
            'chat_id': chat_id,
            'creator_id': user_id,
            'topic': topic,
            'participants': participants,
            'current_turn': 0,
            'max_turns': self.max_turns,
            'turn_duration': self.turn_duration,
            'current_speaker': participants[0],
            'speaker_index': 0,
            'start_time': datetime.now(),
            'status': 'active',
            'messages': [],
            'audience_participation': [],
            'turn_start_time': datetime.now(),
            'moderation_level': 'standard'
        }
        
        return debate_data
    
    def _format_debate_start(self, debate_data: Dict[str, Any]) -> str:
        """Format the debate start message."""
        response = f"🎭 **New Debate Started!**\n\n"
        response += f"📢 **Topic:** {debate_data['topic']}\n\n"
        
        response += f"👥 **Participants:**\n"
        for i, participant in enumerate(debate_data['participants'], 1):
            response += f"{i}. @{participant}\n"
        
        response += f"\n📊 **Format:**\n"
        response += f"• {debate_data['max_turns']} turns total\n"
        response += f"• {debate_data['turn_duration'] // 60} minutes per turn\n"
        response += f"• Current speaker: @{debate_data['current_speaker']}\n\n"
        
        if self.allow_audience_participation:
            response += f"🎯 **Audience Participation:**\n"
            response += f"• Share your opinion with 'vote [option]'\n"
            response += f"• Ask questions with 'question [your question]'\n"
            response += f"• React to arguments with 'react [emoji]'\n\n"
        
        response += f"⏱️ **Turn {debate_data['current_turn'] + 1} begins now!**\n"
        response += f"@{debate_data['current_speaker']} has the floor..."
        
        return response
    
    async def _run_debate(self, chat_id: int):
        """Run the debate process automatically."""
        try:
            debate_data = self.active_debates[chat_id]
            
            while (debate_data['status'] == 'active' and 
                   debate_data['current_turn'] < debate_data['max_turns']):
                
                # Wait for turn duration
                await asyncio.sleep(debate_data['turn_duration'])
                
                # Check if debate is still active
                if chat_id not in self.active_debates:
                    break
                
                # Move to next turn
                await self._advance_debate_turn(chat_id)
                
                # Check if debate should end
                if debate_data['current_turn'] >= debate_data['max_turns']:
                    await self._end_debate(chat_id)
                    break
                    
        except Exception as e:
            logger.error(f"Error running debate in chat {chat_id}: {e}")
            # Try to end debate gracefully
            if chat_id in self.active_debates:
                await self._end_debate(chat_id)
    
    async def _advance_debate_turn(self, chat_id: int):
        """Advance to the next debate turn."""
        try:
            debate_data = self.active_debates[chat_id]
            
            # Increment turn
            debate_data['current_turn'] += 1
            
            # Move to next speaker
            debate_data['speaker_index'] = (debate_data['speaker_index'] + 1) % len(debate_data['participants'])
            debate_data['current_speaker'] = debate_data['participants'][debate_data['speaker_index']]
            
            # Update turn timing
            debate_data['turn_start_time'] = datetime.now()
            
            # Generate AI response for current speaker
            ai_response = await self._generate_ai_debate_response(debate_data)
            
            # Add message to debate
            message_data = {
                'speaker': debate_data['current_speaker'],
                'message': ai_response,
                'turn': debate_data['current_turn'],
                'timestamp': datetime.now(),
                'message_type': 'speech'
            }
            debate_data['messages'].append(message_data)
            
            # Send turn update to chat
            turn_message = self._format_turn_update(debate_data, ai_response)
            
            # In a real implementation, this would be sent via Telegram
            logger.info(f"Turn {debate_data['current_turn']} in chat {chat_id}: {ai_response[:100]}...")
            
        except Exception as e:
            logger.error(f"Error advancing debate turn: {e}")
    
    async def _generate_ai_debate_response(self, debate_data: Dict[str, Any]) -> str:
        """Generate AI response for debate turn."""
        try:
            # This would integrate with OpenAI or other AI service
            # For now, generate a structured response based on the topic
            
            topic = debate_data['topic']
            speaker = debate_data['current_speaker']
            turn = debate_data['current_turn']
            
            # Generate different types of responses based on turn
            if turn == 1:
                # Opening statement
                response = f"As {speaker}, I believe this is a crucial issue that requires careful consideration. "
                response += f"My position is that we must approach this thoughtfully and responsibly."
            elif turn == debate_data['max_turns']:
                # Closing statement
                response = f"In conclusion, as {speaker}, I maintain that our discussion has revealed important insights. "
                response += f"I hope we can find common ground on this critical topic."
            else:
                # Middle turns - build on previous arguments
                response = f"Building on the previous points, as {speaker}, I'd like to emphasize that "
                response += f"we need to consider multiple perspectives on this issue."
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI debate response: {e}")
            return f"As {debate_data['current_speaker']}, I'd like to contribute to this important discussion."
    
    def _format_turn_update(self, debate_data: Dict[str, Any], ai_response: str) -> str:
        """Format the turn update message."""
        response = f"🔄 **Turn {debate_data['current_turn']} Complete**\n\n"
        response += f"🎤 **@{debate_data['current_speaker']}:**\n"
        response += f"{ai_response}\n\n"
        
        if debate_data['current_turn'] < debate_data['max_turns']:
            # Next speaker
            next_speaker_index = (debate_data['speaker_index'] + 1) % len(debate_data['participants'])
            next_speaker = debate_data['participants'][next_speaker_index]
            
            response += f"⏭️ **Next Speaker:** @{next_speaker}\n"
            response += f"⏱️ **Time Remaining:** {debate_data['turn_duration'] // 60} minutes\n"
            response += f"📊 **Progress:** {debate_data['current_turn'] + 1}/{debate_data['max_turns']} turns"
        else:
            response += f"🏁 **Final turn complete!**\n"
            response += f"Debate will conclude shortly..."
        
        return response
    
    async def _join_debate(self, chat_id: int, user_id: int) -> str:
        """Allow a user to join the debate as audience participant."""
        try:
            if chat_id not in self.active_debates:
                return "There's no active debate to join. Start one with 'start debate'!"
            
            debate_data = self.active_debates[chat_id]
            if debate_data['status'] != 'active':
                return "This debate has already ended."
            
            # Check if user already joined
            existing_participant = next(
                (p for p in debate_data['audience_participation'] if p['user_id'] == user_id),
                None
            )
            
            if existing_participant:
                return "You're already participating in this debate!"
            
            # Add user to audience participation
            participant_data = {
                'user_id': user_id,
                'join_time': datetime.now(),
                'votes': [],
                'questions': [],
                'reactions': []
            }
            debate_data['audience_participation'].append(participant_data)
            
            response = f"🎉 **Welcome to the debate!**\n\n"
            response += f"You can now:\n"
            response += f"• Vote on arguments with 'vote [option]'\n"
            response += f"• Ask questions with 'question [your question]'\n"
            response += f"• React with 'react [emoji]'\n\n"
            response += f"Current topic: **{debate_data['topic']}**\n"
            response += f"Current speaker: @{debate_data['current_speaker']}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error joining debate: {e}")
            return "I'm having trouble adding you to the debate. Please try again."
    
    async def _process_audience_participation(self, chat_id: int, user_id: int, user_message: str) -> str:
        """Process audience participation (votes, questions, reactions)."""
        try:
            if chat_id not in self.active_debates:
                return "There's no active debate to participate in."
            
            debate_data = self.active_debates[chat_id]
            if debate_data['status'] != 'active':
                return "This debate has already ended."
            
            # Find user in audience participation
            participant = next(
                (p for p in debate_data['audience_participation'] if p['user_id'] == user_id),
                None
            )
            
            if not participant:
                return "You need to join the debate first with 'join debate'!"
            
            # Parse participation type
            if user_message.startswith('vote '):
                return await self._process_vote(debate_data, participant, user_message[5:])
            elif user_message.startswith('question '):
                return await self._process_question(debate_data, participant, user_message[9:])
            elif user_message.startswith('react '):
                return await self._process_reaction(debate_data, participant, user_message[6:])
            else:
                return "Invalid participation format. Use 'vote [option]', 'question [text]', or 'react [emoji]'."
                
        except Exception as e:
            logger.error(f"Error processing audience participation: {e}")
            return "I'm having trouble processing your participation. Please try again."
    
    async def _process_vote(self, debate_data: Dict[str, Any], participant: Dict[str, Any], vote_option: str) -> str:
        """Process a user's vote."""
        # Record vote
        vote_data = {
            'option': vote_option,
            'timestamp': datetime.now(),
            'turn': debate_data['current_turn']
        }
        participant['votes'].append(vote_data)
        
        return f"✅ **Vote recorded:** {vote_option}\n\nYour vote has been counted for turn {debate_data['current_turn']}."
    
    async def _process_question(self, debate_data: Dict[str, Any], participant: Dict[str, Any], question_text: str) -> str:
        """Process a user's question."""
        # Record question
        question_data = {
            'question': question_text,
            'timestamp': datetime.now(),
            'turn': debate_data['current_turn']
        }
        participant['questions'].append(question_data)
        
        return f"❓ **Question recorded:** {question_text}\n\nYour question will be considered by the debate participants."
    
    async def _process_reaction(self, debate_data: Dict[str, Any], participant: Dict[str, Any], reaction: str) -> str:
        """Process a user's reaction."""
        # Record reaction
        reaction_data = {
            'reaction': reaction,
            'timestamp': datetime.now(),
            'turn': debate_data['current_turn']
        }
        participant['reactions'].append(reaction_data)
        
        return f"🎭 **Reaction recorded:** {reaction}\n\nYour reaction has been noted for turn {debate_data['current_turn']}."
    
    async def _show_debate_status(self, chat_id: int) -> str:
        """Show current debate status."""
        try:
            if chat_id not in self.active_debates:
                return "There's no active debate in this chat. Start one with 'start debate'!"
            
            debate_data = self.active_debates[chat_id]
            
            response = f"📊 **Debate Status**\n\n"
            response += f"🎯 **Topic:** {debate_data['topic']}\n"
            response += f"📈 **Progress:** Turn {debate_data['current_turn'] + 1}/{debate_data['max_turns']}\n"
            response += f"🎤 **Current Speaker:** @{debate_data['current_speaker']}\n"
            response += f"⏱️ **Time Remaining:** {self._calculate_time_remaining(debate_data)} minutes\n"
            response += f"👥 **Participants:** {len(debate_data['participants'])} AI agents\n"
            response += f"👥 **Audience:** {len(debate_data['audience_participation'])} participants\n"
            response += f"💬 **Messages:** {len(debate_data['messages'])}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error showing debate status: {e}")
            return "I'm having trouble showing the debate status. Please try again."
    
    def _calculate_time_remaining(self, debate_data: Dict[str, Any]) -> int:
        """Calculate time remaining in current turn."""
        elapsed = datetime.now() - debate_data['turn_start_time']
        remaining = debate_data['turn_duration'] - elapsed.total_seconds()
        return max(0, int(remaining // 60))
    
    async def _show_debate_summary(self, chat_id: int) -> str:
        """Show debate summary and conclusion."""
        try:
            if chat_id in self.active_debates:
                debate_data = self.active_debates[chat_id]
                if debate_data['status'] == 'active':
                    return "This debate is still in progress. Ask for 'status' to see current progress."
            
            # Check completed debates
            completed_debates = [
                debate for debate in self.debate_history.values()
                if debate['chat_id'] == chat_id
            ]
            
            if not completed_debates:
                return "No completed debates found for this chat. Start one with 'start debate'!"
            
            # Show most recent completed debate
            recent_debate = max(completed_debates, key=lambda x: x['end_time'])
            
            response = f"📋 **Debate Summary**\n\n"
            response += f"🎯 **Topic:** {recent_debate['topic']}\n"
            response += f"📅 **Date:** {recent_debate['start_time'].strftime('%Y-%m-%d %H:%M')}\n"
            response += f"⏱️ **Duration:** {self._calculate_debate_duration(recent_debate)} minutes\n"
            response += f"👥 **AI Participants:** {len(recent_debate['participants'])}\n"
            response += f"👥 **Audience:** {len(recent_debate['audience_participation'])} participants\n"
            response += f"💬 **Total Messages:** {len(recent_debate['messages'])}\n\n"
            
            # Audience participation summary
            if recent_debate['audience_participation']:
                total_votes = sum(len(p['votes']) for p in recent_debate['audience_participation'])
                total_questions = sum(len(p['questions']) for p in recent_debate['audience_participation'])
                total_reactions = sum(len(p['reactions']) for p in recent_debate['audience_participation'])
                
                response += f"📊 **Audience Engagement:**\n"
                response += f"• Votes: {total_votes}\n"
                response += f"• Questions: {total_questions}\n"
                response += f"• Reactions: {total_reactions}\n\n"
            
            response += f"💡 Start a new debate anytime with 'start debate'!"
            
            return response
            
        except Exception as e:
            logger.error(f"Error showing debate summary: {e}")
            return "I'm having trouble showing the debate summary. Please try again."
    
    def _calculate_debate_duration(self, debate_data: Dict[str, Any]) -> int:
        """Calculate total debate duration in minutes."""
        duration = debate_data['end_time'] - debate_data['start_time']
        return int(duration.total_seconds() // 60)
    
    def _show_available_topics(self) -> str:
        """Show available debate topics."""
        response = f"🎭 **Available Debate Topics**\n\n"
        
        for i, topic in enumerate(self.debate_topics, 1):
            response += f"{i}. {topic}\n"
        
        response += f"\n💡 **Debate Format:**\n"
        response += f"• {self.max_turns} turns total\n"
        response += f"• {self.turn_duration // 60} minutes per turn\n"
        response += f"• AI participants: {len(self.available_participants)} available\n"
        response += f"• Audience participation: {'Enabled' if self.allow_audience_participation else 'Disabled'}\n\n"
        
        response += "Start a debate anytime with 'start debate'!"
        
        return response
    
    def _show_debate_help(self) -> str:
        """Show debate help and rules."""
        response = f"🎭 **Debate Help & Rules**\n\n"
        response += f"**Commands:**\n"
        response += f"• 'start debate' - Begin a new debate\n"
        response += f"• 'join debate' - Participate as audience\n"
        response += f"• 'status' - Check debate progress\n"
        response += f"• 'summary' - View debate conclusion\n"
        response += f"• 'topics' - See available subjects\n"
        response += f"• 'help' - Show this help message\n\n"
        
        response += f"**Audience Participation:**\n"
        response += f"• 'vote [option]' - Vote on arguments\n"
        response += f"• 'question [text]' - Ask questions\n"
        response += f"• 'react [emoji]' - Show reactions\n\n"
        
        response += f"**Rules:**\n"
        response += f"• AI agents take turns speaking\n"
        response += f"• Each turn has a time limit\n"
        response += f"• Audience can participate actively\n"
        response += f"• Debates conclude after all turns\n\n"
        
        response += f"💡 **Tip:** Start with 'start debate' to begin!"
        
        return response
    
    async def _offer_debate(self, chat_id: int) -> str:
        """Offer to start a debate."""
        response = f"🎭 **Debate Time!**\n\n"
        response += f"I can host intelligent debates on various topics:\n"
        response += f"• 🤖 AI & Technology\n"
        response += f"• 🌍 Social Issues\n"
        response += f"• 💼 Business & Economy\n"
        response += f"• 🎓 Education & Research\n"
        response += f"• 🌱 Environment & Society\n\n"
        
        response += f"**Features:**\n"
        response += f"• AI agents with different perspectives\n"
        response += f"• Structured turn-based format\n"
        response += f"• Audience participation\n"
        response += f"• Automatic moderation\n\n"
        
        response += f"**Commands:**\n"
        response += f"• 'start debate' - Begin a new debate\n"
        response += f"• 'topics' - See available subjects\n"
        response += f"• 'help' - Learn the rules\n\n"
        
        response += f"🎯 Ready for an intellectual discussion? Just say 'start debate'!"
        
        return response
    
    async def _end_debate(self, chat_id: int):
        """End the debate and save results."""
        try:
            if chat_id not in self.active_debates:
                return
            
            debate_data = self.active_debates[chat_id]
            debate_data['status'] = 'completed'
            debate_data['end_time'] = datetime.now()
            
            # Save to history
            debate_id = debate_data['debate_id']
            self.debate_history[debate_id] = debate_data.copy()
            
            # Remove from active debates
            del self.active_debates[chat_id]
            
            # Generate conclusion message
            conclusion = self._generate_debate_conclusion(debate_data)
            
            logger.info(f"Debate {debate_id} completed in chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error ending debate: {e}")
    
    def _generate_debate_conclusion(self, debate_data: Dict[str, Any]) -> str:
        """Generate a conclusion for the completed debate."""
        response = f"🏁 **Debate Concluded!**\n\n"
        response += f"🎯 **Topic:** {debate_data['topic']}\n"
        response += f"📊 **Final Statistics:**\n"
        response += f"• Total turns: {debate_data['current_turn'] + 1}\n"
        response += f"• AI participants: {len(debate_data['participants'])}\n"
        response += f"• Audience participants: {len(debate_data['audience_participation'])}\n"
        response += f"• Total messages: {len(debate_data['messages'])}\n\n"
        
        # Audience engagement summary
        if debate_data['audience_participation']:
            total_votes = sum(len(p['votes']) for p in debate_data['audience_participation'])
            total_questions = sum(len(p['questions']) for p in debate_data['audience_participation'])
            total_reactions = sum(len(p['reactions']) for p in debate_data['audience_participation'])
            
            response += f"📈 **Audience Engagement:**\n"
            response += f"• Votes cast: {total_votes}\n"
            response += f"• Questions asked: {total_questions}\n"
            response += f"• Reactions: {total_reactions}\n\n"
        
        response += f"💡 **Thank you for participating!**\n"
        response += f"Start a new debate anytime with 'start debate'."
        
        return response
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when debate generation fails."""
        fallback_responses = [
            "I'm having trouble with the debate system right now. Please try again in a few minutes.",
            "The debate service is temporarily unavailable. Please check back later.",
            "I can't start a debate at the moment. Please try again soon.",
            "There seems to be a technical issue with the debate system. Please try again later."
        ]
        
        import random
        return random.choice(fallback_responses)
    
    async def process_special_command(self, command: str, message_info: Dict[str, Any]) -> str:
        """Process special debate commands."""
        command_lower = command.lower()
        chat_id = message_info.get('chat_id')
        user_id = message_info.get('user_id')
        
        if command_lower in ['/debate', '/start_debate']:
            return await self._start_new_debate(chat_id, user_id)
        elif command_lower in ['/join', '/participate']:
            return await self._join_debate(chat_id, user_id)
        elif command_lower in ['/status', '/progress']:
            return await self._show_debate_status(chat_id)
        elif command_lower in ['/summary', '/conclusion']:
            return await self._show_debate_summary(chat_id)
        elif command_lower in ['/topics', '/subjects']:
            return self._show_available_topics()
        elif command_lower in ['/help', '/rules']:
            return self._show_debate_help()
        elif command_lower in ['/cancel', '/stop']:
            return await self._cancel_debate(chat_id)
        else:
            return "I don't recognize that debate command. Try /debate, /join, /status, or /help."
    
    async def _cancel_debate(self, chat_id: int) -> str:
        """Cancel the active debate in a chat."""
        if chat_id in self.active_debates:
            debate_data = self.active_debates[chat_id]
            if debate_data['status'] == 'active':
                del self.active_debates[chat_id]
                return "❌ Debate cancelled. Start a new one anytime with 'start debate'!"
            else:
                return "There's no active debate to cancel."
        else:
            return "There's no active debate in this chat."
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the debate agent."""
        try:
            # Basic health check
            health_status = await super().health_check()
            
            # Debate-specific checks
            debate_status = {
                'available_topics': len(self.debate_topics),
                'available_participants': len(self.available_participants),
                'max_turns': self.max_turns,
                'turn_duration': self.turn_duration,
                'active_debates': len(self.active_debates),
                'completed_debates': len(self.debate_history),
                'allow_audience_participation': self.allow_audience_participation
            }
            
            health_status['debate_specific'] = debate_status
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent': self.handle,
                'error': str(e),
                'error_type': type(e).__name__
            }
