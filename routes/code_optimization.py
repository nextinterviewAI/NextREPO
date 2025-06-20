from fastapi import APIRouter, Depends, HTTPException, Body
from services.llm import generate_optimized_code, generate_optimized_code_with_summary
from models.schemas import CodeOptimizationRequest
from services.rag.retriever_factory import get_rag_retriever

router = APIRouter(prefix="/code", tags=["Code Optimization"])

@router.post("/optimize-code")
async def optimize_code(request: CodeOptimizationRequest):
    try:
        # Retrieve RAG context for the question
        retriever = await get_rag_retriever()
        rag_context = ""
        if retriever is not None:
            context_chunks = await retriever.retrieve_context(request.question)
            rag_context = "\n\n".join(context_chunks)
        
        result = await generate_optimized_code_with_summary(
            question=request.question,
            user_code=request.user_code,
            sample_input=request.sample_input,
            sample_output=request.sample_output,
            rag_context=rag_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing code: {str(e)}")