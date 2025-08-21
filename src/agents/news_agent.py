"""
News agent for AI news aggregation and reporting.
Handles news gathering, summarization, and delivery.
"""

import asyncio
import logging
import aiohttp
import feedparser
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from .base_agent import BaseAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class NewsAgent(BaseAgent):
    """Agent for handling AI news and updates."""
    
    def __init__(self, config):
        super().__init__(config)
        self.agent_type = 'news'
        
        # News-specific settings
        self.rss_feeds = getattr(config, 'rss_feeds', settings.rss_feeds)
        self.news_categories = getattr(config, 'news_categories', ['AI', 'technology', 'research'])
        self.max_articles_per_fetch = getattr(config, 'max_articles_per_fetch', 10)
        self.summarization_enabled = getattr(config, 'summarization_enabled', True)
        
        # News cache
        self.news_cache = {}
        self.last_fetch_time = None
        self.cache_duration = timedelta(minutes=30)  # Cache for 30 minutes
        
        logger.info(f"Initialized news agent with {len(self.rss_feeds)} RSS feeds")
    
    async def _generate_response(self, message_info: Dict[str, Any], agent_context: Dict[str, Any]) -> str:
        """Generate news-related response."""
        try:
            user_message = message_info.get('text', '').lower()
            chat_id = message_info.get('chat_id')
            
            # Parse user intent
            if 'latest' in user_message or 'recent' in user_message:
                return await self._get_latest_news(chat_id)
            elif 'ai' in user_message or 'artificial intelligence' in user_message:
                return await self._get_ai_news(chat_id)
            elif 'technology' in user_message or 'tech' in user_message:
                return await self._get_tech_news(chat_id)
            elif 'research' in user_message or 'study' in user_message:
                return await self._get_research_news(chat_id)
            elif 'summary' in user_message or 'overview' in user_message:
                return await self._get_news_summary(chat_id)
            else:
                return await self._get_general_news(chat_id)
                
        except Exception as e:
            logger.error(f"Error generating news response: {e}")
            return self._get_fallback_response()
    
    async def _get_latest_news(self, chat_id: int) -> str:
        """Get the latest news from all sources."""
        try:
            articles = await self._fetch_news()
            if not articles:
                return "I couldn't fetch the latest news right now. Please try again later."
            
            # Get top 3 most recent articles
            recent_articles = sorted(articles, key=lambda x: x.get('published', ''), reverse=True)[:3]
            
            response = "📰 **Latest News Updates**\n\n"
            for i, article in enumerate(recent_articles, 1):
                response += f"{i}. **{article['title']}**\n"
                if article.get('summary'):
                    response += f"   {article['summary'][:100]}...\n"
                response += f"   📅 {article.get('published', 'Unknown date')}\n"
                response += f"   🔗 {article.get('source', 'Unknown source')}\n\n"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error getting latest news: {e}")
            return "I'm having trouble fetching the latest news. Please try again later."
    
    async def _get_ai_news(self, chat_id: int) -> str:
        """Get AI-specific news."""
        try:
            articles = await self._fetch_news()
            ai_articles = [
                article for article in articles
                if any(keyword in article.get('title', '').lower() 
                      for keyword in ['ai', 'artificial intelligence', 'machine learning', 'deep learning'])
            ]
            
            if not ai_articles:
                return "No AI-related news found at the moment. Try asking for general technology news instead."
            
            # Get top 3 AI articles
            top_ai_articles = ai_articles[:3]
            
            response = "🤖 **Latest AI News**\n\n"
            for i, article in enumerate(top_ai_articles, 1):
                response += f"{i}. **{article['title']}**\n"
                if article.get('summary'):
                    response += f"   {article['summary'][:120]}...\n"
                response += f"   📅 {article.get('published', 'Unknown date')}\n"
                response += f"   🔗 {article.get('source', 'Unknown source')}\n\n"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error getting AI news: {e}")
            return "I'm having trouble fetching AI news. Please try again later."
    
    async def _get_tech_news(self, chat_id: int) -> str:
        """Get technology news."""
        try:
            articles = await self._fetch_news()
            tech_articles = [
                article for article in articles
                if any(keyword in article.get('title', '').lower() 
                      for keyword in ['technology', 'tech', 'software', 'hardware', 'innovation'])
            ]
            
            if not tech_articles:
                return "No technology news found at the moment. Try asking for general news instead."
            
            # Get top 3 tech articles
            top_tech_articles = tech_articles[:3]
            
            response = "💻 **Latest Technology News**\n\n"
            for i, article in enumerate(top_tech_articles, 1):
                response += f"{i}. **{article['title']}**\n"
                if article.get('summary'):
                    response += f"   {article['summary'][:120]}...\n"
                response += f"   📅 {article.get('published', 'Unknown date')}\n"
                response += f"   🔗 {article.get('source', 'Unknown source')}\n\n"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error getting tech news: {e}")
            return "I'm having trouble fetching technology news. Please try again later."
    
    async def _get_research_news(self, chat_id: int) -> str:
        """Get research-related news."""
        try:
            articles = await self._fetch_news()
            research_articles = [
                article for article in articles
                if any(keyword in article.get('title', '').lower() 
                      for keyword in ['research', 'study', 'paper', 'discovery', 'breakthrough'])
            ]
            
            if not research_articles:
                return "No research news found at the moment. Try asking for general news instead."
            
            # Get top 3 research articles
            top_research_articles = research_articles[:3]
            
            response = "🔬 **Latest Research News**\n\n"
            for i, article in enumerate(top_research_articles, 1):
                response += f"{i}. **{article['title']}**\n"
                if article.get('summary'):
                    response += f"   {article['summary'][:120]}...\n"
                response += f"   📅 {article.get('published', 'Unknown date')}\n"
                response += f"   🔗 {article.get('source', 'Unknown source')}\n\n"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error getting research news: {e}")
            return "I'm having trouble fetching research news. Please try again later."
    
    async def _get_general_news(self, chat_id: int) -> str:
        """Get general news overview."""
        try:
            articles = await self._fetch_news()
            if not articles:
                return "I couldn't fetch news right now. Please try again later."
            
            # Get a mix of different categories
            general_articles = articles[:3]
            
            response = "📰 **Today's Top Stories**\n\n"
            for i, article in enumerate(general_articles, 1):
                response += f"{i}. **{article['title']}**\n"
                if article.get('summary'):
                    response += f"   {article['summary'][:100]}...\n"
                response += f"   📅 {article.get('published', 'Unknown date')}\n"
                response += f"   🔗 {article.get('source', 'Unknown source')}\n\n"
            
            response += "💡 *Tip: Ask me for specific news like 'AI news', 'tech news', or 'research news' for more focused updates.*"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error getting general news: {e}")
            return "I'm having trouble fetching news. Please try again later."
    
    async def _get_news_summary(self, chat_id: int) -> str:
        """Get a summary of recent news."""
        try:
            articles = await self._fetch_news()
            if not articles:
                return "I couldn't fetch news for a summary right now. Please try again later."
            
            # Get articles from the last 24 hours
            recent_articles = [
                article for article in articles
                if self._is_recent(article.get('published', ''))
            ]
            
            if not recent_articles:
                return "No recent news found for the last 24 hours."
            
            # Count by category
            categories = {}
            for article in recent_articles:
                category = self._categorize_article(article)
                categories[category] = categories.get(category, 0) + 1
            
            response = "📊 **News Summary (Last 24 Hours)**\n\n"
            response += f"📰 Total Articles: {len(recent_articles)}\n\n"
            
            for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                response += f"• {category}: {count} articles\n"
            
            response += "\n💡 *Ask me for specific news categories or 'latest news' for detailed updates.*"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error getting news summary: {e}")
            return "I'm having trouble generating a news summary. Please try again later."
    
    async def _fetch_news(self) -> List[Dict[str, Any]]:
        """Fetch news from RSS feeds."""
        # Check cache first
        if (self.last_fetch_time and 
            datetime.now() - self.last_fetch_time < self.cache_duration and 
            self.news_cache):
            return self.news_cache
        
        try:
            all_articles = []
            
            # Fetch from each RSS feed concurrently
            tasks = [self._fetch_rss_feed(feed) for feed in self.rss_feeds]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_articles.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error fetching RSS feed: {result}")
            
            # Sort by publication date (newest first)
            all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
            
            # Limit articles
            all_articles = all_articles[:self.max_articles_per_fetch]
            
            # Update cache
            self.news_cache = all_articles
            self.last_fetch_time = datetime.now()
            
            logger.info(f"Fetched {len(all_articles)} news articles from {len(self.rss_feeds)} sources")
            return all_articles
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    async def _fetch_rss_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Fetch articles from a single RSS feed."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Parse RSS feed
                        feed = feedparser.parse(content)
                        articles = []
                        
                        for entry in feed.entries[:5]:  # Limit to 5 articles per feed
                            article = {
                                'title': entry.get('title', ''),
                                'summary': entry.get('summary', ''),
                                'link': entry.get('link', ''),
                                'published': entry.get('published', ''),
                                'source': feed.feed.get('title', 'Unknown Source'),
                                'category': self._categorize_article(entry)
                            }
                            
                            # Clean and validate article data
                            if article['title'] and len(article['title']) > 10:
                                articles.append(article)
                        
                        return articles
                    else:
                        logger.warning(f"Failed to fetch RSS feed {feed_url}: HTTP {response.status}")
                        return []
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching RSS feed: {feed_url}")
            return []
        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return []
    
    def _categorize_article(self, article: Dict[str, Any]) -> str:
        """Categorize an article based on its content."""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        content = title + ' ' + summary
        
        if any(keyword in content for keyword in ['ai', 'artificial intelligence', 'machine learning']):
            return 'AI & Machine Learning'
        elif any(keyword in content for keyword in ['technology', 'tech', 'software', 'hardware']):
            return 'Technology'
        elif any(keyword in content for keyword in ['research', 'study', 'paper', 'discovery']):
            return 'Research'
        elif any(keyword in content for keyword in ['business', 'startup', 'company', 'investment']):
            return 'Business'
        elif any(keyword in content for keyword in ['science', 'physics', 'chemistry', 'biology']):
            return 'Science'
        else:
            return 'General'
    
    def _is_recent(self, published_date: str) -> bool:
        """Check if an article was published recently (within 24 hours)."""
        try:
            # Parse various date formats
            for fmt in ['%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z']:
                try:
                    parsed_date = datetime.strptime(published_date, fmt)
                    return datetime.now() - parsed_date < timedelta(days=1)
                except ValueError:
                    continue
            return False
        except Exception:
            return False
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when news fetching fails."""
        fallback_responses = [
            "I'm having trouble accessing the news right now. Please try again in a few minutes.",
            "The news service is temporarily unavailable. Please check back later.",
            "I can't fetch the latest news at the moment. Please try again soon.",
            "There seems to be a connection issue with the news feeds. Please try again later."
        ]
        
        import random
        return random.choice(fallback_responses)
    
    async def process_special_command(self, command: str, message_info: Dict[str, Any]) -> str:
        """Process special news commands."""
        command_lower = command.lower()
        
        if command_lower in ['/news', '/latest']:
            return await self._get_latest_news(message_info.get('chat_id'))
        elif command_lower in ['/ai_news', '/ai']:
            return await self._get_ai_news(message_info.get('chat_id'))
        elif command_lower in ['/tech_news', '/tech']:
            return await self._get_tech_news(message_info.get('chat_id'))
        elif command_lower in ['/research_news', '/research']:
            return await self._get_research_news(message_info.get('chat_id'))
        elif command_lower in ['/news_summary', '/summary']:
            return await self._get_news_summary(message_info.get('chat_id'))
        elif command_lower in ['/sources', '/feeds']:
            return self._get_sources_info()
        else:
            return "I don't recognize that news command. Try /news, /ai_news, /tech_news, or /news_summary."
    
    def _get_sources_info(self) -> str:
        """Get information about news sources."""
        response = "📰 **News Sources**\n\n"
        response += f"I'm currently monitoring {len(self.rss_feeds)} RSS feeds:\n\n"
        
        for i, feed in enumerate(self.rss_feeds, 1):
            source_name = feed.split('/')[-1].replace('_', ' ').title()
            response += f"{i}. {source_name}\n"
        
        response += "\n💡 *News are updated every 30 minutes. Ask me for specific categories or latest updates.*"
        return response
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the news agent."""
        try:
            # Basic health check
            health_status = await super().health_check()
            
            # News-specific checks
            news_status = {
                'rss_feeds_count': len(self.rss_feeds),
                'cache_status': 'active' if self.news_cache else 'empty',
                'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                'cache_size': len(self.news_cache)
            }
            
            # Test RSS feed connectivity
            if self.rss_feeds:
                try:
                    test_feed = self.rss_feeds[0]
                    async with aiohttp.ClientSession() as session:
                        async with session.get(test_feed, timeout=5) as response:
                            news_status['rss_connectivity'] = 'working' if response.status == 200 else 'failed'
                except Exception as e:
                    news_status['rss_connectivity'] = 'failed'
                    news_status['rss_error'] = str(e)
            else:
                news_status['rss_connectivity'] = 'no_feeds_configured'
            
            health_status['news_specific'] = news_status
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent': self.handle,
                'error': str(e),
                'error_type': type(e).__name__
            }
