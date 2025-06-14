import os
import asyncio
from typing import Optional, Dict, Any
import logging

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI package not installed. Install with: pip install openai")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.openai_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI package is not available")
            return
            
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
            return
            
        try:
            self.openai_client = openai.OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")

    async def generate_response(self, message: str, context: str = "", 
                              system_prompt: str = "") -> str:
        """Generate response using OpenAI API"""
        
        if not self.openai_client:
            return self._generate_fallback_response(message)
        
        try:
            return await self._generate_openai_response(message, context, system_prompt)
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return "I apologize, but I'm having trouble connecting to the AI service. Please check your OpenAI API key and try again."

    async def _generate_openai_response(self, message: str, context: str, system_prompt: str) -> str:
        """Generate response using OpenAI API"""
        try:
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add context if provided
            if context:
                messages.append({"role": "user", "content": f"Context: {context}"})
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            # Call OpenAI API
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                timeout=30
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _generate_fallback_response(self, message: str) -> str:
        """Generate a basic response when OpenAI is not available"""
        message_lower = message.lower()
        if any(word in message_lower for word in ['altitude', 'height', 'high']):
            return (
                "I'm unable to analyze altitude data right now because the AI analysis service is not available. "
                "Please check your OpenAI API key in the .env file and try again. "
                "Once enabled, I can provide detailed altitude insights from your flight log."
            )
        elif any(word in message_lower for word in ['battery', 'power', 'voltage']):
            return (
                "Battery analysis is currently unavailable because the AI service is not connected. "
                "Please verify your OpenAI API configuration. "
                "With AI enabled, I can analyze battery voltage, current, and temperature from your log."
            )
        elif any(word in message_lower for word in ['gps', 'satellite', 'navigation']):
            return (
                "GPS data analysis requires the AI service, which is not active at the moment. "
                "Please ensure your OpenAI API key is set up correctly. "
                "When enabled, I can provide insights on GPS signal quality and loss events."
            )
        elif any(word in message_lower for word in ['time', 'duration']):
            return (
                "I can provide basic flight duration, but for advanced analysis, please enable the AI service by configuring your OpenAI API key. "
                "Duration is calculated from message timestamps in your log."
            )
        elif any(word in message_lower for word in ['error', 'critical', 'warning']):
            return (
                "Error and warning analysis is not available because the AI service is not connected. "
                "Please check your OpenAI API key. "
                "With AI enabled, I can examine log messages for critical events and warnings."
            )
        elif any(word in message_lower for word in ['hello', 'hi', 'help']):
            return (
                "Hello! I'm your UAV flight data assistant. "
                "Currently, advanced AI-powered analysis is disabled. "
                "To unlock full features, please set your OpenAI API key in the .env file."
            )
        else:
            return (
                "I'm unable to provide detailed flight data analysis right now because the AI service is not available. "
                "Please configure your OpenAI API key in the .env file to enable advanced insights, anomaly detection, and comprehensive flight reports. "
                "I can still help with basic questions about your log file format and setup."
            )

    def is_available(self) -> bool:
        """Check if OpenAI client is available and configured"""
        return self.openai_client is not None

    def get_model_info(self) -> dict:
        """Get information about the current model configuration"""
        return {
            "provider": "OpenAI",
            "model": self.model,
            "available": self.is_available(),
            "api_key_configured": bool(os.getenv('OPENAI_API_KEY'))
        }

    async def _analyze_query_intent(self, message: str) -> Dict[str, Any]:
        """Analyze user query to determine intent and extract relevant information"""
        message_lower = message.lower()
        
        # Flight data specific queries with enhanced pattern matching
        query_patterns = {
            'max_altitude': [
                'highest altitude', 'maximum altitude', 'max altitude', 'peak altitude',
                'how high', 'altitude reached', 'highest point', 'maximum height'
            ],
            'flight_duration': [
                'flight time', 'total flight time', 'how long', 'duration', 'flight duration',
                'total time', 'length of flight', 'time in air'
            ],
            'gps_loss': [
                'gps signal', 'gps lost', 'gps loss', 'gps fail', 'satellite signal',
                'navigation lost', 'positioning lost', 'gps first lost', 'when did gps'
            ],
            'battery_temp': [
                'battery temperature', 'battery temp', 'maximum battery temperature',
                'max battery temp', 'battery heat', 'thermal battery'
            ],
            'critical_errors': [
                'critical errors', 'errors', 'critical error', 'mid-flight errors',
                'mid flight errors', 'error messages', 'failures', 'alerts',
                'warnings', 'what went wrong', 'problems during flight'
            ],
            'rc_loss': [
                'rc signal', 'remote control', 'radio signal', 'rc lost', 'rc loss',
                'control signal', 'transmitter signal', 'first instance rc',
                'when was rc', 'rc signal loss'
            ],
            'battery_voltage': [
                'battery voltage', 'voltage', 'battery level', 'power level',
                'electrical system', 'battery stats'
            ],
            'anomalies': [
                'anomalies', 'issues', 'problems', 'unusual', 'strange',
                'anything wrong', 'spot issues', 'detect problems'
            ]
        }
        
        # Check for direct matches
        for query_type, patterns in query_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    return {
                        'type': 'flight_data_query',
                        'query_type': query_type,
                        'confidence': 0.9,
                        'specific_request': True
                    }
        
        # Check for question patterns that indicate flight data queries
        flight_data_indicators = [
            'flight', 'altitude', 'battery', 'gps', 'signal', 'error', 'temperature',
            'voltage', 'rc', 'radio', 'control', 'telemetry', 'log', 'data'
        ]
        
        contains_flight_terms = any(term in message_lower for term in flight_data_indicators)
        
        if contains_flight_terms:
            # Check for question words
            question_words = ['what', 'when', 'how', 'where', 'why', 'which', 'was', 'were', 'did']
            is_question = any(word in message_lower for word in question_words) or message.strip().endswith('?')
            
            if is_question:
                return {
                    'type': 'flight_data_query',
                    'query_type': 'general_flight_query',
                    'confidence': 0.7,
                    'specific_request': False
                }
        
        # General UAV/aviation questions
        uav_terms = [
            'drone', 'uav', 'quadcopter', 'multirotor', 'aircraft', 'flight controller',
            'autopilot', 'waypoint', 'mission', 'rtl', 'loiter', 'stabilize'
        ]
        
        if any(term in message_lower for term in uav_terms):
            return {
                'type': 'general_uav_query',
                'confidence': 0.6
            }
        
        # Check if user is asking for clarification or help
        help_terms = ['help', 'what can you', 'how do i', 'explain', 'tell me about']
        if any(term in message_lower for term in help_terms):
            return {
                'type': 'help_request',
                'confidence': 0.8
            }
        
        # Default case
        return {
            'type': 'general_query',
            'confidence': 0.3
        } 