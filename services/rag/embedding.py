from openai import AsyncOpenAI
import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Try to use shared client from utils.py
try:
    from services.llm.utils import client as shared_client
except ImportError:
    # Fallback: create local client if running standalone
    logger.warning("Shared OpenAI client not found - creating local client")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY must be set for embedding generation")
    shared_client = AsyncOpenAI(api_key=openai_api_key)

async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for given text using shared or fallback OpenAI client
    
    Args:
        text (str): Input text to embed
        
    Returns:
        List[float]: Embedding vector or empty list on failure
    """
    try:
        response = await shared_client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        
        if response and response.data and len(response.data) > 0:
            return response.data[0].embedding
        else:
            logger.warning("Empty data returned from OpenAI embeddings API")
            return []
    
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return []