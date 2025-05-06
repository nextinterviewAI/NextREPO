import openai
import os
from dotenv import load_dotenv
from fastapi import HTTPException
import asyncio
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY environment variable is required")

client = openai.AsyncOpenAI(api_key=openai_api_key)
logger.info("OpenAI API client initialized successfully")

MAX_RETRIES = 3
RETRY_DELAY = 1

SYSTEM_PROMPT = """You are a senior data science interviewer with 10+ years of experience.
Your role is to conduct a technical interview focusing on the candidate's problem-solving approach.

Guidelines:
1. NEVER provide solutions or answers to your questions
2. Ask follow-up questions that probe deeper into the candidate's approach
3. Focus on understanding their thought process and decision-making
4. Challenge assumptions and ask for justification
5. Ask for specific examples and implementations
6. Maintain a professional but conversational tone
7. If the candidate's answer is unclear, ask for clarification
8. Cover technical aspects of their approach: data handling, model selection, evaluation metrics, etc.

Remember: Your goal is to assess the candidate's problem-solving skills and technical understanding, not to teach or provide answers."""

async def retry_with_backoff(func, *args, **kwargs):
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt == MAX_RETRIES - 1:
                logger.error(f"OpenAI API error after {MAX_RETRIES} attempts: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"OpenAI API error: {str(e)}. Please check your API key and try again."
                )
            logger.warning(f"OpenAI API attempt {attempt + 1} failed: {str(e)}")
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
    raise last_error

def format_conversation(conversation: List[Dict]) -> str:
    formatted = ""
    for i, turn in enumerate(conversation, 1):
        formatted += f"Interviewer: {turn['question']}\n"
        if turn['answer']:
            formatted += f"Candidate: {turn['answer']}\n"
    return formatted

async def get_next_question(questions: List[Dict], is_base_question: bool = False) -> str:
    """Generate next question based on conversation history"""
    try:
        logger.info("Generating next question...")
        
        # Convert questions array to conversation format
        conversation = []
        for q in questions:
            if "question" in q and "answer" in q:
                conversation.append({
                    "role": "assistant",
                    "content": q["question"]
                })
                if q["answer"]:
                    conversation.append({
                        "role": "user",
                        "content": q["answer"]
                    })
        
        if is_base_question:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "The candidate has been presented with a technical question about K-Means clustering. Ask them about their approach to solving it.\n"
                                          "The question should:\n"
                                          "1. Be specific to K-Means clustering and the elbow method\n"
                                          "2. Ask about their understanding of the algorithm\n"
                                          "3. Focus on their implementation approach\n"
                                          "4. Be clear and concise\n\n"
                                          "Next question:"}
            ]
        else:
            # Get the original question to maintain context
            original_question = questions[0]["question"] if questions else ""
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation,
                {"role": "user", "content": f"Based on the candidate's response about K-Means clustering, ask a follow-up question that:\n"
                                          "1. Stays focused on K-Means clustering and the elbow method\n"
                                          "2. Probes deeper into their implementation approach\n"
                                          "3. Asks about specific aspects of the algorithm\n"
                                          "4. Tests their understanding of clustering concepts\n\n"
                                          "Original question: {original_question}\n\n"
                                          "Next question:"}
            ]
        
        logger.info(f"Sending request to OpenAI with messages: {messages}")
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        next_question = response.choices[0].message.content.strip()
        logger.info(f"Successfully generated next question: {next_question}")
        return next_question
    except Exception as e:
        logger.error(f"Error generating next question: {str(e)}", exc_info=True)
        raise

async def get_feedback(conversation: List[Dict], user_name: str):
    try:
        logger.info(f"Generating feedback for user: {user_name}")
        
        system_message = """You are a senior data science interviewer providing structured feedback.
        Your feedback should be organized into the following categories:
        1. Summary: A brief overview of the interview performance
        2. Positive Points: Specific strengths demonstrated during the interview
        3. Points to Address: Areas that need immediate attention
        4. Areas for Improvement: Long-term development suggestions
        
        Focus on:
        - Problem-solving approach
        - Technical understanding
        - Communication skills
        - Implementation details
        - Technical decision-making
        
        Provide specific examples from the interview for each category."""

        prompt = """Based on the interview conversation, provide structured feedback for {user_name}.
        Format your response as a JSON object with these exact keys:
        {{
            "summary": "Brief overview of the interview performance",
            "positive_points": ["List of specific strengths demonstrated"],
            "points_to_address": ["List of immediate concerns"],
            "areas_for_improvement": ["List of long-term development areas"]
        }}

        Interview conversation:
        {conversation}
        
        Feedback:"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt.format(
                user_name=user_name,
                conversation=format_conversation(conversation)
            )}
        ]

        logger.info(f"Sending request to OpenAI with messages: {messages}")

        async def call_openai():
            try:
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.5,
                    max_tokens=500,
                    response_format={ "type": "json_object" }
                )
                if not response or not response.choices or not response.choices[0].message:
                    raise ValueError("Invalid response from OpenAI API")
                return response.choices[0].message.content.strip()
            except openai.AuthenticationError as e:
                logger.error("OpenAI Authentication Error: Invalid API key")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid OpenAI API key. Please check your API key in the .env file."
                )
            except openai.RateLimitError as e:
                logger.error("OpenAI Rate Limit Error")
                raise HTTPException(
                    status_code=429,
                    detail="OpenAI API rate limit exceeded. Please try again later."
                )
            except Exception as e:
                logger.error(f"OpenAI API call failed: {str(e)}", exc_info=True)
                raise

        result = await retry_with_backoff(call_openai)
        if not result:
            raise ValueError("Empty response from OpenAI API")
            
        logger.info(f"Successfully generated feedback: {result}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating feedback: {str(e)}. Please try again."
        )
