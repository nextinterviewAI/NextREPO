#!/usr/bin/env python3
"""
RAG Precompute Script

This script processes documents from data/ folder and uploads semantic chunks to Qdrant.
Handles document loading, chunking, embedding generation, and vector storage.
"""

import asyncio
import os
import logging
from typing import List, Dict, Any
from services.rag.doc_loader import load_docx_files
from services.rag.embedding import get_embedding
from services.rag.qdrant_client import client as qdrant_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_collection_if_not_exists(collection_name: str = "docs"):
    """
    Create Qdrant collection if it doesn't exist.
    Sets up vector configuration for OpenAI embeddings.
    """
    try:
        # Check if collection exists
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if collection_name not in collection_names:
            logger.info(f"Creating collection: {collection_name}")
            
            # Create collection with vector configuration
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": 1536,  # OpenAI text-embedding-ada-002 dimension
                    "distance": "Cosine"
                }
            )
            logger.info(f"Collection '{collection_name}' created successfully")
        else:
            logger.info(f"Collection '{collection_name}' already exists")
            
    except Exception as e:
        logger.error(f"Error creating collection: {str(e)}")
        raise

async def upload_chunks_to_qdrant(chunks: List[Dict[str, str]], collection_name: str = "docs"):
    """
    Upload document chunks to Qdrant with embeddings.
    Generates embeddings for each chunk and stores with metadata.
    """
    try:
        logger.info(f"Starting upload of {len(chunks)} chunks to Qdrant...")
        
        uploaded_count = 0
        failed_count = 0
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding for the chunk
                embedding = await get_embedding(chunk["text"])
                
                if not embedding:
                    logger.warning(f"Failed to generate embedding for chunk {i}")
                    failed_count += 1
                    continue
                
                # Prepare point for Qdrant
                # Use integer ID as Qdrant only accepts integers or UUIDs
                point = {
                    "id": i,  # Use simple integer ID
                    "vector": embedding,
                    "payload": {
                        "text": chunk["text"],
                        "source": chunk["source"]
                    }
                }
                
                # Upload to Qdrant with retry logic
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        qdrant_client.upsert(
                            collection_name=collection_name,
                            points=[point]
                        )
                        break
                    except Exception as e:
                        if retry == max_retries - 1:
                            raise e
                        logger.warning(f"Retry {retry + 1} for chunk {i}: {str(e)}")
                        await asyncio.sleep(1)  # Wait before retry
                
                uploaded_count += 1
                
                # Log progress every 10 chunks
                if uploaded_count % 10 == 0:
                    logger.info(f"Uploaded {uploaded_count} chunks...")
                    
            except Exception as e:
                logger.error(f"Error uploading chunk {i}: {str(e)}")
                failed_count += 1
        
        logger.info(f"Upload completed: {uploaded_count} successful, {failed_count} failed")
        return uploaded_count, failed_count
        
    except Exception as e:
        logger.error(f"Error in upload process: {str(e)}")
        raise

async def main():
    """
    Main precompute function.
    Orchestrates the entire RAG preprocessing pipeline.
    """
    try:
        # Configuration
        data_dir = "data"
        collection_name = "docs"
        chunk_size = 7500
        
        logger.info("Starting RAG precompute process...")
        
        # Check if data directory exists
        if not os.path.exists(data_dir):
            logger.error(f"Data directory '{data_dir}' not found!")
            return
        
        # Create collection if needed
        await create_collection_if_not_exists(collection_name)
        
        # Load and chunk documents
        logger.info(f"Loading documents from {data_dir}...")
        chunks = load_docx_files(data_dir, chunk_size)
        
        if not chunks:
            logger.warning("No documents found to process!")
            return
        
        logger.info(f"Created {len(chunks)} semantic chunks from documents")
        
        # Upload chunks to Qdrant
        uploaded, failed = await upload_chunks_to_qdrant(chunks, collection_name)
        
        # Summary
        logger.info("=" * 50)
        logger.info("RAG PRECOMPUTE SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total chunks processed: {len(chunks)}")
        logger.info(f"Successfully uploaded: {uploaded}")
        logger.info(f"Failed uploads: {failed}")
        logger.info(f"Collection: {collection_name}")
        logger.info("=" * 50)
        
        if failed == 0:
            logger.info("✅ RAG precompute completed successfully!")
        else:
            logger.warning(f"⚠️  RAG precompute completed with {failed} failures")
            
    except Exception as e:
        logger.error(f"❌ RAG precompute failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 