"""
RAG Services Module

This module provides Retrieval-Augmented Generation (RAG) functionality.
Handles document loading, embedding generation, and intelligent retrieval.
"""

from .retriever import RAGRetriever
from .embedding import get_embedding
from .doc_loader import load_docx_files

__all__ = [
    "RAGRetriever",
    "get_embedding",
    "load_docx_files"
]