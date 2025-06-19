import faiss
import numpy as np
import numpy.typing as npt
import os
import pickle
import logging
from typing import List, Dict, Any, Tuple
from services.rag.embedding import get_embedding

logger = logging.getLogger(__name__)

DIMENSION = 1536  # OpenAI ada-002 embedding dimension
INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "/tmp/faiss_index")

async def build_index(documents: List[Dict[str, str]]) -> Tuple[faiss.Index, List[str]]:
    """
    Build FAISS index from document texts.
    
    Args:
        documents (List[Dict]): List of {'source', 'text'}
        
    Returns:
        Tuple[faiss.Index, List[str]]: FAISS index and corresponding texts
    """
    logger.info(f"Building FAISS index from {len(documents)} documents")
    
    texts = [doc["text"] for doc in documents]

    # Generate embeddings asynchronously
    embeddings = []
    for i, text in enumerate(texts):
        try:
            embedding = await get_embedding(text)
            if embedding:
                embeddings.append(embedding)
            else:
                logger.warning(f"Empty embedding for document {i}")
        except Exception as e:
            logger.error(f"Error generating embedding for doc {i}: {str(e)}")
            continue

    if not embeddings:
        logger.error("No valid embeddings generated")
        raise ValueError("No valid embeddings were created from the documents")

    # Convert to float32 and reshape if needed
    embedding_array: npt.NDArray[np.float32] = np.array(embeddings).astype("float32")
    logger.info(f"Embedding array shape: {embedding_array.shape}")

    # Ensure correct dimensions
    if len(embedding_array.shape) == 1:
        embedding_array = embedding_array.reshape(1, -1)

    # Build FAISS index
    index = faiss.IndexFlatL2(DIMENSION)
    if embedding_array.ndim == 1:
        embedding_array = embedding_array.reshape(1, -1)
    elif embedding_array.shape[1] != DIMENSION:
        raise ValueError(f"Each embedding must have dimension {DIMENSION}, got {embedding_array.shape[1]}")
    index.add(embedding_array) #type: ignore

    logger.info(f"Index built with {index.ntotal} vectors")
    return index, texts
