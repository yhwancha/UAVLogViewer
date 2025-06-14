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
        """Process incoming chat message with enhanced flight data analysis"""
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
            
            # If flight data is available, always try to provide comprehensive analysis
            if flight_data:
                return await self._handle_flight_data_analysis(message, flight_data, conversation)
            else:
                return await self._handle_no_flight_data(message, conversation)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'content': "I apologize, but I encountered an error processing your request. Please try again.",
                'type': 'error'
            }

    async def _handle_flight_data_analysis(self, message: str, flight_data: Dict[str, Any], 
                                         conversation: ConversationState) -> Dict[str, Any]:
        """Handle any question about flight data with comprehensive LLM analysis"""
        try:
            from mavlink_parser.parser import MAVLinkParser
            parser = MAVLinkParser()
            # First, try to get direct data using the parser for specific queries
            direct_answer = await self._try_direct_query(message, flight_data)

            # Analyze query intent for agentic anomaly reasoning
            query_intent = await self.llm_client._analyze_query_intent(message)
            if query_intent.get('query_type') in ['anomalies', 'flight_anomalies', 'issues', 'problems', 'unusual', 'anything wrong', 'spot issues', 'detect problems']:
                # Use agentic anomaly prompt
                agentic_prompt = await parser.generate_agentic_anomaly_prompt(flight_data)
                # Add conversation history for context
                conversation_context = self._format_conversation_history(conversation)
                if conversation_context != "No previous conversation.":
                    agentic_prompt += f"\n\nConversation History:\n{conversation_context}"
                response = await self.llm_client.generate_response(
                    message,
                    agentic_prompt,
                    "You are an expert UAV flight data analyst. Use the provided patterns and changes to reason about possible anomalies, issues, or safety concerns. Do not use fixed thresholds; instead, explain your reasoning and suggest recommendations."
                )
                conversation.add_message('assistant', response)
                return {
                    'content': response,
                    'type': 'response',
                    'data': {
                        'has_flight_data': True,
                        'analysis_method': 'agentic_anomaly_reasoning'
                    }
                }

            # Prepare comprehensive flight data context for LLM
            detailed_context = await self._prepare_comprehensive_flight_context(flight_data)
            # Create enhanced system prompt for flight data analysis
            system_prompt = self._get_enhanced_flight_analysis_prompt()
            # Build the full context including direct answer if available
            full_context = detailed_context
            if direct_answer:
                full_context += f"\n\nDirect Query Result: {direct_answer}"
            # Add conversation history
            conversation_context = self._format_conversation_history(conversation)
            if conversation_context != "No previous conversation.":
                full_context += f"\n\nConversation History:\n{conversation_context}"
            # Generate LLM response with comprehensive context
            response = await self.llm_client.generate_response(
                message, 
                full_context, 
                system_prompt
            )
            # Add response to conversation history
            conversation.add_message('assistant', response)
            return {
                'content': response,
                'type': 'response',
                'data': {
                    'has_flight_data': True,
                    'analysis_method': 'comprehensive_llm_analysis'
                }
            }
        except Exception as e:
            logger.error(f"Error in flight data analysis: {e}")
            return {
                'content': "I encountered an error analyzing the flight data. Please try rephrasing your question.",
                'type': 'error'
            }

    async def _try_direct_query(self, message: str, flight_data: Dict[str, Any]) -> Optional[str]:
        """Try to get direct answer using parser for specific queries"""
        try:
            from mavlink_parser.parser import MAVLinkParser
            parser = MAVLinkParser()
            
            # Analyze query intent
            query_intent = await self.llm_client._analyze_query_intent(message)
            
            if query_intent.get('specific_request', False):
                query_type = query_intent['query_type']
                result = await parser.execute_query(flight_data, query_type)
                return result
            
            return None
            
        except Exception as e:
            logger.warning(f"Direct query failed: {e}")
            return None

    async def _prepare_comprehensive_flight_context(self, flight_data: Dict[str, Any]) -> str:
        """Prepare comprehensive flight data context for LLM analysis"""
        try:
            from mavlink_parser.parser import MAVLinkParser
            parser = MAVLinkParser()
            
            context_parts = []
            
            # Basic flight information
            context_parts.append("=== FLIGHT DATA ANALYSIS ===")
            
            # Flight summary
            summary = await parser.generate_summary(flight_data)
            context_parts.append(f"Flight Summary: {summary}")
            
            # Detailed statistics
            stats = flight_data.get('flight_stats', {})
            if stats:
                context_parts.append("\n=== FLIGHT STATISTICS ===")
                for key, value in stats.items():
                    if isinstance(value, (int, float)):
                        context_parts.append(f"{key.replace('_', ' ').title()}: {value:.2f}")
                    else:
                        context_parts.append(f"{key.replace('_', ' ').title()}: {value}")
            
            # Altitude data analysis
            altitude_data = flight_data.get('altitude_data', [])
            if altitude_data:
                context_parts.append(f"\n=== ALTITUDE DATA ===")
                context_parts.append(f"Total altitude readings: {len(altitude_data)}")
                altitudes = [d['altitude'] for d in altitude_data if d.get('altitude') is not None]
                if altitudes:
                    context_parts.append(f"Altitude range: {min(altitudes):.1f}m to {max(altitudes):.1f}m")
                    context_parts.append(f"Average altitude: {sum(altitudes)/len(altitudes):.1f}m")
                    
                    # Altitude timeline (sample points)
                    sample_points = altitude_data[::max(1, len(altitude_data)//10)]  # 10 sample points
                    context_parts.append("Altitude timeline (samples):")
                    for point in sample_points:
                        timestamp = point.get('timestamp', 0)
                        altitude = point.get('altitude', 0)
                        context_parts.append(f"  T+{timestamp:.1f}s: {altitude:.1f}m")
            
            # Battery data analysis
            battery_data = flight_data.get('battery_data', [])
            if battery_data:
                context_parts.append(f"\n=== BATTERY DATA ===")
                context_parts.append(f"Total battery readings: {len(battery_data)}")
                
                voltages = [d['voltage'] for d in battery_data if d.get('voltage') is not None]
                if voltages:
                    context_parts.append(f"Voltage range: {min(voltages):.2f}V to {max(voltages):.2f}V")
                
                temperatures = [d['temperature'] for d in battery_data if d.get('temperature') is not None]
                if temperatures:
                    context_parts.append(f"Temperature range: {min(temperatures):.1f}°C to {max(temperatures):.1f}°C")
                
                currents = [d['current'] for d in battery_data if d.get('current') is not None]
                if currents:
                    context_parts.append(f"Current range: {min(currents):.2f}A to {max(currents):.2f}A")
            
            # GPS data analysis
            gps_data = flight_data.get('gps_data', [])
            if gps_data:
                context_parts.append(f"\n=== GPS DATA ===")
                context_parts.append(f"Total GPS readings: {len(gps_data)}")
                
                fix_types = [d['fix_type'] for d in gps_data if d.get('fix_type') is not None]
                if fix_types:
                    poor_fixes = [f for f in fix_types if f < 3]
                    context_parts.append(f"GPS signal quality: {len(poor_fixes)} poor signals out of {len(fix_types)} readings")
                
                satellites = [d['satellites'] for d in gps_data if d.get('satellites') is not None]
                if satellites:
                    context_parts.append(f"Satellite count range: {min(satellites)} to {max(satellites)} satellites")
            
            # Error analysis
            errors = flight_data.get('errors', [])
            if errors:
                context_parts.append(f"\n=== ERRORS AND WARNINGS ===")
                context_parts.append(f"Total messages: {len(errors)}")
                
                severity_counts = {}
                for error in errors:
                    sev = error.get('severity', 6)
                    severity_name = {1: 'Emergency', 2: 'Critical', 3: 'Error', 4: 'Warning', 5: 'Notice', 6: 'Info'}.get(sev, 'Unknown')
                    severity_counts[severity_name] = severity_counts.get(severity_name, 0) + 1
                
                for severity, count in severity_counts.items():
                    context_parts.append(f"{severity}: {count} messages")
                
                # Show critical and warning messages
                critical_errors = [e for e in errors if e.get('severity', 10) <= 4]
                if critical_errors:
                    context_parts.append("\nCritical/Warning Messages:")
                    for error in critical_errors[:5]:  # Show first 5
                        timestamp = error.get('timestamp', 0)
                        text = error.get('text', 'Unknown error')
                        severity = error.get('severity', 6)
                        severity_name = {1: 'Emergency', 2: 'Critical', 3: 'Error', 4: 'Warning'}.get(severity, 'Unknown')
                        context_parts.append(f"  T+{timestamp:.1f}s [{severity_name}]: {text}")
            
            # RC data analysis
            rc_data = flight_data.get('rc_data', [])
            if rc_data:
                context_parts.append(f"\n=== RC CONTROL DATA ===")
                context_parts.append(f"Total RC readings: {len(rc_data)}")
                
                # Analyze RC channels
                for chan_num in range(1, 5):
                    chan_key = f'chan{chan_num}'
                    chan_values = [d[chan_key] for d in rc_data if d.get(chan_key) is not None]
                    if chan_values:
                        context_parts.append(f"Channel {chan_num}: {min(chan_values)} to {max(chan_values)} PWM")
            
            # Flight modes
            modes = flight_data.get('modes', [])
            if modes:
                context_parts.append(f"\n=== FLIGHT MODES ===")
                mode_changes = []
                for mode in modes:
                    timestamp = mode.get('timestamp', 0)
                    mode_name = mode.get('mode', 'Unknown')
                    mode_changes.append(f"T+{timestamp:.1f}s: {mode_name}")
                
                context_parts.append(f"Mode changes: {len(mode_changes)}")
                for change in mode_changes[:10]:  # Show first 10 mode changes
                    context_parts.append(f"  {change}")
            
            # Anomaly detection
            try:
                anomalies = await parser.detect_anomalies(flight_data)
                if anomalies:
                    context_parts.append(f"\n=== DETECTED ANOMALIES ===")
                    context_parts.append(f"Total anomalies: {len(anomalies)}")
                    for anomaly in anomalies[:5]:  # Show top 5 anomalies
                        severity = anomaly.get('severity', 'unknown')
                        description = anomaly.get('description', 'Unknown anomaly')
                        context_parts.append(f"[{severity.upper()}] {description}")
            except Exception as e:
                logger.warning(f"Anomaly detection failed: {e}")
            
            # Message type counts
            message_counts = flight_data.get('message_counts', {})
            if message_counts:
                context_parts.append(f"\n=== MESSAGE TYPES ===")
                total_messages = sum(message_counts.values())
                context_parts.append(f"Total messages parsed: {total_messages}")
                context_parts.append("Message type breakdown:")
                
                # Sort by count and show top message types
                sorted_types = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)
                for msg_type, count in sorted_types[:10]:
                    percentage = (count / total_messages) * 100 if total_messages > 0 else 0
                    context_parts.append(f"  {msg_type}: {count} messages ({percentage:.1f}%)")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error preparing comprehensive context: {e}")
            return "Flight data available but detailed analysis failed."

    def _get_enhanced_flight_analysis_prompt(self) -> str:
        """Get enhanced system prompt for comprehensive flight data analysis"""
        return """You are an expert UAV flight data analyst with deep knowledge of ArduPilot/MAVLink telemetry systems. You have access to comprehensive flight data from a .bin log file that has been parsed and analyzed.

Your capabilities include:
- Analyzing altitude profiles, battery performance, GPS signal quality, RC control inputs
- Detecting flight anomalies and potential issues
- Understanding flight modes, error messages, and system status
- Correlating different data streams to provide insights
- Explaining technical concepts in accessible language

Instructions for analysis:
1. KEEP RESPONSES CONCISE AND FOCUSED - aim for 2-3 sentences maximum
2. USE THE PROVIDED FLIGHT DATA to answer questions with specific numbers, timestamps, and facts
3. CORRELATE different data streams when relevant (e.g., altitude drops with error messages)
4. PROVIDE CONTEXT for findings (e.g., "This voltage level is concerning because...")
5. BE SPECIFIC with timestamps, values, and units
6. EXPLAIN technical terms briefly for users who may not be experts
7. PRIORITIZE safety-related findings

Data interpretation guidelines:
- Altitude: Usually in meters above takeoff point
- Battery voltage: Typical range 11-17V for multi-cell LiPo batteries
- GPS fix type: 0=No fix, 2=2D fix, 3=3D fix (good), 4+=Enhanced
- RC channels: Typical range 1000-2000 PWM, center ~1500
- Timestamps: Seconds from flight start
- Error severity: 1=Emergency, 2=Critical, 3=Error, 4=Warning

Answer the user's question directly and concisely using the provided flight data. If you need to make assumptions, state them briefly. Focus on the most important findings."""

    async def _handle_no_flight_data(self, message: str, conversation: ConversationState) -> Dict[str, Any]:
        """Handle queries when no flight data is available"""
        # Check if user is asking about flight data specifically
        flight_related_terms = [
            'flight', 'altitude', 'battery', 'gps', 'signal', 'error', 'temperature',
            'voltage', 'rc', 'radio', 'control', 'telemetry', 'log', 'data', 'bin'
        ]
        
        message_lower = message.lower()
        is_flight_related = any(term in message_lower for term in flight_related_terms)
        
        if is_flight_related:
            return {
                'content': "I'd be happy to analyze flight data, but I don't have any .bin log file loaded currently. Please upload a .bin file using the main file drop zone, and I'll be able to answer detailed questions about altitude, battery performance, GPS signal, errors, flight duration, and much more.",
                'type': 'clarification',
                'suggested_questions': [
                    "Upload a .bin file to get started with analysis",
                    "What kind of flight data can you analyze?",
                    "How do I interpret MAVLink telemetry data?"
                ]
            }
        else:
            # Handle general UAV/technical questions
            return await self._handle_general_question(message, conversation, None)

    async def _handle_general_question(self, message: str, conversation: ConversationState, 
                                     flight_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle general questions about UAVs, flight systems, etc."""
        
        context = self._build_general_context(conversation, flight_data)
        
        system_prompt = """You are an expert UAV (drone) systems engineer and flight data analyst. You help users understand UAV technology, flight operations, telemetry systems, and troubleshooting.

Topics you can help with:
- UAV/drone technology and components
- Flight control systems (ArduPilot, PX4, etc.)
- MAVLink protocol and telemetry
- Flight modes and autonomous operations
- Sensor systems (GPS, IMU, barometer, etc.)
- Battery systems and power management
- RC control and failsafe systems
- Flight planning and mission execution
- Troubleshooting common UAV issues

Keep responses concise and focused (2-3 sentences maximum). Provide helpful, accurate, and educational responses. If discussing safety-critical topics, emphasize safety considerations."""
        
        response = await self.llm_client.generate_response(message, context, system_prompt)
        
        conversation.add_message('assistant', response)
        
        return {
            'content': response,
            'type': 'response',
            'data': {
                'has_flight_data': flight_data is not None,
                'analysis_method': 'general_knowledge'
            }
        }

    def _build_general_context(self, conversation: ConversationState, 
                             flight_data: Optional[Dict[str, Any]]) -> str:
        """Build context for general questions"""
        context_parts = []
        
        if flight_data:
            context_parts.append("Note: Flight data is available for analysis if needed.")
            vehicle_type = flight_data.get('vehicle_type', 'Unknown')
            duration = flight_data.get('flight_duration', 0)
            if duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                context_parts.append(f"Current loaded flight: {vehicle_type}, {minutes}m {seconds}s duration")
        
        # Add conversation history
        conversation_context = self._format_conversation_history(conversation)
        if conversation_context != "No previous conversation.":
            context_parts.append(f"\nConversation History:\n{conversation_context}")
        
        return "\n".join(context_parts)

    def _format_conversation_history(self, conversation: ConversationState) -> str:
        """Format conversation history for LLM context"""
        if not conversation.messages:
            return "No previous conversation."
        
        formatted = []
        for msg in conversation.messages[-6:]:  # Last 6 messages for more context
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content']
            # Truncate very long messages but keep more context
            if len(content) > 200:
                content = content[:200] + "..."
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)

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
            
            system_prompt = """You are an expert UAV (drone) flight data analyst and assistant. You help users understand their flight data, diagnose issues, and learn about UAV operations. 

Key capabilities:
- Analyze MAVLink telemetry data from .bin flight logs
- Explain flight patterns, anomalies, and performance metrics
- Help diagnose common UAV issues (GPS loss, battery problems, RC signal loss, etc.)
- Provide educational information about UAV systems and flight operations

Guidelines:
- Keep responses concise and focused (2-3 sentences maximum)
- Be precise and technical when analyzing data
- Explain technical terms briefly for less experienced users
- If you don't have specific data, clearly state what information you need
- Always prioritize safety-related findings in your analysis"""
            
            response = await self.llm_client.generate_response(message, context, system_prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return "I apologize, but I couldn't generate a detailed analysis at the moment. Please try asking a more specific question."

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