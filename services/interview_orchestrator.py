"""
Interview Orchestrator Service

This module provides a pure LLM approach to interview management.
Handles all interview logic including quality assessment, question generation,
flow progression, and phase transitions using AI instead of hardcoded rules.
"""

import logging
from typing import Dict, Any, Optional, List
from services.llm.utils import client, retry_with_backoff, safe_strip
from services.db import (
    get_interview_session, update_interview_session_answer, 
    add_follow_up_question, transition_to_coding_phase
)
from services.rag.retriever_factory import get_rag_retriever
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)
from datetime import datetime

logger = logging.getLogger(__name__)

class InterviewOrchestrator:
    """Manages entire interview flow using pure LLM approach."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_data = None
        self.interview_type = None
        
    async def initialize(self):
        """Initialize the orchestrator with session data."""
        session = await get_interview_session(self.session_id)
        if not session:
            raise ValueError(f"Session not found: {self.session_id}")
        
        self.session_data = session["meta"]["session_data"]
        self.interview_type = self.session_data.get("interview_type", "approach")
        logger.info(f"Initialized orchestrator for {self.interview_type} interview")
    
    async def process_answer(self, user_answer: str) -> Dict[str, Any]:
        """Process user answer and determine next action using LLM."""
        await self.initialize()
        
        logger.info(f"Processing answer for session {self.session_id}, interview_type: {self.interview_type}")
        
        # Get RAG context (skip for non-coding to avoid irrelevant drift)
        if self.interview_type in ["approach", "non-coding"]:
            rag_context = ""
        else:
            rag_context = await self._get_rag_context()
        
        # Build comprehensive prompt for LLM decision (includes current bad answer count)
        prompt = self._build_decision_prompt(user_answer, rag_context)
        
        # Get LLM decision
        llm_response = await self._get_llm_decision(prompt)
        
        # Execute the decision  
        result = await self._execute_llm_decision(llm_response, user_answer)
        
        logger.info(f"Interview orchestrator result: {result}")
        return result
    
    def _build_decision_prompt(self, user_answer: str, rag_context: str) -> str:
        """Build comprehensive prompt for LLM to make all decisions."""
        
        # Build conversation history
        conversation_history = self._build_conversation_history()
        
        # Calculate current good answer count and total answered questions
        follow_up_questions = self.session_data.get('follow_up_questions', [])
        answered_questions = [q for q in follow_up_questions if q.get('answer')]
        good_answers = [q for q in answered_questions if not q.get('answer_rejected', False)]
        current_good_answers = len(good_answers)
        total_answered = len(answered_questions)
        
        logger.info(f"Current good answers: {current_good_answers}, Total answered: {total_answered}, Interview type: {self.interview_type}")
        
        # Base system prompt
        system_prompt = """You are a Senior Technical Interviewer having a natural conversation with a candidate.

Your task is to analyze the user's answer and determine the next action. You must respond with a JSON object containing:

{
    "action": "next_question|retry_same|transition_phase|complete_session",
    "reason": "explanation of your decision",
    "quality_assessment": "good|bad|excellent",
    "next_question": "the next question to ask (if action is next_question)",
    "feedback": "feedback for the user (if action is retry_same)",
    "phase": "verbal|coding|completed",
    "ready_to_code": true|false,
    "clarification_count": number,
    "max_clarifications": number,
    "answer_rejected": true|false,
    "retry_same_question": true|false,
    "session_complete": true|false
}

Note: "complete_session" action means suggest to the user that they should end the interview and come back better prepared.

CRITICAL RULES:
1. Only generate next_question if answer quality is good/excellent
2. For bad answers, ask user to retry the same question
3. Respect clarification limits (max 2 per question, 5 total)
4. **BAD ANSWER THRESHOLDS - CRITICAL:**
   - For approach/non-coding interviews: ONLY use action "complete_session" if user would have 3+ bad quality answers (including current)
   - For coding interviews: ONLY use action "complete_session" if user would have 4-5+ bad quality answers (including current)
   - **DO NOT end sessions prematurely**
