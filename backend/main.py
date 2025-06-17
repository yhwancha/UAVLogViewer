import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from dotenv import load_dotenv
import logging
import datetime
import json
import redis.asyncio as aioredis

from chatbot.agent import ChatbotAgent
from mavlink_parser.parser import MAVLinkParser
from models.chat_models import ChatMessage, ChatResponse, FlightDataQuery

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UAV Chatbot Backend", version="1.0.0")

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global components
chatbot_agent = ChatbotAgent()
mavlink_parser = MAVLinkParser()

# Redis connection (singleton)
redis = None

def convert_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@app.on_event("startup")
async def startup_event():
    global redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)

@app.on_event("shutdown")
async def shutdown_event():
    global redis
    if redis:
        await redis.close()

@app.get("/")
async def root():
    return {"message": "UAV Chatbot Backend is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/debug/flight-store")
async def debug_flight_store():
    keys = await redis.keys("*:*")
    chat_keys = await redis.keys("chat_history:*:*")
    return {
        "flight_store_keys": keys,
        "chat_history_keys": chat_keys
    }

@app.post("/upload-flight-log")
async def upload_flight_log(
    file: UploadFile = File(...),
    timestamp: str = Query(..., description="Upload timestamp (e.g., 20240607T153000)")
):
    """Upload and parse a MAVLink flight log file (.bin or .tlog)"""
    try:
        logger.info(f"Received file upload request: {file.filename}")
        logger.info(f"Content type: {file.content_type}")
        logger.info(f"Timestamp: {timestamp}")
        
        # Support both .bin (DataFlash) and .tlog (telemetry) files
        if not (file.filename.endswith('.bin') or file.filename.endswith('.tlog')):
            logger.warning(f"Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail="Only .bin and .tlog files are supported"
            )
        
        # Save uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        content = await file.read()
        logger.info(f"File size: {len(content)} bytes")
        
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Parse the MAVLink data
        logger.info(f"Starting to parse file: {temp_path}")
        parsed_data = await mavlink_parser.parse_file(temp_path)
        logger.info(f"Parsed data keys: {list(parsed_data.keys()) if parsed_data else 'None'}")
        
        # Store parsed data in Redis with the key 'filename:timestamp'
        redis_key = f"{file.filename}:{timestamp}"
        await redis.set(redis_key, json.dumps(parsed_data, default=convert_datetime), ex=86400)
        logger.info(f"Stored flight data in Redis. Key: {redis_key}")
        
        # Store summary separately as 'summary:filename:timestamp'
        flight_summary = await mavlink_parser.generate_summary(parsed_data)
        summary_key = f"summary:{file.filename}:{timestamp}"
        await redis.set(summary_key, json.dumps(flight_summary, default=convert_datetime), ex=86400)
        logger.info(f"Stored flight summary in Redis. Key: {summary_key}")
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Format duration
        duration = parsed_data.get("flight_duration", 0)
        if duration and duration > 0:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration_text = f"{minutes}m {seconds}s"
        else:
            duration_text = "Unknown"
        
        response_data = {
            "message": "Flight log uploaded and parsed successfully",
            "flight_info": {
                "duration": duration_text,
                "duration_seconds": parsed_data.get("flight_duration", 0),
                "messages_count": len(parsed_data.get("messages", [])),
                "start_time": parsed_data.get("start_time", "Unknown"),
                "vehicle_type": parsed_data.get("vehicle_type", "Unknown"),
                "max_altitude": parsed_data.get("flight_stats", {}).get("max_altitude", "Unknown"),
                "summary": flight_summary
            }
        }
        logger.info(f"Returning response: {response_data}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

async def get_flight_data(filename: str, timestamp: str):
    if not filename or not timestamp:
        return None
    redis_key = f"{filename}:{timestamp}"
    data = await redis.get(redis_key)
    if not data:
        return None
    return json.loads(data)

async def get_chat_history(filename: str, timestamp: str):
    key = f"chat_history:{filename}:{timestamp}"
    data = await redis.get(key)
    return json.loads(data) if data else []

async def save_chat_history(filename: str, timestamp: str, history: list):
    key = f"chat_history:{filename}:{timestamp}"
    await redis.set(key, json.dumps(history, default=convert_datetime), ex=86400)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(
    message: ChatMessage,
    filename: str = Query(..., description="Flight log file name (e.g., log1.bin)"),
    timestamp: str = Query(..., description="Upload timestamp (e.g., 20240607T153000)")
):
    """Handle chat messages from the frontend"""
    try:
        logger.info(f"Received chat message: {message.content}")
        logger.info(f"Filename: {filename}, Timestamp: {timestamp}")
        current_flight_data = await get_flight_data(filename, timestamp)
        if not current_flight_data:
            logger.info("No flight data found, returning info message")
            return ChatResponse(
                content="No flight data loaded. Please upload a .bin or .tlog flight log file first.",
                message_type="info"
            )
        # Load chat history
        history = await get_chat_history(filename, timestamp)
        history.append({"role": "user", "content": message.content})
        # Pass history to agent if needed
        response = await chatbot_agent.process_message(
            message.content, 
            current_flight_data,
            message.session_id
        )
        history.append({"role": "assistant", "content": response["content"]})
        await save_chat_history(filename, timestamp, history)
        return ChatResponse(
            content=response["content"],
            message_type=response.get("type", "response"),
            data=response.get("data")
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/flight-summary")
async def get_flight_summary(
    filename: str = Query(..., description="Flight log file name (e.g., log1.bin)"),
    timestamp: str = Query(..., description="Upload timestamp (e.g., 20240607T153000)")
):
    """Get a summary of the currently loaded flight data"""
    summary_key = f"summary:{filename}:{timestamp}"
    summary_data = await redis.get(summary_key)
    if not summary_data:
        raise HTTPException(status_code=404, detail="No summary data loaded for this file/timestamp")
    try:
        summary = json.loads(summary_data)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading summary: {str(e)}")

@app.post("/query-flight-data")
async def query_flight_data(
    query: FlightDataQuery,
    filename: str = Query(..., description="Flight log file name (e.g., log1.bin)"),
    timestamp: str = Query(..., description="Upload timestamp (e.g., 20240607T153000)")
):
    """Execute specific queries against flight data"""
    current_flight_data = await get_flight_data(filename, timestamp)
    
    if not current_flight_data:
        raise HTTPException(status_code=404, detail="No flight data loaded for this file/timestamp")
    
    try:
        result = await mavlink_parser.execute_query(current_flight_data, query.query_type, query.parameters)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True,
        log_level="info"
    ) 