"""
Research endpoints for Academe API.

Handles document-based research queries using the Research Agent.
"""

import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.v1.deps import get_current_user_id
from core.agents import ResearchAgent
from core.database import UserRepository
from core.models import UserProfile

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class ResearchRequest(BaseModel):
    """Research query request."""
    query: str = Field(..., min_length=1, description="Research question")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    top_k: int = Field(5, ge=1, le=20, description="Number of context chunks to retrieve")
    use_citations: bool = Field(True, description="Include source citations")


class SourceInfo(BaseModel):
    """Source information for citations."""
    document_id: str
    filename: str
    page_number: Optional[int]
    section_title: Optional[str]
    relevance_score: float
    excerpt: str


class ResearchResponse(BaseModel):
    """Research query response."""
    answer: str
    sources: List[SourceInfo]
    agent_used: str
    processing_time_ms: Optional[int]
    conversation_id: Optional[str]


@router.post("/query", response_model=ResearchResponse)
async def research_query(
    request: ResearchRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Answer research questions using RAG-powered Research Agent.
    
    This endpoint:
    1. Searches user's uploaded documents for relevant content
    2. Uses Research Agent to generate coherent answers with citations
    3. Returns formatted answer with source attribution
    
    Args:
        request: Research query and parameters
        current_user_id: Authenticated user ID
        
    Returns:
        Research answer with sources and citations
        
    Raises:
        HTTPException: If user not found or research fails
    """
    try:
        # Get user profile
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(current_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Initialize Research Agent
        research_agent = ResearchAgent()
        
        # Get answer from Research Agent
        import time
        start_time = time.time()
        
        answer = research_agent.answer_question(
            question=request.query,
            user=user,
            use_citations=request.use_citations
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Get sources (if available from agent)
        # For now, we'll do a separate search to get sources
        from core.vectors import SemanticSearchService
        search_service = SemanticSearchService()
        
        search_results = search_service.search(
            query=request.query,
            user_id=current_user_id,
            top_k=request.top_k
        )
        
        # Format sources
        sources = [
            SourceInfo(
                document_id=result.document.id,
                filename=result.document.filename or result.document.original_filename,
                page_number=result.chunk.page_number,
                section_title=result.chunk.section_title,
                relevance_score=result.score,
                excerpt=result.chunk.content[:200] + "..." if len(result.chunk.content) > 200 else result.chunk.content
            )
            for result in search_results
        ]
        
        logger.info(f"Research query processed: {request.query[:50]}... ({len(sources)} sources)")
        
        return ResearchResponse(
            answer=answer,
            sources=sources,
            agent_used="research_agent",
            processing_time_ms=processing_time,
            conversation_id=request.conversation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}"
        )


@router.post("/summarize/{document_id}")
async def summarize_document(
    document_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Generate a summary of a specific document.
    
    Args:
        document_id: Document to summarize
        current_user_id: Authenticated user ID
        
    Returns:
        Document summary
    """
    try:
        user_repo = UserRepository()
        user = user_repo.get_user_by_id(current_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        research_agent = ResearchAgent()
        summary = research_agent.summarize_document(document_id, user)
        
        return {
            "document_id": document_id,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Summarization failed"
        )
