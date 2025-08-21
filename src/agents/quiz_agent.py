"""
Quiz agent for interactive quizzes and polls.
Handles quiz generation, scoring, and leaderboards.
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


class QuizAgent(BaseAgent):
    """Agent for handling quizzes and polls."""
    
    def __init__(self, config):
        super().__init__(config)
        self.agent_type = 'quiz'
        
        # Quiz-specific settings
        self.quiz_categories = getattr(config, 'quiz_categories', ['AI', 'technology', 'general', 'science'])
        self.difficulty_levels = getattr(config, 'difficulty_levels', ['easy', 'medium', 'hard'])
        self.max_questions_per_quiz = getattr(config, 'max_questions_per_quiz', 5)
        self.quiz_timeout = getattr(config, 'quiz_timeout', 300)  # 5 minutes
        
        # Active quizzes tracking
        self.active_quizzes = {}  # chat_id -> quiz_data
        self.quiz_results = {}  # quiz_id -> results
        
        # Quiz question bank (in production, this would come from a database)
        self.question_bank = self._initialize_question_bank()
        
        logger.info(f"Initialized quiz agent with {len(self.question_bank)} questions across {len(self.quiz_categories)} categories")
    
    async def _generate_response(self, message_info: Dict[str, Any], agent_context: Dict[str, Any]) -> str:
        """Generate quiz-related response."""
        try:
            user_message = message_info.get('text', '').lower()
            chat_id = message_info.get('chat_id')
            user_id = message_info.get('user_id')
            
            # Parse user intent
            if 'start' in user_message or 'begin' in user_message or 'new' in user_message:
                return await self._start_new_quiz(chat_id, user_id)
            elif 'answer' in user_message or 'option' in user_message:
                return await self._process_answer(chat_id, user_id, user_message)
            elif 'score' in user_message or 'result' in user_message:
                return await self._show_quiz_results(chat_id, user_id)
            elif 'leaderboard' in user_message or 'ranking' in user_message:
                return await self._show_leaderboard(chat_id)
            elif 'help' in user_message or 'rules' in user_message:
                return self._show_quiz_help()
            elif 'category' in user_message or 'topic' in user_message:
                return await self._show_available_categories(chat_id)
            else:
                return await self._offer_quiz(chat_id)
                
        except Exception as e:
            logger.error(f"Error generating quiz response: {e}")
            return self._get_fallback_response()
    
    async def _start_new_quiz(self, chat_id: int, user_id: int) -> str:
        """Start a new quiz for the chat."""
        try:
            # Check if there's already an active quiz
            if chat_id in self.active_quizzes:
                active_quiz = self.active_quizzes[chat_id]
                if active_quiz['status'] == 'active':
                    return "There's already an active quiz in this chat! Please finish it first or ask me to cancel it."
            
            # Create new quiz
            quiz_data = await self._create_quiz(chat_id, user_id)
            self.active_quizzes[chat_id] = quiz_data
            
            # Format quiz presentation
            response = self._format_quiz_question(quiz_data)
            
            logger.info(f"Started new quiz in chat {chat_id} with {len(quiz_data['questions'])} questions")
            return response
            
        except Exception as e:
            logger.error(f"Error starting quiz: {e}")
            return "I'm having trouble starting a quiz right now. Please try again later."
    
    async def _create_quiz(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """Create a new quiz with questions."""
        # Select category and difficulty
        category = random.choice(self.quiz_categories)
        difficulty = random.choice(self.difficulty_levels)
        
        # Get questions for the category and difficulty
        available_questions = [
            q for q in self.question_bank
            if q['category'].lower() == category.lower() and q['difficulty'] == difficulty
        ]
        
        if not available_questions:
            # Fallback to any questions in the category
            available_questions = [
                q for q in self.question_bank
                if q['category'].lower() == category.lower()
            ]
        
        if not available_questions:
            # Fallback to any questions
            available_questions = self.question_bank
        
        # Select random questions
        selected_questions = random.sample(
            available_questions, 
            min(self.max_questions_per_quiz, len(available_questions))
        )
        
        # Create quiz structure
        quiz_data = {
            'quiz_id': f"quiz_{chat_id}_{int(datetime.now().timestamp())}",
            'chat_id': chat_id,
            'creator_id': user_id,
            'category': category,
            'difficulty': difficulty,
            'questions': selected_questions,
            'current_question': 0,
            'total_questions': len(selected_questions),
            'start_time': datetime.now(),
            'status': 'active',
            'participants': {},
            'answers': {}
        }
        
        return quiz_data
    
    def _format_quiz_question(self, quiz_data: Dict[str, Any]) -> str:
        """Format the current quiz question for display."""
        current_q = quiz_data['questions'][quiz_data['current_question']]
        
        response = f"🧠 **Quiz Started!**\n\n"
        response += f"📚 Category: {quiz_data['category']}\n"
        response += f"⚡ Difficulty: {quiz_data['difficulty']}\n"
        response += f"📊 Progress: {quiz_data['current_question'] + 1}/{quiz_data['total_questions']}\n\n"
        
        response += f"**Question {quiz_data['current_question'] + 1}:**\n"
        response += f"{current_q['question']}\n\n"
        
        # Add answer options
        for i, option in enumerate(current_q['options']):
            response += f"{i + 1}. {option}\n"
        
        response += f"\n⏱️ Time limit: {self.quiz_timeout // 60} minutes\n"
        response += f"💡 Reply with the number (1-{len(current_q['options'])}) to answer!"
        
        return response
    
    async def _process_answer(self, chat_id: int, user_id: int, user_message: str) -> str:
        """Process a user's quiz answer."""
        try:
            if chat_id not in self.active_quizzes:
                return "There's no active quiz in this chat. Start one with 'start quiz'!"
            
            quiz_data = self.active_quizzes[chat_id]
            if quiz_data['status'] != 'active':
                return "This quiz has already ended. Start a new one!"
            
            # Extract answer number
            try:
                answer_number = int(user_message.strip())
                if answer_number < 1 or answer_number > 4:
                    return "Please answer with a number between 1 and 4."
            except ValueError:
                return "Please answer with a number (1, 2, 3, or 4)."
            
            # Check if user already answered this question
            user_key = f"{user_id}_{quiz_data['current_question']}"
            if user_key in quiz_data['answers']:
                return "You've already answered this question!"
            
            # Record answer
            current_question = quiz_data['questions'][quiz_data['current_question']]
            is_correct = (answer_number - 1) == current_question['correct_answer_index']
            
            quiz_data['answers'][user_key] = {
                'answer_index': answer_number - 1,
                'is_correct': is_correct,
                'answer_time': datetime.now()
            }
            
            # Update participant stats
            if user_id not in quiz_data['participants']:
                quiz_data['participants'][user_id] = {
                    'correct_answers': 0,
                    'total_answers': 0,
                    'start_time': datetime.now()
                }
            
            quiz_data['participants'][user_id]['total_answers'] += 1
            if is_correct:
                quiz_data['participants'][user_id]['correct_answers'] += 1
            
            # Provide feedback
            response = f"✅ **Answer recorded!**\n\n"
            if is_correct:
                response += f"🎉 Correct! Well done!\n"
            else:
                correct_answer = current_question['options'][current_question['correct_answer_index']]
                response += f"❌ Incorrect. The correct answer was: **{correct_answer}**\n"
            
            if current_question.get('explanation'):
                response += f"\n💡 **Explanation:** {current_question['explanation']}\n"
            
            # Check if this was the last question
            if quiz_data['current_question'] == quiz_data['total_questions'] - 1:
                response += await self._finish_quiz(chat_id)
            else:
                # Move to next question
                quiz_data['current_question'] += 1
                response += f"\n{self._format_quiz_question(quiz_data)}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            return "I'm having trouble processing your answer. Please try again."
    
    async def _finish_quiz(self, chat_id: int) -> str:
        """Finish the quiz and show results."""
        try:
            quiz_data = self.active_quizzes[chat_id]
            quiz_data['status'] = 'completed'
            quiz_data['end_time'] = datetime.now()
            
            # Calculate results
            results = self._calculate_quiz_results(quiz_data)
            
            # Store results
            quiz_id = quiz_data['quiz_id']
            self.quiz_results[quiz_id] = results
            
            # Format results message
            response = f"\n🏁 **Quiz Complete!**\n\n"
            response += f"📊 **Final Results:**\n"
            
            # Sort participants by score
            sorted_participants = sorted(
                results['participants'].items(),
                key=lambda x: x[1]['score'],
                reverse=True
            )
            
            for i, (user_id, participant_data) in enumerate(sorted_participants, 1):
                response += f"{i}. User {user_id}: {participant_data['correct_answers']}/{participant_data['total_answers']} "
                response += f"({participant_data['score']:.1f}%)\n"
            
            response += f"\n🎯 **Quiz Summary:**\n"
            response += f"• Category: {quiz_data['category']}\n"
            response += f"• Difficulty: {quiz_data['difficulty']}\n"
            response += f"• Total Questions: {quiz_data['total_questions']}\n"
            response += f"• Participants: {len(results['participants'])}\n"
            response += f"• Average Score: {results['average_score']:.1f}%\n"
            
            response += f"\n💡 Start a new quiz anytime with 'start quiz'!"
            
            # Clean up active quiz
            del self.active_quizzes[chat_id]
            
            return response
            
        except Exception as e:
            logger.error(f"Error finishing quiz: {e}")
            return "I'm having trouble finishing the quiz. Please try again."
    
    def _calculate_quiz_results(self, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate final results for a completed quiz."""
        participants = quiz_data['participants']
        total_questions = quiz_data['total_questions']
        
        # Calculate individual scores
        for user_id, participant_data in participants.items():
            correct_answers = participant_data['correct_answers']
            score_percentage = (correct_answers / total_questions) * 100
            participant_data['score'] = score_percentage
        
        # Calculate overall statistics
        total_participants = len(participants)
        if total_participants > 0:
            total_score = sum(p['score'] for p in participants.values())
            average_score = total_score / total_participants
        else:
            average_score = 0
        
        return {
            'quiz_id': quiz_data['quiz_id'],
            'participants': participants,
            'total_questions': total_questions,
            'total_participants': total_participants,
            'average_score': average_score,
            'start_time': quiz_data['start_time'],
            'end_time': quiz_data.get('end_time', datetime.now())
        }
    
    async def _show_quiz_results(self, chat_id: int, user_id: int) -> str:
        """Show quiz results for a specific user."""
        try:
            # Check if there's an active quiz
            if chat_id in self.active_quizzes:
                quiz_data = self.active_quizzes[chat_id]
                if quiz_data['status'] == 'active':
                    current_progress = quiz_data['participants'].get(user_id, {})
                    if current_progress:
                        correct = current_progress.get('correct_answers', 0)
                        total = current_progress.get('total_answers', 0)
                        remaining = quiz_data['total_questions'] - total
                        
                        response = f"📊 **Your Current Progress:**\n\n"
                        response += f"✅ Correct: {correct}\n"
                        response += f"❌ Incorrect: {total - correct}\n"
                        response += f"⏳ Remaining: {remaining}\n"
                        response += f"📈 Score: {(correct / total * 100):.1f}%" if total > 0 else "📈 Score: 0%"
                        
                        return response
                    else:
                        return "You haven't answered any questions yet in this quiz."
            
            # Check completed quizzes
            user_results = []
            for quiz_id, results in self.quiz_results.items():
                if user_id in results['participants']:
                    user_results.append((quiz_id, results))
            
            if not user_results:
                return "You haven't completed any quizzes yet. Start one with 'start quiz'!"
            
            # Show recent results
            recent_result = user_results[-1]  # Most recent
            quiz_id, results = recent_result
            participant_data = results['participants'][user_id]
            
            response = f"📊 **Your Recent Quiz Results:**\n\n"
            response += f"🎯 Quiz: {quiz_id}\n"
            response += f"✅ Correct: {participant_data['correct_answers']}/{participant_data['total_questions']}\n"
            response += f"📈 Score: {participant_data['score']:.1f}%\n"
            response += f"📅 Date: {results['start_time'].strftime('%Y-%m-%d %H:%M')}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error showing quiz results: {e}")
            return "I'm having trouble showing your results. Please try again."
    
    async def _show_leaderboard(self, chat_id: int) -> str:
        """Show quiz leaderboard for the chat."""
        try:
            # Get all quiz results for this chat
            chat_results = []
            for quiz_id, results in self.quiz_results.items():
                if results.get('chat_id') == chat_id:
                    chat_results.append(results)
            
            if not chat_results:
                return "No quiz results found for this chat yet. Start a quiz to create a leaderboard!"
            
            # Aggregate scores across all quizzes
            user_scores = {}
            for results in chat_results:
                for user_id, participant_data in results['participants'].items():
                    if user_id not in user_scores:
                        user_scores[user_id] = {
                            'total_correct': 0,
                            'total_questions': 0,
                            'quizzes_taken': 0
                        }
                    
                    user_scores[user_id]['total_correct'] += participant_data['correct_answers']
                    user_scores[user_id]['total_questions'] += participant_data['total_questions']
                    user_scores[user_id]['quizzes_taken'] += 1
            
            # Calculate average scores
            for user_id, data in user_scores.items():
                if data['total_questions'] > 0:
                    data['average_score'] = (data['total_correct'] / data['total_questions']) * 100
                else:
                    data['average_score'] = 0
            
            # Sort by average score
            sorted_users = sorted(
                user_scores.items(),
                key=lambda x: x[1]['average_score'],
                reverse=True
            )
            
            response = f"🏆 **Quiz Leaderboard**\n\n"
            
            for i, (user_id, data) in enumerate(sorted_users[:10], 1):  # Top 10
                response += f"{i}. User {user_id}: {data['average_score']:.1f}% "
                response += f"({data['quizzes_taken']} quizzes)\n"
            
            response += f"\n📊 Total Participants: {len(sorted_users)}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}")
            return "I'm having trouble showing the leaderboard. Please try again."
    
    def _show_quiz_help(self) -> str:
        """Show quiz help and rules."""
        response = "🧠 **Quiz Help & Rules**\n\n"
        response += "**Commands:**\n"
        response += "• 'start quiz' - Begin a new quiz\n"
        response += "• '1', '2', '3', '4' - Answer questions\n"
        response += "• 'score' - Check your current score\n"
        response += "• 'leaderboard' - View top performers\n"
        response += "• 'help' - Show this help message\n\n"
        
        response += "**Rules:**\n"
        response += "• Answer with numbers 1-4\n"
        response += "• One answer per question\n"
        response += "• Time limit: 5 minutes per quiz\n"
        response += "• Questions are randomly selected\n"
        response += "• Categories: AI, Technology, Science, General\n\n"
        
        response += "💡 **Tip:** Start with 'start quiz' to begin!"
        
        return response
    
    async def _show_available_categories(self, chat_id: int) -> str:
        """Show available quiz categories."""
        response = "📚 **Available Quiz Categories**\n\n"
        
        for category in self.quiz_categories:
            # Count questions in each category
            category_questions = [
                q for q in self.question_bank
                if q['category'].lower() == category.lower()
            ]
            
            response += f"• **{category}**: {len(category_questions)} questions\n"
        
        response += f"\n💡 **Difficulty Levels:** {', '.join(self.difficulty_levels).title()}\n"
        response += f"🎯 **Questions per Quiz:** {self.max_questions_per_quiz}\n"
        response += f"⏱️ **Time Limit:** {self.quiz_timeout // 60} minutes\n\n"
        
        response += "Start a quiz anytime with 'start quiz'!"
        
        return response
    
    async def _offer_quiz(self, chat_id: int) -> str:
        """Offer to start a quiz."""
        response = "🧠 **Quiz Time!**\n\n"
        response += "I can create interactive quizzes on various topics:\n"
        response += "• 🤖 AI & Machine Learning\n"
        response += "• 💻 Technology & Programming\n"
        response += "• 🔬 Science & Research\n"
        response += "• 🌍 General Knowledge\n\n"
        
        response += "**Commands:**\n"
        response += "• 'start quiz' - Begin a new quiz\n"
        response += "• 'help' - Learn the rules\n"
        response += "• 'categories' - See available topics\n"
        response += "• 'leaderboard' - View top scores\n\n"
        
        response += "🎯 Ready to test your knowledge? Just say 'start quiz'!"
        
        return response
    
    def _initialize_question_bank(self) -> List[Dict[str, Any]]:
        """Initialize the question bank with sample questions."""
        return [
            {
                'question': 'What does AI stand for?',
                'options': ['Artificial Intelligence', 'Automated Information', 'Advanced Interface', 'Algorithmic Integration'],
                'correct_answer_index': 0,
                'explanation': 'AI stands for Artificial Intelligence, which refers to machines that can perform tasks requiring human intelligence.',
                'category': 'AI',
                'difficulty': 'easy'
            },
            {
                'question': 'Which programming language is most commonly used for AI development?',
                'options': ['Python', 'Java', 'C++', 'JavaScript'],
                'correct_answer_index': 0,
                'explanation': 'Python is the most popular language for AI due to its extensive libraries like TensorFlow and PyTorch.',
                'category': 'AI',
                'difficulty': 'medium'
            },
            {
                'question': 'What is machine learning?',
                'options': ['A type of computer hardware', 'A subset of AI that learns from data', 'A programming language', 'A database system'],
                'correct_answer_index': 1,
                'explanation': 'Machine learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed.',
                'category': 'AI',
                'difficulty': 'medium'
            },
            {
                'question': 'What is the primary purpose of neural networks?',
                'options': ['To store data', 'To process information similar to human brains', 'To connect to the internet', 'To display graphics'],
                'correct_answer_index': 1,
                'explanation': 'Neural networks are designed to process information in a way similar to how human brains work, using interconnected nodes.',
                'category': 'AI',
                'difficulty': 'hard'
            },
            {
                'question': 'Which company developed ChatGPT?',
                'options': ['Google', 'Microsoft', 'OpenAI', 'Facebook'],
                'correct_answer_index': 2,
                'explanation': 'ChatGPT was developed by OpenAI, an AI research company.',
                'category': 'AI',
                'difficulty': 'easy'
            },
            {
                'question': 'What is the Internet?',
                'options': ['A computer program', 'A global network of computers', 'A type of software', 'A hardware device'],
                'correct_answer_index': 1,
                'explanation': 'The Internet is a global network of interconnected computers that allows information sharing worldwide.',
                'category': 'Technology',
                'difficulty': 'easy'
            },
            {
                'question': 'What does CPU stand for?',
                'options': ['Central Processing Unit', 'Computer Personal Unit', 'Central Program Utility', 'Computer Processing Unit'],
                'correct_answer_index': 0,
                'explanation': 'CPU stands for Central Processing Unit, which is the main processor of a computer.',
                'category': 'Technology',
                'difficulty': 'medium'
            },
            {
                'question': 'What is the capital of France?',
                'options': ['London', 'Berlin', 'Paris', 'Madrid'],
                'correct_answer_index': 2,
                'explanation': 'Paris is the capital and largest city of France.',
                'category': 'General',
                'difficulty': 'easy'
            },
            {
                'question': 'How many planets are in our solar system?',
                'options': ['7', '8', '9', '10'],
                'correct_answer_index': 1,
                'explanation': 'There are 8 planets in our solar system: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune.',
                'category': 'Science',
                'difficulty': 'easy'
            },
            {
                'question': 'What is the chemical symbol for gold?',
                'options': ['Ag', 'Au', 'Fe', 'Cu'],
                'correct_answer_index': 1,
                'explanation': 'Au is the chemical symbol for gold, derived from the Latin word "aurum".',
                'category': 'Science',
                'difficulty': 'medium'
            }
        ]
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when quiz generation fails."""
        fallback_responses = [
            "I'm having trouble with the quiz system right now. Please try again in a few minutes.",
            "The quiz service is temporarily unavailable. Please check back later.",
            "I can't create a quiz at the moment. Please try again soon.",
            "There seems to be a technical issue with the quiz system. Please try again later."
        ]
        
        import random
        return random.choice(fallback_responses)
    
    async def process_special_command(self, command: str, message_info: Dict[str, Any]) -> str:
        """Process special quiz commands."""
        command_lower = command.lower()
        chat_id = message_info.get('chat_id')
        user_id = message_info.get('user_id')
        
        if command_lower in ['/quiz', '/start_quiz']:
            return await self._start_new_quiz(chat_id, user_id)
        elif command_lower in ['/score', '/results']:
            return await self._show_quiz_results(chat_id, user_id)
        elif command_lower in ['/leaderboard', '/ranking']:
            return await self._show_leaderboard(chat_id)
        elif command_lower in ['/help', '/rules']:
            return self._show_quiz_help()
        elif command_lower in ['/categories', '/topics']:
            return await self._show_available_categories(chat_id)
        elif command_lower in ['/cancel', '/stop']:
            return await self._cancel_quiz(chat_id)
        else:
            return "I don't recognize that quiz command. Try /quiz, /score, /leaderboard, or /help."
    
    async def _cancel_quiz(self, chat_id: int) -> str:
        """Cancel the active quiz in a chat."""
        if chat_id in self.active_quizzes:
            quiz_data = self.active_quizzes[chat_id]
            if quiz_data['status'] == 'active':
                del self.active_quizzes[chat_id]
                return "❌ Quiz cancelled. Start a new one anytime with 'start quiz'!"
            else:
                return "There's no active quiz to cancel."
        else:
            return "There's no active quiz in this chat."
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the quiz agent."""
        try:
            # Basic health check
            health_status = await super().health_check()
            
            # Quiz-specific checks
            quiz_status = {
                'question_bank_size': len(self.question_bank),
                'categories': self.quiz_categories,
                'difficulty_levels': self.difficulty_levels,
                'active_quizzes': len(self.active_quizzes),
                'completed_quizzes': len(self.quiz_results),
                'max_questions_per_quiz': self.max_questions_per_quiz,
                'quiz_timeout': self.quiz_timeout
            }
            
            health_status['quiz_specific'] = quiz_status
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent': self.handle,
                'error': str(e),
                'error_type': type(e).__name__
            }
