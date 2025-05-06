from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from services.db import get_db, fetch_base_question, save_session_data, get_available_topics
from services.llm import get_next_question, get_feedback
from pydantic import BaseModel
import logging
from datetime import datetime
import io
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a StringIO handler to capture logs
log_capture_string = io.StringIO()
handler = logging.StreamHandler(log_capture_string)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

router = APIRouter()

class InterviewInit(BaseModel):
    topic: str
    user_name: str

class InterviewResponse(BaseModel):
    question: str
    answer: str = ""

# In-memory storage for interview sessions
interview_sessions = {}

@router.post("/init")
async def init_interview(init_data: InterviewInit):
    try:
        # Check if the topic exists in the database
        available_topics = await get_available_topics()
        
        if init_data.topic not in available_topics:
            error_msg = f"Topic '{init_data.topic}' not found. Available topics are: {available_topics}"
            logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)
        
        # Fetch base question from MongoDB
        try:
            base_question_data = await fetch_base_question(init_data.topic)
        except Exception as e:
            logger.error(f"Error fetching base question: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        
        # Initialize session
        session_id = f"{init_data.user_name}_{init_data.topic}_{datetime.now().timestamp()}"
        
        session_data = {
            "user_name": init_data.user_name,
            "topic": init_data.topic,
            "questions": [{
                "question": base_question_data["question"],
                "answer": "",
                "difficulty": base_question_data["difficulty"],
                "example": base_question_data["example"],
                "code_stub": base_question_data["code_stub"],
                "tags": base_question_data["tags"]
            }]
        }
        
        try:
            await save_session_data(session_id, session_data)
        except Exception as e:
            logger.error(f"Error saving session data: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error saving session: {str(e)}")
        
        # Get first follow-up question
        try:
            first_follow_up = await get_next_question([], is_base_question=True)
        except Exception as e:
            logger.error(f"Error generating follow-up question: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error generating follow-up question: {str(e)}")
        
        return {
            "session_id": session_id,
            "base_question": base_question_data["question"],
            "difficulty": base_question_data["difficulty"],
            "example": base_question_data["example"],
            "code_stub": base_question_data["code_stub"],
            "tags": base_question_data["tags"],
            "first_follow_up": first_follow_up
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing interview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer")
async def submit_answer(session_id: str, answer: str):
    try:
        logger.error(f"Submitting answer for session: {session_id}")
        
        # Get session data from database
        db = await get_db()
        session_data = await db.interview_sessions.find_one({"session_id": session_id})
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
            
        # Update session data with the answer
        if "questions" not in session_data:
            session_data["questions"] = []
            
        # Add the answer to the last question
        if session_data["questions"]:
            session_data["questions"][-1]["answer"] = answer
            
        # Generate next question
        try:
            next_question = await get_next_question(session_data["questions"])
            session_data["questions"].append({"question": next_question, "answer": ""})
            
            # Update session in database
            await db.interview_sessions.update_one(
                {"session_id": session_id},
                {"$set": {"questions": session_data["questions"]}}
            )
            
            return {"question": next_question}
        except Exception as e:
            logger.error(f"Error generating next question: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error generating next question: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback/{session_id}")
async def get_interview_feedback(session_id: str):
    try:
        # Get session data from database
        db = await get_db()
        session_data = await db.interview_sessions.find_one({"session_id": session_id})
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
            
        # Format conversation for feedback
        conversation = []
        for q in session_data.get("questions", []):
            if "question" in q and "answer" in q:
                conversation.append({
                    "question": q["question"],
                    "answer": q["answer"]
                })
                
        if not conversation:
            logger.error(f"No conversation found for session: {session_id}")
            raise HTTPException(status_code=404, detail="No conversation found for this session")
            
        # Get feedback
        feedback_json = await get_feedback(conversation, session_data["user_name"])
        
        # Parse the JSON feedback
        try:
            feedback = json.loads(feedback_json)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing feedback JSON: {str(e)}")
            raise HTTPException(status_code=500, detail="Error parsing feedback")
        
        # Delete the session from database
        await db.interview_sessions.delete_one({"session_id": session_id})
        
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topics")
async def get_topics():
    """Get list of available interview topics"""
    try:
        topics = await get_available_topics()
        return {"topics": topics}
    except Exception as e:
        logger.error(f"Error getting topics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def get_logs():
    """Get the latest logs"""
    try:
        # Get the logs from the StringIO buffer
        logs = log_capture_string.getvalue()
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
