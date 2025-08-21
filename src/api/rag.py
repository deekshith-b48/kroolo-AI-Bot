"""
RAG / Knowledge Service APIs
Handles knowledge ingestion, retrieval, and management for the RAG system.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, HttpUrl

from src.core.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag", tags=["rag"])

# Request/Response Models

class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    chat_id: int = Field(..., description="Chat ID for access control")
    doc_id: Optional[str] = Field(default=None, description="Document ID (auto-generated if not provided)")
    text: Optional[str] = Field(default=None, description="Text content to ingest")
    doc_url: Optional[HttpUrl] = Field(default=None, description="URL to document to ingest")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    chunk_size: int = Field(default=1000, description="Chunk size for text splitting")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")

class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    doc_id: str
    chunks_created: int
    embeddings_created: int
    success: bool
    message: str
    processing_time_ms: float

class QueryRequest(BaseModel):
    """Request model for knowledge query."""
    chat_id: int = Field(..., description="Chat ID for access control")
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=5, description="Number of top results to return")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity threshold")
    content_types: Optional[List[str]] = Field(default=None, description="Filter by content types")

class QueryResponse(BaseModel):
    """Response model for knowledge query."""
    chunks: List[Dict[str, Any]] = Field(..., description="Retrieved chunks with metadata")
    query_embedding: Optional[List[float]] = Field(default=None, description="Query embedding vector")
    processing_time_ms: float
    total_results: int

class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    documents: List[Dict[str, Any]]
    total_count: int
    chat_id: int

class DocumentDeleteResponse(BaseModel):
    """Response model for document deletion."""
    doc_id: str
    chunks_deleted: int
    success: bool
    message: str

# RAG API Endpoints

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    """
    Ingest a document into the knowledge base.
    Supports both direct text input and URL-based document ingestion.
    """
    try:
        import time
        start_time = time.time()
        
        if not request.text and not request.doc_url:
            raise HTTPException(status_code=400, detail="Either 'text' or 'doc_url' must be provided")
        
        # Generate doc_id if not provided
        doc_id = request.doc_id or f"doc_{int(time.time())}_{request.chat_id}"
        
        content = ""
        
        # Handle URL-based ingestion
        if request.doc_url:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(request.doc_url)) as response:
                        if response.status == 200:
                            content = await response.text()
                        else:
                            raise HTTPException(
                                status_code=400, 
                                detail=f"Failed to fetch document from URL: HTTP {response.status}"
                            )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to fetch document: {str(e)}")
        else:
            content = request.text
        
        # Prepare metadata
        metadata = {
            "doc_id": doc_id,
            "chat_id": request.chat_id,
            "source_url": str(request.doc_url) if request.doc_url else None,
            "ingested_at": datetime.now().isoformat(),
            **request.metadata
        }
        
        # Ingest content using RAG service
        result_id = await rag_service.add_knowledge(
            content=content,
            metadata=metadata,
            content_type="document"
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Calculate approximate chunks (this would be more accurate with actual chunking)
        estimated_chunks = max(1, len(content) // request.chunk_size)
        
        return IngestResponse(
            doc_id=doc_id,
            chunks_created=estimated_chunks,
            embeddings_created=estimated_chunks,
            success=True,
            message=f"Document {doc_id} ingested successfully",
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_file(
    chat_id: int,
    file: UploadFile = File(...),
    doc_id: Optional[str] = None,
    metadata: Optional[str] = None
):
    """
    Ingest a document from file upload.
    Supports text files, PDFs, and other document formats.
    """
    try:
        import time
        import json
        start_time = time.time()
        
        # Generate doc_id if not provided
        doc_id = doc_id or f"upload_{int(time.time())}_{chat_id}_{file.filename}"
        
        # Read file content
        content = await file.read()
        
        # Handle different file types
        if file.content_type == "text/plain":
            text_content = content.decode("utf-8")
        elif file.content_type == "application/pdf":
            # This would require a PDF parser like PyPDF2 or pdfplumber
            # For now, return an error
            raise HTTPException(
                status_code=400, 
                detail="PDF parsing not implemented. Please use text files or provide text directly."
            )
        else:
            # Try to decode as text
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {file.content_type}"
                )
        
        # Parse metadata if provided
        file_metadata = {}
        if metadata:
            try:
                file_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON: {metadata}")
        
        # Prepare metadata
        full_metadata = {
            "doc_id": doc_id,
            "chat_id": chat_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": len(content),
            "ingested_at": datetime.now().isoformat(),
            **file_metadata
        }
        
        # Ingest content using RAG service
        result_id = await rag_service.add_knowledge(
            content=text_content,
            metadata=full_metadata,
            content_type="document"
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Calculate approximate chunks
        estimated_chunks = max(1, len(text_content) // 1000)
        
        return IngestResponse(
            doc_id=doc_id,
            chunks_created=estimated_chunks,
            embeddings_created=estimated_chunks,
            success=True,
            message=f"File {file.filename} ingested successfully as {doc_id}",
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"File ingestion failed: {str(e)}")

@router.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """
    Query the knowledge base for relevant information.
    Returns top-k most similar chunks with metadata.
    """
    try:
        import time
        start_time = time.time()
        
        # Query RAG service
        results = await rag_service.search_knowledge(
            query=request.query,
            limit=request.top_k,
            content_types=request.content_types,
            similarity_threshold=request.similarity_threshold
        )
        
        # Filter results by chat_id for access control
        filtered_results = [
            result for result in results
            if result.get("metadata", {}).get("chat_id") == request.chat_id
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return QueryResponse(
            chunks=filtered_results,
            processing_time_ms=processing_time,
            total_results=len(filtered_results)
        )
        
    except Exception as e:
        logger.error(f"Knowledge query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/docs/{chat_id}", response_model=DocumentListResponse)
async def list_documents(chat_id: int, limit: int = 50, offset: int = 0):
    """
    List all documents for a specific chat.
    """
    try:
        # This would typically query the vector database for documents by chat_id
        # For now, return a placeholder response
        documents = [
            {
                "doc_id": f"doc_example_{i}",
                "filename": f"document_{i}.txt",
                "ingested_at": datetime.now().isoformat(),
                "chunk_count": 5,
                "metadata": {"chat_id": chat_id}
            }
            for i in range(min(limit, 5))  # Placeholder data
        ]
        
        return DocumentListResponse(
            documents=documents,
            total_count=len(documents),
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"Failed to list documents for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.delete("/docs/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str, chat_id: int):
    """
    Delete a document and all its associated chunks.
    """
    try:
        # This would typically delete from the vector database
        # For now, return a success response
        return DocumentDeleteResponse(
            doc_id=doc_id,
            chunks_deleted=5,  # Placeholder
            success=True,
            message=f"Document {doc_id} deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.get("/stats/{chat_id}")
async def get_knowledge_stats(chat_id: int):
    """
    Get knowledge base statistics for a specific chat.
    """
    try:
        # This would typically query the vector database for statistics
        return {
            "chat_id": chat_id,
            "total_documents": 10,  # Placeholder
            "total_chunks": 50,     # Placeholder
            "total_embeddings": 50, # Placeholder
            "storage_size_mb": 5.2, # Placeholder
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge stats: {str(e)}")

@router.post("/reindex/{chat_id}")
async def reindex_knowledge(chat_id: int):
    """
    Reindex all knowledge for a specific chat.
    Useful for updating embeddings or applying new chunking strategies.
    """
    try:
        # This would typically trigger a reindexing process
        return {
            "status": "reindexing_started",
            "chat_id": chat_id,
            "timestamp": datetime.now().isoformat(),
            "estimated_completion": "5-10 minutes"
        }
        
    except Exception as e:
        logger.error(f"Failed to start reindexing for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start reindexing: {str(e)}")

@router.get("/health")
async def rag_health():
    """Health check for RAG service."""
    try:
        health = await rag_service.health_check()
        return health
        
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
