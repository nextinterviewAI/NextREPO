import os
import logging
import asyncio
from typing import Optional
from models.schemas import RAGRetriever
from services.rag.doc_loader import load_docx_files
from services.rag.vector_store import build_index, save_index

logger = logging.getLogger(__name__)

# Global retriever instance
_rag_retriever = None

async def initialize_rag_retriever(data_dir: str = "data/docs"):
    global _rag_retriever
    
    if _rag_retriever is not None:
        return _rag_retriever

    try:
        # Load documents
        logger.info(f"Loading documents from {data_dir}")
        documents = load_docx_files(data_dir)
        
        if not documents:
            raise ValueError("No valid .docx files found")
        
        documents = load_docx_files(data_dir)
    
        if not documents:
            raise ValueError(f"No valid documents found in {data_dir}")
        
        index, texts = await build_index(documents)
        _rag_retriever = RAGRetriever(index=index, texts=texts)
        logger.info(f"RAGRetriever initialized with {len(texts)} document chunks")
        return _rag_retriever

    except Exception as e:
        logger.error(f"Error initializing RAGRetriever: {str(e)}")
        raise

async def get_rag_retriever(force_rebuild: bool = False, data_dir: str = "data/docs") -> RAGRetriever:
    """
    Get or create a RAG retriever instance
    
    Args:
        force_rebuild (bool): If True, rebuild the index even if retriever exists
        
    Returns:
        RAGRetriever: Initialized retriever instance
        
    Raises:
        FileNotFoundError: If data directory doesn't exist
        ValueError: If no valid documents found
        Exception: For other initialization errors
    """
    global _rag_retriever
    
    # Return existing retriever if available and not forcing rebuild
    if _rag_retriever is not None and not force_rebuild:
        logger.info("Returning existing RAG retriever instance")
        return _rag_retriever
    
    try:
        logger.info("Initializing RAG retriever...")
        
        # Check data directory
        data_dir = os.getenv("RAG_DATA_DIR", "data/docs")
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"Data directory {data_dir} does not exist")
        
        logger.info(f"Loading documents from: {data_dir}")
        
        # Load documents
        documents = load_docx_files(data_dir)
        
        if not documents:
            raise ValueError(f"No valid documents found in {data_dir}")
        
        logger.info(f"Loaded {len(documents)} documents")
        
        # Build FAISS index
        logger.info("Building FAISS index...")
        index, texts = await build_index(documents)
        
        if not texts:
            raise ValueError("No texts extracted from documents")
        
        logger.info(f"Built index with {len(texts)} text chunks")
        
        # Create retriever instance
        _rag_retriever = RAGRetriever(index=index, texts=texts)
        
        logger.info("RAG retriever initialized successfully")
        return _rag_retriever
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG retriever: {str(e)}")
        raise

def get_retriever():
    if _rag_retriever is None:
        raise RuntimeError("RAGRetriever not initialized. Call initialize_rag_retriever() first.")
    return _rag_retriever

def get_retriever_status() -> dict:
    """
    Get the current status of the RAG retriever
    
    Returns:
        dict: Status information
    """
    global _rag_retriever
    
    if _rag_retriever is None:
        return {
            "initialized": False,
            "message": "RAG retriever not initialized"
        }
    
    return {
        "initialized": True,
        "document_count": len(_rag_retriever.texts),
        "index_total": _rag_retriever.index.ntotal,
        "message": "RAG retriever ready"
    }

async def rebuild_rag_retriever() -> RAGRetriever:
    """
    Force rebuild the RAG retriever
    
    Returns:
        RAGRetriever: Newly built retriever instance
    """
    logger.info("Force rebuilding RAG retriever...")
    return await get_rag_retriever(force_rebuild=True)