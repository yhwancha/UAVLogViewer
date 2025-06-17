import re
import asyncio
from typing import Dict, Any, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryHandler:
    def __init__(self):
        # Clarification needed patterns
        self.vague_patterns = [
            r'\b(tell me about|show me|analyze|check|look at|examine)\s*(?:the)?\s*(?:flight|data|log)?\s*$',
            r'\b(what happened|any issues|problems|status|summary)\s*$',
            r'\b(help|info|information)\s*$'
        ]

    async def check_for_clarification(self, message: str, flight_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if query needs clarification and return clarification response if needed"""
        if not await self._is_ambiguous_query(message):
            return None
            
        try:
            clarifying_questions = await self.get_suggested_clarifications(message)
            context_msg = self._create_flight_context_message(flight_data)
            
            return {
                'content': context_msg,
                'type': 'clarification',
                'suggested_questions': clarifying_questions
            }
        except Exception as e:
            logger.warning(f"Error generating clarifications: {e}")
            return None

    def _create_flight_context_message(self, flight_data: Dict[str, Any]) -> str:
        """Create context message for clarification requests"""
        flight_duration = flight_data.get('flight_duration', 0)
        if flight_duration > 0:
            minutes = int(flight_duration // 60)
            seconds = int(flight_duration % 60)
            return f"I have flight data loaded ({minutes}m {seconds}s flight). Could you be more specific about what you'd like to know?"
        else:
            return "I have flight data loaded. Could you be more specific about what you'd like to analyze?"

    async def _is_ambiguous_query(self, message: str) -> bool:
        """Check if a query is too ambiguous and needs clarification"""
        message_lower = message.lower().strip()
        
        # Very short or vague queries
        if len(message_lower) < 5:
            return True
            
        # Common ambiguous patterns
        ambiguous_patterns = [
            r'^(what|how|tell me|explain)$',
            r'^(what|how|tell me|explain)\s+(about|is|are)?\s*$',
            r'^(help|info|information)$',
            r'^(drone|uav|flight|battery|gps)$',
            r'^(anything|something|details|more)$'
        ]
        
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

    async def get_suggested_clarifications(self, message: str) -> List[str]:
        """Get suggested clarifying questions using LLM for better contextual responses"""
        try:
            from llm.llm_client import LLMClient
            import os
            
            # Load clarification prompt
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompts/clarify/ask.md')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Process includes and template variables
            prompt_template = self._process_includes(prompt_template)
            prompt_template = prompt_template.replace('{word_limit}', '100')
            
            # Format with user's question
            formatted_prompt = prompt_template.format(question=message)
            
            # Generate clarifying questions using LLM
            llm_client = LLMClient()
            response = await llm_client.generate_response(formatted_prompt)
            
            # Parse the response to extract individual questions
            # Look for numbered lists, bullet points, or question marks
            import re
            questions = []
            
            # Split by common patterns and clean up
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Remove common prefixes and clean up
                line = re.sub(r'^[-*•]\s*', '', line)  # Remove bullet points
                line = re.sub(r'^\d+\.\s*', '', line)  # Remove numbers
                line = re.sub(r'^Question \d+:\s*', '', line, flags=re.IGNORECASE)
                
                # Only keep lines that end with question marks or look like questions
                if '?' in line or any(word in line.lower() for word in ['what', 'how', 'when', 'where', 'which', 'would you like', 'are you']):
                    questions.append(line)
            
            # If we couldn't parse properly, fall back to splitting by question marks
            if not questions:
                potential_questions = response.split('?')
                for q in potential_questions:
                    q = q.strip()
                    if q and len(q) > 10:  # Reasonable length check
                        questions.append(q + '?')
            
            # Return up to 3 questions
            return questions[:3] if questions else self._get_fallback_clarifications(message)
            
        except Exception as e:
            logger.warning(f"Error generating LLM clarifications: {e}")
            return self._get_fallback_clarifications(message)
    
    def _process_includes(self, content: str) -> str:
        """Process {{include:filename}} patterns in prompt content"""
        import re
        import os
        
        # Find all include patterns
        include_pattern = r'\{\{include:([^}]+)\}\}'
        matches = re.findall(include_pattern, content)
        
        for include_file in matches:
            try:
                include_path = os.path.join(os.path.dirname(__file__), 'prompts', include_file)
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
    
    def _get_fallback_clarifications(self, message: str) -> List[str]:
        """Fallback clarifying questions when LLM fails"""
        suggestions = []
        
        message_lower = message.lower()
        
        # If message mentions flight but is vague
        if 'flight' in message_lower:
            suggestions.extend([
                "Are you asking about flight duration, altitude, or performance?",
                "What specific aspect of the flight interests you?",
                "Would you like to see flight statistics or error analysis?"
            ])
        
        # If message mentions battery but is vague
        elif 'battery' in message_lower:
            suggestions.extend([
                "Are you asking about battery voltage, temperature, or current consumption?",
                "Do you want to know about battery performance during the flight?"
            ])
        
        # If message mentions GPS but is vague
        elif 'gps' in message_lower:
            suggestions.extend([
                "Are you asking about GPS signal loss, accuracy, or satellite count?",
                "Do you want to check for navigation issues?"
            ])
        
        # Default suggestions
        else:
            suggestions.extend([
                "What was the maximum altitude reached?",
                "How long was the flight duration?",
                "Were there any critical errors or warnings?",
                "Tell me about GPS performance during the flight",
                "What was the battery status throughout the flight?"
            ])
        
        return suggestions[:3]  # Return top 3 suggestions