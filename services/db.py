from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import logging
import random
from datetime import datetime
 
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
if not MONGO_URI:
    raise ValueError("MONGODB_URI environment variable is not set")
 
DB_NAME = os.getenv("DB_NAME", "test")
if not DB_NAME:
    raise ValueError("DB_NAME environment variable is not set")
 
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

async def get_db():
    """Get database instance"""
    return db
 
async def fetch_base_question(topic: str):
    """Fetch base question for a topic from mainquestionbanks"""
    try:
        logger.info(f"Fetching base question for topic: {topic}")
        
        topic_doc = await db.interview_topics.find_one({"topic": topic})
        if not topic_doc:
            raise Exception(f"Topic '{topic}' not found")
        
        topic_id = topic_doc["_id"]
        logger.info(f"Found topic ID: {topic_id}")

        pipeline = [
            {
                "$match": {
                    "topicId": topic_id,
                    "$or": [
                        {"isAvailableForMock": True},
                        {"isAvailableForMockInterview": True}
                    ],
                    "isDeleted": False
                }
            },
            {"$sample": {"size": 1}}
        ]

        count = await db.mainquestionbanks.count_documents({
            "topicId": topic_id,
            "$or": [
                {"isAvailableForMock": True},
                {"isAvailableForMockInterview": True}
            ],
            "isDeleted": False
        })
        logger.warning(f"Found {count} available questions for topic '{topic}' with topicId {topic_id}")

        cursor = db.mainquestionbanks.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if not result:
            logger.warning(f"No questions found for topic '{topic}' (topicId: {topic_id})")
            raise Exception(f"No questions found for topic '{topic}' (topicId: {topic_id})")

        question_doc = result[0]
        logger.info(f"Fetched question: {question_doc.get('question', 'No question text')}")

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
    
async def create_indexes():
    """Create necessary indexes"""
    try:
        await db.interview_topics.drop_index("topic_1")
        await db.interview_topics.create_index("topic", unique=True)
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
       
        topics = await db.interview_topics.find({}).to_list(length=None)
        logger.error(f"Raw topics data: {topics}")
       
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

        if "interview_topics" in collections:
            topics = await db.interview_topics.find({}).to_list(length=10)
            logger.info(f"Topics in interview_topics collection: {topics}")
        else:
            logger.info("interview_topics collection does not exist")

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

async def validate_user_id(user_id: str) -> bool:
    """Check if a user with the given user_id exists in the users collection."""
    db = await get_db()
    user = await db.users.find_one({"_id": user_id})
    return user is not None

async def save_user_ai_interaction(user_id: str, endpoint: str, input_data: dict, ai_response: dict, meta: dict = None):
    db = await get_db()
    doc = {
        "user_id": user_id,
        "timestamp": datetime.utcnow(),
        "endpoint": endpoint,
        "input": input_data,
        "ai_response": ai_response
    }
    if meta:
        doc["meta"] = meta
    await db.user_ai_interactions.insert_one(doc)

async def fetch_interactions_for_session(user_id: str, session_id: str):
    db = await get_db()
    interactions = await db.user_ai_interactions.find({
        "user_id": user_id,
        "input.session_id": session_id
    }).sort("timestamp", 1).to_list(length=None)
    return interactions

async def fetch_user_history(user_id: str, limit: int = 50):
    db = await get_db()
    interactions = await db.user_ai_interactions.find({
        "user_id": user_id
    }).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return interactions

# Advanced session reconstruction

def reconstruct_session_state(interactions):
    """
    Given a list of interactions (sorted by timestamp), reconstruct the session state:
    - questions: list of {question, answer}
    - clarifications: list of {clarification, response}
    - question_count, topic, etc.
    """
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
                if session_data["questions"]:
                    session_data["questions"][-1]["answer"] = inp.get("answer")
                if "question" in resp:
                    session_data["questions"].append({"question": resp["question"], "answer": ""})
                session_data["question_count"] = session_data.get("question_count", 1) + 1
    return session_data

async def fetch_user_session_summaries(user_id: str, limit: int = 20):
    db = await get_db()
    # Aggregate sessions by session_id
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$input.session_id",
            "first": {"$first": "$timestamp"},
            "last": {"$last": "$timestamp"},
            "topic": {"$first": "$input.topic"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"last": -1}},
        {"$limit": limit}
    ]
    summaries = await db.user_ai_interactions.aggregate(pipeline).to_list(length=limit)
    # Format output
    return [
        {
            "session_id": s["_id"],
            "topic": s.get("topic"),
            "start_time": s.get("first"),
            "end_time": s.get("last"),
            "interaction_count": s.get("count")
        }
        for s in summaries if s["_id"]
    ]
 