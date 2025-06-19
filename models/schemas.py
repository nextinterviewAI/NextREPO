import asyncio
import numpy as np
from typing import List
import faiss  # Import the full faiss module
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class InterviewInit(BaseModel):
    topic: str
    user_name: str

class InterviewResponse(BaseModel):
    question: str
    answer: str = ""

class AnswerRequest(BaseModel):
    session_id: str
    answer: str
    clarification: bool = False

class ClarificationRequest(BaseModel):
    session_id: str
    question: str

class ApproachAnalysisRequest(BaseModel):
    question: str
    user_answer: str

class CodeOptimizationRequest(BaseModel):
    question: str
    user_code: str
    sample_input: str
    sample_output: str

class FeedbackResponse(BaseModel):
    feedback: str
    strengths: List[str]
    areas_for_improvement: List[str]
    score: int

class RAGRetriever:
    """
    A standalone class for retrieving context from documents.
    Should be initialized with a pre-built index and texts.
    """
    
    def __init__(self, index: faiss.Index, texts: List[str]):
        """
        Initialize with a FAISS index and corresponding document texts
        
        Args:
            index (faiss.Index): Pre-built FAISS index
            texts (List[str]): Original document texts
        """
        self.index = index
        self.texts = texts
        logger.info("RAGRetriever initialized with existing index and texts")

    async def retrieve_context(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve relevant context based on query"""
        try:
            # Generate embedding for query
            from services.rag.embedding import get_embedding
            
            query_embedding = await get_embedding(query)
            if not query_embedding:
                logger.warning("Empty embedding for query")
                return []

            # Convert to numpy array and reshape
            query_vector = np.array([query_embedding]).astype('float32')
            
            # FAISS search - returns distances and indices
            D, I = self.index.search(query_vector, top_k)  # type: ignore
            
            # Map indices to text chunks
            results = []
            for idx in I[0]:
                if 0 <= idx < len(self.texts):
                    results.append(self.texts[idx])
                else:
                    logger.warning(f"Invalid index returned by FAISS: {idx}")
            
            logger.info(f"Retrieved {len(results)} context chunks for query: {query[:100]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []