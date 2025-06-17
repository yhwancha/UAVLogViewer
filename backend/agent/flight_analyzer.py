import logging
import os
import json
import redis.asyncio as aioredis
from typing import Dict, Any, Optional
from mavlink_parser.parser import MAVLinkParser
from llm.llm_client import LLMClient
from .util import format_flight_time

logger = logging.getLogger(__name__)

class FlightAnalyzer:
    """Flight data analyzer with LLM-powered analysis capabilities"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.redis_client = None
        # Import QueryHandler here to avoid circular imports
        from .query_handler import QueryHandler
        self.query_handler = QueryHandler()
        
    async def _get_redis_client(self):
        """Get or create Redis client"""
        if self.redis_client is None:
            REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
        return self.redis_client

    async def detect_patterns_and_changes(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instead of hardcoded anomaly detection, extract patterns and changes for LLM-based reasoning.
        Returns a dict summarizing key changes and patterns in the data.
        """
        patterns = {}

        # Altitude changes
        altitude_data = flight_data.get('altitude_data', [])
        if altitude_data:
            altitudes = [d['altitude'] for d in altitude_data if d['altitude'] is not None]
            timestamps = [d['timestamp'] for d in altitude_data if d['altitude'] is not None]
            if len(altitudes) > 1:
                diffs = [altitudes[i] - altitudes[i-1] for i in range(1, len(altitudes))]
                max_drop = min(diffs)
                max_rise = max(diffs)
                patterns['altitude_changes'] = {
                    'max_drop': max_drop,
                    'max_rise': max_rise,
                    'all_diffs': diffs[:100]  # limit for brevity
                }

        # Battery voltage changes
        battery_data = flight_data.get('battery_data', [])
        if battery_data:
            voltages = [d['voltage'] for d in battery_data if d['voltage'] is not None]
            if len(voltages) > 1:
                diffs = [voltages[i] - voltages[i-1] for i in range(1, len(voltages))]
                patterns['battery_voltage_changes'] = {
                    'max_drop': min(diffs),
                    'max_rise': max(diffs),
                    'all_diffs': diffs[:100]
                }

        # GPS fix pattern
        gps_data = flight_data.get('gps_data', [])
        if gps_data:
            fix_types = [d.get('fix_type', 3) for d in gps_data]
            patterns['gps_fix_types'] = fix_types[:100]

        # Attitude changes
        attitude_data = flight_data.get('attitude_data', [])
        if attitude_data:
            rolls = [d['roll'] for d in attitude_data if d['roll'] is not None]
            pitches = [d['pitch'] for d in attitude_data if d['pitch'] is not None]
            patterns['attitude_rolls'] = rolls[:100]
            patterns['attitude_pitches'] = pitches[:100]

        # Error messages
        errors = flight_data.get('errors', [])
        if errors:
            patterns['error_messages'] = [e['text'] for e in errors[:20]]

        return patterns

    async def prepare_comprehensive_flight_context(self, flight_data: Dict[str, Any], session_id: str) -> str:
        """Prepare comprehensive flight data context for LLM analysis, prioritizing Redis summary data"""
        try:
            context_parts = []
            context_parts.append("=== FLIGHT DATA ANALYSIS ===")
            logger.debug(f"Preparing context for session_id: {session_id}")
            
            # Try to get comprehensive data from Redis first
            redis_flight_data = await self._get_redis_flight_data(session_id)
            
            if redis_flight_data:
                logger.info("Using Redis flight data for context generation")
                return await self._format_redis_context(redis_flight_data, session_id)
            else:
                logger.info("Redis data not available, using raw flight_data")
                return await self._format_raw_context(flight_data, session_id)
                
        except Exception as e:
            logger.error(f"Error preparing comprehensive context: {e}")
            return "Flight data available but detailed analysis failed."
    
    async def _get_redis_flight_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Try to get flight data from Redis with multiple key formats"""
        # session_id should be in format "filename:timestamp"
        possible_keys = [
            session_id,  # Direct session_id (filename:timestamp)
            f"flight_data:{session_id}",
            f"{session_id}:flight_data"
        ]
        
        redis_client = await self._get_redis_client()
        
        for key in possible_keys:
            try:
                data = await redis_client.get(key)
                if data:
                    parsed_data = json.loads(data) if isinstance(data, str) else data
                    logger.info(f"Found Redis flight data with key: {key}")
                    return parsed_data
            except Exception as e:
                logger.debug(f"Failed to get data with key {key}: {e}")
                continue
        
        logger.info(f"No Redis flight data found for session_id: {session_id}")
        return None
    
    async def _get_redis_summary(self, session_id: str) -> Optional[str]:
        """Try to get flight summary from Redis - session_id should be filename:timestamp"""
        # The actual Redis key format is "summary:filename:timestamp"
        summary_key = f"summary:{session_id}"
        
        try:
            redis_client = await self._get_redis_client()
            summary = await redis_client.get(summary_key)
            if summary:
                # Summary is stored as JSON string, need to parse it
                if isinstance(summary, str) and summary.startswith('"') and summary.endswith('"'):
                    # Remove extra JSON quotes if present
                    summary = json.loads(summary)
                logger.info(f"Found Redis summary with key: {summary_key}")
                return summary
            else:
                logger.info(f"No summary found with key: {summary_key}")
                return None
        except Exception as e:
            logger.warning(f"Failed to get summary with key {summary_key}: {e}")
            return None
    
    async def _format_redis_context(self, redis_data: Dict[str, Any], session_id: str) -> str:
        """Format context using Redis data (optimized path)"""
        context_parts = ["=== FLIGHT DATA ANALYSIS ==="]
        
        # 1. Flight Summary from Redis (simple string summary)
        try:
            summary = await self._get_redis_summary(session_id)
            if summary:
                context_parts.append(f"Flight Summary: {summary}")
            else:
                # Generate basic summary from Redis flight data
                basic_info = []
                if redis_data.get("vehicle_type"):
                    basic_info.append(f"Vehicle: {redis_data['vehicle_type']}")
                if redis_data.get("autopilot_type") and redis_data["autopilot_type"] != "Unknown":
                    basic_info.append(f"Autopilot: {redis_data['autopilot_type']}")
                if redis_data.get("flight_duration"):
                    duration = redis_data["flight_duration"]
                    minutes, seconds = int(duration // 60), int(duration % 60)
                    basic_info.append(f"Duration: {minutes}m {seconds}s")
                context_parts.append(f"Flight Summary: {' | '.join(basic_info) if basic_info else 'Flight data available'}")
        except Exception as e:
            logger.warning(f"Error getting Redis summary: {e}")
            context_parts.append("Flight Summary: Summary retrieval failed")
        
        # 2. Key Statistics (from pre-calculated flight_stats)
        stats = redis_data.get('flight_stats', {})
        if stats:
            context_parts.append("\n=== KEY FLIGHT STATISTICS ===")
            
            # Priority stats for LLM analysis
            priority_stats = [
                ('max_altitude', 'Max Altitude', 'm'),
                ('max_battery_voltage', 'Max Battery Voltage', 'V'),
                ('min_battery_voltage', 'Min Battery Voltage', 'V'),
                ('battery_voltage_drop', 'Battery Voltage Drop', 'V'),
                ('avg_current', 'Average Current', 'A'),
                ('max_current', 'Max Current', 'A'),
                ('total_current_consumed', 'Total Current Consumed', 'mAh'),
                ('avg_satellites', 'Average GPS Satellites', ''),
                ('min_satellites', 'Min GPS Satellites', ''),
                ('gps_loss_events', 'GPS Loss Events', ''),
                ('rc_loss_events', 'RC Loss Events', ''),
                ('max_roll', 'Max Roll Angle', '°'),
                ('max_pitch', 'Max Pitch Angle', '°'),
                ('max_cpu_load', 'Max CPU Load', '%'),
                ('avg_cpu_load', 'Average CPU Load', '%')
            ]
            
            stats_shown = 0
            for key, label, unit in priority_stats:
                if key in stats and stats[key] is not None and stats_shown < 12:  # Limit to 12 key stats
                    value = stats[key]
                    if isinstance(value, (int, float)):
                        if unit == '°':
                            context_parts.append(f"{label}: {abs(value):.1f}{unit}")
                        elif unit == '%':
                            context_parts.append(f"{label}: {value:.1f}{unit}")
                        elif unit in ['V', 'A']:
                            context_parts.append(f"{label}: {value:.2f}{unit}")
                        elif unit == 'm':
                            context_parts.append(f"{label}: {value:.1f}{unit}")
                        elif unit == 'mAh':
                            context_parts.append(f"{label}: {value:.0f}{unit}")
                        else:
                            context_parts.append(f"{label}: {value:.0f}{unit}")
                        stats_shown += 1
        
        # 3. Critical Issues Summary (optimized)
        errors = redis_data.get('errors', [])
        if errors:
            critical_errors = [e for e in errors if e.get('severity', 10) <= 4]
            if critical_errors:
                context_parts.append(f"\n=== CRITICAL ISSUES SUMMARY ===")
                context_parts.append(f"Total critical/warning messages: {len(critical_errors)}")
                
                # Group similar errors
                error_groups = {}
                for error in critical_errors:
                    text = error.get('text', 'Unknown error')
                    # Group by error text (simplified)
                    error_key = text[:50]  # First 50 chars as grouping key
                    if error_key not in error_groups:
                        error_groups[error_key] = {
                            'count': 0,
                            'first_time': error.get('timestamp', 0),
                            'severity': error.get('severity', 6),
                            'full_text': text
                        }
                    error_groups[error_key]['count'] += 1
                
                # Show top 3 error types
                sorted_errors = sorted(error_groups.items(), 
                                     key=lambda x: (x[1]['severity'], -x[1]['count']))
                
                for error_key, info in sorted_errors[:3]:
                    time_str = format_flight_time(info['first_time'], redis_data)
                    severity_name = {1: 'Emergency', 2: 'Critical', 3: 'Error', 4: 'Warning'}.get(info['severity'], 'Unknown')
                    if info['count'] > 1:
                        context_parts.append(f"  {time_str} [{severity_name}]: {info['full_text']} (occurred {info['count']} times)")
                    else:
                        context_parts.append(f"  {time_str} [{severity_name}]: {info['full_text']}")
                
                if len(error_groups) > 3:
                    context_parts.append(f"  ... and {len(error_groups) - 3} more error types")
        
        # 4. Flight Modes Summary (optimized)
        modes = redis_data.get('modes', [])
        if modes:
            context_parts.append(f"\n=== FLIGHT MODES SUMMARY ===")
            context_parts.append(f"Total mode changes: {len(modes)}")
            
            # Show first and last few modes
            if len(modes) <= 6:
                for mode in modes:
                    timestamp = mode.get('timestamp', 0)
                    mode_name = mode.get('mode', 'Unknown')
                    time_str = format_flight_time(timestamp, redis_data)
                    context_parts.append(f"  {time_str}: {mode_name}")
            else:
                # Show first 3 and last 2
                for mode in modes[:3]:
                    timestamp = mode.get('timestamp', 0)
                    mode_name = mode.get('mode', 'Unknown')
                    time_str = format_flight_time(timestamp, redis_data)
                    context_parts.append(f"  {time_str}: {mode_name}")
                
                context_parts.append(f"  ... {len(modes) - 5} mode changes ...")
                
                for mode in modes[-2:]:
                    timestamp = mode.get('timestamp', 0)
                    mode_name = mode.get('mode', 'Unknown')
                    time_str = format_flight_time(timestamp, redis_data)
                    context_parts.append(f"  {time_str}: {mode_name}")
        
        # 5. Data Quality Summary (new section)
        context_parts.append(f"\n=== DATA QUALITY ===")
        
        # Message counts summary
        message_counts = redis_data.get('message_counts', {})
        if message_counts:
            total_messages = sum(message_counts.values())
            context_parts.append(f"Total messages: {total_messages}")
            
            # Key data availability
            key_data_types = ['ATTITUDE', 'GPS', 'BATTERY_STATUS', 'RC_CHANNELS', 'GLOBAL_POSITION_INT']
            available_data = []
            for data_type in key_data_types:
                if data_type in message_counts:
                    available_data.append(f"{data_type}({message_counts[data_type]})")
            
            if available_data:
                context_parts.append(f"Key telemetry: {', '.join(available_data)}")
        
        # Data arrays summary
        data_summary = []
        if redis_data.get('altitude_data'):
            data_summary.append(f"Altitude({len(redis_data['altitude_data'])})")
        if redis_data.get('battery_data'):
            data_summary.append(f"Battery({len(redis_data['battery_data'])})")
        if redis_data.get('gps_data'):
            data_summary.append(f"GPS({len(redis_data['gps_data'])})")
        if redis_data.get('rc_data'):
            data_summary.append(f"RC({len(redis_data['rc_data'])})")
        if redis_data.get('attitude_data'):
            data_summary.append(f"Attitude({len(redis_data['attitude_data'])})")
        
        if data_summary:
            context_parts.append(f"Processed arrays: {', '.join(data_summary)}")
        
        return "\n".join(context_parts)
    
    async def _format_raw_context(self, flight_data: Dict[str, Any], session_id: str) -> str:
        """Format context using raw flight_data (fallback path)"""
        context_parts = ["=== FLIGHT DATA ANALYSIS ==="]
        
        # Basic flight summary
        basic_info = []
        if flight_data.get("vehicle_type"):
            basic_info.append(f"Vehicle: {flight_data['vehicle_type']}")
        if flight_data.get("flight_duration"):
            duration = flight_data["flight_duration"]
            minutes, seconds = int(duration // 60), int(duration % 60)
            basic_info.append(f"Duration: {minutes}m {seconds}s")
        context_parts.append(f"Flight Summary: {' | '.join(basic_info) if basic_info else 'Processing raw flight data'}")
        
        # Use flight_stats if available (already calculated)
        stats = flight_data.get('flight_stats', {})
        if stats:
            context_parts.append("\n=== FLIGHT STATISTICS ===")
            key_stats = ['max_altitude', 'max_battery_voltage', 'min_battery_voltage', 
                        'avg_current', 'gps_loss_events', 'rc_loss_events']
            
            for key in key_stats:
                if key in stats and stats[key] is not None:
                    value = stats[key]
                    if isinstance(value, (int, float)):
                        context_parts.append(f"{key.replace('_', ' ').title()}: {value:.2f}")
                    else:
                        context_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        # Critical errors only
        errors = flight_data.get('errors', [])
        if errors:
            critical_errors = [e for e in errors if e.get('severity', 10) <= 4]
            if critical_errors:
                context_parts.append(f"\n=== CRITICAL ISSUES ===")
                context_parts.append(f"Critical/warning messages: {len(critical_errors)}")
                
                for error in critical_errors[:3]:
                    timestamp = error.get('timestamp', 0)
                    text = error.get('text', 'Unknown error')
                    time_str = format_flight_time(timestamp, flight_data)
                    context_parts.append(f"  {time_str}: {text}")
        
        # Flight modes summary
        modes = flight_data.get('modes', [])
        if modes:
            context_parts.append(f"\n=== FLIGHT MODES ===")
            context_parts.append(f"Mode changes: {len(modes)}")
            for mode in modes[:3]:
                timestamp = mode.get('timestamp', 0)
                mode_name = mode.get('mode', 'Unknown')
                time_str = format_flight_time(timestamp, flight_data)
                context_parts.append(f"  {time_str}: {mode_name}")
        
        return "\n".join(context_parts)

    async def execute_anomaly_analysis(self, message: str, flight_data: Dict[str, Any], session_id: str) -> str:
        """Execute anomaly detection analysis"""
        try:
            # Get patterns and comprehensive context
            patterns = await self.detect_patterns_and_changes(flight_data)
            context = await self.prepare_comprehensive_flight_context(flight_data, session_id)
            
            # Load anomaly detection prompt
            prompt_template = self._load_prompt('anomaly/detect.md', word_limit=60)
            
            # Format the prompt with all required placeholders
            formatted_prompt = prompt_template.format(
                patterns=patterns,
                context=context,
                question=message
            )
            
            response = await self.llm_client.generate_response(formatted_prompt)
            # Summarize if needed for anomaly analysis (higher word limit)
            response = await self._summarize_if_needed(response, target_word_limit=100)
            return response
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return "I encountered an error detecting anomalies. Please try again."
    
    async def execute_standard_analysis(self, message: str, flight_data: Dict[str, Any], session_id: str) -> str:
        """Execute standard flight data analysis"""
        try:
            context = await self.prepare_comprehensive_flight_context(flight_data, session_id)
            prompt_template = self._load_prompt('telemetry/enhanced_analysis.md', word_limit=80)
            formatted_prompt = f"{prompt_template}\n\nFlight Data Context:\n{context}\n\nUser Question: {message}"
            
            response = await self.llm_client.generate_response(formatted_prompt)
            # Summarize if needed for standard analysis
            response = await self._summarize_if_needed(response, target_word_limit=80)
            return response
            
        except Exception as e:
            logger.error(f"Error in standard analysis: {e}")
            return "I encountered an error analyzing the flight data. Please try rephrasing your question."
    
    async def handle_general_query(self, query: str, word_limit: int = 80) -> str:
        """Handle general UAV knowledge queries"""
        try:
            # Load general knowledge prompt with standard word limit
            prompt_template = self._load_prompt('general/knowledge.md', word_limit=word_limit)
            
            formatted_prompt = f"{prompt_template}\n\nUser Question: {query}"
            
            response = await self.llm_client.generate_response(formatted_prompt)
            # Summarize if needed
            response = await self._summarize_if_needed(response, target_word_limit=word_limit)
            return response
            
        except Exception as e:
            logger.error(f"Error in general query handling: {e}")
            return "I encountered an error processing your question. Please try again."

    async def handle_general_query_with_clarification(self, message: str) -> Dict[str, Any]:
        """Handle general queries with optional clarification"""
        # Check if the query is too ambiguous and needs clarification
        if await self.query_handler._is_ambiguous_query(message):
            try:
                clarifying_questions = await self.query_handler.get_suggested_clarifications(message)
                return {
                    'content': "I'd be happy to help! Could you be more specific about what you're looking for?",
                    'type': 'clarification',
                    'suggested_questions': clarifying_questions
                }
            except Exception as e:
                logger.warning(f"Error generating clarifications: {e}")
                # Fall through to general handling
        
        # Handle as general query
        response = await self.handle_general_query(message)
        return {
            'content': response,
            'type': 'response',
            'data': {'has_flight_data': False}
        }

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
            # Create summarization prompt
            summarization_prompt = f"""Please summarize this response in {target_word_limit} words or less, keeping the key information and maintaining a helpful tone:

{response}

Summary (max {target_word_limit} words):"""
            
            # Generate summary
            summary = await self.llm_client.generate_response(summarization_prompt)
            
            logger.info(f"Summarized long response: {word_count} words → {self._count_words(summary)} words")
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing response: {e}")
            # Fallback: return original response
            return response

    def _load_prompt(self, filename: str, word_limit: int = 80) -> str:
        """Load prompt file with include support and template variables"""
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', filename)
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