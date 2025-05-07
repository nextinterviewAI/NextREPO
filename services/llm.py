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

async def get_next_question(questions: List[Dict], is_base_question: bool = False, topic: str = None) -> str:
    """Generate next question based on conversation history and topic"""
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
            # For the first follow-up, use a natural interview question
            return "Can you walk me through your thought process on how you would approach this problem?"
        else:
            # For subsequent follow-ups, use the conversation history
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation,
                {"role": "user", "content": "Based on the candidate's response, ask a follow-up question that:\n"
                                          "1. Probes deeper into their understanding\n"
                                          "2. Asks about specific aspects of their solution\n"
                                          "3. Tests their technical knowledge\n"
                                          "4. Is relevant to their previous answer\n\n"
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

async def get_clarification(main_question: str, clarification_request: str) -> str:
    try:
        messages = [
            {"role": "system", "content": "You are a technical interviewer helping a candidate understand the question better. Your role is to provide guidance using ONLY business operations language. STRICTLY FORBIDDEN: Do not use ANY of these terms: database, table, schema, SQL, query, data, relationship, entity, attribute, field, key, primary key, foreign key, normalization, join, store, organize, structure, track, manage, information, system, or any other technical terms. NEVER use words like 'create', 'establish', 'write', or 'design'. Instead, explain what the business needs to do in simple, operational terms. Use only words like 'customer', 'book', 'order', 'purchase', 'name', 'title', 'date', 'quantity', etc. If the candidate asks about technical details, explain what the business needs to do in simple terms that guide them to discover the solution themselves."},
            {"role": "user", "content": f"Main question: {main_question}\n\nCandidate's clarification request: {clarification_request}\n\nProvide simple, business operations guidance:"}
        ]
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        clarification_resp = response.choices[0].message.content.strip()
        return clarification_resp
    except Exception as e:
        raise Exception(f"Error generating clarification: {str(e)}")

async def get_feedback(conversation: List[Dict], user_name: str):
    try:
        logger.info(f"Generating feedback for user: {user_name}")
        
        system_message = """You are a senior technical interviewer providing structured feedback.
        Your feedback should be balanced, constructive, and help the candidate improve.
        
        Guidelines for feedback:
        1. Be specific and provide examples from the interview
        2. Include both strengths and areas for improvement
        3. Focus on technical skills, problem-solving, and communication
        4. Provide actionable suggestions for improvement
        5. Be honest but professional in your assessment
        
        Format your response as a JSON object with these exact keys:
        {
            "summary": "Brief overview of the interview performance",
            "positive_points": ["List of specific strengths demonstrated"],
            "points_to_address": ["List of immediate concerns that need attention"],
            "areas_for_improvement": ["List of long-term development areas"]
        }"""

        prompt = """Based on the interview conversation, provide structured feedback for {user_name}.
        Make sure to:
        1. Identify at least 2-3 areas for improvement
        2. Point out specific technical gaps or misunderstandings
        3. Suggest ways to improve their approach
        4. Be constructive but honest in your assessment

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

async def check_answer_quality(questions: List[Dict], topic: str) -> str:
    try:
        # Format the answers for the LLM
        answers_text = "\n".join([
            f"Q{i+1}: {q['question']}\nA{i+1}: {q['answer']}" for i, q in enumerate(questions)
        ])
        prompt = (
            f"You are an expert technical interviewer. Review the following answers to {topic} interview questions. "
            "If the answers are mostly relevant, thoughtful, and show understanding, respond with 'good'. "
            "If the answers are mostly gibberish, irrelevant, or show no understanding, respond with 'bad'.\n"
            f"Answers:\n{answers_text}\n\nRespond with only 'good' or 'bad'."
        )
        messages = [
            {"role": "system", "content": "You are a strict technical interviewer."},
            {"role": "user", "content": prompt}
        ]
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.0,
            max_tokens=10
        )
        result = response.choices[0].message.content.strip().lower()
        if "good" in result:
            return "good"
        return "bad"
    except Exception as e:
        raise Exception(f"Error checking answer quality: {str(e)}")
