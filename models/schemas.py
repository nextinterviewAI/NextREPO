from pydantic import BaseModel

class InitRequest(BaseModel):
    topic: str
    user_name: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str

class FeedbackRequest(BaseModel):
    session_id: str
    user_name: str

class CodeOptimizationRequest(BaseModel):
    question: str
    user_code_snippet: str