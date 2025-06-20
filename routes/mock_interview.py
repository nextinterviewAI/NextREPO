from fastapi import APIRouter, Depends, HTTPException, Body
from services.db import get_db, fetch_base_question, save_session_data, get_available_topics
from services.llm.interview import get_next_question
from services.llm.feedback import get_feedback
from services.llm.clarification import get_clarification
from services.llm.check_answer_quality import check_answer_quality, check_single_answer_quality
from models.schemas import InterviewInit, AnswerRequest, ClarificationRequest
import logging
from datetime import datetime
from services.rag.retriever_factory import get_rag_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock", tags=["Mock Interview"])

@router.post("/init")
async def init_interview(init_data: InterviewInit):
    try:
        # Generate session ID
        session_id = f"{init_data.user_name}_{init_data.topic}_{datetime.now().timestamp()}"
        
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
        
        # Retrieve RAG context for the topic
        retriever = await get_rag_retriever()
        rag_context = ""
        if retriever is not None:
            context_chunks = await retriever.retrieve_context(init_data.topic)
            rag_context = "\n\n".join(context_chunks)
        
        # Get first follow-up question
        try:
            first_follow_up = await get_next_question([], is_base_question=True, topic=init_data.topic, rag_context=rag_context)
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
            "language": base_question_data["language"],
            "first_follow_up": first_follow_up
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing interview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer")
async def submit_answer(answer_request: AnswerRequest = Body(...)):
    try:
        session_id = answer_request.session_id
        answer = answer_request.answer
        clarification = answer_request.clarification

        logger.info(f"Submitting answer for session: {session_id}")

        db = await get_db()
        session_data = await db.interview_sessions.find_one({"session_id": session_id})
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")

        question_count = session_data.get("question_count", 1)
        topic = session_data.get("topic")
        base_question_data = await fetch_base_question(topic)

        if not clarification:
            if "questions" not in session_data:
                session_data["questions"] = []
            if session_data["questions"]:
                session_data["questions"][-1]["answer"] = answer

            # Validate answer quality before proceeding
            retriever = await get_rag_retriever()
            rag_context = ""
            if retriever is not None:
                context_chunks = await retriever.retrieve_context(topic)
                rag_context = "\n\n".join(context_chunks)
            last_question = session_data["questions"][-1]["question"] if session_data["questions"] else ""
            answer_quality = await check_single_answer_quality(last_question, answer, topic, rag_context=rag_context)
            if answer_quality != "good":
                return {
                    "question": f"{last_question}\n\nNote: It seems your answer was unclear or not understood. Please try again or clarify your response.",
                    "ready_to_code": False,
                    "language": base_question_data["language"]
                }

        if question_count < 5 and not clarification:
            # Retrieve RAG context for the topic
            retriever = await get_rag_retriever()
            rag_context = ""
            if retriever is not None:
                context_chunks = await retriever.retrieve_context(topic)
                rag_context = "\n\n".join(context_chunks)
            try:
                next_question = await get_next_question(session_data["questions"], topic=topic, rag_context=rag_context)
                session_data["questions"].append({"question": next_question, "answer": ""})
                session_data["question_count"] = question_count + 1
                await db.interview_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"questions": session_data["questions"], "question_count": session_data["question_count"]}}
                )
                return {
                    "question": next_question,
                    "ready_to_code": False,
                    "language": base_question_data["language"]
                }
            except Exception as e:
                logger.error(f"Error generating next question: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error generating next question: {str(e)}")

        elif question_count == 5 and not clarification:
            quality = await check_answer_quality(session_data["questions"], session_data["topic"])
            if quality == "good":
                session_data["question_count"] = question_count + 1
                session_data["clarification_mode"] = True
                await db.interview_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "questions": session_data["questions"],
                        "question_count": session_data["question_count"],
                        "clarification_mode": True
                    }}
                )
                return {
                    "question": "You can start coding. Ask clarifications if needed.",
                    "clarification": True,
                    "ready_to_code": True,
                    "code_stub": base_question_data["code_stub"],
                    "language": base_question_data["language"],
                    "tags": base_question_data["tags"]
                }
            else:
                return {
                    "question": "Your answers so far seem unclear or incomplete. Please review and try again before proceeding.",
                    "ready_to_code": False,
                    "language": base_question_data["language"]
                }

        elif question_count > 5 or clarification:
            try:
                current_question = session_data["questions"][0]["question"] if session_data["questions"] else None
                if not current_question:
                    raise HTTPException(status_code=404, detail="No main question found")

                clarification_resp = await get_clarification(current_question, answer)

                if "clarifications" not in session_data:
                    session_data["clarifications"] = []

                session_data["clarifications"].append({"clarification": answer, "response": clarification_resp})
                await db.interview_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"clarifications": session_data["clarifications"]}}
                )

                return {
                    "clarification": clarification_resp,
                    "ready_to_code": True,
                    "language": base_question_data["language"]
                }

            except Exception as e:
                logger.error(f"Error generating clarification: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error generating clarification: {str(e)}")
        else:
            return {
                "question": "You can only ask clarifications after starting the coding phase.",
                "ready_to_code": False,
                "language": base_question_data["language"]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{session_id}")
async def get_interview_feedback(session_id: str):
    try:
        db = await get_db()
        session_data = await db.interview_sessions.find_one({"session_id": session_id})
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")

        conversation = []
        for q in session_data.get("questions", []):
            if "question" in q and "answer" in q:
                conversation.append({
                    "question": q["question"],
                    "answer": q["answer"]
                })

        for clar in session_data.get("clarifications", []):
            conversation.append({
                "question": f"[Clarification] {clar['clarification']}",
                "answer": clar["response"]
            })

        if not conversation:
            logger.error(f"No conversation found for session: {session_id}")
            raise HTTPException(status_code=404, detail="No conversation found for this session")

        feedback_json = await get_feedback(conversation, session_data["user_name"])

        try:
            feedback = feedback_json  
        except Exception as e:
            logger.error(f"Error parsing feedback JSON: {str(e)}")
            raise HTTPException(status_code=500, detail="Error parsing feedback")

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


@router.post("/clarify")
async def ask_clarification(clarification_request: ClarificationRequest):
    try:
        logger.info(f"Requesting clarification for session: {clarification_request.session_id}")
        db = await get_db()
        session_data = await db.interview_sessions.find_one({"session_id": clarification_request.session_id})
        if not session_data:
            logger.error(f"Session not found: {clarification_request.session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")

        current_question = session_data["questions"][0]["question"] if session_data["questions"] else None
        if not current_question:
            raise HTTPException(status_code=404, detail="No main question found")

        clarification_resp = await get_clarification(current_question, clarification_request.question)

        if "clarifications" not in session_data:
            session_data["clarifications"] = []

        session_data["clarifications"].append({"clarification": clarification_request.question, "response": clarification_resp})
        await db.interview_sessions.update_one(
            {"session_id": clarification_request.session_id},
            {"$set": {"clarifications": session_data["clarifications"]}}
        )

        return {"clarification": clarification_resp}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing clarification request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))