from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# === Interview Models ===

class InterviewInit(BaseModel):
    topic: str
    user_name: str

class InterviewResponse(BaseModel):
    question: str
    answer: str = ""

class AnswerRequest(BaseModel):
    session_id: str
    answer: str
    clarification: bool = False

class ClarificationRequest(BaseModel):
    session_id: str
    question: str

class ApproachAnalysisRequest(BaseModel):
    question: str
    user_answer: str


class CodeOptimizationRequest(BaseModel):
    question: str
    user_code: str
    sample_input: str
    sample_output: str


class FeedbackResponse(BaseModel):
    feedback: str
    strengths: List[str]
    areas_for_improvement: List[str]
    score: int