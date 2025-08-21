"""
Database session management for the Kroolo AI Bot.
Handles async SQLAlchemy sessions, connection pooling, and database initialization.
"""

import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from config.settings import settings

logger = logging.getLogger(__name__)

# Global engine and session factory
engine: Optional[create_async_engine] = None
async_session_maker: Optional[async_sessionmaker] = None


async def init_database():
    """Initialize database connection and create tables."""
    global engine, async_session_maker
    
    try:
        # Create async engine with connection pooling
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # SQL logging in debug mode
            pool_size=20,  # Connection pool size
            max_overflow=30,  # Additional connections beyond pool_size
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,  # Recycle connections every hour
            pool_timeout=30,  # Connection timeout
            poolclass=NullPool if settings.debug else None  # No pooling in debug mode
        )
        
        # Create session factory
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("Database connection established successfully")
        
        # Create tables if they don't exist
        await create_tables()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def create_tables():
    """Create database tables if they don't exist."""
    try:
        from ..models.base import Base
        from ..models.agent import Agent
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created/verified successfully")
        
        # Initialize default data
        await initialize_default_data()
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


async def initialize_default_data():
    """Initialize default data in the database."""
    try:
        from ..models.agent import DEFAULT_AGENTS
        
        async with get_db_session() as session:
            # Check if agents already exist
            existing_agents = await session.execute(
                text("SELECT COUNT(*) FROM agents")
            )
            count = existing_agents.scalar()
            
            if count == 0:
                # Insert default agents
                for agent_data in DEFAULT_AGENTS:
                    agent = Agent(**agent_data)
                    session.add(agent)
                
                await session.commit()
                logger.info(f"Initialized {len(DEFAULT_AGENTS)} default agents")
            else:
                logger.info(f"Database already contains {count} agents")
                
    except Exception as e:
        logger.error(f"Failed to initialize default data: {e}")
        # Don't raise here as this is not critical for startup


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def close_database():
    """Close database connections."""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


async def health_check() -> dict:
    """Perform database health check."""
    try:
        if not engine:
            return {
                "status": "not_initialized",
                "error": "Database engine not initialized"
            }
        
        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                return {
                    "status": "healthy",
                    "connection": "active",
                    "pool_size": engine.pool.size(),
                    "checked_out": engine.pool.checkedout()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Database query test failed"
                }
                
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__
        }


async def get_database_stats() -> dict:
    """Get database statistics."""
    try:
        if not engine:
            return {"error": "Database not initialized"}
        
        stats = {
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin()
        }
        
        # Get table counts
        async with engine.begin() as conn:
            tables = ['agents', 'chats', 'messages', 'content']
            for table in tables:
                try:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    stats[f"{table}_count"] = count
                except Exception:
                    stats[f"{table}_count"] = 0
        
        return stats
        
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# Database utilities
async def execute_query(query: str, params: dict = None) -> list:
    """Execute a raw SQL query."""
    async with get_db_session() as session:
        result = await session.execute(text(query), params or {})
        return result.fetchall()


async def execute_update(query: str, params: dict = None) -> int:
    """Execute an update/insert/delete query."""
    async with get_db_session() as session:
        result = await session.execute(text(query), params or {})
        await session.commit()
        return result.rowcount


async def transaction():
    """Get a database transaction context."""
    if not async_session_maker:
        raise RuntimeError("Database not initialized")
    
    return async_session_maker()
