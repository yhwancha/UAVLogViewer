import logging
from typing import Dict, Any, Optional
from mavlink_parser.parser import MAVLinkParser

logger = logging.getLogger(__name__)

def format_flight_time(timestamp: float, flight_data: Optional[Dict[str, Any]] = None) -> str:
    """Format flight timestamp into a readable format"""
    # Convert to minutes and seconds for better readability
    minutes = int(timestamp // 60)
    seconds = int(timestamp % 60)
    
    if minutes > 0:
        time_desc = f"{minutes}m {seconds}s"
    else:
        time_desc = f"{seconds}s"
    
    # Try to get actual time if start_time is available
    if flight_data and flight_data.get("start_time"):
        try:
            from datetime import datetime, timedelta
            start_time = flight_data["start_time"]
            
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
                actual_time = start_dt + timedelta(seconds=timestamp)
                return f"{actual_time.strftime('%H:%M:%S')} ({time_desc} into flight)"
        except Exception as e:
            logger.warning(f"Could not parse start_time for formatting: {e}")
    
    return f"{time_desc} into flight"

async def detect_patterns_and_changes(flight_data: Dict[str, Any]) -> Dict[str, Any]:
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

async def prepare_comprehensive_flight_context(flight_data: Dict[str, Any]) -> str:
    """Prepare comprehensive flight data context for LLM analysis"""
    try:
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
                    time_str = format_flight_time(timestamp, flight_data)
                    context_parts.append(f"  {time_str}: {altitude:.1f}m")
        
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
                    time_str = format_flight_time(timestamp, flight_data)
                    context_parts.append(f"  {time_str} [{severity_name}]: {text}")
        
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
                time_str = format_flight_time(timestamp, flight_data)
                mode_changes.append(f"{time_str}: {mode_name}")
            
            context_parts.append(f"Mode changes: {len(mode_changes)}")
            for change in mode_changes[:10]:  # Show first 10 mode changes
                context_parts.append(f"  {change}")
        
        # Anomaly detection
        try:
            patterns = await detect_patterns_and_changes(flight_data)
            if patterns:
                context_parts.append(f"\n=== DETECTED PATTERNS ===")
                context_parts.append(f"Data patterns detected for analysis")
                # Show a summary of pattern types found
                pattern_types = list(patterns.keys())
                if pattern_types:
                    context_parts.append(f"Pattern categories: {', '.join(pattern_types)}")
        except Exception as e:
            logger.warning(f"Pattern detection failed: {e}")
        
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