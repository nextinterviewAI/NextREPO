"""
Approach Analysis Service

This module provides AI-powered analysis of user's problem-solving approaches.
Evaluates responses and provides personalized feedback based on user history.
"""

from services.llm.utils import MODEL_NAME, client, retry_with_backoff, safe_strip, parse_json_response, get_fallback_analysis
from typing import Dict, Any
import logging
from services.rag.retriever_factory import get_rag_retriever
import asyncio
from bson import ObjectId
from bson.errors import InvalidId

logger = logging.getLogger(__name__)

class ApproachAnalysisService:
    """
    Service for analyzing user's problem-solving approaches.
    Provides personalized feedback based on user history and patterns.
    """
    
    def __init__(self, use_rag: bool = False):
        self.client = client
        self.use_rag = use_rag  # Make RAG optional for performance
        logger.info(f"ApproachAnalysisService initialized with RAG: {use_rag}")

    async def _get_context(self, question: str, top_k: int = 1) -> str:
        """
        Retrieve relevant context from RAG system for question analysis.
        Optimized for performance with minimal top_k and optional usage.
        """
        try:
            # Make RAG optional for faster responses
            if not hasattr(self, 'use_rag') or not self.use_rag:
                return ""
            
            retriever = await get_rag_retriever()
            if retriever is None:
                logger.warning("RAGRetriever not initialized")
                return ""
            
            # Use minimal top_k for better performance
            context_chunks = await retriever.retrieve_context(question, top_k=top_k)
            
            # Limit context length for better performance
            context = "\n\n".join(context_chunks)
            if len(context) > 500:  # Reduced from 1000 to 500 characters
                context = context[:500] + "..."
            
            return context
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return ""

    async def _get_user_name_from_db(self, user_id: str) -> str:
        try:
            from services.db import get_db

            db = await get_db()
            user_doc = None

            # Attempt to find by ObjectId first
            try:
                object_id = ObjectId(user_id)
                user_doc = await db.users.find_one({"_id": object_id})
                if user_doc:
                    logger.info(f"Database lookup successful for user_id: {user_id}. Document found.")

            except InvalidId:
                logger.warning(f"Invalid ObjectId format for user_id {user_id}: {e}. Trying as string.")
                user_doc = await db.users.find_one({"_id": user_id})

            except Exception as e:
                logger.error(f"Unexpected error during user lookup for ID '{user_id}': {e}")
                return "Candidate"

            if user_doc:
                user_name = user_doc.get("user_name")
                if user_name:
                    logger.info(f"Successfully fetched user name: {user_name} for user_id: {user_id}")
                    return user_name
                else:
                    logger.warning(f"User found but 'user_name' field is missing or empty for user_id: {user_id}. Using fallback.")
                    return "Candidate"
            else:
                logger.warning(f"User not found in database for user_id: {user_id}. Using fallback.")
                return "Candidate"

        except Exception as e:
            logger.error(f"Critical error fetching user name for user_id {user_id}: {e}", exc_info=True)
            return "Candidate"


    @retry_with_backoff
    async def analyze_approach(self, question: str, user_answer: str, user_name: str = None, previous_attempt: dict = None, personalized_guidance: str = None, user_patterns: Any = None, user_id: str = None) -> Dict[str, Any]: # type: ignore
        """
        Analyze user's approach to a question and provide personalized feedback.
        Uses user history and patterns to tailor the analysis. 
        """
        try: 
            # Get user's name from database if not provided
            if not user_name and user_id:
                # Log the ID before the call
                logger.info(f"Attempting to fetch user name for user_id: {user_id}")
                user_name = await self._get_user_name_from_db(user_id)
                # Log the result after the call
                logger.info(f"_get_user_name_from_db returned: {user_name}")
            
            # Get relevant context from RAG system (reduced top_k for performance)
            context = await self._get_context(question, top_k=2)

            # Build personalized context from user history (optimized)
            extra_context = self._build_optimized_context(
                previous_attempt, personalized_guidance, user_patterns, user_name
            )

            # Build final prompt with personalized context (optimized and concise)
            name_reference = f"{user_name}" if user_name else "the candidate"
            prompt = f"""
Expert interviewer evaluating {name_reference}'s approach.

{extra_context}

SCORING CRITERIA (1-10 scale):
- 9-10: Excellent - Complete, clear, well-structured, shows deep understanding
- 7-8: Good - Solid understanding, minor gaps, mostly clear explanation
- 5-6: Fair - Basic understanding, some gaps, needs improvement
- 3-4: Poor - Limited understanding, significant gaps, unclear
- 1-2: Very Poor - Minimal understanding, major gaps, incorrect approach

Question: {question}
Response: {user_answer}
Context: {context[:200] if context else ""}

INPUT VALIDITY CHECK:
- First, assess if the user's answer shows genuine engagement with the question.
- If the response is: off-topic, nonsensical (e.g., 'approach', 'blah blah'), empty, just repeating the question, or contains no technical substance — treat it as low-faith effort.
- For such cases:
    • Set score = 1 or 2
    • In feedback, clearly state: "This response does not meaningfully address the question."
    • strengths = ["Attempted to respond"]
    • areas_for_improvement = ["Provide specific, thoughtful reasoning", "Engage with the actual problem"]
    • DO NOT include historical strengths (e.g., 'strong foundation') unless explicitly demonstrated in this answer
- Do not fabricate insights or carry forward past strengths without current evidence.
- Only proceed to detailed analysis if the answer demonstrates real effort and technical engagement.

Evaluation Framework:
1. Structure & Clarity: Did they break down the problem logically?
2. What Was Missing: What critical step/concept was not covered?
3. Blind Spots: Subtle but important things they missed?
4. Historical Tracking: Did they improve or repeat mistakes? (N/A if none)
5. Interview Variations: Suggest 1-2 variations and adaptations needed
6. Final Tip: One actionable coaching insight for future questions

IMPORTANT SCORING GUIDELINES:
- Give credit for understanding the approach even if execution is incomplete
- A score of 5-6 is appropriate for someone who understands the concept but doesn't fully execute
- A score of 7-8 is appropriate for someone who shows good understanding with minor gaps
- Be encouraging while honest - focus on what they did well and how to improve
- Use the candidate's name naturally in feedback to make it more personal and engaging

Return ONLY valid JSON:
{{
    "feedback": "...",
    "strengths": [...],
    "areas_for_improvement": [...],
    "score": number
}}
"""

            # Generate analysis using AI with safe OpenAI call (rate limiting + retries)
            from services.llm.utils import safe_openai_call
            
            response = await safe_openai_call(
                self.client.chat.completions.create,
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": f"Expert interviewer providing constructive feedback for {name_reference}. Be encouraging while honest. Focus on strengths first, then areas for improvement. Use personalization data to tailor feedback. Score fairly based on understanding, not just execution. IMPORTANT: Use the candidate's name naturally throughout the feedback to make it more personal and engaging."},
                    {"role": "user", "content": prompt}
                ]
            )

            content = safe_strip(getattr(response.choices[0].message, 'content', None))
            result = parse_json_response(content, get_fallback_analysis())

            # Log success
            logger.info(f"Successfully analyzed approach for question: {question[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Error analyzing approach: {str(e)}")
            return get_fallback_analysis()
    
    def _build_optimized_context(self, previous_attempt: dict = None, personalized_guidance: str = None, user_patterns: Any = None, user_name: str = None) -> str:
        """
        Build optimized context string to reduce prompt length and improve performance.
        """
        extra_context = ""
        
        # Add personalized greeting if user name is available
        if user_name:
            extra_context += f"Personalized Context for {user_name}:\n"
        
        if previous_attempt:
            extra_context += f"Previous attempt: Answer: {previous_attempt.get('answer', '')[:100]}... Result: {previous_attempt.get('result', '')}. Output: {previous_attempt.get('output', '')[:100]}...\n"
        
        if user_patterns:
            patterns = user_patterns
            extra_context += f"Performance: Avg score {patterns.get('average_score', 'N/A')}/10, {patterns.get('completion_rate', 0)*100:.0f}% completion\n"
            extra_context += f"Recent topics: {', '.join(patterns.get('recent_topics', [])[:3])}\n"
            extra_context += f"Performance trend: {patterns.get('performance_trend', [])[-3:]}\n"
            
            if patterns.get('strengths'):
                extra_context += f"Strengths: {', '.join(patterns['strengths'][:2])}\n"
            
            if patterns.get('common_weaknesses'):
                extra_context += f"Areas for improvement: {', '.join(patterns['common_weaknesses'][:2])}\n"
        
        if personalized_guidance:
            guidance = personalized_guidance.replace("You often struggle with:", "Areas:").replace("Your strengths include:", "Strengths:").replace("Keep leveraging these in your answers.", "")
            extra_context += f"Guidance: {guidance[:200]}...\n"
        
        extra_context += "Use this data to tailor feedback. Connect current performance to past trends.\n\n"
        return extra_context