5. **TRANSITION RULES - CRITICAL:**
   - For coding interviews: if user has 5+ good answers AND current answer is good, use action "transition_phase"
   - For approach interviews: if user has 7+ good answers AND current answer is good, use action "complete_session"
   - **DO NOT ask follow-up questions when transition criteria are met**
6. Never ask for code in non-coding interviews
7. Generate contextually relevant follow-up questions

IMPORTANT: Make your questions sound natural and conversational, like a real interviewer would ask. Use casual language, show interest, and ask follow-ups that feel like a genuine conversation, not a textbook quiz. Avoid repetitive language and vary your vocabulary naturally.

CRITICAL: When asking candidates to retry an answer, NEVER give away specific technical details, component names, or solution approaches. Simply ask them to clarify or try again without revealing what they should have said.

**TRANSITION PRIORITY: Phase transitions take priority over follow-up questions. When transition criteria are met, transition immediately.**

**SESSION ENDING: Only end sessions when bad answer thresholds are actually exceeded. Be patient and give candidates multiple chances to improve.**

BASE-QUESTION SCOPE:
- All follow-up questions must remain strictly within the scope of the base question
  and should build only on what the candidate has already said. Do not introduce
  unrelated topics or drift away from the base question.

DYNAMIC RUBRIC (Topic-Agnostic):
1. First, derive 1-3 Essential Correctness Criteria directly from the base question text.
2. Evaluate the user's latest answer against these criteria.
3. MAJORITY RULE: If the answer satisfies a majority of the criteria (e.g., 2 of 3 or 1 of 1),
   and directly addresses the base question, set quality_assessment = "good" and prefer
   action = "next_question".
4. If marking quality_assessment = "bad", the feedback MUST briefly reference which
   criteria were unclear or unmet without revealing the exact answer.
5. Concise but accurate answers should be accepted as "good".

NON-LEADING FEEDBACK:
- When asking for a retry, keep the rationale non-leading and avoid giving away
  specific solution elements. Reference unmet criteria at a high level only."""

        # Interview type specific instructions
        if self.interview_type == "coding":
             type_instructions = """
CODING INTERVIEW SPECIFIC RULES:
- Focus on problem understanding and solution design
- Generate contextually relevant follow-up questions based on the user's specific answer
- Ask about aspects the user didn't cover or areas that need deeper exploration
- Questions should build on previous answers and explore new dimensions
- Avoid generic questions like "edge cases" unless specifically relevant
- Use conversational language: "Hmm, what about..." or "That's interesting, but..."
- Show genuine interest in their thinking
- If user would have 4-5+ bad quality answers (including current), use action "complete_session" to suggest ending
- **TRANSITION TO CODING PHASE: After 5 good answers, use action "transition_phase"**
- No actual code writing until coding phase"""
        else:
            type_instructions = """
APPROACH/NON-CODING INTERVIEW SPECIFIC RULES:
- Focus on business logic, real-world application, and strategic thinking
- Ask about stakeholder considerations, business impact, and implementation challenges
- Questions about problem scope, edge cases, and business value
- For data science/ML questions: focus on methodology and business outcomes
- Technical methodology IS business logic when it directly impacts business decisions
- Use conversational language: "That's a good point, but what about..." or "I'm curious about..."
- Show genuine interest in their business thinking
- If user would have 3+ bad quality answers (including current), use action "complete_session" to suggest ending
- **COMPLETE SESSION: After 7 good answers, use action "complete_session"**
- Never ask for actual code writing, but technical methodology discussion is encouraged
- When asking for retries: ask for clarification without revealing specific technical details"""

        # Calculate current bad answer count
        # Count all bad answers provided by the user, not just questions marked as rejected
        follow_up_questions = self.session_data.get('follow_up_questions', [])
        answered_questions = [q for q in follow_up_questions if q.get('answer')]
        
        # Total bad answers so far (legacy counter retained for analytics)
        session_bad_count = self.session_data.get('bad_answer_count', 0)
        current_bad_answers = session_bad_count
        
        # Consecutive bad answers (used for non-coding end condition)
        consecutive_bad_answers = self.session_data.get('consecutive_bad_answer_count', 0)
        
        # Note: Current answer quality will be assessed by the LLM in the decision
        # If current answer is bad, we'll increment the counters in the execution phase
        
        logger.info(f"Current bad answers count: {current_bad_answers}, Consecutive: {consecutive_bad_answers}, Interview type: {self.interview_type}")
        logger.info(f"Answered questions: {[q.get('answer', '')[:20] + '...' for q in answered_questions]}")
        
        # Build user prompt
        user_prompt = f"""
