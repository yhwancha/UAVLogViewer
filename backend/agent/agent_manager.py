import os
import json
import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from models.chat_models import ConversationState, ChatResponse
from llm.llm_client import LLMClient
from .query_handler import QueryHandler
from mavlink_parser.parser import MAVLinkParser
from .flight_analyzer import detect_patterns_and_changes, prepare_comprehensive_flight_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatbotAgent:
    def __init__(self):
        self.llm_client = LLMClient()
        self.query_handler = QueryHandler()
        self.conversations: Dict[str, ConversationState] = {}

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
        """Handle flight data analysis with comprehensive context"""
        try:
            # Check if the query is too ambiguous and needs clarification
            if await self._is_ambiguous_query(message):
                try:
                    clarifying_questions = await self.query_handler.get_suggested_clarifications(message)
                    # Add flight-specific context to clarifications
                    flight_duration = flight_data.get('flight_duration', 0)
                    if flight_duration > 0:
                        minutes = int(flight_duration // 60)
                        seconds = int(flight_duration % 60)
                        context_msg = f"I have flight data loaded ({minutes}m {seconds}s flight). Could you be more specific about what you'd like to know?"
                    else:
                        context_msg = "I have flight data loaded. Could you be more specific about what you'd like to analyze?"
                    
                    return {
                        'content': context_msg,
                        'type': 'clarification',
                        'suggested_questions': clarifying_questions
                    }
                except Exception as e:
                    logger.warning(f"Error generating clarifications: {e}")
                    # Fall through to normal analysis
            
            # Check if this is an anomaly detection request
            anomaly_keywords = ['anomaly', 'anomalies', 'issue', 'issues', 'problem', 'problems', 
                              'wrong', 'unusual', 'concerning', 'detect', 'spot', 'find problems']
            message_lower = message.lower()
            is_anomaly_request = any(keyword in message_lower for keyword in anomaly_keywords)
            
            if is_anomaly_request:
                # Use anomaly detection with higher word limit
                response = await self._handle_anomaly_detection(message, flight_data)
                # Summarize if needed (anomaly responses can be longer, so use 100 word limit)
                response = await self._summarize_if_needed(response, target_word_limit=100)
                conversation.add_message('assistant', response)
                return {
                    'content': response,
                    'type': 'response',
                    'data': {
                        'has_flight_data': True,
                        'analysis_method': 'anomaly_detection'
                    }
                }
            else:
                # Regular flight data analysis
                context = prepare_comprehensive_flight_context(flight_data)
                
                # Load enhanced analysis prompt with standard word limit
                prompt_template = self._load_prompt('telemetry/enhanced_analysis.md', word_limit=80)
                
                # Format the prompt with context and query
                formatted_prompt = f"{prompt_template}\n\nFlight Data Context:\n{context}\n\nUser Question: {message}"
                
                response = await self.llm_client.generate_response(formatted_prompt)
                # Summarize if needed
                response = await self._summarize_if_needed(response, target_word_limit=80)
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

    async def _handle_anomaly_detection(self, query: str, flight_data: Dict) -> str:
        """Handle anomaly detection requests"""
        try:
            # Get patterns and comprehensive context
            patterns = detect_patterns_and_changes(flight_data)
            context = prepare_comprehensive_flight_context(flight_data)
            
            # Load anomaly detection prompt with higher word limit for complex analysis
            prompt_template = self._load_prompt('anomaly/detect.md', word_limit=100)
            
            # Format the prompt with all required placeholders
            formatted_prompt = prompt_template.format(
                patterns=patterns,
                context=context,
                question=query
            )
            
            response = await self.llm_client.generate_response(formatted_prompt)
            # Note: Summarization is handled in the calling method
            return response
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return "I encountered an error detecting anomalies. Please try again."

    async def _handle_general_query(self, query: str) -> str:
        """Handle general UAV knowledge queries"""
        try:
            # Load general knowledge prompt with standard word limit
            prompt_template = self._load_prompt('general/knowledge.md', word_limit=80)
            
            formatted_prompt = f"{prompt_template}\n\nUser Question: {query}"
            
            response = await self.llm_client.generate_response(formatted_prompt)
            # Summarize if needed
            response = await self._summarize_if_needed(response, target_word_limit=80)
            return response
            
        except Exception as e:
            logger.error(f"Error in general query handling: {e}")
            return "I encountered an error processing your question. Please try again."

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
            # Check if the query is too ambiguous and needs clarification
            if await self._is_ambiguous_query(message):
                try:
                    clarifying_questions = await self.query_handler.get_suggested_clarifications(message)
                    return {
                        'content': "I'd be happy to help! Could you be more specific about what you're looking for?",
                        'type': 'clarification',
                        'suggested_questions': clarifying_questions
                    }
                except Exception as e:
                    logger.warning(f"Error generating clarifications: {e}")
                    # Fall through to general query handling
            
            # Handle general UAV/technical questions
            try:
                response = await self._handle_general_query(message)
                # Summarization is already handled in _handle_general_query
                conversation.add_message('assistant', response)
                return {
                    'content': response,
                    'type': 'response',
                    'data': {
                        'has_flight_data': False,
                        'analysis_method': 'general_knowledge'
                    }
                }
            except Exception as e:
                logger.error(f"Error in general query handling: {e}")
                return {
                    'content': "I encountered an error processing your question. Please try again.",
                    'type': 'error'
                }

    async def _is_ambiguous_query(self, message: str) -> bool:
        """Check if a query is too ambiguous and needs clarification"""
        message_lower = message.lower().strip()
        
        # Very short or vague queries
        if len(message_lower) < 10:
            return True
            
        # Common ambiguous patterns
        ambiguous_patterns = [
            r'^(what|how|tell me|explain)$',
            r'^(what|how|tell me|explain)\s+(about|is|are)?\s*$',
            r'^(help|info|information)$',
            r'^(drone|uav|flight|battery|gps)$',
            r'^(anything|something|details|more)$'
        ]
        
        import re
        for pattern in ambiguous_patterns:
            if re.search(pattern, message_lower):
                return True
                
        # Check for very generic questions
        generic_words = ['what', 'how', 'tell', 'explain', 'help', 'info']
        specific_words = ['altitude', 'battery', 'gps', 'error', 'voltage', 'temperature', 'signal', 'duration', 'mode']
        
        has_generic = any(word in message_lower for word in generic_words)
        has_specific = any(word in message_lower for word in specific_words)
        
        # If it has generic words but no specific context, it might be ambiguous
        if has_generic and not has_specific and len(message_lower.split()) < 5:
            return True
            
        return False

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

    def _load_prompt(self, filename: str, word_limit: int = 80) -> str:
        """Load prompt file with include support and template variables"""
        prompt_path = os.path.join(os.path.dirname(__file__), '../prompts', filename)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process includes: {{include:path/to/file.md}}
        content = self._process_includes(content)
        
        # Replace template variables
        content = content.replace('{word_limit}', str(word_limit))
        
        return content
    
    def _process_includes(self, content: str) -> str:
        """Process {{include:filename}} patterns in prompt content"""
        import re
        
        # Find all include patterns
        include_pattern = r'\{\{include:([^}]+)\}\}'
        matches = re.findall(include_pattern, content)
        
        for include_file in matches:
            try:
                include_path = os.path.join(os.path.dirname(__file__), '../prompts', include_file)
                with open(include_path, 'r', encoding='utf-8') as f:
                    include_content = f.read()
                
                # Replace the include pattern with the file content
                pattern = f'{{{{include:{include_file}}}}}'
                content = content.replace(pattern, include_content)
                
            except FileNotFoundError:
                logger.warning(f"Include file not found: {include_file}")
                # Remove the include pattern if file not found
                pattern = f'{{{{include:{include_file}}}}}'
                content = content.replace(pattern, f"[Include file not found: {include_file}]")
        
        return content 

    def _count_words(self, text: str) -> int:
        """Count words in text, excluding common formatting"""
        import re
        # Remove markdown formatting and extra whitespace
        clean_text = re.sub(r'\*\*.*?\*\*', '', text)  # Remove bold
        clean_text = re.sub(r'\*.*?\*', '', clean_text)  # Remove italic
        clean_text = re.sub(r'`.*?`', '', clean_text)    # Remove code
        clean_text = re.sub(r'\s+', ' ', clean_text)     # Normalize whitespace
        
        words = clean_text.strip().split()
        return len(words)
    
    async def _summarize_if_needed(self, response: str, target_word_limit: int = 80) -> str:
        """Summarize response if it exceeds word limit to ensure readability"""
        word_count = self._count_words(response)
        
        if word_count <= target_word_limit:
            return response
            
        try:
            # Load summarization prompt
            summarize_template = self._load_prompt('common/summarize.md')
            
            # Format with original response
            formatted_prompt = summarize_template.format(original_response=response)
            
            # Generate summary
            summary = await self.llm_client.generate_response(formatted_prompt)
            
            logger.info(f"Summarized long response: {word_count} words → {self._count_words(summary)} words")
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing response: {e}")
            # Fallback: return original response
            return response 