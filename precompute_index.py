import asyncio
from services.rag.doc_loader import load_docx_files
from services.rag.vector_store import build_index, save_index
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = "data/docs"
INDEX_SAVE_PATH = "data/rag/faiss_index"

async def main():
    try:
        logger.info(f"Loading documents from {DATA_DIR}")
        documents = load_docx_files(DATA_DIR)

        if not documents:
            logger.error("No valid documents found")
            raise ValueError("No valid .docx files found")

        logger.info(f"Building FAISS index from {len(documents)} documents")
        index, texts = await build_index(documents)

        logger.info(f"Saving index and texts to {INDEX_SAVE_PATH}")
        save_index(index, texts, path=INDEX_SAVE_PATH)

        logger.info("RAG index precomputed and saved successfully")
    
    except Exception as e:
        logger.error(f"Error in precompute: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())