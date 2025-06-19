from fastapi import APIRouter
from services.rag.retriever import RAGRetriever

router = APIRouter(prefix="/rag", tags=["RAG"])

rag_retriever = RAGRetriever(data_dir="data/docs")

@router.post("/retrieve")
async def retrieve_context(question: str):
    """Test endpoint to retrieve context before sending to LLM"""
    context = rag_retriever.retrieve_context(question)
    return {
        "question": question,
        "context": context
    }