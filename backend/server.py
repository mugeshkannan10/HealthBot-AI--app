from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# LLM Integration
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class HealthQuery(BaseModel):
    question: str
    user_id: Optional[str] = None

class HealthResponse(BaseModel):
    answer: str
    query_id: str
    timestamp: datetime

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    question: str
    answer: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    total: int

# Health Knowledge System Prompt
HEALTH_SYSTEM_PROMPT = """You are an AI-powered Public Health Assistant designed to provide accurate, helpful, and accessible health information to the general public. Your primary goals are:

1. **Disease Awareness & Prevention**: Provide clear information about common diseases, their symptoms, causes, and prevention methods
2. **Health Education**: Explain health concepts in simple, understandable language suitable for all education levels
3. **General Wellness**: Offer guidance on healthy lifestyle choices, nutrition, exercise, and mental health
4. **Symptom Information**: Help users understand symptoms and when to seek medical care

**Important Guidelines:**
- Always recommend consulting healthcare professionals for diagnosis and treatment
- Provide evidence-based information from reputable health organizations
- Use simple, clear language accessible to the general public
- Be empathetic and supportive in your responses
- Never provide specific medication dosages or replace professional medical advice
- Focus on prevention, awareness, and general health education
- If asked about serious symptoms, emphasize the importance of seeking immediate medical attention

**Response Format:**
- Keep responses concise but comprehensive
- Use bullet points for lists when helpful
- Include when to seek medical care when relevant
- End with encouraging, supportive language

Remember: You are promoting health awareness and education, not providing medical diagnosis or treatment."""

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "AI-Powered Public Health Chatbot API"}

@api_router.post("/health/query", response_model=HealthResponse)
async def ask_health_question(query: HealthQuery):
    """Process health-related questions using AI"""
    # Validate question is not empty
    if not query.question or not query.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")
    
    try:
        # Create unique session ID
        session_id = f"health_chat_{uuid.uuid4()}"
        
        # Initialize LLM Chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=HEALTH_SYSTEM_PROMPT
        ).with_model("openai", "gpt-4o")
        
        # Create user message
        user_message = UserMessage(text=query.question.strip())
        
        # Get AI response
        ai_response = await chat.send_message(user_message)
        
        # Store in database
        query_id = str(uuid.uuid4())
        user_id = query.user_id or "anonymous"
        
        chat_message = {
            "id": query_id,
            "user_id": user_id,
            "question": query.question,
            "answer": ai_response,
            "timestamp": datetime.now(timezone.utc),
            "category": "general_health"
        }
        
        await db.health_queries.insert_one(chat_message)
        
        return HealthResponse(
            answer=ai_response,
            query_id=query_id,
            timestamp=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logging.error(f"Error processing health query: {str(e)}")
        raise HTTPException(status_code=500, detail="Sorry, I encountered an error processing your health question. Please try again.")

@api_router.get("/health/history/{user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(user_id: str, limit: int = 20, skip: int = 0):
    """Get chat history for a user"""
    try:
        # Get total count
        total = await db.health_queries.count_documents({"user_id": user_id})
        
        # Get messages with pagination
        cursor = db.health_queries.find({"user_id": user_id}).sort("timestamp", -1).skip(skip).limit(limit)
        messages_data = await cursor.to_list(length=limit)
        
        messages = []
        for msg in messages_data:
            messages.append(ChatMessage(
                id=msg["id"],
                user_id=msg["user_id"],
                question=msg["question"],
                answer=msg["answer"],
                timestamp=msg["timestamp"],
                category=msg.get("category", "general_health")
            ))
        
        return ChatHistoryResponse(messages=messages, total=total)
        
    except Exception as e:
        logging.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching chat history")

@api_router.get("/health/stats")
async def get_health_stats():
    """Get basic statistics about health queries"""
    try:
        total_queries = await db.health_queries.count_documents({})
        unique_users = len(await db.health_queries.distinct("user_id"))
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        recent_queries = await db.health_queries.count_documents({"timestamp": {"$gte": yesterday}})
        
        return {
            "total_queries": total_queries,
            "unique_users": unique_users,
            "recent_queries_24h": recent_queries,
            "status": "active"
        }
        
    except Exception as e:
        logging.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching statistics")

# Original status check endpoints
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()