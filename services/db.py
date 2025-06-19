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
 
DB_NAME = os.getenv("DB_NAME", "test")
if not DB_NAME:
    raise ValueError("DB_NAME environment variable is not set")
 
# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
 
async def get_db():
    """Get database instance"""
    return db
 
async def fetch_base_question(topic: str):
    """Fetch base question for a topic from mainquestionbanks"""
    try:
        logger.info(f"Fetching base question for topic: {topic}")
        
        # Step 1: Get topic document to find its ID
        topic_doc = await db.interview_topics.find_one({"topic": topic})
        if not topic_doc:
            raise Exception(f"Topic '{topic}' not found")
        
        topic_id = str(topic_doc["_id"])
        logger.info(f"Found topic ID: {topic_id}")

        # Step 2: Aggregate to get one random mock-available question
        pipeline = [
            {
                "$match": {
                    "topicId": topic_id,
                    "isAvailableForMock": True,
                    "isDeleted": False
                }
            },
            {"$sample": {"size": 1}}
        ]

        cursor = db.mainquestionbanks.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if not result:
            logger.warning(f"No questions found for topic '{topic}'")
            raise Exception(f"No questions found for topic '{topic}'")

        question_doc = result[0]
        logger.info(f"Fetched question: {question_doc.get('question', 'No question text')}")

        # Return standardized structure expected by route
        return {
            "question": question_doc.get("question", ""),
            "code_stub": question_doc.get("base_code", ""),
            "language": question_doc.get("programming_language", ""),
            "difficulty": question_doc.get("level", ""),
            "example": question_doc.get("description", ""),
            "tags": [t["topic_name"] for t in question_doc.get("topics", [])]
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
        await db.interview_topics.drop_index("topic_1")
        await db.interview_topics.create_index("topic", unique=True)
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
    """Check MongoDB collections and their contents (updated version)"""
    try:
        # List all collections
        collections = await db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Check interview_topics collection
        if "interview_topics" in collections:
            topics = await db.interview_topics.find({}).to_list(length=10)
            logger.info(f"Topics in interview_topics collection: {topics}")
        else:
            logger.info("interview_topics collection does not exist")

        # Check mainquestionbanks collection (your new source of questions)
        if "mainquestionbanks" in collections:
            sample = await db.mainquestionbanks.find(
                {}, 
                {"question": 1, "topicId": 1, "isAvailableForMock": 1}
            ).limit(5).to_list(length=5)
            logger.info(f"Sample from mainquestionbanks: {sample}")
        else:
            logger.info("mainquestionbanks collection does not exist")

    except Exception as e:
        logger.error(f"Error checking collections: {str(e)}", exc_info=True)
        raise
 