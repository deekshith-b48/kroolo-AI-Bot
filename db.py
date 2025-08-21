"""
Database module for Kroolo Agent Bot
SQLite schema and queries for users, communities, and logs
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.metadata = MetaData()
        self.SessionLocal = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection and create tables"""
        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        
        self.engine = create_engine(self.database_url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        
        # Define tables
        self.users_table = Table(
            "users", self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("telegram_id", Integer, unique=True, index=True, nullable=False),
            Column("username", String(255)),
            Column("role", String(50), default="user"),  # user | moderator | admin | superadmin
            Column("created_at", DateTime, default=datetime.utcnow)
        )
        
        self.communities_table = Table(
            "communities", self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("chat_id", Integer, unique=True, index=True, nullable=False),
            Column("settings", Text),  # JSON string for simplicity
            Column("topics", Text),  # JSON string for topics
            Column("created_at", DateTime, default=datetime.utcnow)
        )
        
        self.logs_table = Table(
            "logs", self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("user_id", Integer),
            Column("chat_id", Integer),
            Column("action", String(255)),
            Column("details", Text),
            Column("timestamp", DateTime, default=datetime.utcnow)
        )
        
        # Create tables
        self.metadata.create_all(self.engine)
        logger.info("Database initialized successfully")
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def log_action(self, user_id: Optional[int], chat_id: Optional[int], action: str, details: str = ""):
        """Log an action to the database"""
        session = self.get_session()
        try:
            ins = self.logs_table.insert().values(
                user_id=user_id,
                chat_id=chat_id,
                action=action,
                details=details,
                timestamp=datetime.utcnow()
            )
            session.execute(ins)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
            session.rollback()
        finally:
            session.close()
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        session = self.get_session()
        try:
            result = session.execute(
                self.users_table.select().where(self.users_table.c.telegram_id == telegram_id)
            ).fetchone()
            if result:
                return dict(result)
            return None
        finally:
            session.close()
    
    def create_user(self, telegram_id: int, username: Optional[str] = None, role: str = "user") -> bool:
        """Create a new user"""
        session = self.get_session()
        try:
            ins = self.users_table.insert().values(
                telegram_id=telegram_id,
                username=username,
                role=role
            )
            session.execute(ins)
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def update_user_role(self, telegram_id: int, new_role: str) -> bool:
        """Update user role"""
        session = self.get_session()
        try:
            session.execute(
                self.users_table.update()
                .where(self.users_table.c.telegram_id == telegram_id)
                .values(role=new_role)
            )
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update user role: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_community_settings(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get community settings"""
        session = self.get_session()
        try:
            result = session.execute(
                self.communities_table.select().where(self.communities_table.c.chat_id == chat_id)
            ).fetchone()
            if result:
                settings = json.loads(result.settings) if result.settings else {}
                topics = json.loads(result.topics) if result.topics else []
                return {
                    "chat_id": result.chat_id,
                    "settings": settings,
                    "topics": topics,
                    "created_at": result.created_at
                }
            return None
        finally:
            session.close()
    
    def update_community_settings(self, chat_id: int, settings: Dict[str, Any], topics: List[str] = None) -> bool:
        """Update community settings"""
        session = self.get_session()
        try:
            # Check if community exists
            existing = session.execute(
                self.communities_table.select().where(self.communities_table.c.chat_id == chat_id)
            ).fetchone()
            
            if existing:
                # Update existing
                session.execute(
                    self.communities_table.update()
                    .where(self.communities_table.c.chat_id == chat_id)
                    .values(
                        settings=json.dumps(settings),
                        topics=json.dumps(topics or [])
                    )
                )
            else:
                # Create new
                ins = self.communities_table.insert().values(
                    chat_id=chat_id,
                    settings=json.dumps(settings),
                    topics=json.dumps(topics or [])
                )
                session.execute(ins)
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update community settings: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_logs(self, limit: int = 100, user_id: Optional[int] = None, chat_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get logs with optional filtering"""
        session = self.get_session()
        try:
            query = self.logs_table.select().order_by(self.logs_table.c.timestamp.desc()).limit(limit)
            
            if user_id:
                query = query.where(self.logs_table.c.user_id == user_id)
            if chat_id:
                query = query.where(self.logs_table.c.chat_id == chat_id)
            
            results = session.execute(query).fetchall()
            return [dict(row) for row in results]
        finally:
            session.close()
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get all users with a specific role"""
        session = self.get_session()
        try:
            results = session.execute(
                self.users_table.select().where(self.users_table.c.role == role)
            ).fetchall()
            return [dict(row) for row in results]
        finally:
            session.close()
    
    def backup_database(self) -> Dict[str, Any]:
        """Create a backup of the database"""
        try:
            users = self.get_users_by_role("admin")  # Get all users
            communities = []
            logs = self.get_logs(limit=1000)  # Get recent logs
            
            # Get all communities
            session = self.get_session()
            try:
                community_results = session.execute(self.communities_table.select()).fetchall()
                for row in community_results:
                    communities.append({
                        "chat_id": row.chat_id,
                        "settings": json.loads(row.settings) if row.settings else {},
                        "topics": json.loads(row.topics) if row.topics else [],
                        "created_at": row.created_at.isoformat() if row.created_at else None
                    })
            finally:
                session.close()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "users": users,
                "communities": communities,
                "logs": logs
            }
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return {"error": str(e)}
