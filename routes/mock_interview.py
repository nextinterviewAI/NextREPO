from fastapi import APIRouter, Depends, HTTPException, Body
from services.db import get_db, fetch_base_question, get_available_topics, validate_user_id, save_user_ai_interaction, fetch_interactions_for_session, fetch_user_history, fetch_user_session_summaries
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
    # Validate user_id
    if not await validate_user_id(init_data.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    try:
        # Generate session ID
        session_id = f"{init_data.user_name}_{init_data.topic}_{datetime.now().timestamp()}"
        
        # user_id is now available as init_data.user_id
        # Get base question
        base_question_data = await fetch_base_question(init_data.topic)
        
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

        response = {
            "session_id": session_id,
            "base_question": base_question_data["question"],
            "difficulty": base_question_data["difficulty"],
            "example": base_question_data["example"],
            "code_stub": base_question_data["code_stub"],
            "tags": base_question_data["tags"],
            "language": base_question_data["language"],
            "first_follow_up": first_follow_up
        }
        # Save interaction (do not block response)
        try:
            await save_user_ai_interaction(
                user_id=init_data.user_id,
                endpoint="mock_interview",
                input_data={**init_data.dict(), "session_id": session_id},
                ai_response=response,
                meta={"step": "init"}
            )
        except Exception as e:
            logger.warning(f"Failed to save user-AI interaction: {e}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing interview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer")
async def submit_answer(answer_request: AnswerRequest = Body(...)):
    # Validate user_id
    if not await validate_user_id(answer_request.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    try:
        session_id = answer_request.session_id
        user_id = answer_request.user_id
        # Reconstruct session state from user_ai_interactions
        interactions = await fetch_interactions_for_session(user_id, session_id)
        if not interactions:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
        # Rebuild questions, answers, clarifications from interactions
        session_data = {"questions": [], "clarifications": [], "question_count": 1, "topic": None}
        for inter in interactions:
            inp = inter.get("input", {})
            resp = inter.get("ai_response", {})
            meta = inter.get("meta", {})
            if meta.get("step") == "init":
                session_data["topic"] = inp.get("topic")
                session_data["questions"].append({"question": resp.get("base_question"), "answer": ""})
                session_data["question_count"] = 1
            elif meta.get("step") == "answer":
                if "clarification" in meta and meta["clarification"]:
                    session_data["clarifications"].append({"clarification": inp.get("answer"), "response": resp.get("clarification")})
                else:
                    # Normal answer
                    if session_data["questions"]:
                        session_data["questions"][-1]["answer"] = inp.get("answer")
                    if "question" in resp:
                        session_data["questions"].append({"question": resp["question"], "answer": ""})
                    session_data["question_count"] = session_data.get("question_count", 1) + 1

        if session_data["question_count"] < 5:
            # Retrieve RAG context for the topic
            retriever = await get_rag_retriever()
            rag_context = ""
            if retriever is not None:
                context_chunks = await retriever.retrieve_context(session_data["topic"])
                rag_context = "\n\n".join(context_chunks)
            try:
                next_question = await get_next_question(session_data["questions"], topic=session_data["topic"], rag_context=rag_context)
                session_data["questions"].append({"question": next_question, "answer": ""})
                session_data["question_count"] = session_data["question_count"] + 1
                ai_response = {
                    "question": next_question,
                    "ready_to_code": False,
                    "language": session_data["questions"][-1]["language"]
                }
                try:
                    await save_user_ai_interaction(
                        user_id=user_id,
                        endpoint="mock_interview",
                        input_data=answer_request.dict(),
                        ai_response=ai_response,
                        meta={"step": "answer", "clarification": False}
                    )
                except Exception as e:
                    logger.warning(f"Failed to save user-AI interaction: {e}")
                return ai_response
            except Exception as e:
                logger.error(f"Error generating next question: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error generating next question: {str(e)}")

        elif session_data["question_count"] == 5:
            quality = await check_answer_quality(session_data["questions"], session_data["topic"])
            if quality == "good":
                session_data["question_count"] = session_data["question_count"] + 1
                session_data["clarification_mode"] = True
                ai_response = {
                    "question": "You can start coding. Ask clarifications if needed.",
                    "clarification": True,
                    "ready_to_code": True,
                    "code_stub": session_data["questions"][-1]["code_stub"],
                    "language": session_data["questions"][-1]["language"],
                    "tags": session_data["questions"][-1]["tags"]
                }
                try:
                    await save_user_ai_interaction(
                        user_id=user_id,
                        endpoint="mock_interview",
                        input_data=answer_request.dict(),
                        ai_response=ai_response,
                        meta={"step": "answer", "clarification": True}
                    )
                except Exception as e:
                    logger.warning(f"Failed to save user-AI interaction: {e}")
                return ai_response
            else:
                ai_response = {
                    "question": "Your answers so far seem unclear or incomplete. Please review and try again before proceeding.",
                    "ready_to_code": False,
                    "language": session_data["questions"][-1]["language"]
                }
                try:
                    await save_user_ai_interaction(
                        user_id=user_id,
                        endpoint="mock_interview",
                        input_data=answer_request.dict(),
                        ai_response=ai_response,
                        meta={"step": "answer", "clarification": False}
                    )
                except Exception as e:
                    logger.warning(f"Failed to save user-AI interaction: {e}")
                return ai_response

        elif session_data["question_count"] > 5 or session_data["clarifications"]:
            try:
                current_question = session_data["questions"][0]["question"] if session_data["questions"] else None
                if not current_question:
                    raise HTTPException(status_code=404, detail="No main question found")

                clarification_resp = await get_clarification(current_question, answer_request.answer)

                if "clarifications" not in session_data:
                    session_data["clarifications"] = []

                session_data["clarifications"].append({"clarification": answer_request.answer, "response": clarification_resp})
                ai_response = {
                    "clarification": clarification_resp,
                    "ready_to_code": True,
                    "language": session_data["questions"][0]["language"]
                }
                try:
                    await save_user_ai_interaction(
                        user_id=user_id,
                        endpoint="mock_interview",
                        input_data=answer_request.dict(),
                        ai_response=ai_response,
                        meta={"step": "answer", "clarification": True}
                    )
                except Exception as e:
                    logger.warning(f"Failed to save user-AI interaction: {e}")
                return ai_response

            except Exception as e:
                logger.error(f"Error generating clarification: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error generating clarification: {str(e)}")
        else:
            return {
                "question": "You can only ask clarifications after starting the coding phase.",
                "ready_to_code": False,
                "language": session_data["questions"][0]["language"]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{session_id}")
async def get_interview_feedback(session_id: str):
    try:
        # Find the user_id from the latest interaction for this session
        db = await get_db()
        last_interaction = await db.user_ai_interactions.find_one({"input.session_id": session_id}, sort=[("timestamp", -1)])
        if not last_interaction:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
        user_id = last_interaction["user_id"]
        interactions = await fetch_interactions_for_session(user_id, session_id)
        if not interactions:
            logger.error(f"No conversation found for session: {session_id}")
            raise HTTPException(status_code=404, detail="No conversation found for this session")
        # Rebuild conversation
        conversation = []
        for inter in interactions:
            inp = inter.get("input", {})
            resp = inter.get("ai_response", {})
            meta = inter.get("meta", {})
            if meta.get("step") == "init":
                conversation.append({"question": resp.get("base_question"), "answer": ""})
            elif meta.get("step") == "answer":
                if "clarification" in meta and meta["clarification"]:
                    conversation.append({"question": f"[Clarification] {inp.get('answer')}", "answer": resp.get("clarification")})
                else:
                    if "question" in resp and "answer" in inp:
                        conversation.append({"question": resp["question"], "answer": inp["answer"]})
        if not conversation:
            logger.error(f"No conversation found for session: {session_id}")
            raise HTTPException(status_code=404, detail="No conversation found for this session")
        feedback_json = await get_feedback(conversation, last_interaction["input"].get("user_name", "Candidate"))
        try:
            feedback = feedback_json
        except Exception as e:
            logger.error(f"Error parsing feedback JSON: {str(e)}")
            raise HTTPException(status_code=500, detail="Error parsing feedback")
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
        # Find the user_id from the latest interaction for this session
        db = await get_db()
        last_interaction = await db.user_ai_interactions.find_one({"input.session_id": clarification_request.session_id}, sort=[("timestamp", -1)])
        if not last_interaction:
            logger.error(f"Session not found: {clarification_request.session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
        user_id = last_interaction["user_id"]
        interactions = await fetch_interactions_for_session(user_id, clarification_request.session_id)
        if not interactions:
            logger.error(f"Session not found: {clarification_request.session_id}")
            raise HTTPException(status_code=404, detail="Interview session not found")
        # Rebuild session_data as needed for clarification
        # ... (similar to answer logic) ...
        # Use the latest question for clarification
        last_question = None
        for inter in reversed(interactions):
            resp = inter.get("ai_response", {})
            meta = inter.get("meta", {})
            if meta.get("step") == "answer" and not meta.get("clarification", False):
                last_question = resp.get("question")
                break
        if not last_question:
            raise HTTPException(status_code=404, detail="No main question found")
        clarification_resp = await get_clarification(last_question, clarification_request.question)
        # Save the clarification interaction
        try:
            await save_user_ai_interaction(
                user_id=user_id,
                endpoint="mock_interview",
                input_data=clarification_request.dict(),
                ai_response={"clarification": clarification_resp},
                meta={"step": "answer", "clarification": True}
            )
        except Exception as e:
            logger.warning(f"Failed to save user-AI interaction: {e}")
        return {"clarification": clarification_resp}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing clarification request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/interactions/{user_id}")
async def get_user_interactions(user_id: str, limit: int = 50):
    try:
        if not await validate_user_id(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        interactions = await fetch_user_history(user_id, limit)
        return {"interactions": interactions}
    except Exception as e:
        logger.error(f"Error fetching user interactions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching user interactions")

@router.get("/user/sessions/{user_id}")
async def get_user_session_summaries(user_id: str, limit: int = 20):
    try:
        if not await validate_user_id(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        summaries = await fetch_user_session_summaries(user_id, limit)
        return {"sessions": summaries}
    except Exception as e:
        logger.error(f"Error fetching user session summaries: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching user session summaries")

@router.get("/user/session/{user_id}/{session_id}")
async def get_user_session_interactions(user_id: str, session_id: str):
    try:
        if not await validate_user_id(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        interactions = await fetch_interactions_for_session(user_id, session_id)
        if not interactions:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"interactions": interactions}
    except Exception as e:
        logger.error(f"Error fetching session interactions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching session interactions")