from fastapi import APIRouter, Depends, HTTPException, Body
from services.llm import generate_optimized_code
from models.schemas import CodeOptimizationRequest

router = APIRouter(prefix="/code", tags=["Code Optimization"])

@router.post("/optimize-code")
async def optimize_code(request: CodeOptimizationRequest):
    try:
        optimized_code = await generate_optimized_code(
            question=request.question,
            user_code=request.user_code,
            sample_input=request.sample_input,
            sample_output=request.sample_output
        )
        return {"optimized_code": optimized_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing code: {str(e)}")