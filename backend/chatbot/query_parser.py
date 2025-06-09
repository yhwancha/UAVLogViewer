import re
import asyncio
from typing import Dict, Any, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryParser:
    def __init__(self):
        # Define query patterns with keywords and their associated query types
        self.query_patterns = {
            'max_altitude': {
                'keywords': ['maximum altitude', 'max altitude', 'highest altitude', 'peak altitude', 
                           'highest height', 'maximum height', 'max height', 'top altitude'],
                'indicators': ['altitude', 'height', 'high', 'peak', 'maximum', 'max', 'top']
            },
            'flight_duration': {
                'keywords': ['flight duration', 'flight time', 'total time', 'how long', 
                           'duration', 'flight length', 'time spent flying'],
                'indicators': ['duration', 'time', 'long', 'length', 'minutes', 'seconds', 'hours']
            },
            'gps_loss': {
                'keywords': ['gps loss', 'gps signal loss', 'satellite loss', 'navigation loss',
                           'gps issues', 'gps problems', 'lost gps', 'gps failed'],
                'indicators': ['gps', 'satellite', 'navigation', 'signal', 'lost', 'loss', 'fail']
            },
            'battery_temp': {
                'keywords': ['battery temperature', 'battery temp', 'maximum battery temperature',
                           'battery heat', 'battery thermal', 'battery overheating'],
                'indicators': ['battery', 'temperature', 'temp', 'heat', 'thermal', 'hot']
            },
            'critical_errors': {
                'keywords': ['critical errors', 'errors', 'critical messages', 'emergency',
                           'warnings', 'critical warnings', 'system errors', 'failures'],
                'indicators': ['error', 'critical', 'emergency', 'warning', 'failure', 'problem']
            },
            'rc_loss': {
                'keywords': ['rc loss', 'remote control loss', 'radio loss', 'rc signal loss',
                           'control signal', 'remote signal', 'transmitter loss'],
                'indicators': ['rc', 'remote', 'control', 'radio', 'signal', 'transmitter', 'loss']
            },
            'battery_voltage': {
                'keywords': ['battery voltage', 'voltage', 'battery power', 'power level',
                           'battery level', 'electrical', 'volts'],
                'indicators': ['voltage', 'volt', 'power', 'electrical', 'battery']
            },
            'speed': {
                'keywords': ['speed', 'velocity', 'how fast', 'maximum speed', 'ground speed',
                           'air speed', 'fastest'],
                'indicators': ['speed', 'velocity', 'fast', 'mph', 'kph', 'm/s']
            }
        }
        
        # Question indicators
        self.question_indicators = ['what', 'when', 'how', 'where', 'why', 'which', 'tell me', 'show me']
        
        # Clarification needed patterns
        self.vague_patterns = [
            r'\b(tell me about|show me|analyze|check|look at|examine)\s*(?:the)?\s*(?:flight|data|log)?\s*$',
            r'\b(what happened|any issues|problems|status|summary)\s*$',
            r'\b(help|info|information)\s*$'
        ]

    async def parse_intent(self, message: str) -> Dict[str, Any]:
        """Parse user message to determine intent and extract query information"""
        try:
            message_lower = message.lower().strip()
            
            # Try to identify specific flight data queries first
            specific_query = self._identify_specific_query(message_lower)
            if specific_query and specific_query['confidence'] > 0.5:  # Only high confidence matches
                return {
                    'type': 'flight_data_query',
                    'specific_query': specific_query['query_type'],
                    'confidence': specific_query['confidence'],
                    'needs_clarification': False,
                    'message': message,
                    'matched_keywords': specific_query.get('matched_keywords', [])
                }
            
            # Check if message is too vague and needs clarification
            if self._needs_clarification(message_lower):
                return {
                    'type': 'general_question',
                    'needs_clarification': True,
                    'confidence': 0.5,
                    'message': message
                }
            
            # Default to general question (let AI handle it)
            return {
                'type': 'general_question',
                'needs_clarification': False,
                'confidence': 0.7,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            return {
                'type': 'general_question',  # Default to AI handling
                'needs_clarification': False,
                'confidence': 0.5,
                'message': message
            }

    def _identify_specific_query(self, message: str) -> Optional[Dict[str, Any]]:
        """Identify specific flight data queries"""
        best_match = None
        highest_confidence = 0.0
        
        for query_type, patterns in self.query_patterns.items():
            confidence, matched_keywords = self._calculate_match_confidence(message, patterns)
            
            if confidence > highest_confidence and confidence > 0.3:  # Minimum confidence threshold
                highest_confidence = confidence
                best_match = {
                    'query_type': query_type,
                    'confidence': confidence,
                    'matched_keywords': matched_keywords
                }
        
        return best_match

    def _calculate_match_confidence(self, message: str, patterns: Dict[str, List[str]]) -> tuple:
        """Calculate confidence score for pattern matching"""
        confidence = 0.0
        matched_keywords = []
        
        # Check exact keyword matches (highest weight)
        for keyword in patterns['keywords']:
            if keyword in message:
                confidence += 0.8
                matched_keywords.append(keyword)
        
        # Check indicator words (lower weight)
        indicator_matches = 0
        for indicator in patterns['indicators']:
            if re.search(r'\b' + re.escape(indicator) + r'\b', message):
                indicator_matches += 1
                matched_keywords.append(indicator)
        
        # Weight indicator matches
        if indicator_matches > 0:
            confidence += min(indicator_matches * 0.2, 0.6)  # Cap at 0.6
        
        # Bonus for question format
        if any(q_word in message for q_word in self.question_indicators):
            confidence += 0.1
        
        # Normalize confidence to max 1.0
        confidence = min(confidence, 1.0)
        
        return confidence, matched_keywords

    def _needs_clarification(self, message: str) -> bool:
        """Check if the message is too vague and needs clarification"""
        # Very short messages (only 1 word)
        if len(message.split()) <= 1:
            return True
        
        # Only basic greetings need clarification
        basic_greetings = [
            r'^\s*(hello|hi|hey)\s*$',
            r'^\s*(help)\s*$'
        ]
        
        for pattern in basic_greetings:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        
        return False

    def _is_general_question(self, message: str) -> bool:
        """Check if message is a general question about UAVs/flight"""
        general_topics = [
            'uav', 'drone', 'quadcopter', 'helicopter', 'aircraft', 'vehicle',
            'flight', 'flying', 'pilot', 'aviation', 'aeronautics',
            'mavlink', 'telemetry', 'protocol', 'data', 'logging',
            'autopilot', 'ardupilot', 'pixhawk', 'flight controller',
            'sensors', 'accelerometer', 'gyroscope', 'magnetometer',
            'mission', 'waypoint', 'autonomous', 'manual'
        ]
        
        for topic in general_topics:
            if re.search(r'\b' + re.escape(topic) + r'\b', message):
                return True
        
        return False

    def extract_parameters(self, message: str, query_type: str) -> Dict[str, Any]:
        """Extract parameters from message for specific query types"""
        parameters = {}
        
        try:
            # Extract numbers (could be thresholds, time ranges, etc.)
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', message)
            if numbers:
                parameters['numbers'] = [float(n) for n in numbers]
            
            # Extract time-related parameters
            time_patterns = {
                'minutes': r'(\d+)\s*(?:minute|min)s?',
                'seconds': r'(\d+)\s*(?:second|sec)s?',
                'hours': r'(\d+)\s*(?:hour|hr)s?'
            }
            
            for unit, pattern in time_patterns.items():
                matches = re.findall(pattern, message, re.IGNORECASE)
                if matches:
                    parameters[unit] = [int(m) for m in matches]
            
            # Extract altitude units
            altitude_units = re.search(r'\b(meter|metre|foot|feet|ft|m)\b', message, re.IGNORECASE)
            if altitude_units:
                parameters['altitude_unit'] = altitude_units.group(1).lower()
            
            # Extract severity levels for errors
            if query_type == 'critical_errors':
                severity_keywords = ['critical', 'emergency', 'alert', 'warning', 'error']
                found_severities = [kw for kw in severity_keywords if kw in message.lower()]
                if found_severities:
                    parameters['severity_filter'] = found_severities
            
            # Extract time ranges
            time_range_pattern = r'(?:between|from)\s+(\d+(?::\d+)?)\s+(?:to|and)\s+(\d+(?::\d+)?)'
            time_range = re.search(time_range_pattern, message, re.IGNORECASE)
            if time_range:
                parameters['time_range'] = {
                    'start': time_range.group(1),
                    'end': time_range.group(2)
                }
            
        except Exception as e:
            logger.warning(f"Error extracting parameters: {e}")
        
        return parameters

    def get_suggested_clarifications(self, message: str) -> List[str]:
        """Get suggested clarifying questions based on partial intent"""
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