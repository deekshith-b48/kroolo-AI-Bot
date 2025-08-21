"""
Configuration settings for the Kroolo AI Bot.
Uses Pydantic settings for type safety and validation.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application
    app_name: str = "Kroolo AI Bot"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Telegram Configuration
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str = Field(..., env="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: str = Field(..., env="TELEGRAM_WEBHOOK_SECRET")
    
    # Secondary Bot Tokens (Optional)
    telegram_news_bot_token: Optional[str] = Field(None, env="TELEGRAM_NEWS_BOT_TOKEN")
    telegram_quiz_bot_token: Optional[str] = Field(None, env="TELEGRAM_QUIZ_BOT_TOKEN")
    telegram_debate_bot_token: Optional[str] = Field(None, env="TELEGRAM_DEBATE_BOT_TOKEN")
    telegram_mod_bot_token: Optional[str] = Field(None, env="TELEGRAM_MOD_BOT_TOKEN")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=2000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    mongodb_url: Optional[str] = Field(None, env="MONGODB_URL")
    
    # Vector Database
    qdrant_url: str = Field(..., env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, env="QDRANT_API_KEY")
    vector_dimension: int = Field(default=768, env="VECTOR_DIMENSION")
    
    # External APIs
    news_api_key: Optional[str] = Field(None, env="NEWS_API_KEY")
    rss_feeds: List[str] = Field(default=[], env="RSS_FEEDS")
    
    # Rate Limiting
    rate_limit_per_user: int = Field(default=10, env="RATE_LIMIT_PER_USER")
    rate_limit_per_chat: int = Field(default=50, env="RATE_LIMIT_PER_CHAT")
    rate_limit_global: int = Field(default=1000, env="RATE_LIMIT_GLOBAL")
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    
    # Content & Scheduling
    default_timezone: str = Field(default="Asia/Kolkata", env="DEFAULT_TIMEZONE")
    news_digest_time: str = Field(default="09:00", env="NEWS_DIGEST_TIME")
    quiz_time: str = Field(default="19:00", env="QUIZ_TIME")
    fun_fact_time: str = Field(default="21:00", env="FUN_FACT_TIME")
    
    # Monitoring & Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Admin Configuration
    bot_admin_ids: str = Field(default="123456789", env="BOT_ADMIN_IDS")
    admin_webhook_secret: str = Field(default="admin-webhook-secret", env="ADMIN_WEBHOOK_SECRET")
    enable_admin_api: bool = Field(default=True, env="ENABLE_ADMIN_API")
    admin_session_timeout: int = Field(default=3600, env="ADMIN_SESSION_TIMEOUT")
    
    @validator("rss_feeds", pre=True)
    def parse_rss_feeds(cls, v):
        """Parse RSS feeds from comma-separated string."""
        if isinstance(v, str):
            return [feed.strip() for feed in v.split(",") if feed.strip()]
        return v
    
    @validator("telegram_webhook_url")
    def validate_webhook_url(cls, v):
        """Ensure webhook URL is HTTPS."""
        if not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Bot token mapping
BOT_TOKENS = {
    "main": settings.telegram_bot_token,
    "news": settings.telegram_news_bot_token,
    "quiz": settings.telegram_quiz_bot_token,
    "debate": settings.telegram_debate_bot_token,
    "mod": settings.telegram_mod_bot_token,
}

# Filter out None tokens
BOT_TOKENS = {k: v for k, v in BOT_TOKENS.items() if v is not None}
