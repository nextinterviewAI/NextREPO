import faiss
import numpy as np
import pickle
import os
import logging

logger = logging.getLogger(__name__)

DIMENSION = 1536  # OpenAI ada-002 embedding dimension
INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "/tmp/faiss_index")

def build_index(documents):
    """
    Build FAISS index from document texts.

    Args:
        documents (List[Dict]): List of {'source', 'text'}

    Returns:
        faiss.Index: FAISS index object
        List[str]: List of corresponding texts
    """
    index = faiss.IndexFlatL2(DIMENSION)

    texts = [doc["text"] for doc in documents]
    embeddings = [get_embedding(text) for text in texts]

    # Convert to numpy array
    embedding_array = np.array(embeddings).astype("float32")
    index.add(embedding_array)

    logger.info(f"Index built with {index.ntotal} vectors")
    return index, texts