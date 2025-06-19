import numpy as np
import logging
from typing import List

from services.rag.vector_store import build_index
from services.rag.doc_loader import load_docx_files
from services.rag.embedding import get_embedding

logger = logging.getLogger(__name__)

class RAGRetriever:
    def __init__(self, data_dir: str = "data/docs"):
        self.data_dir = data_dir
        self.index, self.texts = self._initialize_index()

    def _initialize_index(self):
        """Load docs → generate embeddings → build FAISS index"""
        documents = load_docx_files(self.data_dir)
        logger.info(f"Loaded {len(documents)} documents")
        
        return build_index(documents)

    def retrieve_context(self, query: str, top_k: int = 3) -> List[str]:
        """
        Retrieve most relevant context based on query

        Args:
            query (str): User's question
            top_k (int): Number of context chunks to retrieve

        Returns:
            List[str]: Most similar document chunks
        """
        try:
            query_vector = np.array(get_embedding(query)).astype("float32").reshape(1, -1)
            D, I = self.index.search(query_vector, top_k)
            
            results = [self.texts[i] for i in I[0]]
            logger.info(f"Retrieved {len(results)} context chunks for query: {query[:100]}...")
            return results
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []