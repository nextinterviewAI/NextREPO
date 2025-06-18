from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import logging
import random
 
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
load_dotenv()
 
# MongoDB configuration
MONGO_URI = os.getenv("MONGODB_URI")
if not MONGO_URI:
    raise ValueError("MONGODB_URI environment variable is not set")
 
DB_NAME = os.getenv("DB_NAME")
if not DB_NAME:
    raise ValueError("DB_NAME environment variable is not set")
 
# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
 
async def get_db():
    """Get database instance"""
    return db
 
async def fetch_base_question(topic: str):
    """Fetch base question for a topic"""
    try:
        logger.error(f"Attempting to fetch base question for topic: {topic}")
       
        # First find the topic document
        logger.error(f"Searching for topic document with topic: {topic}")
        topic_doc = await db.interview_topics.find_one({"topic": topic})
       
        if not topic_doc:
            all_topics = await db.interview_topics.find({}).to_list(length=None)
            logger.error(f"All topic documents: {all_topics}")
            available_topics = []
            for t in all_topics:
                if "topic" in t:
                    available_topics.append(t["topic"])
            logger.error(f"Topic '{topic}' not found in database. Available topics are: {available_topics}")
            raise Exception(f"Topic '{topic}' not found")
           
        logger.error(f"Found topic document: {topic_doc}")
       
        # Then find the question for this topic using the topic's _id
        topic_id = str(topic_doc.get("_id"))
        logger.error(f"Searching for questions with topic_id: {topic_id}")
        question = await db.interview_questions.find_one({"topic_id": topic_id})
       
        if not question:
            logger.error(f"No questions found for topic '{topic}' with ID {topic_id}")
            raise Exception(f"No questions found for topic '{topic}'")
           
        logger.error(f"Selected question document: {question}")
        logger.error(f"Question language field: {question.get('language')}")
       
        # Get language with SQL default for SQL Modelling topic
        language = question.get("language")
        if topic == "SQL Modelling":
            language = "mysql"
        elif not language:
            language = "python"  # Default to python if not specified
           
        logger.error(f"Final language value: {language}")
       
        # Return the complete question document
        return {
            "question": question.get("question", ""),
            "difficulty": question.get("difficulty", "Medium"),
            "example": question.get("example", ""),
            "code_stub": question.get("code_stub", ""),
            "tags": question.get("tags", []),
            "language": language  # Use the processed language value
        }
    except Exception as e:
        logger.error(f"Error fetching base question: {str(e)}", exc_info=True)
        raise
 
async def save_session_data(session_id: str, data: dict):
    """Save interview session data"""
    try:
        await db.interview_sessions.insert_one({
            "session_id": session_id,
            **data
        })
    except Exception as e:
        logger.error(f"Error saving session data: {str(e)}")
        raise
 
async def create_indexes():
    """Create necessary indexes"""
    try:
        await db.interview_topics.create_index("name", unique=True)
        await db.interview_sessions.create_index("session_id", unique=True)
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise
 
async def get_available_topics():
    """Get list of available topics"""
    try:
        # First check if the collection exists
        collections = await db.list_collection_names()
        logger.error(f"Available collections: {collections}")
       
        if "interview_topics" not in collections:
            logger.error("interview_topics collection does not exist")
            return []
           
        # Get all topics and log their structure
        topics = await db.interview_topics.find({}).to_list(length=None)
        logger.error(f"Raw topics data: {topics}")
       
        # Extract topics safely
        available_topics = []
        for topic in topics:
            if "topic" in topic:
                available_topics.append(topic["topic"])
            else:
                logger.error(f"Topic document missing 'topic' field: {topic}")
               
        logger.error(f"Available topics: {available_topics}")
        return available_topics
    except Exception as e:
        logger.error(f"Error getting topics: {str(e)}", exc_info=True)
        raise
 
async def check_collections():
    """Check MongoDB collections and their contents"""
    try:
        # List all collections
        collections = await db.list_collection_names()
        logger.error(f"Available collections: {collections}")
       
        # Check interview_topics collection
        if "interview_topics" in collections:
            topics = await db.interview_topics.find({}).to_list(length=None)
            logger.error(f"Topics in interview_topics collection: {topics}")
        else:
            logger.error("interview_topics collection does not exist")
           
        # Check interview_questions collection
        if "interview_questions" in collections:
            questions = await db.interview_questions.find({}).to_list(length=None)
            logger.error(f"Questions in interview_questions collection: {questions}")
        else:
            logger.error("interview_questions collection does not exist")
    except Exception as e:
        logger.error(f"Error checking collections: {str(e)}", exc_info=True)
        raise
 