import openai
import os
from dotenv import load_dotenv
from fastapi import HTTPException
import asyncio
from typing import List, Dict
import logging
import json

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

SYSTEM_PROMPT = """You are a senior technical interviewer with 10+ years of experience.
Your role is to conduct a technical interview focusing on the candidate's problem-solving approach.

Guidelines:
1. NEVER provide solutions or answers to your questions
2. Ask follow-up questions that probe deeper into the candidate's approach
3. Focus on understanding their thought process and decision-making
4. Challenge assumptions and ask for justification
5. Ask for specific examples and implementations
6. Maintain a professional but conversational tone
7. If the candidate's answer is unclear, ask for clarification
8. After 4 good answers, transition to the coding phase
9. During coding phase, act like a real interviewer:
   - Never provide solutions or hints
   - Guide candidates to think through problems
   - Only respond to specific questions
   - Focus on their problem-solving approach
10. Keep questions focused and relevant to the topic

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

async def get_feedback(conversation: List[Dict], user_name: str) -> str:
    """Generate feedback based on the interview conversation"""
    try:
        # Format conversation for feedback
        formatted_conversation = []
        for msg in conversation:
            if "question" in msg and "answer" in msg:
                formatted_conversation.append(f"Interviewer: {msg['question']}")
                formatted_conversation.append(f"Candidate: {msg['answer']}")
        
        conversation_text = "\n".join(formatted_conversation)
        
        # Create feedback prompt
        feedback_prompt = f"""Based on the following interview conversation with {user_name}, provide a comprehensive and personalized feedback in JSON format. The feedback should:

1. Include a personalized 2-3 line summary that specifically references {user_name}'s performance and unique aspects of their responses
2. Provide three modules with exactly 3 points each, all personalized to {user_name}'s specific answers:
   - Positive Points: What {user_name} did well, with specific examples from their responses
   - Points to Address: Specific areas where {user_name}'s answers could be improved
   - Areas for Improvement: Broader areas for {user_name}'s growth, based on their actual responses

Guidelines:
- Use {user_name}'s name in the summary
- Reference specific examples from their answers
- Be specific about what they said or didn't say
- Focus on their unique responses, not generic feedback
- If their answers were unclear or incorrect, explicitly state this
- If they showed particular strengths, highlight those specific instances

Format the response as a JSON object with the following structure:
{{
    "summary": "2-3 line personalized summary mentioning {user_name} and their specific performance",
    "positive_points": [
        "specific point about {user_name}'s good response",
        "specific point about {user_name}'s good response",
        "specific point about {user_name}'s good response"
    ],
    "points_to_address": [
        "specific point about {user_name}'s response that needs improvement",
        "specific point about {user_name}'s response that needs improvement",
        "specific point about {user_name}'s response that needs improvement"
    ],
    "areas_for_improvement": [
        "specific area where {user_name} could improve based on their responses",
        "specific area where {user_name} could improve based on their responses",
        "specific area where {user_name} could improve based on their responses"
    ]
}}

Interview conversation:
{conversation_text}

Provide the feedback in the exact JSON format specified above, with no additional text or explanation. Ensure the response is valid JSON and specifically references {user_name}'s performance."""
        
        # Get feedback from OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert interviewer providing detailed, constructive feedback. Be specific and actionable in your feedback points. Always personalize feedback for {user_name} and reference their specific responses. Always return valid JSON."},
                {"role": "user", "content": feedback_prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={ "type": "json_object" }
        )
        
        # Extract and validate the feedback
        feedback = response.choices[0].message.content.strip()
        
        # Validate JSON format
        try:
            feedback_dict = json.loads(feedback)
            
            # Ensure all required fields are present
            required_fields = ["summary", "positive_points", "points_to_address", "areas_for_improvement"]
            for field in required_fields:
                if field not in feedback_dict:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure each list has exactly 3 points
            for field in ["positive_points", "points_to_address", "areas_for_improvement"]:
                if not isinstance(feedback_dict[field], list) or len(feedback_dict[field]) != 3:
                    raise ValueError(f"{field} must contain exactly 3 points")
            
            # Validate personalization
            if user_name.lower() not in feedback_dict["summary"].lower():
                raise ValueError("Summary must include the user's name")
            
            return feedback
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in feedback: {str(e)}")
            raise Exception("Invalid feedback format received from OpenAI")
        except ValueError as e:
            logger.error(f"Invalid feedback structure: {str(e)}")
            raise Exception(f"Invalid feedback structure: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error generating feedback: {str(e)}", exc_info=True)
        raise Exception(f"Error generating feedback: {str(e)}")

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

async def generate_optimized_code(question: str, user_code: str) -> str:
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a senior software engineer specializing in writing clean, efficient, and maintainable code. Your task is to review and optimize the provided code snippet based on best practices, readability, performance, and correctness."
            },
            {
                "role": "user",
                "content": f"Question Context: {question}\n\nUser Code:\n{user_code}\n\nPlease provide an optimized version of this code and explain the changes made."
            }
        ]
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.4,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating optimized code: {str(e)}", exc_info=True)
        raise