import faiss
import numpy as np
import numpy.typing as npt
import os
import pickle
import logging
from typing import List, Dict, Any, Tuple
from services.rag.embedding import get_embedding

logger = logging.getLogger(__name__)

DIMENSION = 1536  
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

# services/rag/vector_store.py

def save_index(index: faiss.Index, texts: list, path: str = "/tmp/faiss_index"):
    """Save FAISS index and texts to disk"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Save FAISS index
        faiss.write_index(index, f"{path}.faiss")

        # Save document texts
        with open(f"{path}_texts.pkl", "wb") as f:
            pickle.dump(texts, f)

        logger.info(f"FAISS index and texts saved to {path}")
    except Exception as e:
        logger.error(f"Error saving index: {str(e)}")
        raise

def load_index(path: str = "/tmp/faiss_index"):
    """Load FAISS index and texts from disk"""
    try:
        if not os.path.exists(f"{path}.faiss") or not os.path.exists(f"{path}_texts.pkl"):
            raise FileNotFoundError("FAISS index or texts file not found")

        index = faiss.read_index(f"{path}.faiss")
        with open(f"{path}_texts.pkl", "rb") as f:
            texts = pickle.load(f)

        logger.info(f"Loaded FAISS index with {index.ntotal} vectors")
        return index, texts
    except Exception as e:
        logger.error(f"Error loading index: {str(e)}")
        raise