INTERVIEW CONTEXT:
- Type: {self.interview_type}
- Current Phase: {self.session_data.get('current_phase', 'verbal')}
- Questions Answered: {total_answered}
- Good Quality Answers: {current_good_answers}
- Total Clarifications: {sum(q.get('clarification_count', 0) for q in self.session_data.get('follow_up_questions', []))}
- Bad Quality Answers So Far: {current_bad_answers}
- Consecutive Bad Answers: {consecutive_bad_answers}
- Base Question: {self.session_data.get('questions', [{}])[0].get('question', '') if self.session_data.get('questions') else ''}

CONVERSATION HISTORY:
{conversation_history}

USER'S LATEST ANSWER:
{user_answer}

RAG CONTEXT:
{rag_context}

Based on this information, determine the next action. Remember:
- Assess answer quality first
- If this answer is bad, it would make the total bad answers: {current_bad_answers + 1}
- **PHASE TRANSITION LOGIC - CRITICAL:**
  - For coding interviews: if user has 5+ good answers AND current answer is good, use action "transition_phase"
  - For approach interviews: if user has 7+ good answers AND current answer is good, use action "complete_session"
- Decide whether to progress or retry
- Generate appropriate questions or feedback
- Manage interview flow and phase transitions
- **BAD ANSWER THRESHOLDS:**
  - For approach/non-coding interviews: ONLY suggest ending if the candidate would have 4+ CONSECUTIVE bad quality answers (including this one)
  - For coding interviews: ONLY suggest ending if the candidate would have 4-5+ bad quality answers (including this one)
- **IMPORTANT**: Do NOT end the session prematurely. Only end if the threshold is actually exceeded.

**TRANSITION DECISION TREE:**
1. If interview_type = "coding" AND current_good_answers >= 5 AND current_answer_quality = "good" → action = "transition_phase"
2. If interview_type = "approach" AND current_good_answers >= 7 AND current_answer_quality = "good" → action = "complete_session"
3. If current_answer_quality = "bad" → action = "retry_same"
4. Otherwise → action = "next_question"

**CRITICAL**: If the user has provided multiple bad answers to the same question, consider ending the session after 3+ attempts for approach/non-coding interviews or 4-5+ attempts for coding interviews.

