from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ChatMessage(BaseModel):
    content: str
    session_id: str = Field(alias="sessionId")
    timestamp: Optional[datetime] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    content: str
    message_type: str = "response"  # response, info, error, clarification
    timestamp: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    requires_clarification: bool = False
    suggested_questions: Optional[List[str]] = None

class FlightDataQuery(BaseModel):
    query_type: str  # altitude, gps_loss, battery, flight_time, errors, rc_loss
    parameters: Optional[Dict[str, Any]] = None

class ConversationState(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]] = []
    context: Dict[str, Any] = {}
    last_query: Optional[str] = None
    awaiting_clarification: bool = False
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation history"""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })

class FlightAnalysisResult(BaseModel):
    query: str
    result: Any
    confidence: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None 