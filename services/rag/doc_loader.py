from docx import Document
import os
import logging

logger = logging.getLogger(__name__)

def load_docx_files(data_dir: str):
    """
    Load all .docx files from a directory and return as text chunks.
    
    Args:
        data_dir (str): Path to folder containing .docx files
    
    Returns:
        List[Dict]: List of documents with 'source' and 'text'
    """
    documents = []
    
    if not os.path.exists(data_dir):
        logger.error(f"Document directory does not exist: {data_dir}")
        raise FileNotFoundError(f"Directory not found: {data_dir}")
    
    for filename in os.listdir(data_dir):
        if filename.endswith(".docx"):
            try:
                doc = Document(os.path.join(data_dir, filename))
                full_text = "\n".join([para.text for para in doc.paragraphs])
                
                # Split into chunks if needed
                documents.append({
                    "source": filename,
                    "text": full_text
                })
            except Exception as e:
                logger.warning(f"Error reading {filename}: {str(e)}")
    
    logger.info(f"Loaded {len(documents)} documents")
    return documents