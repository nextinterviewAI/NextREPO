#!/usr/bin/env python3
"""
RAG Verification Script

This script checks if documents were uploaded successfully to Qdrant.
Verifies collection existence, data integrity, and retrieval functionality.
"""

import asyncio
import logging
from services.rag.qdrant_client import client as qdrant_client
from services.rag.retriever_factory import get_rag_retriever
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def verify_collection():
    """
    Verify Qdrant collection and data.
    Checks collection existence and point count.
    """
    try:
        collection_name = "docs"
        
        # Check if collection exists
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if collection_name not in collection_names:
            logger.error(f"Collection '{collection_name}' not found!")
            return False
        
        logger.info(f"✅ Collection '{collection_name}' exists")
        
        # Get collection info
        collection_info = qdrant_client.get_collection(collection_name)
        points_count = collection_info.points_count
        
        logger.info(f"📊 Collection has {points_count} points (chunks)")
        
        if points_count == 0:
            logger.warning("⚠️  Collection is empty!")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying collection: {str(e)}")
        return False

async def test_rag_retrieval():
    """
    Test RAG retrieval functionality.
    Performs a test query to verify the RAG system works correctly.
    """
    try:
        logger.info("Testing RAG retrieval...")
        
        # Get RAG retriever
        retriever = await get_rag_retriever()
        
        # Test query
        test_query = "What is data analysis?"
        logger.info(f"Testing with query: '{test_query}'")
        
        # Retrieve context
        context_chunks = await retriever.retrieve_context(test_query, top_k=3)
        
        if context_chunks:
            logger.info(f"✅ RAG retrieval successful! Found {len(context_chunks)} chunks")
            # Log first 100 characters of each chunk
            for i, chunk in enumerate(context_chunks):
                logger.info(f"Chunk {i+1}: {chunk[:100]}...")
        else:
            logger.warning("⚠️  No context retrieved")
            
        return len(context_chunks) > 0
        
    except Exception as e:
        logger.error(f"Error testing RAG retrieval: {str(e)}")
        return False

async def main():
    """
    Main verification function.
    Orchestrates the verification process for RAG system.
    """
    try:
        logger.info("Starting RAG verification...")
        
        # Verify collection
        collection_ok = await verify_collection()
        
        if not collection_ok:
            logger.error("❌ Collection verification failed!")
            return
        
        # Test RAG retrieval
        retrieval_ok = await test_rag_retrieval()
        
        if not retrieval_ok:
            logger.error("❌ RAG retrieval test failed!")
            return
        
        # Success summary
        logger.info("=" * 50)
        logger.info("✅ RAG VERIFICATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 50)
        logger.info("Your RAG system is ready to use!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ RAG verification failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 