Respond with the JSON object as specified above."""

        return {
            "system": system_prompt + type_instructions,
            "user": user_prompt
        }
    
    def _build_conversation_history(self) -> str:
        """Build conversation history for context."""
        history = []
        
        # Add base question
        if self.session_data.get("questions"):
            base_q = self.session_data["questions"][0]
            history.append(f"Base Question: {base_q.get('question', '')}")
        
        # Add recent Q&A pairs (last 2 for context)
        follow_ups = self.session_data.get("follow_up_questions", [])
        recent_qa = [q for q in follow_ups[-2:] if q.get("answer")]
        
        for q in recent_qa:
            history.append(f"Q: {q.get('question', '')}")
            history.append(f"A: {q.get('answer', '')}")
        
        return "\n".join(history)
    
    async def _get_llm_decision(self, prompt: Dict[str, str]) -> Dict[str, Any]:
        """Get decision from LLM."""
        try:
            messages = [
                ChatCompletionSystemMessageParam(role="system", content=prompt["system"]),
                ChatCompletionUserMessageParam(role="user", content=prompt["user"])
            ]
            
            # Reduce variability for non-coding/approach verbal decisions
            temperature = 0.0 if self.interview_type in ["approach", "non-coding"] else 0.3
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=temperature,
                max_tokens=500
            )
            
            content = safe_strip(getattr(response.choices[0].message, 'content', None))
            logger.info(f"LLM Decision: {content[:200]}...")
            
            # Parse JSON response
            import json
            try:
                decision = json.loads(content)
                
                # Add debugging for transition logic
                action = decision.get("action", "unknown")
                quality = decision.get("quality_assessment", "unknown")
                ready_to_code = decision.get("ready_to_code", False)
                
                logger.info(f"Parsed LLM decision: action={action}, quality={quality}, ready_to_code={ready_to_code}")
                
                # Validate critical fields
                if action == "transition_phase":
                    logger.info(f"LLM requested transition to coding phase")
                elif action == "next_question" and self.interview_type == "coding":
                    # Check if we should have transitioned
                    follow_up_questions = self.session_data.get('follow_up_questions', [])
                    answered_questions = [q for q in follow_up_questions if q.get('answer')]
                    good_answers = [q for q in answered_questions if not q.get('answer_rejected', False)]
                    current_good_answers = len(good_answers) + 1  # +1 for current answer
                    
                    logger.info(f"LLM chose next_question for coding interview. Good answers: {current_good_answers}, should_transition: {current_good_answers >= 5}")
                    
                    if current_good_answers >= 5:
                        logger.warning(f"LLM should have chosen transition_phase instead of next_question for coding interview with {current_good_answers} good answers")
                
                return decision
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {content}")
                # Fallback decision
                return {
                    "action": "retry_same",
                    "reason": "LLM response parsing failed",
                    "quality_assessment": "bad",
                    "feedback": "Please provide a more detailed answer to the question.",
                    "phase": self.session_data.get("current_phase", "verbal"),
                    "ready_to_code": False,
                    "clarification_count": 1,
                    "max_clarifications": 2,
                    "answer_rejected": True,
                    "retry_same_question": True,
                    "session_complete": False
                }
                
        except Exception as e:
            logger.error(f"Error getting LLM decision: {str(e)}")
            # Fallback decision
            return {
                "action": "retry_same",
                "reason": f"LLM error: {str(e)}",
                "quality_assessment": "bad",
                "feedback": "Please provide a more detailed answer to the question.",
                "phase": self.session_data.get("current_phase", "verbal"),
                "ready_to_code": False,
                "clarification_count": 1,
                "max_clarifications": 2,
                "answer_rejected": True,
                "retry_same_question": True,
                "session_complete": False
            }
    
    async def _execute_llm_decision(self, decision: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Execute the LLM's decision."""
        action = decision.get("action", "retry_same")
        quality_assessment = decision.get("quality_assessment", "unknown")
        
        logger.info(f"Executing LLM decision: action={action}, quality={quality_assessment}, interview_type={self.interview_type}")
        
        # Update session with user's answer
        await update_interview_session_answer(self.session_id, user_answer, False)
        
        if action == "next_question":
            # Mark the answer as accepted in the database
            await self._mark_answer_as_accepted(user_answer)
            
            # Check if we should transition to coding phase for coding interviews
            if self.interview_type == "coding":
                follow_up_questions = self.session_data.get('follow_up_questions', [])
                answered_questions = [q for q in follow_up_questions if q.get('answer')]
                good_answers = [q for q in answered_questions if not q.get('answer_rejected', False)]
                current_good_answers = len(good_answers) + 1  # +1 for current answer
                
                logger.info(f"After accepting answer: good_answers={current_good_answers}, should_transition={current_good_answers >= 5}")
                
                if current_good_answers >= 5:
                    logger.info(f"Transitioning to coding phase after {current_good_answers} good answers")
                    await transition_to_coding_phase(self.session_id)
                    return {
                        "question": "Excellent! You've demonstrated strong understanding. Now let's move to the coding phase. You can start coding.",
                        "clarification": True,
                        "ready_to_code": True,
                        "language": self.session_data.get("language", "Python")
                    }
            
            # Add the next question to session
            next_question = decision.get("next_question", "")
            if next_question:
                await add_follow_up_question(self.session_id, next_question)
            
            return {
                "question": next_question,
                "ready_to_code": decision.get("ready_to_code", False),
                "language": self.session_data.get("language", "Python") if self.interview_type == "coding" else None
            }
            
        elif action == "retry_same":
            # Mark the answer as rejected in the database and increment bad answer count
            await self._mark_answer_as_rejected(user_answer)
            await self._increment_bad_answer_count()
            # Track consecutive bad answers for non-coding end condition
            await self._increment_consecutive_bad_answer_count()
            logger.info(f"Answer marked as rejected. Quality: {decision.get('quality_assessment', 'unknown')}")
            
            # Check if we should automatically end the session due to too many bad answers
            # Get fresh session data after incrementing bad answer count
            session = await get_interview_session(self.session_id)
            if session:
                session_data = session["meta"]["session_data"]
                current_bad_count = session_data.get('bad_answer_count', 0)
                current_consecutive_bad = session_data.get('consecutive_bad_answer_count', 0)
            else:
                current_bad_count = 0
                current_consecutive_bad = 0
            
            logger.info(f"Retry check: bad answers: {current_bad_count}, consecutive: {current_consecutive_bad}, threshold: {'4+ consecutive' if self.interview_type in ['approach', 'non-coding'] else '4-5+'}")
            
            # Auto-end session if threshold exceeded
            if self.interview_type in ["approach", "non-coding"] and current_consecutive_bad >= 4:
                logger.info(f"Auto-ending {self.interview_type} interview after {current_bad_count} bad answers")
                await self._mark_session_as_completed()
                return {
                    "question": "I think we should end this interview here. You might want to review the material and come back better prepared next time. Please end the session and come back when you're better prepared.",
                    "session_complete": True
                }
            elif self.interview_type == "coding" and current_bad_count >= 4:
                logger.info(f"Auto-ending coding interview after {current_bad_count} bad answers")
                await self._mark_session_as_completed()
                return {
                    "question": "I think we should end this interview here. You might want to review the material and come back better prepared next time. Please end the session and come back when you're better prepared.",
                    "session_complete": True
                }
            
            # Return retry request
            return {
                "question": decision.get("feedback", "Please provide a more detailed answer."),
                "current_question": self._get_current_question(),
                "ready_to_code": False,
                "answer_rejected": True,
                "retry_same_question": True,
                "clarification_count": decision.get("clarification_count", 1),
                "max_clarifications": decision.get("max_clarifications", 2),
                "interview_type": self.interview_type,
                "quality_feedback": decision.get("feedback", ""),
                "language": self.session_data.get("language", "Python") if self.interview_type == "coding" else None
            }
            
        elif action == "transition_phase":
            # Transition to coding phase
            if self.interview_type == "coding":
                logger.info(f"LLM requested transition to coding phase for session {self.session_id}")
                await transition_to_coding_phase(self.session_id)
                return {
                    "question": "Great! Now let's move to the coding phase. You can start coding.",
                    "clarification": True,
                    "ready_to_code": True,
                    "language": self.session_data.get("language", "Python")
                }
            else:
                # For approach interviews, complete the session
                logger.info(f"LLM requested transition for approach interview, completing session {self.session_id}")
                await self._mark_session_as_completed()
                return {
                    "question": "Great discussion! You can submit the session and check your feedback.",
                    "session_complete": True
                }
                
        elif action == "complete_session":
            # LLM suggests ending session due to too many bad answers
            # Note: LLM cannot actually end the session - user must do this manually
            
            # Validate that we actually have enough bad answers to end the session
            follow_up_questions = self.session_data.get('follow_up_questions', [])
            answered_questions = [q for q in follow_up_questions if q.get('answer')]
            
            # Get current session bad answer count
            session_bad_count = self.session_data.get('bad_answer_count', 0)
            current_bad_count = session_bad_count
            current_consecutive_bad = self.session_data.get('consecutive_bad_answer_count', 0)
            
            # Check if current answer should also be counted as bad
            # (it will be incremented if we decide to retry, but for completion check we count it now)
            if quality_assessment == "bad":
                current_bad_count += 1
                current_consecutive_bad += 1
            
            logger.info(f"LLM requested session completion. Current bad answers: {current_bad_count}, Consecutive: {current_consecutive_bad}, Threshold: {'4+ consecutive' if self.interview_type in ['approach', 'non-coding'] else '4-5+'}")
            logger.info(f"Bad answers breakdown: {current_bad_count} rejected answers out of {len(answered_questions) + 1} total answers")
            
            # Only allow completion if threshold is actually met
            if self.interview_type in ["approach", "non-coding"] and current_consecutive_bad >= 4:
                logger.info(f"LLM decided to complete session. Reason: {decision.get('reason', 'unknown')}")
                await self._mark_session_as_completed()
                return {
                    "question": "I think we should end this interview here. You might want to review the material and come back better prepared next time. Please end the session and come back when you're better prepared.",
                    "session_complete": True
                }
            elif self.interview_type == "coding" and current_bad_count >= 4:
                logger.info(f"LLM decided to complete session. Reason: {decision.get('reason', 'unknown')}")
                await self._mark_session_as_completed()
                return {
                    "question": "I think we should end this interview here. You might want to review the material and come back better prepared next time. Please end the session and come back when you're better prepared.",
                    "session_complete": True
                }
            else:
                # Threshold not met, override LLM decision and ask to retry
                logger.warning(f"LLM requested premature session completion. Overriding decision. Bad answers: {current_bad_count}, Consecutive: {current_consecutive_bad}, Required: {'4+ consecutive' if self.interview_type in ['approach', 'non-coding'] else '4-5+'}")
                await self._mark_answer_as_rejected(user_answer)
                return {
                    "question": "Let's try that again. Please provide a more detailed answer to the question.",
                    "current_question": self._get_current_question(),
                    "ready_to_code": False,
                    "answer_rejected": True,
                    "retry_same_question": True,
                    "clarification_count": 1,
                    "max_clarifications": 2,
                    "interview_type": self.interview_type,
                    "quality_feedback": "Please provide a more detailed answer.",
                    "language": self.session_data.get("language", "Python") if self.interview_type == "coding" else None
                }
        
        # Default fallback
        return {
            "question": "Please provide a more detailed answer to continue.",
            "ready_to_code": False,
            "language": self.session_data.get("language", "Python") if self.interview_type == "coding" else None
        }
    
    def _get_current_question(self) -> str:
        """Get the current question being answered."""
        follow_ups = self.session_data.get("follow_up_questions", [])
        if follow_ups:
            return follow_ups[-1].get("question", "")
        elif self.session_data.get("questions"):
            return self.session_data["questions"][0].get("question", "")
        return ""
    
    async def _mark_answer_as_rejected(self, user_answer: str):
        """Mark the current answer as rejected in the database."""
        try:
            from services.db import get_db
            db = await get_db()
            
            # Get fresh session data
            session = await get_interview_session(self.session_id)
            if not session:
                return
            
            session_data = session["meta"]["session_data"]
            follow_up_questions = session_data.get("follow_up_questions", [])
            
            if follow_up_questions:
                # Find the last question with an answer and mark it as rejected
                for question in reversed(follow_up_questions):
                    if question.get("answer") == user_answer:
                        question["answer_rejected"] = True
                        break
                
                # Update the database
                await db.user_ai_interactions.update_one(
                    {"session_id": self.session_id},
                    {
                        "$set": {
                            "meta.session_data": session_data,
                            "timestamp": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Marked answer as rejected for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error marking answer as rejected: {str(e)}")
    
    async def _increment_bad_answer_count(self):
        """Increment the session-level bad answer counter."""
        try:
            from services.db import get_db
            db = await get_db()
            
            # Get fresh session data
            session = await get_interview_session(self.session_id)
            if not session:
                return
            
            session_data = session["meta"]["session_data"]
            current_count = session_data.get("bad_answer_count", 0)
            new_count = current_count + 1
            session_data["bad_answer_count"] = new_count
            
            # Update the database
            await db.user_ai_interactions.update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "meta.session_data": session_data,
                        "timestamp": datetime.utcnow()
                    }
                }
            )
            logger.info(f"Incremented bad answer count to {new_count} for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error incrementing bad answer count: {str(e)}")

    async def _increment_consecutive_bad_answer_count(self):
        """Increment the consecutive bad answer counter (used for non-coding threshold)."""
        try:
            from services.db import get_db
            db = await get_db()

            # Get fresh session data
            session = await get_interview_session(self.session_id)
            if not session:
                return

            session_data = session["meta"]["session_data"]
            current_count = session_data.get("consecutive_bad_answer_count", 0)
            new_count = current_count + 1
            session_data["consecutive_bad_answer_count"] = new_count

            # Update the database
            await db.user_ai_interactions.update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "meta.session_data": session_data,
                        "timestamp": datetime.utcnow()
                    }
                }
            )
            logger.info(f"Incremented consecutive bad answer count to {new_count} for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error incrementing consecutive bad answer count: {str(e)}")
    
    async def _mark_session_as_completed(self):
        """Mark the session as completed due to too many bad answers."""
        try:
            from services.db import get_db
            db = await get_db()
            
            # Get fresh session data
            session = await get_interview_session(self.session_id)
            if not session:
                return
            
            session_data = session["meta"]["session_data"]
            session_data["status"] = "completed"
            session_data["current_phase"] = "completed"
            session_data["completion_reason"] = "too_many_bad_answers"
            
            # Update the database
            await db.user_ai_interactions.update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "meta.session_data": session_data,
                        "timestamp": datetime.utcnow()
                    }
                }
            )
            logger.info(f"Marked session as completed due to too many bad answers: {self.session_id}")
        except Exception as e:
            logger.error(f"Error marking session as completed: {str(e)}")
    
    async def _mark_answer_as_accepted(self, user_answer: str):
        """Mark the current answer as accepted in the database."""
        try:
            from services.db import get_db
            db = await get_db()
            
            # Get fresh session data
            session = await get_interview_session(self.session_id)
            if not session:
                return
            
            session_data = session["meta"]["session_data"]
            follow_up_questions = session_data.get("follow_up_questions", [])
            
            if follow_up_questions:
                # Find the last question with an answer and mark it as accepted
                for question in reversed(follow_up_questions):
                    if question.get("answer") == user_answer:
                        question["answer_rejected"] = False
                        break
                
                # Update the database
                await db.user_ai_interactions.update_one(
                    {"session_id": self.session_id},
                    {
                        "$set": {
                            "meta.session_data": session_data,
                            "timestamp": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Marked answer as accepted for session {self.session_id}")
                
                # Reset consecutive bad counter on accepted answer
                session = await get_interview_session(self.session_id)
                if session:
                    session_data = session["meta"]["session_data"]
                    session_data["consecutive_bad_answer_count"] = 0
                    await db.user_ai_interactions.update_one(
                        {"session_id": self.session_id},
                        {
                            "$set": {
                                "meta.session_data": session_data,
                                "timestamp": datetime.utcnow()
                            }
                        }
                    )
                    logger.info(f"Reset consecutive bad answer count to 0 for session {self.session_id}")
                
                # Fallback transition check for coding interviews
                if self.interview_type == "coding":
                    answered_questions = [q for q in follow_up_questions if q.get('answer')]
                    good_answers = [q for q in answered_questions if not q.get('answer_rejected', False)]
                    current_good_answers = len(good_answers)
                    
                    logger.info(f"Fallback check: good_answers={current_good_answers}, should_transition={current_good_answers >= 5}")
                    
                    if current_good_answers >= 5 and session_data.get("current_phase") == "verbal":
                        logger.info(f"Fallback: Transitioning to coding phase after {current_good_answers} good answers")
                        await transition_to_coding_phase(self.session_id)
                        
        except Exception as e:
            logger.error(f"Error marking answer as accepted: {str(e)}")
    
    async def _get_rag_context(self) -> str:
        """Get RAG context for the topic."""
        try:
            retriever = await get_rag_retriever()
            if retriever:
                context_chunks = await retriever.retrieve_context(self.session_data.get("topic", ""))
                return "\n\n".join(context_chunks)
        except Exception as e:
            logger.warning(f"Failed to get RAG context: {e}")
        return ""

class CodingPhaseOrchestrator:
    """Handles coding phase logic separately."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_data = None
        
    async def initialize(self):
        """Initialize with session data."""
        session = await get_interview_session(self.session_id)
        if not session:
            raise ValueError(f"Session not found: {self.session_id}")
        self.session_data = session["meta"]["session_data"]
    
    async def handle_clarification(self, answer: str) -> Dict[str, Any]:
        """Handle clarification during coding phase."""
        await self.initialize()
        
        # Get current clarification count and ensure it's a number
        current_count = self.session_data.get("coding_clarification_count", 0)
        if not isinstance(current_count, int):
            current_count = 0
        
        # Increment for this request
        clarification_count = current_count + 1
        max_clarifications = 2
        
        if clarification_count > max_clarifications:
            message = "You've reached the maximum clarification attempts. Let's proceed with coding based on your current understanding."
        else:
            # Generate clarification response using LLM
            prompt = f"""
            You are a Senior Technical Interviewer conducting a coding interview. A candidate has asked for clarification about the problem.
            
            Base Question: {self.session_data.get('questions', [{}])[0].get('question', '')}
            Candidate's Clarification Request: {answer}
            
            Provide a helpful clarification response as the interviewer. Be concise, helpful, and speak directly to the candidate. 
            Use phrases like "You can..." or "I'd suggest..." rather than referring to "the interviewer" in third person.
            """
            
            try:
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                message = safe_strip(getattr(response.choices[0].message, 'content', None))
            except Exception as e:
                logger.error(f"Error generating clarification: {str(e)}")
                message = "Please clarify what specific aspect you need help with."
        
        # Update clarification count
        from services.db import get_db
        db = await get_db()
        await db.user_ai_interactions.update_one(
            {"session_id": self.session_id},
            {"$set": {"meta.session_data.coding_clarification_count": clarification_count}}
        )
        
        return {
            "question": message,
            "clarification": True,
            "ready_to_code": True,
            "clarification_count": clarification_count,
            "max_clarifications": max_clarifications,
            "language": self.session_data.get("language", "Python")
        }
    
    async def handle_code_submission(self, code: str) -> Dict[str, Any]:
        """Handle final code submission."""
        await self.initialize()
        
        # Mark session as completed
        self.session_data["status"] = "completed"
        self.session_data["current_phase"] = "completed"
        
        from services.db import get_db
        db = await get_db()
        await db.user_ai_interactions.update_one(
            {"session_id": self.session_id},
            {
                "$set": {
                    "meta.session_data": self.session_data,
                    "timestamp": datetime.utcnow()
                }
            }
        )
        
        return {"message": "Code submitted successfully. You can now generate feedback."}