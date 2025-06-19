from fastapi import APIRouter, HTTPException
from models.schemas import RAGRetriever
from services.rag.doc_loader import load_docx_files
from services.rag.vector_store import build_index 
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])

# Global variable to store the retriever
rag_retriever: Optional[RAGRetriever] = None

async def initialize_rag_retriever():
    """Initialize the RAG retriever with documents from data directory"""
    global rag_retriever
    
    if rag_retriever is not None:
        return rag_retriever
    
    try:
        data_dir = "data/docs"
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"Data directory {data_dir} does not exist")
        
        # Load documents using your existing doc_loader
        documents = load_docx_files(data_dir)
        
        if not documents:
            raise ValueError("No valid documents found in data directory")
        
        # Build the FAISS index using your existing vector_store
        index, texts = await build_index(documents)
        
        # Initialize the retriever
        rag_retriever = RAGRetriever(index=index, texts=texts)
        logger.info(f"RAG retriever initialized with {len(texts)} documents")
        
        return rag_retriever
        
    except Exception as e:
        logger.error(f"Error initializing RAG retriever: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize RAG system: {str(e)}")

@router.post("/retrieve")
async def retrieve_context(question: str):
    """Test endpoint to retrieve context before sending to LLM"""
    try:
        # Initialize retriever if not already done
        retriever = await initialize_rag_retriever()
        
        # Retrieve context
        context = await retriever.retrieve_context(question)
        
        return {
            "question": question,
            "context": context,
            "context_count": len(context)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving context: {str(e)}")

@router.get("/status")
async def get_rag_status():
    """Get the status of the RAG system"""
    global rag_retriever
    
    if rag_retriever is None:
        return {"status": "not_initialized", "message": "RAG system not initialized"}
    
    return {
        "status": "initialized",
        "document_count": len(rag_retriever.texts),
        "index_total": rag_retriever.index.ntotal
    }