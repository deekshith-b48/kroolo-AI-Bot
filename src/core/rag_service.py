"""
RAG (Retrieval Augmented Generation) service for the Kroolo AI Bot.
Handles vector database operations, semantic search, and knowledge retrieval.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import hashlib

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logging.warning("Qdrant client not available. RAG service will be limited.")

from config.settings import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval Augmented Generation operations."""
    
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.collection_name = "kroolo_knowledge"
        self.vector_size = 768  # Default for many embedding models
        self.is_initialized = False
        
        # Cache for embeddings
        self.embedding_cache = {}
        self.cache_size_limit = 1000
        
        logger.info("RAG service initialized")
    
    async def initialize(self):
        """Initialize the RAG service."""
        try:
            if not QDRANT_AVAILABLE:
                logger.warning("Qdrant not available. RAG service will be limited.")
                return
            
            # Initialize Qdrant client
            self.client = QdrantClient(
                url=settings.qdrant_url,
                timeout=10.0
            )
            
            # Test connection
            await self._test_connection()
            
            # Initialize embedding model
            await self._initialize_embedding_model()
            
            # Ensure collection exists
            await self._ensure_collection()
            
            self.is_initialized = True
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            self.is_initialized = False
    
    async def _test_connection(self):
        """Test connection to Qdrant."""
        try:
            # Get collections info
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant. Found {len(collections.collections)} collections")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    async def _initialize_embedding_model(self):
        """Initialize the sentence embedding model."""
        try:
            # Use a lightweight model for production
            model_name = getattr(settings, 'embedding_model', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
            
            logger.info(f"Embedding model initialized: {model_name} (vector size: {self.vector_size})")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # Fallback to a basic model
            try:
                self.embedding_model = SentenceTransformer('paraphrase-MiniLM-L3-v2')
                self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
                logger.info(f"Fallback embedding model initialized")
            except Exception as fallback_error:
                logger.error(f"Failed to initialize fallback embedding model: {fallback_error}")
                raise
    
    async def _ensure_collection(self):
        """Ensure the knowledge collection exists."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise
    
    async def add_knowledge(self, content: str, metadata: Dict[str, Any], 
                           content_type: str = "text") -> str:
        """
        Add knowledge content to the vector database.
        
        Args:
            content: The text content to store
            metadata: Additional metadata about the content
            content_type: Type of content (text, news, fact, etc.)
            
        Returns:
            Content ID
        """
        try:
            if not self.is_initialized:
                raise RuntimeError("RAG service not initialized")
            
            # Generate content ID
            content_hash = hashlib.md5(content.encode()).hexdigest()
            content_id = f"{content_type}_{content_hash[:8]}"
            
            # Generate embedding
            embedding = await self._get_embedding(content)
            
            # Prepare point data
            point = PointStruct(
                id=content_id,
                vector=embedding.tolist(),
                payload={
                    "content": content,
                    "content_type": content_type,
                    "metadata": metadata,
                    "created_at": datetime.now().isoformat(),
                    "embedding_model": self.embedding_model.get_model_name() if self.embedding_model else "unknown"
                }
            )
            
            # Add to collection
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Added knowledge content: {content_id}")
            return content_id
            
        except Exception as e:
            logger.error(f"Failed to add knowledge: {e}")
            raise
    
    async def search_knowledge(self, query: str, limit: int = 5, 
                              content_types: Optional[List[str]] = None,
                              similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Search for relevant knowledge based on a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            content_types: Filter by content types
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant content items
        """
        try:
            if not self.is_initialized:
                logger.warning("RAG service not initialized. Returning empty results.")
                return []
            
            # Generate query embedding
            query_embedding = await self._get_embedding(query)
            
            # Prepare search parameters
            search_params = {
                "query_vector": query_embedding.tolist(),
                "limit": limit,
                "with_payload": True,
                "with_vectors": False
            }
            
            # Add filters if content types specified
            if content_types:
                search_params["query_filter"] = Filter(
                    must=[
                        FieldCondition(
                            key="content_type",
                            match=MatchValue(value=content_type)
                        ) for content_type in content_types
                    ]
                )
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                **search_params
            )
            
            # Process results
            results = []
            for result in search_results:
                if result.score >= similarity_threshold:
                    results.append({
                        "id": result.id,
                        "content": result.payload["content"],
                        "content_type": result.payload["content_type"],
                        "metadata": result.payload["metadata"],
                        "similarity_score": result.score,
                        "created_at": result.payload.get("created_at")
                    })
            
            logger.info(f"Search query '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search knowledge: {e}")
            return []
    
    async def get_context_for_agent(self, query: str, agent_context: Dict[str, Any], 
                                   max_results: int = 3) -> str:
        """
        Get relevant context for an AI agent based on the query.
        
        Args:
            query: User query
            agent_context: Agent context information
            max_results: Maximum number of context items
            
        Returns:
            Formatted context string
        """
        try:
            # Get relevant knowledge
            results = await self.search_knowledge(
                query=query,
                limit=max_results,
                similarity_threshold=0.6
            )
            
            if not results:
                return ""
            
            # Format context
            context_parts = []
            for i, result in enumerate(results, 1):
                content_type = result["content_type"]
                content = result["content"]
                score = result["similarity_score"]
                
                context_parts.append(f"{i}. [{content_type.upper()}] {content} (relevance: {score:.2f})")
            
            context = "\n\n".join(context_parts)
            
            # Add metadata if available
            if results and results[0].get("metadata"):
                metadata = results[0]["metadata"]
                if metadata.get("source"):
                    context += f"\n\nSource: {metadata['source']}"
                if metadata.get("date"):
                    context += f"\nDate: {metadata['date']}"
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context for agent: {e}")
            return ""
    
    async def add_news_article(self, title: str, content: str, summary: str, 
                              source: str, category: str, tags: List[str]) -> str:
        """Add a news article to the knowledge base."""
        metadata = {
            "title": title,
            "summary": summary,
            "source": source,
            "category": category,
            "tags": tags,
            "content_length": len(content),
            "type": "news_article"
        }
        
        # Combine title and content for better search
        searchable_content = f"{title}\n\n{summary}\n\n{content}"
        
        return await self.add_knowledge(
            content=searchable_content,
            metadata=metadata,
            content_type="news"
        )
    
    async def add_fun_fact(self, fact: str, category: str, source: str, 
                          tags: List[str]) -> str:
        """Add a fun fact to the knowledge base."""
        metadata = {
            "category": category,
            "source": source,
            "tags": tags,
            "type": "fun_fact"
        }
        
        return await self.add_knowledge(
            content=fact,
            metadata=metadata,
            content_type="fact"
        )
    
    async def add_quiz_question(self, question: str, options: List[str], 
                               correct_answer: str, explanation: str,
                               category: str, difficulty: str) -> str:
        """Add a quiz question to the knowledge base."""
        metadata = {
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "category": category,
            "difficulty": difficulty,
            "type": "quiz_question"
        }
        
        # Combine question and explanation for search
        searchable_content = f"{question}\n\nExplanation: {explanation}"
        
        return await self.add_knowledge(
            content=searchable_content,
            metadata=metadata,
            content_type="quiz"
        )
    
    async def add_debate_topic(self, topic: str, description: str, 
                              arguments_for: List[str], arguments_against: List[str],
                              category: str) -> str:
        """Add a debate topic to the knowledge base."""
        metadata = {
            "description": description,
            "arguments_for": arguments_for,
            "arguments_against": arguments_against,
            "category": category,
            "type": "debate_topic"
        }
        
        # Combine topic and description for search
        searchable_content = f"{topic}\n\n{description}"
        
        return await self.add_knowledge(
            content=searchable_content,
            metadata=metadata,
            content_type="debate"
        )
    
    async def _get_embedding(self, text: str):
        """Get embedding for text, using cache if available."""
        try:
            # Check cache first
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash in self.embedding_cache:
                return self.embedding_cache[text_hash]
            
            # Generate new embedding
            if self.embedding_model:
                embedding = self.embedding_model.encode(text)
                
                # Cache the embedding
                if len(self.embedding_cache) < self.cache_size_limit:
                    self.embedding_cache[text_hash] = embedding
                
                return embedding
            else:
                raise RuntimeError("Embedding model not available")
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            import numpy as np
            return np.zeros(self.vector_size)
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        try:
            if not self.is_initialized:
                return {"error": "RAG service not initialized"}
            
            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)
            
            # Count by content type
            content_type_counts = {}
            try:
                # This is a simplified approach - in production you'd want more efficient aggregation
                all_points = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=1000,
                    with_payload=True
                )
                
                for point in all_points[0]:
                    content_type = point.payload.get("content_type", "unknown")
                    content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
                    
            except Exception as e:
                logger.warning(f"Could not get detailed stats: {e}")
                content_type_counts = {"error": "Could not retrieve"}
            
            stats = {
                "total_points": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance.value,
                "content_type_distribution": content_type_counts,
                "embedding_model": self.embedding_model.get_model_name() if self.embedding_model else "unknown",
                "cache_size": len(self.embedding_cache),
                "is_initialized": self.is_initialized
            }
            
            return stats
            
        except Exception as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def clear_knowledge_base(self, content_type: Optional[str] = None):
        """Clear the knowledge base or specific content type."""
        try:
            if not self.is_initialized:
                raise RuntimeError("RAG service not initialized")
            
            if content_type:
                # Delete specific content type
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="content_type",
                                match=MatchValue(value=content_type)
                            )
                        ]
                    )
                )
                logger.info(f"Cleared content type: {content_type}")
            else:
                # Clear entire collection
                self.client.delete_collection(self.collection_name)
                await self._ensure_collection()
                logger.info("Cleared entire knowledge base")
                
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the RAG service."""
        try:
            if not self.is_initialized:
                return {
                    "status": "not_initialized",
                    "error": "RAG service not initialized"
                }
            
            # Test Qdrant connection
            try:
                collections = self.client.get_collections()
                qdrant_status = "healthy"
            except Exception as e:
                qdrant_status = "unhealthy"
                qdrant_error = str(e)
            
            # Test embedding model
            try:
                test_embedding = await self._get_embedding("test")
                embedding_status = "healthy"
                embedding_vector_size = len(test_embedding)
            except Exception as e:
                embedding_status = "unhealthy"
                embedding_error = str(e)
                embedding_vector_size = None
            
            health_status = {
                "status": "healthy" if qdrant_status == "healthy" and embedding_status == "healthy" else "unhealthy",
                "qdrant": {
                    "status": qdrant_status,
                    "error": qdrant_error if qdrant_status == "unhealthy" else None
                },
                "embedding_model": {
                    "status": embedding_status,
                    "vector_size": embedding_vector_size,
                    "error": embedding_error if embedding_status == "unhealthy" else None
                },
                "collection": self.collection_name,
                "cache_size": len(self.embedding_cache),
                "is_initialized": self.is_initialized
            }
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def shutdown(self):
        """Shutdown the RAG service."""
        try:
            if self.client:
                self.client.close()
            logger.info("RAG service shutdown")
        except Exception as e:
            logger.error(f"Error during RAG service shutdown: {e}")


# Global RAG service instance
rag_service = RAGService()
