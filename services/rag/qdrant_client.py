"""
Qdrant Vector Database Client Module

This module provides connection to Qdrant vector database for RAG operations.
Handles vector storage and retrieval for document embeddings.
"""

import os
from qdrant_client import QdrantClient

# Get Qdrant configuration from environment variables
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

if not QDRANT_URL:
    raise ValueError("QDRANT_URL must be set in environment variables.")

# Initialize Qdrant client
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)