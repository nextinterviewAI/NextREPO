"""
Code Optimization API Routes

This module handles code optimization requests, providing improved code solutions
with explanations and performance enhancements.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from services.code_optimizer import generate_optimized_code, generate_optimized_code_with_summary
from models.schemas import CodeOptimizationRequest
from services.rag.retriever_factory import get_rag_retriever
from services.db import validate_user_id, save_user_ai_interaction

router = APIRouter(tags=["Code Optimization"])

@router.post("/optimize-code")
async def optimize_code(request: CodeOptimizationRequest):
    """
    Optimize user's code with improvements and explanations.
    Uses RAG context to provide relevant optimization suggestions.
    """
    # Validate user exists
    if not await validate_user_id(request.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    try:
        # Get RAG context for relevant optimization suggestions
        retriever = await get_rag_retriever()
        rag_context = ""
        if retriever is not None:
            context_chunks = await retriever.retrieve_context(request.question)
            rag_context = "\n\n".join(context_chunks)
        
        # Generate optimized code with summary
        result = await generate_optimized_code_with_summary(
            question=request.question,
            user_code=request.user_code,
            sample_input=request.sample_input,
            sample_output=request.sample_output,
            rag_context=rag_context
        )
        
        # Save interaction for analytics (non-blocking)
        try:
            await save_user_ai_interaction(
                user_id=request.user_id,
                endpoint="code_optimization",
                input_data=request.dict(),
                ai_response=result
            )
        except Exception as e:
            print(f"Failed to save user-AI interaction: {e}")
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing code: {str(e)}")