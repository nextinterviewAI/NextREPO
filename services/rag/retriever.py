import numpy as np
import logging
from typing import List

from services.rag.embedding import get_embedding

logger = logging.getLogger(__name__)

class RAGRetriever:
    def __init__(self, index, texts):
        self.index = index
        self.texts = texts

    async def retrieve_context(self, query: str, top_k: int = 3) -> List[str]:
        """
        Retrieve most relevant context based on query

        Args:
            query (str): User's question
            top_k (int): Number of chunks to retrieve

        Returns:
            List[str]: Top K similar document chunks
        """
        try:
            # Generate embedding for query
            query_embedding = await get_embedding(query)

            if not query_embedding:
                logger.warning("Empty embedding for query")
                return []

            # Convert to numpy array and normalize
            query_vector = np.array([query_embedding]).astype("float32")

            # Search FAISS index
            results = self.index.search(query_vector, top_k)
            distances, indices = results[0], results[1]

            # Map indices to document texts
            valid_indices = [idx for idx in indices[0] if 0 <= idx < len(self.texts)]
            results = [self.texts[idx] for idx in valid_indices]
            
            logger.info(f"Retrieved {len(results)} context chunks for query: {query[:100]}...")
            return results

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}", exc_info=True)
            return []