from fastapi import APIRouter, Depends, HTTPException, Body
from services.approach_analysis import ApproachAnalysisService
from models.schemas import ApproachAnalysisRequest
from services.db import validate_user_id, save_user_ai_interaction

router = APIRouter(prefix="/approach", tags=["Approach Analysis"])

analysis_service = ApproachAnalysisService()

@router.post("/analyze-approach")
async def analyze_approach(request: ApproachAnalysisRequest):
    """
    Analyze a user's approach to a question and provide structured feedback.
    """
    # Validate user_id
    if not await validate_user_id(request.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    try:
        result = await analysis_service.analyze_approach(
            question=request.question,
            user_answer=request.user_answer,
            user_id=request.user_id
        )
        # Save interaction (do not block response)
        try:
            await save_user_ai_interaction(
                user_id=request.user_id,
                endpoint="approach_analysis",
                input_data=request.dict(),
                ai_response=result
            )
        except Exception as e:
            print(f"Failed to save user-AI interaction: {e}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing approach: {str(e)}")