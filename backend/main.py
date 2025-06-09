import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from dotenv import load_dotenv
import logging
from datetime import datetime

from chatbot.agent import ChatbotAgent
from mavlink_parser.parser import MAVLinkParser
from models.chat_models import ChatMessage, ChatResponse, FlightDataQuery

# Load environment variables
load_dotenv()

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

# Global storage for parsed flight data
flight_data_store: Dict[str, Any] = {}

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {"message": "UAV Chatbot Backend is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/debug/flight-store")
async def debug_flight_store():
    """Debug endpoint to check current flight data store"""
    return {
        "has_data": "current_flight" in flight_data_store,
        "store_keys": list(flight_data_store.keys()),
        "data_summary": {
            key: type(value).__name__ if value else "None"
            for key, value in flight_data_store.items()
        }
    }

@app.post("/upload-flight-log")
async def upload_flight_log(file: UploadFile = File(...)):
    """Upload and parse a MAVLink .bin flight log file"""
    try:
        logger.info(f"Received file upload request: {file.filename}")
        logger.info(f"Content type: {file.content_type}")
        
        if not file.filename.endswith('.bin'):
            logger.warning(f"Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail="Only .bin files are supported"
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
        
        # Store parsed data globally (in production, use database)
        flight_data_store["current_flight"] = parsed_data
        flight_data_store["upload_info"] = {
            "filename": file.filename,
            "size": len(content),
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Stored flight data. Store keys: {list(flight_data_store.keys())}")
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Generate additional flight info
        flight_summary = await mavlink_parser.generate_summary(parsed_data)
        
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

@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(message: ChatMessage):
    """Handle chat messages from the frontend"""
    try:
        logger.info(f"Received chat message: {message.content}")
        
        # Get current flight data
        current_flight_data = flight_data_store.get("current_flight")
        logger.info(f"Flight data available: {current_flight_data is not None}")
        
        if current_flight_data:
            logger.info(f"Flight data keys: {list(current_flight_data.keys())}")
        
        if not current_flight_data and "flight" in message.content.lower():
            logger.info("No flight data found, returning info message")
            return ChatResponse(
                content="No flight data loaded. Please upload a .bin flight log file first.",
                message_type="info"
            )
        
        # Process message with chatbot agent
        response = await chatbot_agent.process_message(
            message.content, 
            current_flight_data,
            message.session_id
        )
        
        return ChatResponse(
            content=response["content"],
            message_type=response.get("type", "response"),
            data=response.get("data")
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/flight-summary")
async def get_flight_summary():
    """Get a summary of the currently loaded flight data"""
    current_flight_data = flight_data_store.get("current_flight")
    
    if not current_flight_data:
        raise HTTPException(status_code=404, detail="No flight data loaded")
    
    try:
        summary = await mavlink_parser.generate_summary(current_flight_data)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.post("/query-flight-data")
async def query_flight_data(query: FlightDataQuery):
    """Execute specific queries against flight data"""
    current_flight_data = flight_data_store.get("current_flight")
    
    if not current_flight_data:
        raise HTTPException(status_code=404, detail="No flight data loaded")
    
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