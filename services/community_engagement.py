"""
Community Engagement Service for Kroolo Agent Bot
Handles news, quizzes, fun facts, and scheduled posts
"""

import logging
import random
import sqlite3
import feedparser
from typing import Dict, Any, List, Optional
from datetime import datetime, time
import pytz
from services.ai_service import AIService
from utils.logger import log_user_action, log_admin_action

logger = logging.getLogger(__name__)

class CommunityEngagementService:
    """Service for community engagement features"""
    
    def __init__(self, ai_service: AIService, database_path: str = "kroolo.db"):
        self.ai_service = ai_service
        self.database_path = database_path
        self._init_database()
        
        # Quiz questions database
        self.quiz_questions = [
            {
                "question": "What is the primary purpose of machine learning?",
                "options": ["To replace humans", "To make predictions from data", "To write code automatically", "To browse the internet"],
                "correct_answer": "To make predictions from data",
                "explanation": "Machine learning focuses on creating algorithms that can learn and make predictions from data."
            },
            {
                "question": "Which of these is NOT a type of machine learning?",
                "options": ["Supervised Learning", "Unsupervised Learning", "Reinforcement Learning", "Random Learning"],
                "correct_answer": "Random Learning",
                "explanation": "Random Learning is not a recognized type of machine learning."
            },
            {
                "question": "What does GPT stand for?",
                "options": ["General Purpose Technology", "Generative Pre-trained Transformer", "Global Processing Tool", "General Programming Tool"],
                "correct_answer": "Generative Pre-trained Transformer",
                "explanation": "GPT stands for Generative Pre-trained Transformer, which describes its architecture and training approach."
            },
            {
                "question": "Which programming language is most commonly used in AI/ML?",
                "options": ["Java", "Python", "C++", "JavaScript"],
                "correct_answer": "Python",
                "explanation": "Python is the most popular language for AI/ML due to its simplicity and rich ecosystem of libraries."
            },
            {
                "question": "What is the main advantage of deep learning over traditional machine learning?",
                "options": ["It's faster", "It can automatically learn features", "It uses less memory", "It's easier to understand"],
                "correct_answer": "It can automatically learn features",
                "explanation": "Deep learning can automatically learn hierarchical features from raw data, unlike traditional ML which requires manual feature engineering."
            }
        ]
        
        # Fun facts database
        self.fun_facts = [
            "🤖 The term 'Artificial Intelligence' was first coined at a conference at Dartmouth College in 1956.",
            "🧠 Neural networks were inspired by the human brain, but they're actually much simpler than real neurons.",
            "📱 Your smartphone likely uses AI for features like face recognition, voice assistants, and camera optimization.",
            "🎯 Machine learning models can sometimes 'hallucinate' and generate completely false but convincing information.",
            "🌐 AI can now generate realistic images, write code, and compose music - tasks that were once thought to be uniquely human.",
            "🔍 AI is used in medical diagnosis, helping doctors detect diseases like cancer earlier and more accurately.",
            "🚗 Self-driving cars use multiple AI systems working together: computer vision, path planning, and decision making.",
            "🎮 AI has been playing games since the 1950s, starting with checkers and now mastering complex games like Go and StarCraft.",
            "📊 AI can analyze millions of data points in seconds, finding patterns that humans might never notice.",
            "🌍 AI is helping fight climate change by optimizing energy usage, predicting weather patterns, and monitoring environmental changes."
        ]
        
        # Jokes database
        self.jokes = [
            "Why did the AI go to therapy? Because it had too many deep issues! 😄",
            "What do you call an AI that's always late? A procrastinator! 🤖",
            "Why did the machine learning model break up with its girlfriend? It found a better fit! 📊",
            "What's an AI's favorite type of music? Algorithm and blues! 🎵",
            "Why did the chatbot go to the doctor? It had a virus! 🦠",
            "What do you call an AI that tells jokes? A comedian-tron! 😂",
            "Why did the neural network feel lonely? It had too many hidden layers! 🧠",
            "What's an AI's favorite dessert? Artificial sweetener! 🍰",
            "Why did the robot go to the gym? To get more artificial intelligence! 💪",
            "What do you call an AI that's good at math? A calculator! 🧮"
        ]
    
    def _init_database(self):
        """Initialize database tables for community engagement"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Quiz scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    points INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    total_questions INTEGER DEFAULT 0,
                    last_quiz_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Scheduled jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_type TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    time_scheduled TEXT NOT NULL,
                    timezone TEXT DEFAULT 'UTC',
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # News cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    link TEXT NOT NULL,
                    summary TEXT,
                    published_date TEXT,
                    cached_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Community engagement database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing community engagement database: {e}")
    
    async def fetch_ai_news(self, limit: int = 5) -> List[Dict[str, str]]:
        """Fetch AI-related news prioritizing Exa.ai search, then RSS, then AI fallback."""
        # 1) Try Exa.ai if available via injected AIService
        try:
            if getattr(self.ai_service, "exa_api_key", None):
                import httpx, time
                query = "latest AI news from reputable sources in the last 48 hours"
                payload = {
                    "query": query,
                    "num_results": min(max(limit, 3), 10),
                    "use_cached": True,
                    "type": "neural",
                    "include_domains": [],
                }
                start = time.time()
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(
                        "https://api.exa.ai/search",
                        headers={
                            "x-api-key": self.ai_service.exa_api_key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    articles: List[Dict[str, str]] = []
                    for r in results[:limit]:
                        articles.append({
                            "title": r.get("title") or "Untitled",
                            "link": r.get("url") or "",
                            "summary": (r.get("text") or "")[:300] + ("..." if (r.get("text") and len(r.get("text")) > 300) else ""),
                            "published": r.get("publishedDate") or r.get("published_date") or "",
                            "source": r.get("domain") or "exa.ai",
                        })
                    if articles:
                        return articles
                else:
                    logger.warning(f"Exa search failed: HTTP {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Exa search error, falling back to RSS: {e}")

        # 2) RSS fallback
        try:
            # Use environment RSS feeds or fallback to defaults
            import os
            rss_feeds_env = os.getenv("RSS_FEEDS")
            
            if rss_feeds_env:
                # Parse RSS_FEEDS from environment
                import json
                try:
                    rss_sources = json.loads(rss_feeds_env)
                except:
                    rss_sources = [
                        "https://feeds.feedburner.com/oreilly/radar",
                        "https://rss.cnn.com/rss/edition.rss"
                    ]
            else:
                # Default RSS sources for AI news
                rss_sources = [
                    "https://feeds.feedburner.com/artificial-intelligence-news",
                    "https://www.artificialintelligence-news.com/feed/",
                    "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml"
                ]
            
            all_articles = []
            
            for source in rss_sources:
                try:
                    feed = feedparser.parse(source)
                    for entry in feed.entries[:max(1, limit//max(1, len(rss_sources))) + 1]:
                        article = {
                            "title": entry.title,
                            "link": entry.link,
                            "summary": getattr(entry, 'summary', '')[:200] + "..." if hasattr(entry, 'summary') and len(entry.summary) > 200 else getattr(entry, 'summary', 'No summary available'),
                            "published": getattr(entry, 'published', 'Unknown date'),
                            "source": source
                        }
                        all_articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to fetch from {source}: {e}")
                    continue
            
            # Sort by date and limit results
            all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
            if all_articles:
                return all_articles[:limit]
        except Exception as e:
            logger.error(f"Error fetching AI news via RSS: {e}")

        # 3) AI-generated fallback
        return await self._generate_ai_news_fallback()
    
    async def _generate_ai_news_fallback(self) -> List[Dict[str, str]]:
        """Generate AI news summary when RSS fails"""
        try:
            prompt = "Generate 3 recent AI news headlines with brief summaries (max 100 words each). Format as: Title: [Title] Summary: [Summary]"
            response = await self.ai_service.ask_ai(prompt)
            
            # Parse the AI response into structured format
            articles = []
            lines = response.split('\n')
            current_article = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('Title:'):
                    if current_article:
                        articles.append(current_article)
                    current_article = {'title': line.replace('Title:', '').strip()}
                elif line.startswith('Summary:'):
                    current_article['summary'] = line.replace('Summary:', '').strip()
                    current_article['link'] = 'AI-generated summary'
                    current_article['published'] = 'Today'
                    current_article['source'] = 'AI-generated'
            
            if current_article:
                articles.append(current_article)
            
            return articles[:3]
            
        except Exception as e:
            logger.error(f"Error generating AI news fallback: {e}")
            return [
                {
                    "title": "AI News Service Temporarily Unavailable",
                    "summary": "We're experiencing technical difficulties. Please try again later.",
                    "link": "#",
                    "published": "Now",
                    "source": "System"
                }
            ]
    
    async def get_random_quiz(self) -> Dict[str, Any]:
        """Get a random quiz question"""
        quiz = random.choice(self.quiz_questions).copy()
        # Shuffle options to make it more challenging
        options = quiz["options"].copy()
        random.shuffle(options)
        quiz["options"] = options
        return quiz
    
    def get_random_fun_fact(self) -> str:
        """Get a random AI fun fact"""
        return random.choice(self.fun_facts)
    
    def get_random_joke(self) -> str:
        """Get a random tech/AI joke"""
        return random.choice(self.jokes)
    
    def record_quiz_answer(self, user_id: int, username: str, is_correct: bool) -> Dict[str, Any]:
        """Record quiz answer and update user score"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT * FROM quiz_scores WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user:
                # Update existing user
                points_to_add = 10 if is_correct else 0
                new_points = user[3] + points_to_add
                new_correct = user[4] + (1 if is_correct else 0)
                new_total = user[5] + 1
                
                cursor.execute("""
                    UPDATE quiz_scores 
                    SET points = ?, correct_answers = ?, total_questions = ?, last_quiz_date = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_points, new_correct, new_total, user_id))
                
                current_score = new_points
            else:
                # Create new user
                points_to_add = 10 if is_correct else 0
                cursor.execute("""
                    INSERT INTO quiz_scores (user_id, username, points, correct_answers, total_questions, last_quiz_date)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, username, points_to_add, 1 if is_correct else 0, 1))
                
                current_score = points_to_add
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "points_earned": points_to_add,
                "total_points": current_score,
                "is_correct": is_correct
            }
            
        except Exception as e:
            logger.error(f"Error recording quiz answer: {e}")
            return {"success": False, "error": str(e)}
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get quiz leaderboard"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, points, correct_answers, total_questions
                FROM quiz_scores 
                ORDER BY points DESC, correct_answers DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            leaderboard = []
            for i, row in enumerate(rows, 1):
                leaderboard.append({
                    "rank": i,
                    "username": row[0] or f"User_{row[1]}",
                    "points": row[1],
                    "correct_answers": row[2],
                    "total_questions": row[3],
                    "accuracy": round((row[2] / row[3]) * 100, 1) if row[3] > 0 else 0
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def schedule_job(self, job_type: str, chat_id: int, time_str: str, timezone: str, user_id: int) -> Dict[str, Any]:
        """Schedule a recurring job"""
        try:
            # Validate time format (HH:MM)
            try:
                hour, minute = map(int, time_str.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time format")
            except:
                return {"success": False, "error": "Invalid time format. Use HH:MM (e.g., 09:00)"}
            
            # Validate timezone
            try:
                pytz.timezone(timezone)
            except:
                timezone = 'UTC'  # Default to UTC if invalid
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if job already exists for this type and chat
            cursor.execute("""
                SELECT id FROM scheduled_jobs 
                WHERE job_type = ? AND chat_id = ? AND is_active = 1
            """, (job_type, chat_id))
            
            existing_job = cursor.fetchone()
            
            if existing_job:
                # Update existing job
                cursor.execute("""
                    UPDATE scheduled_jobs 
                    SET time_scheduled = ?, timezone = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (time_str, timezone, existing_job[0]))
                message = f"Updated {job_type} schedule to {time_str} {timezone}"
            else:
                # Create new job
                cursor.execute("""
                    INSERT INTO scheduled_jobs (job_type, chat_id, time_scheduled, timezone, created_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (job_type, chat_id, time_str, timezone, user_id))
                message = f"Scheduled {job_type} daily at {time_str} {timezone}"
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": message, "time": time_str, "timezone": timezone}
            
        except Exception as e:
            logger.error(f"Error scheduling job: {e}")
            return {"success": False, "error": str(e)}
    
    def unschedule_job(self, job_type: str, chat_id: int) -> Dict[str, Any]:
        """Unschedule a recurring job"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE scheduled_jobs 
                SET is_active = 0 
                WHERE job_type = ? AND chat_id = ? AND is_active = 1
            """, (job_type, chat_id))
            
            if cursor.rowcount > 0:
                message = f"Stopped {job_type} schedule"
                success = True
            else:
                message = f"No active {job_type} schedule found"
                success = False
            
            conn.commit()
            conn.close()
            
            return {"success": success, "message": message}
            
        except Exception as e:
            logger.error(f"Error unscheduling job: {e}")
            return {"success": False, "error": str(e)}
    
    def get_scheduled_jobs(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get all scheduled jobs for a chat"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT job_type, time_scheduled, timezone, created_at
                FROM scheduled_jobs 
                WHERE chat_id = ? AND is_active = 1
                ORDER BY job_type
            """, (chat_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            jobs = []
            for row in rows:
                jobs.append({
                    "type": row[0],
                    "time": row[1],
                    "timezone": row[2],
                    "created": row[3]
                })
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting scheduled jobs: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's quiz statistics"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT points, correct_answers, total_questions, last_quiz_date
                FROM quiz_scores 
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "points": row[0],
                    "correct_answers": row[1],
                    "total_questions": row[2],
                    "last_quiz_date": row[3],
                    "accuracy": round((row[1] / row[2]) * 100, 1) if row[2] > 0 else 0,
                    "rank": self._get_user_rank(user_id)
                }
            else:
                return {
                    "points": 0,
                    "correct_answers": 0,
                    "total_questions": 0,
                    "last_quiz_date": None,
                    "accuracy": 0,
                    "rank": "Unranked"
                }
                
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"error": str(e)}
    
    def _get_user_rank(self, user_id: int) -> str:
        """Get user's rank in leaderboard"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) + 1
                FROM quiz_scores 
                WHERE points > (SELECT points FROM quiz_scores WHERE user_id = ?)
            """, (user_id,))
            
            rank = cursor.fetchone()[0]
            conn.close()
            
            if rank == 1:
                return "🥇 1st"
            elif rank == 2:
                return "🥈 2nd"
            elif rank == 3:
                return "🥉 3rd"
            else:
                return f"{rank}th"
                
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return "Unranked"
