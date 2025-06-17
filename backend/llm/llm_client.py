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
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4.1-nano')
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