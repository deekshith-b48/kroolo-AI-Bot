"""
Agent manager for handling agent lifecycle and configuration.
Manages agent instances, their capabilities, and routing decisions.
"""

import logging
from typing import Dict, List, Optional, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.agent import Agent
from ..database.session import get_db_session
from ..agents.base_agent import BaseAgent
from ..agents.news_agent import NewsAgent
from ..agents.quiz_agent import QuizAgent
from ..agents.debate_agent import DebateAgent
from ..agents.fun_agent import FunAgent
from ..agents.persona_agent import PersonaAgent

logger = logging.getLogger(__name__)


class AgentManager:
    """Manages agent instances and their lifecycle."""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_types: Dict[str, Type[BaseAgent]] = {
            "news": NewsAgent,
            "quiz": QuizAgent,
            "debate": DebateAgent,
            "fun": FunAgent,
            "persona": PersonaAgent,
        }
        self._initialized = False
    
    async def initialize(self):
        """Initialize the agent manager and load agent configurations."""
        if self._initialized:
            return
        
        try:
            # Load agent configurations from database
            await self._load_agent_configs()
            self._initialized = True
            logger.info("Agent manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent manager: {e}")
            # Fallback to default configurations
            await self._load_default_agents()
    
    async def _load_agent_configs(self):
        """Load agent configurations from database."""
        async with get_db_session() as session:
            stmt = select(Agent).where(Agent.is_active == True)
            result = await session.execute(stmt)
            agents = result.scalars().all()
            
            for agent_config in agents:
                await self._create_agent_instance(agent_config)
    
    async def _load_default_agents(self):
        """Load default agent configurations if database is unavailable."""
        from ..models.agent import DEFAULT_AGENTS
        
        for agent_config in DEFAULT_AGENTS:
            # Create a mock agent config object
            mock_config = type('MockAgent', (), agent_config)()
            await self._create_agent_instance(mock_config)
    
    async def _create_agent_instance(self, agent_config: Agent):
        """Create an agent instance from configuration."""
        try:
            agent_type = self._get_agent_type(agent_config)
            if agent_type:
                agent_instance = agent_type(agent_config)
                self._agents[agent_config.handle] = agent_instance
                logger.info(f"Created agent instance: {agent_config.handle}")
            else:
                logger.warning(f"Unknown agent type for {agent_config.handle}")
        except Exception as e:
            logger.error(f"Failed to create agent {agent_config.handle}: {e}")
    
    def _get_agent_type(self, agent_config: Agent) -> Optional[Type[BaseAgent]]:
        """Determine the agent type based on configuration."""
        # Check routing tags for type hints
        routing_tags = getattr(agent_config, 'routing_tags', [])
        
        if "news" in routing_tags or "reporter" in routing_tags:
            return NewsAgent
        elif "quiz" in routing_tags or "master" in routing_tags:
            return QuizAgent
        elif "debate" in routing_tags:
            return DebateAgent
        elif "fun" in routing_tags or "fact" in routing_tags:
            return FunAgent
        else:
            # Default to persona agent
            return PersonaAgent
    
    async def get_agent_by_handle(self, handle: str) -> Optional[BaseAgent]:
        """Get agent by handle."""
        if not self._initialized:
            await self.initialize()
        
        return self._agents.get(handle)
    
    async def get_agent_by_type(self, agent_type: str) -> Optional[BaseAgent]:
        """Get agent by type."""
        if not self._initialized:
            await self.initialize()
        
        for agent in self._agents.values():
            if agent.agent_type == agent_type:
                return agent
        
        return None
    
    async def get_available_agents(self, chat_id: int) -> List[BaseAgent]:
        """Get all available agents for a specific chat."""
        if not self._initialized:
            await self.initialize()
        
        # TODO: Implement chat-specific agent filtering based on configuration
        # For now, return all active agents
        return list(self._agents.values())
    
    async def get_default_agent(self, chat_id: int) -> Optional[BaseAgent]:
        """Get the default agent for a chat."""
        if not self._initialized:
            await self.initialize()
        
        # Try to find a default agent
        for agent in self._agents.values():
            if getattr(agent.config, 'is_default', False):
                return agent
        
        # Fallback to first available persona agent
        for agent in self._agents.values():
            if isinstance(agent, PersonaAgent):
                return agent
        
        # Last resort: return first available agent
        if self._agents:
            return list(self._agents.values())[0]
        
        return None
    
    async def get_agents_by_capability(self, capability: str) -> List[BaseAgent]:
        """Get agents that have a specific capability."""
        if not self._initialized:
            await self.initialize()
        
        capable_agents = []
        for agent in self._agents.values():
            if capability in getattr(agent.config, 'capabilities', []):
                capable_agents.append(agent)
        
        return capable_agents
    
    async def get_agents_by_tag(self, tag: str) -> List[BaseAgent]:
        """Get agents that have a specific routing tag."""
        if not self._initialized:
            await self.initialize()
        
        tagged_agents = []
        for agent in self._agents.values():
            if tag in getattr(agent.config, 'routing_tags', []):
                tagged_agents.append(agent)
        
        return tagged_agents
    
    async def reload_agent(self, handle: str) -> bool:
        """Reload a specific agent configuration."""
        try:
            # Remove existing instance
            if handle in self._agents:
                del self._agents[handle]
            
            # Reload from database
            async with get_db_session() as session:
                stmt = select(Agent).where(Agent.handle == handle, Agent.is_active == True)
                result = await session.execute(stmt)
                agent_config = result.scalar_one_or_none()
                
                if agent_config:
                    await self._create_agent_instance(agent_config)
                    logger.info(f"Reloaded agent: {handle}")
                    return True
                else:
                    logger.warning(f"Agent not found or inactive: {handle}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to reload agent {handle}: {e}")
            return False
    
    async def reload_all_agents(self) -> bool:
        """Reload all agent configurations."""
        try:
            self._agents.clear()
            self._initialized = False
            await self.initialize()
            return True
        except Exception as e:
            logger.error(f"Failed to reload all agents: {e}")
            return False
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        status = {
            "total_agents": len(self._agents),
            "initialized": self._initialized,
            "agents": {}
        }
        
        for handle, agent in self._agents.items():
            status["agents"][handle] = {
                "type": agent.agent_type,
                "active": agent.is_active,
                "capabilities": getattr(agent.config, 'capabilities', []),
                "routing_tags": getattr(agent.config, 'routing_tags', [])
            }
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all agents."""
        health_status = {
            "overall": "healthy",
            "agents": {},
            "errors": []
        }
        
        for handle, agent in self._agents.items():
            try:
                agent_health = await agent.health_check()
                health_status["agents"][handle] = agent_health
                
                if agent_health.get("status") != "healthy":
                    health_status["overall"] = "degraded"
                    health_status["errors"].append(f"Agent {handle}: {agent_health.get('error', 'Unknown error')}")
                    
            except Exception as e:
                health_status["agents"][handle] = {"status": "unhealthy", "error": str(e)}
                health_status["overall"] = "unhealthy"
                health_status["errors"].append(f"Agent {handle}: {str(e)}")
        
        return health_status
