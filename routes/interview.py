from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Dict
from services.db import get_db, fetch_base_question, save_session_data, get_available_topics
from services.llm import get_next_question, get_feedback, get_clarification, check_answer_quality
from pydantic import BaseModel
import logging
from datetime import datetime
import io
import json
import time

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

class AnswerRequest(BaseModel):
    session_id: str
    answer: str
    clarification: bool = False

class ClarificationRequest(BaseModel):
    session_id: str
    question: str

# In-memory storage for interview sessions
interview_sessions = {}

@router.post("/init")
async def init_interview(init_data: InterviewInit):
    try:
        # Generate session ID
        session_id = f"{init_data.user_name}_{init_data.topic}_{time.time()}"
        
        # Get base question
        base_question_data = await fetch_base_question(init_data.topic)
        
        # Save initial session data
        await save_session_data(session_id, {
            "user_name": init_data.user_name,
            "topic": init_data.topic,
            "questions": [{
                "question": base_question_data["question"],
                "answer": ""
            }]
        })
        
        # Get first follow-up question
        try:
            first_follow_up = await get_next_question([], is_base_question=True, topic=init_data.topic)
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
async def submit_answer(
    answer_request: AnswerRequest = Body(...)
):
    try:
        session_id = answer_request.session_id
        answer = answer_request.answer
        clarification = answer_request.clarification
        logger.error(f"Submitting answer for session: {session_id}")
        
        # Get session data from database
        db = await get_db()
        session_data = await db.interview_sessions.find_one({"session_id": session_id})
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Track question count
        question_count = session_data.get("question_count", 1)
        
        # Update session data with the answer (if not clarification)
        if not clarification:
            if "questions" not in session_data:
                session_data["questions"] = []
            if session_data["questions"]:
                session_data["questions"][-1]["answer"] = answer
        
        # Interview flow logic
        if question_count < 4 and not clarification:
            # Generate next follow-up question
            try:
                next_question = await get_next_question(session_data["questions"], topic=session_data["topic"])
                session_data["questions"].append({"question": next_question, "answer": ""})
                session_data["question_count"] = question_count + 1
                await db.interview_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"questions": session_data["questions"], "question_count": session_data["question_count"]}}
                )
                return {"question": next_question}
            except Exception as e:
                logger.error(f"Error generating next question: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error generating next question: {str(e)}")
        elif question_count == 4 and not clarification:
            # End of Q&A, check answer quality before switching to clarification mode
            quality = await check_answer_quality(session_data["questions"], session_data["topic"])
            if quality == "good":
                session_data["question_count"] = question_count + 1
                await db.interview_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"questions": session_data["questions"], "question_count": session_data["question_count"]}}
                )
                return {"question": "You have the right approach for this question. You can start coding. If you have any doubts or need clarification regarding the main question, you can ask me."}
            else:
                return {"question": "Your answers so far seem unclear or incomplete. Please review your responses and try to answer the questions more thoughtfully before proceeding to the coding phase."}
        elif question_count > 4 or clarification:
            # Handle clarification (use get_clarification and store for feedback)
            try:
                current_question = session_data["questions"][0]["question"] if session_data["questions"] else None
                if not current_question:
                    raise HTTPException(status_code=404, detail="No main question found")
                clarification_resp = await get_clarification(current_question, answer)
                # Store clarifications in session for feedback
                if "clarifications" not in session_data:
                    session_data["clarifications"] = []
                session_data["clarifications"].append({"clarification": answer, "response": clarification_resp})
                await db.interview_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"clarifications": session_data["clarifications"]}}
                )
                return {"clarification": clarification_resp}
            except Exception as e:
                logger.error(f"Error generating clarification: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error generating clarification: {str(e)}")
        else:
            return {"question": "You can only ask for clarifications regarding the main question."}
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
                
        # Add clarifications to conversation for feedback
        for clar in session_data.get("clarifications", []):
            conversation.append({
                "question": f"[Clarification] {clar['clarification']}",
                "answer": clar["response"]
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

@router.post("/clarify")
async def ask_clarification(clarification_request: ClarificationRequest):
    try:
        logger.info(f"Requesting clarification for session: {clarification_request.session_id}")
        
        # Get session data from database
        db = await get_db()
        session_data = await db.interview_sessions.find_one({"session_id": clarification_request.session_id})
        if not session_data:
            logger.error(f"Session not found: {clarification_request.session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
            
        # Get the current question
        current_question = session_data["questions"][0]["question"] if session_data["questions"] else None
        if not current_question:
            raise HTTPException(status_code=404, detail="No main question found")
            
        # Generate clarification response
        try:
            clarification_resp = await get_clarification(current_question, clarification_request.question)
            # Store clarifications in session for feedback
            if "clarifications" not in session_data:
                session_data["clarifications"] = []
            session_data["clarifications"].append({"clarification": clarification_request.question, "response": clarification_resp})
            await db.interview_sessions.update_one(
                {"session_id": clarification_request.session_id},
                {"$set": {"clarifications": session_data["clarifications"]}}
            )
            return {"clarification": clarification_resp}
        except Exception as e:
            logger.error(f"Error generating clarification: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error generating clarification: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing clarification request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
