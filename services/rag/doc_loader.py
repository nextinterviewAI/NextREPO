from docx import Document
import os
import logging
import re
from typing import List, Dict, Any
from services.llm.utils import is_valid_for_embedding

# Import spaCy for semantic chunking
# Note: Install spaCy model with: python -m spacy download en_core_web_sm
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None

logger = logging.getLogger(__name__)

def create_semantic_chunks(text: str, max_chunk_size: int = 7500) -> List[str]:
    """
    Create semantically coherent chunks from text using NLP
    """
    if not SPACY_AVAILABLE or not text.strip():
        # Fallback to simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk + " " + sentence) <= max_chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    # Use spaCy for semantic chunking
    doc = nlp(text)
    chunks = []
    current_chunk = ""
    
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue
            
        # Check if adding this sentence would exceed chunk size
        if len(current_chunk + " " + sent_text) <= max_chunk_size:
            current_chunk += " " + sent_text if current_chunk else sent_text
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sent_text
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def load_docx_files(data_dir: str, chunk_size: int = 7500) -> List[Dict[str, str]]:
    """
    Load all .docx files from a directory and split large texts into chunks.
    
    Args:
        data_dir (str): Path to folder containing .docx files
        chunk_size (int): Max token size per chunk for embedding compatibility
    
    Returns:
        List[Dict]: List of document chunks with 'source' and 'text'
    """
    documents = []
    
    if not os.path.exists(data_dir):
        logger.error(f"Document directory does not exist: {data_dir}")
        raise FileNotFoundError(f"Directory not found: {data_dir}")

    logger.info(f"Loading .docx files from {data_dir}")
    
    for filename in os.listdir(data_dir):
        if filename.endswith(".docx"):
            file_path = os.path.join(data_dir, filename)
            try:
                # Load document
                doc = Document(file_path)
                full_text = "\n".join([para.text for para in doc.paragraphs])

                # Create semantic chunks
                semantic_chunks = create_semantic_chunks(full_text, chunk_size)
                num_chunks = len(semantic_chunks)

                logger.info(f"Processing {filename} - creating {num_chunks} semantic chunks")
                
                for i, chunk in enumerate(semantic_chunks):
                    if not is_valid_for_embedding(chunk):
                        logger.warning(f"Skipping oversized chunk from {filename}")
                        continue
                    
                    documents.append({
                        "source": f"{filename}-chunk{i}",
                        "text": chunk
                    })

                logger.info(f"Loaded {num_chunks} chunks from {filename}")
            except Exception as e:
                logger.warning(f"Error reading {filename}: {str(e)}")
    
    logger.info(f"Successfully loaded {len(documents)} document chunks")
    return documents