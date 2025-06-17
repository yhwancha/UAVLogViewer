import logging
from typing import Dict, Any, Optional
from datetime import datetime

from models.chat_models import ConversationState
from .flight_analyzer import FlightAnalyzer
from .query_handler import QueryHandler

logger = logging.getLogger(__name__)

class ChatbotAgent:
    """Main chatbot agent that routes messages and manages conversations"""
    
    # Keywords for detecting different types of requests
    ANOMALY_KEYWORDS = {
        'anomaly', 'anomalies', 'issue', 'issues', 'problem', 'problems', 
        'wrong', 'unusual', 'concerning', 'detect', 'spot', 'find problems'
    }
    
    FLIGHT_RELATED_TERMS = {
        'flight', 'altitude', 'battery', 'gps', 'signal', 'error', 'temperature',
        'voltage', 'rc', 'radio', 'control', 'telemetry', 'log', 'data', 'bin'
    }

    def __init__(self):
        self.flight_analyzer = FlightAnalyzer()
        self.query_handler = QueryHandler()
        self.conversations: Dict[str, ConversationState] = {}

    async def process_message(self, message: str, flight_data: Optional[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """Process incoming chat message and route to appropriate handler"""
        try:
            conversation = self._get_or_create_conversation(session_id)
            self._add_user_message(conversation, message)
            
            if flight_data:
                return await self._handle_flight_data(message, flight_data, conversation, session_id)
            else:
                return await self._handle_no_flight_data(message, conversation)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._create_response("I apologize, but I encountered an error processing your request. Please try again.", 'error')


    async def _handle_flight_data(self, message: str, flight_data: Dict[str, Any], conversation: ConversationState, session_id: str) -> Dict[str, Any]:
        """Handle queries when flight data is available"""
        try:
            # Check if clarification is needed
            clarification = await self.query_handler.check_for_clarification(message, flight_data)
            if clarification:
                return clarification
            
            # Execute appropriate analysis
            if self._is_anomaly_request(message):
                response = await self.flight_analyzer.execute_anomaly_analysis(message, flight_data, session_id)
                analysis_method = 'anomaly_detection'
            else:
                response = await self.flight_analyzer.execute_standard_analysis(message, flight_data, session_id)
                analysis_method = 'standard_analysis'
            
            # Add to conversation and return response
            conversation.add_message('assistant', response)
            return self._create_response(response, 'response', {
                'has_flight_data': True,
                'analysis_method': analysis_method
            })
                
        except Exception as e:
            logger.error(f"Error in flight data analysis: {e}")
            return self._create_response("I encountered an error analyzing the flight data. Please try rephrasing your question.", 'error')

    async def _handle_no_flight_data(self, message: str, conversation: ConversationState) -> Dict[str, Any]:
        """Handle queries when no flight data is available"""
        if self._is_flight_related_query(message):
            return self._create_no_flight_data_response()
        
        # Handle general queries with clarification
        result = await self.flight_analyzer.handle_general_query_with_clarification(message)
        
        # Add to conversation if it's a response (not clarification)
        if result.get('type') == 'response':
            conversation.add_message('assistant', result['content'])
        
        return result

    def _get_or_create_conversation(self, session_id: str) -> ConversationState:
        """Get existing conversation or create new one"""
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationState(session_id=session_id)
        return self.conversations[session_id]

    def _add_user_message(self, conversation: ConversationState, message: str):
        """Add user message to conversation history"""
        conversation.messages.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })

    def _is_anomaly_request(self, message: str) -> bool:
        """Check if the message is requesting anomaly detection"""
        return any(keyword in message.lower() for keyword in self.ANOMALY_KEYWORDS)

    def _is_flight_related_query(self, message: str) -> bool:
        """Check if the message is related to flight data analysis"""
        return any(term in message.lower() for term in self.FLIGHT_RELATED_TERMS)

    def _create_response(self, content: str, response_type: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create standardized response format"""
        response = {
            'content': content,
            'type': response_type
        }
        if data:
            response['data'] = data
        return response

    def _create_no_flight_data_response(self) -> Dict[str, Any]:
        """Create response when flight data is requested but not available"""
        return {
            'content': "I'd be happy to analyze flight data, but I don't have any .bin log file loaded currently. Please upload a .bin file using the main file drop zone, and I'll be able to answer detailed questions about altitude, battery performance, GPS signal, errors, flight duration, and much more.",
            'type': 'clarification',
            'suggested_questions': [
                "Upload a .bin file to get started with analysis",
                "What kind of flight data can you analyze?",
                "How do I interpret MAVLink telemetry data?"
            ]
        } 