"""
Interview Initialization Service

This module handles the creation of new interview sessions.
Creates sessions with base questions and generates personalized first follow-ups.
"""

import logging
from typing import Dict, Any, Optional
from services.db import (
    get_db, fetch_question_by_module, get_user_name_from_id,
    create_interview_session
)
from services.rag.retriever_factory import get_rag_retriever
from services.llm.utils import client, safe_strip
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)

logger = logging.getLogger(__name__)

class InterviewInitializer:
    """Handles interview session initialization."""
    
    def __init__(self, user_id: str, module_code: str):
        self.user_id = user_id
        self.module_code = module_code
    
    async def initialize_interview(self) -> Dict[str, Any]:
        """Initialize a complete interview session."""
        try:
            # Fetch base question using module_code
            base_question_data = await self._fetch_base_question()
            if not base_question_data:
                raise ValueError(f"No questions available for module: {self.module_code}")
            
            # Get user name for personalization
            user_name = await self._get_user_name()
            
            # Generate personalized first follow-up
            first_follow_up = await self._generate_personalized_follow_up(
                base_question_data, user_name
            )
            
            # Create session
            session_id = await self._create_session(base_question_data, first_follow_up)
            
            # Return session data
            return {
                "session_id": session_id,
                "base_question": base_question_data.get("question", ""),
                "description": base_question_data.get("example", ""),  # Fixed: example not description
                "level": base_question_data.get("difficulty", ""),    # Fixed: difficulty not level
                "question_type": base_question_data.get("question_type", ""),
                "programming_language": base_question_data.get("language", ""),  # Fixed: language not programming_language
                "base_code": base_question_data.get("code_stub", ""),  # Fixed: code_stub not base_code
                "tags": base_question_data.get("tags", []),
                "example": base_question_data.get("example", ""),
                "dbSetupCommands": base_question_data.get("dbSetupCommands", ""),
                "difficulty": base_question_data.get("difficulty", ""),
                "first_follow_up": first_follow_up,
                "base_question_id": str(base_question_data.get("_id", "")),
                "module_code": self.module_code,
                "topic_code": base_question_data.get("topic_code", ""),
                "interview_type": base_question_data.get("interview_type", "approach"),
                "code_stub": base_question_data.get("code_stub", ""),
                "language": base_question_data.get("language", ""),
                "sample_input": base_question_data.get("expectedOutput", ""),  # Fixed: expectedOutput not sample_input
                "sample_output": base_question_data.get("expectedOutput", "")  # Fixed: expectedOutput not sample_output
            }
            
        except Exception as e:
            logger.error(f"Error initializing interview: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error initializing interview: {str(e)}")
    
    async def _fetch_base_question(self) -> Optional[Dict[str, Any]]:
        """Fetch a random base question for the module."""
        try:
            # Use the correct function that handles module_code
            base_question = await fetch_question_by_module(self.module_code)
            if not base_question:
                raise ValueError(f"No questions found for module: {self.module_code}")
            return base_question
        except Exception as e:
            logger.error(f"Error fetching base question: {str(e)}")
            raise
    
    async def _get_user_name(self) -> str:
        """Get user name for personalization."""
        try:
            user_name = await get_user_name_from_id(self.user_id)
            return user_name or ""
        except Exception as e:
            logger.warning(f"Could not fetch user name: {str(e)}")
            return ""
    
    async def _generate_personalized_follow_up(
        self, base_question_data: Dict[str, Any], user_name: str
    ) -> str:
        """Generate personalized first follow-up question using LLM."""
        try:
            interview_type = base_question_data.get("interview_type", "approach")
            
            # Build system prompt
            system_prompt = """You are a Senior Technical Interviewer creating the first follow-up question for a mock interview session.

Your task is to generate a personalized welcome message and first question that:
1. Greets the user by name (if provided)
2. Welcomes them to the interview
3. Asks them to review the base question
4. Provides appropriate first instruction based on interview type

INTERVIEW TYPE RULES:
- For CODING interviews: Ask them to walk through their initial approach
- For APPROACH interviews: Ask them to provide a brief answer to the question

Keep the message warm, professional, and encouraging. Maximum 2-3 sentences."""

            # Build user prompt
            user_prompt = f"""
Generate the first follow-up question for this interview:

INTERVIEW DETAILS:
- Type: {interview_type}
- User Name: {user_name if user_name else "User"}
- Base Question: {base_question_data.get('question', '')}
- Module: {self.module_code}

Generate a personalized welcome message and first instruction."""

            # Get LLM response
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                    ChatCompletionUserMessageParam(role="user", content=user_prompt)
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            content = safe_strip(getattr(response.choices[0].message, 'content', None))
            
            if content:
                return content
            else:
                # Fallback message
                if user_name:
                    if interview_type == "coding":
                        return f"Hello {user_name}, welcome to your mock interview session. I hope your preparation is going well. Please take a moment to review the problem above. When you're ready, walk me through your initial approach to solving this problem."
                    else:
                        return f"Hello {user_name}, welcome to your mock interview session. I hope your preparation is going well. Please take a moment to review the problem above. When you're ready, provide me a brief answer to the above given question."
                else:
                    if interview_type == "coding":
                        return "Hello! Welcome to your mock interview session. I hope your preparation is going well. Please take a moment to review the problem above. When you're ready, walk me through your initial approach to solving this problem."
                    else:
                        return "Hello! Welcome to your mock interview session. I hope your preparation is going well. Please take a moment to review the problem above. When you're ready, provide me a brief answer to the above given question."
                        
        except Exception as e:
            logger.error(f"Error generating personalized follow-up: {str(e)}")
            # Fallback message
            if user_name:
                return f"Hello {user_name}, welcome to your mock interview session. Please review the problem above and provide your answer."
            else:
                return "Hello! Welcome to your mock interview session. Please review the problem above and provide your answer."
    
    async def _create_session(
        self, base_question_data: Dict[str, Any], first_follow_up: str
    ) -> str:
        """Create the interview session in the database."""
        try:
            # Get RAG context
            rag_context = await self._get_rag_context()
            
            # Generate unique session ID
            from datetime import datetime
            session_id = f"{self.user_id}_{self.module_code}_{datetime.now().timestamp()}"
            
            # Get user name for session creation
            user_name = await self._get_user_name()
            
            # Create session with correct parameters
            await create_interview_session(
                user_id=self.user_id,
                session_id=session_id,
                topic=self.module_code,
                user_name=user_name,
                base_question_data=base_question_data,
                first_follow_up=first_follow_up,
                base_question_id=str(base_question_data.get("_id", ""))
            )
            
            # Add first follow-up question (this might be redundant since it's already added in create_interview_session)
            # await add_follow_up_question(session_id, first_follow_up)
            
            logger.info(f"Created interview session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    async def _get_rag_context(self) -> str:
        """Get RAG context for the topic."""
        try:
            retriever = await get_rag_retriever()
            if retriever:
                context_chunks = await retriever.retrieve_context(self.module_code)
                return "\n\n".join(context_chunks)
        except Exception as e:
            logger.warning(f"Failed to get RAG context: {e}")
        
        return ""
