import os
import json
import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from models.chat_models import ConversationState, ChatResponse
from chatbot.llm_client import LLMClient
from chatbot.query_parser import QueryParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatbotAgent:
    def __init__(self):
        self.llm_client = LLMClient()
        self.query_parser = QueryParser()
        self.conversations: Dict[str, ConversationState] = {}
        
        # Flight data query patterns
        self.query_patterns = {
            'altitude': ['altitude', 'height', 'high', 'maximum height', 'peak'],
            'flight_time': ['duration', 'time', 'long', 'flight time', 'total time'],
            'gps_loss': ['gps', 'signal', 'satellite', 'navigation', 'lost'],
            'battery': ['battery', 'voltage', 'power', 'current', 'temperature'],
            'errors': ['error', 'critical', 'emergency', 'warning', 'problem', 'issue'],
            'rc_loss': ['rc', 'remote', 'control', 'signal loss', 'radio']
        }

    async def process_message(self, message: str, flight_data: Optional[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """Process incoming chat message with agentic behavior"""
        try:
            # Get or create conversation state
            if session_id not in self.conversations:
                self.conversations[session_id] = ConversationState(session_id=session_id)
            
            conversation = self.conversations[session_id]
            
            # Add user message to conversation history
            conversation.messages.append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Parse the query intent
            query_intent = await self.query_parser.parse_intent(message)
            
            # Check if we need clarification
            if query_intent['needs_clarification']:
                return await self._handle_clarification_request(message, conversation, query_intent)
            
            # Process based on query type
            if query_intent['type'] == 'flight_data_query' and flight_data:
                response = await self._handle_flight_data_query(message, flight_data, conversation, query_intent)
            elif query_intent['type'] == 'general_question':
                response = await self._handle_general_question(message, conversation, flight_data)
            else:
                response = await self._handle_unknown_query(message, conversation)
            
            # Add bot response to conversation history
            conversation.messages.append({
                'role': 'assistant',
                'content': response['content'],
                'timestamp': datetime.now().isoformat()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'content': "I apologize, but I encountered an error processing your request. Please try again.",
                'type': 'error'
            }

    async def _handle_flight_data_query(self, message: str, flight_data: Dict[str, Any], 
                                      conversation: ConversationState, query_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle flight data specific queries"""
        try:
            query_type = query_intent.get('specific_query')
            
            # Import here to avoid circular imports
            from mavlink_parser.parser import MAVLinkParser
            parser = MAVLinkParser()
            
            # Execute the query
            if query_type == 'max_altitude':
                result = await parser.execute_query(flight_data, 'max_altitude')
                response_content = f"The maximum altitude reached during this flight was {result}"
                
            elif query_type == 'flight_duration':
                result = await parser.execute_query(flight_data, 'flight_duration')
                response_content = f"The total flight time was {result}"
                
            elif query_type == 'gps_loss':
                result = await parser.execute_query(flight_data, 'gps_loss')
                response_content = result
                
            elif query_type == 'battery_temp':
                result = await parser.execute_query(flight_data, 'battery_temp')
                response_content = result
                
            elif query_type == 'critical_errors':
                result = await parser.execute_query(flight_data, 'critical_errors')
                response_content = result
                
            elif query_type == 'rc_loss':
                result = await parser.execute_query(flight_data, 'rc_loss')
                response_content = result
                
            else:
                # Use LLM to provide contextual analysis
                response_content = await self._generate_llm_response(message, flight_data, conversation)
            
            # Add helpful suggestions
            suggestions = self._get_related_suggestions(query_type)
            
            return {
                'content': response_content,
                'type': 'response',
                'data': {
                    'query_type': query_type,
                    'suggestions': suggestions
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling flight data query: {e}")
            return {
                'content': "I encountered an error analyzing the flight data. Please try rephrasing your question.",
                'type': 'error'
            }

    async def _handle_clarification_request(self, message: str, conversation: ConversationState, 
                                          query_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests that need clarification"""
        clarification_questions = [
            "Could you be more specific about what flight data you're interested in?",
            "Are you asking about altitude, battery, GPS, errors, or something else?",
            "What specific aspect of the flight would you like me to analyze?"
        ]
        
        suggested_questions = [
            "What was the maximum altitude?",
            "How long was the flight?",
            "Were there any GPS issues?",
            "What was the battery temperature?",
            "Were there any critical errors?"
        ]
        
        conversation.awaiting_clarification = True
        
        return {
            'content': clarification_questions[0],
            'type': 'clarification',
            'requires_clarification': True,
            'suggested_questions': suggested_questions
        }

    async def _handle_general_question(self, message: str, conversation: ConversationState, 
                                     flight_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle general questions about UAVs, flight data, etc."""
        
        # Create context for LLM
        context = self._build_conversation_context(conversation, flight_data)
        
        llm_response = await self.llm_client.generate_response(
            message, 
            context,
            system_prompt=self._get_system_prompt()
        )
        
        return {
            'content': llm_response,
            'type': 'response'
        }

    async def _handle_unknown_query(self, message: str, conversation: ConversationState) -> Dict[str, Any]:
        """Handle queries that couldn't be categorized"""
        return {
            'content': "I'm not sure I understand what you're asking. Could you please rephrase your question? I can help you analyze flight data, explain UAV concepts, or answer questions about telemetry.",
            'type': 'clarification',
            'suggested_questions': [
                "What was the highest altitude reached?",
                "How long was the total flight time?",
                "Were there any critical errors?",
                "Tell me about the GPS performance"
            ]
        }

    async def _generate_llm_response(self, message: str, flight_data: Dict[str, Any], 
                                   conversation: ConversationState) -> str:
        """Generate contextual response using LLM"""
        try:
            # Prepare flight data summary for LLM
            summary = await self._prepare_flight_summary(flight_data)
            
            context = f"""
            Flight Data Summary:
            {summary}
            
            Conversation History:
            {self._format_conversation_history(conversation)}
            """
            
            system_prompt = """You are an expert UAV flight data analyst. Analyze the provided flight data and answer the user's question accurately and helpfully. Be specific with numbers and provide context for the findings."""
            
            response = await self.llm_client.generate_response(message, context, system_prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return "I apologize, but I couldn't generate a detailed analysis at the moment. Please try asking a more specific question."

    def _build_conversation_context(self, conversation: ConversationState, 
                                  flight_data: Optional[Dict[str, Any]]) -> str:
        """Build context string for LLM"""
        context_parts = []
        
        if flight_data:
            context_parts.append("Flight data is available for analysis:")
            
            # Add basic flight info
            if flight_data.get('vehicle_type'):
                context_parts.append(f"- Vehicle type: {flight_data['vehicle_type']}")
            
            if flight_data.get('flight_duration'):
                duration = flight_data['flight_duration']
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                context_parts.append(f"- Flight duration: {minutes} minutes {seconds} seconds")
            
            # Add flight statistics if available
            stats = flight_data.get('flight_stats', {})
            if stats.get('max_altitude'):
                context_parts.append(f"- Maximum altitude: {stats['max_altitude']:.1f} meters")
            
            if stats.get('max_battery_voltage'):
                context_parts.append(f"- Battery voltage range: {stats.get('min_battery_voltage', 0):.1f}V - {stats['max_battery_voltage']:.1f}V")
            
            if stats.get('gps_loss_events'):
                context_parts.append(f"- GPS signal loss events: {stats['gps_loss_events']}")
            
            if stats.get('rc_loss_events'):
                context_parts.append(f"- RC signal loss events: {stats['rc_loss_events']}")
            
            # Add error information
            errors = flight_data.get('errors', [])
            critical_errors = [e for e in errors if e.get('severity', 10) <= 2]
            if critical_errors:
                context_parts.append(f"- Critical errors found: {len(critical_errors)}")
                for error in critical_errors[:3]:  # Show first 3 errors
                    context_parts.append(f"  * {error.get('text', 'Unknown error')}")
        else:
            context_parts.append("No flight data currently loaded.")
        
        # Add recent conversation history
        recent_messages = conversation.messages[-4:]  # Last 4 messages
        if recent_messages:
            context_parts.append("\nRecent conversation:")
            for msg in recent_messages:
                role = "User" if msg['role'] == 'user' else "Assistant"
                context_parts.append(f"{role}: {msg['content'][:100]}...")  # Truncate long messages
        
        return "\n".join(context_parts)

    async def _prepare_flight_summary(self, flight_data: Dict[str, Any]) -> str:
        """Prepare flight data summary for LLM context"""
        try:
            # Import here to avoid circular imports
            from mavlink_parser.parser import MAVLinkParser
            parser = MAVLinkParser()
            return await parser.generate_summary(flight_data)
        except Exception as e:
            logger.error(f"Error preparing flight summary: {e}")
            return "Flight data available but summary generation failed."

    def _format_conversation_history(self, conversation: ConversationState) -> str:
        """Format conversation history for LLM context"""
        if not conversation.messages:
            return "No previous conversation."
        
        formatted = []
        for msg in conversation.messages[-4:]:  # Last 4 messages
            role = "User" if msg['role'] == 'user' else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)

    def _get_related_suggestions(self, query_type: str) -> List[str]:
        """Get related question suggestions based on query type"""
        suggestions_map = {
            'max_altitude': [
                "What was the average altitude?",
                "Show me the altitude profile",
                "Were there any altitude warnings?"
            ],
            'flight_duration': [
                "What was the average speed?",
                "How much battery was consumed?",
                "Show me the flight path"
            ],
            'gps_loss': [
                "How many satellites were visible?",
                "What was the GPS accuracy?",
                "Were there any navigation errors?"
            ],
            'battery_temp': [
                "What was the battery voltage range?",
                "How much current was drawn?",
                "Were there any power warnings?"
            ],
            'critical_errors': [
                "Show me all warning messages",
                "What caused these errors?",
                "Were there any sensor failures?"
            ]
        }
        
        return suggestions_map.get(query_type, [
            "What was the maximum altitude?",
            "How long was the flight?",
            "Were there any issues?"
        ])

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM"""
        return """You are an expert UAV (drone) flight data analyst and assistant. You help users understand their flight data, diagnose issues, and learn about UAV operations. 

Key capabilities:
- Analyze MAVLink telemetry data from .bin flight logs
- Explain flight patterns, anomalies, and performance metrics
- Help diagnose common UAV issues (GPS loss, battery problems, RC signal loss, etc.)
- Provide educational information about UAV systems and flight operations

Guidelines:
- Be precise and technical when analyzing data
- Explain technical terms for less experienced users
- Suggest follow-up questions to help users explore their data
- If you don't have specific data, clearly state what information you need
- Always prioritize safety-related findings in your analysis""" 