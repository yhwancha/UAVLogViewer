import re
import asyncio
from typing import Dict, Any, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryHandler:
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

    async def get_suggested_clarifications(self, message: str) -> List[str]:
        """Get suggested clarifying questions using LLM for better contextual responses"""
        try:
            from llm.llm_client import LLMClient
            import os
            
            # Load clarification prompt
            prompt_path = os.path.join(os.path.dirname(__file__), '../prompts/clarify/ask.md')
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

    @staticmethod
    async def execute_query(flight_data: Dict[str, Any], query_type: str, parameters: Optional[Dict] = None) -> Any:
        try:
            if query_type == "max_altitude" or query_type == "highest_altitude":
                max_alt = flight_data.get("flight_stats", {}).get("max_altitude")
                if max_alt:
                    return f"The highest altitude reached during the flight was {max_alt:.1f} meters."
                return "No altitude data available"
            
            elif query_type == "flight_duration" or query_type == "total_flight_time":
                duration = flight_data.get("flight_duration", 0)
                if duration > 0:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    return f"The total flight time was {minutes} minutes and {seconds} seconds ({duration:.1f} seconds total)."
                return "Flight duration not available"
            
            elif query_type == "gps_loss" or query_type == "gps_signal_loss":
                gps_data = flight_data.get("gps_data", [])
                if gps_data:
                    gps_losses = [(i, d) for i, d in enumerate(gps_data) if d.get('fix_type', 3) < 3]
                    if gps_losses:
                        first_loss = gps_losses[0][1]
                        total_losses = len(gps_losses)
                        loss_timestamp = first_loss['timestamp']
                        
                        # Convert timestamp to minutes and seconds for better readability
                        minutes = int(loss_timestamp // 60)
                        seconds = int(loss_timestamp % 60)
                        
                        from datetime import datetime, timedelta
                        start_time = flight_data.get("start_time")
                        
                        # Try to get actual time if start_time is available
                        actual_time_str = ""
                        if start_time:
                            try:
                                # Handle different start_time formats
                                if isinstance(start_time, str):
                                    try:
                                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                    except ValueError:
                                        start_dt = datetime.fromisoformat(start_time)
                                elif hasattr(start_time, 'strftime'):
                                    start_dt = start_time
                                else:
                                    start_dt = None
                                
                                if start_dt:
                                    loss_time = start_dt + timedelta(seconds=loss_timestamp)
                                    actual_time_str = f" at {loss_time.strftime('%H:%M:%S')}"
                            except Exception as e:
                                logger.warning(f"Could not parse start_time: {e}")
                                actual_time_str = ""
                        
                        # Format the response with better time representation
                        if minutes > 0:
                            time_desc = f"{minutes}m {seconds}s"
                        else:
                            time_desc = f"{seconds}s"
                        
                        return f"GPS signal was first lost{actual_time_str} ({time_desc} into the flight). " + \
                               f"Total GPS signal losses detected: {total_losses}"
                    else:
                        return "No GPS signal loss detected during the flight."
                return "No GPS data available"
            
            elif query_type == "battery_temp" or query_type == "max_battery_temperature":
                battery_data = flight_data.get("battery_data", [])
                if battery_data:
                    temperatures = [d['temperature'] for d in battery_data 
                                  if d.get('temperature') is not None and d['temperature'] > -50]
                    if temperatures:
                        max_temp = max(temperatures)
                        avg_temp = sum(temperatures) / len(temperatures)
                        return f"Maximum battery temperature: {max_temp:.1f}°C. Average temperature: {avg_temp:.1f}°C."
                    else:
                        return "Battery temperature data not available in this log."
                return "No battery data available"
            
            elif query_type == "critical_errors" or query_type == "mid_flight_errors":
                errors = flight_data.get("errors", [])
                if errors:
                    critical_errors = [e for e in errors if e.get('severity', 10) <= 3]
                    if critical_errors:
                        error_summary = {}
                        for error in critical_errors:
                            error_text = error.get('text', 'Unknown error')
                            if error_text not in error_summary:
                                error_summary[error_text] = {
                                    'count': 0,
                                    'first_time': error.get('timestamp', 0),
                                    'severity': error.get('severity', 10)
                                }
                            error_summary[error_text]['count'] += 1
                        result = f"Found {len(critical_errors)} critical/warning events:\n"
                        for error_text, info in list(error_summary.items())[:10]:
                            severity_name = {1: "Emergency", 2: "Critical", 3: "Warning", 4: "Info"}.get(info['severity'], "Unknown")
                            # Format time more readably
                            timestamp = info['first_time']
                            minutes = int(timestamp // 60)
                            seconds = int(timestamp % 60)
                            if minutes > 0:
                                time_desc = f"{minutes}m {seconds}s"
                            else:
                                time_desc = f"{seconds}s"
                            result += f"- [{severity_name}] {error_text} (occurred {info['count']} times, first at {time_desc} into flight)\n"
                        if len(error_summary) > 10:
                            result += f"... and {len(error_summary) - 10} more error types"
                        return result.strip()
                    else:
                        return "No critical errors detected during the flight."
                return "No error data available"
            
            elif query_type == "rc_loss" or query_type == "rc_signal_loss":
                rc_data = flight_data.get("rc_data", [])
                if rc_data:
                    rc_losses = []
                    for i, d in enumerate(rc_data):
                        rssi = d.get('rssi', 255)
                        chan1 = d.get('chan1', 1500)
                        if rssi < 50 or chan1 < 900 or chan1 > 2100:
                            rc_losses.append(d)
                    if rc_losses:
                        first_loss = rc_losses[0]
                        loss_timestamp = first_loss['timestamp']
                        
                        # Convert timestamp to minutes and seconds for better readability
                        minutes = int(loss_timestamp // 60)
                        seconds = int(loss_timestamp % 60)
                        
                        from datetime import datetime, timedelta
                        start_time = flight_data.get("start_time")
                        
                        # Try to get actual time if start_time is available
                        actual_time_str = ""
                        if start_time:
                            try:
                                # Handle different start_time formats
                                if isinstance(start_time, str):
                                    try:
                                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                    except ValueError:
                                        start_dt = datetime.fromisoformat(start_time)
                                elif hasattr(start_time, 'strftime'):
                                    start_dt = start_time
                                else:
                                    start_dt = None
                                
                                if start_dt:
                                    loss_time = start_dt + timedelta(seconds=loss_timestamp)
                                    actual_time_str = f" at {loss_time.strftime('%H:%M:%S')}"
                            except Exception as e:
                                logger.warning(f"Could not parse start_time: {e}")
                                actual_time_str = ""
                        
                        # Format the response with better time representation
                        if minutes > 0:
                            time_desc = f"{minutes}m {seconds}s"
                        else:
                            time_desc = f"{seconds}s"
                        
                        return f"RC signal was first lost{actual_time_str} ({time_desc} into the flight). " + \
                               f"Total RC signal issues detected: {len(rc_losses)}"
                    else:
                        return "No RC signal loss detected during the flight."
                return "No RC data available"
            
            elif query_type == "anomalies" or query_type == "flight_anomalies":
                # This should now be handled by flight_analyzer.detect_patterns_and_changes and LLM, but for compatibility:
                return "Anomaly detection is now handled by the LLM using detected patterns."
            
            elif query_type == "battery_voltage" or query_type == "voltage_range":
                stats = flight_data.get("flight_stats", {})
                if stats.get("max_battery_voltage"):
                    min_v = stats.get("min_battery_voltage", 0)
                    max_v = stats["max_battery_voltage"]
                    return f"Battery voltage ranged from {min_v:.1f}V to {max_v:.1f}V during the flight."
                return "No battery voltage data available"
            
            elif query_type == "vehicle_type":
                vehicle_type = flight_data.get("vehicle_type", "Unknown")
                return f"Vehicle type: {vehicle_type}"
            
            else:
                return f"Unknown query type: {query_type}. Supported queries: max_altitude, flight_duration, gps_loss, battery_temp, critical_errors, rc_loss, anomalies, battery_voltage, vehicle_type"
        except Exception as e:
            logger.error(f"Error executing query {query_type}: {e}")
            return f"Error processing query: {str(e)}"

    @staticmethod
    async def analyze_query_intent(message: str) -> Dict[str, Any]:
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