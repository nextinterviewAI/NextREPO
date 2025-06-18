from fastapi import APIRouter, Depends, HTTPException, Body
from services.approach_analysis import ApproachAnalysisService
from models.schemas import ApproachAnalysisRequest

router = APIRouter(prefix="/approach", tags=["Approach Analysis"])

analysis_service = ApproachAnalysisService()

@router.post("/analyze-approach")
async def analyze_approach(request: ApproachAnalysisRequest):
    """
    Analyze a user's approach to a question and provide structured feedback.
    """
    try:
        result = await analysis_service.analyze_approach(
            question=request.question,
            user_answer=request.user_answer
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing approach: {str(e)}")