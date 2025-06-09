import os
import asyncio
from typing import Dict, Any, List, Optional
from pymavlink import mavutil, DFReader
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MAVLinkParser:
    def __init__(self):
        self.supported_message_types = [
            'GPS', 'ATT', 'CTUN', 'BAT', 'IMU', 'MAG', 'BARO', 
            'RCIN', 'RCOU', 'MODE', 'MSG', 'ERR', 'CMD', 'POS', 'AHR2'
        ]

    async def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse an ArduPilot DataFlash .bin file and extract flight data"""
        try:
            logger.info(f"Starting to parse file: {file_path}")
            
            # Open the DataFlash log file
            mlog = mavutil.mavlink_connection(file_path)
            
            parsed_data = {
                "messages": [],
                "flight_stats": {},
                "timeline": [],
                "errors": [],
                "start_time": None,
                "end_time": None,
                "vehicle_type": "Unknown"
            }
            
            message_counts = {}
            altitude_data = []
            battery_data = []
            gps_data = []
            rc_data = []
            attitude_data = []
            modes = []
            
            start_timestamp = None
            end_timestamp = None
            
            # Parse messages
            while True:
                try:
                    msg = mlog.recv_match(blocking=False)
                    if msg is None:
                        break
                    
                    msg_type = msg.get_type()
                    
                    # Get timestamp (different methods for different log types)
                    if hasattr(msg, 'TimeUS'):
                        timestamp = msg.TimeUS / 1000000.0  # Convert microseconds to seconds
                    elif hasattr(msg, '_timestamp'):
                        timestamp = msg._timestamp
                    else:
                        timestamp = 0
                    
                    if start_timestamp is None and timestamp > 0:
                        start_timestamp = timestamp
                    if timestamp > 0:
                        end_timestamp = timestamp
                    
                    # Count message types
                    message_counts[msg_type] = message_counts.get(msg_type, 0) + 1
                    
                    # Debug: Log the first occurrence of each message type
                    if message_counts[msg_type] == 1:
                        logger.info(f"Found message type: {msg_type}")
                    
                    # Extract specific data based on message type
                    if msg_type == 'GPS':
                        if hasattr(msg, 'Alt') and hasattr(msg, 'Lat') and hasattr(msg, 'Lng'):
                            altitude_data.append({
                                'timestamp': timestamp,
                                'latitude': msg.Lat,
                                'longitude': msg.Lng,
                                'absolute_alt': msg.Alt,
                                'relative_alt': msg.RelAlt if hasattr(msg, 'RelAlt') else msg.Alt,
                                'altitude': msg.Alt,
                                'lat': msg.Lat,
                                'lon': msg.Lng
                            })
                            gps_data.append({
                                'timestamp': timestamp,
                                'fix_type': msg.Status if hasattr(msg, 'Status') else 3,
                                'satellites': msg.NSats if hasattr(msg, 'NSats') else 0,
                                'hdop': msg.HDop if hasattr(msg, 'HDop') else None,
                                'vdop': msg.VDop if hasattr(msg, 'VDop') else None
                            })
                    
                    elif msg_type == 'POS':
                        if hasattr(msg, 'Alt'):
                            altitude_data.append({
                                'timestamp': timestamp,
                                'latitude': msg.Lat if hasattr(msg, 'Lat') else None,
                                'longitude': msg.Lng if hasattr(msg, 'Lng') else None,
                                'absolute_alt': msg.Alt,
                                'relative_alt': msg.RelAlt if hasattr(msg, 'RelAlt') else msg.Alt,
                                'altitude': msg.Alt,
                                'altitude_source': 'POS'
                            })
                    
                    elif msg_type == 'CTUN':
                        if hasattr(msg, 'Alt'):
                            altitude_data.append({
                                'timestamp': timestamp,
                                'latitude': None,
                                'longitude': None,
                                'absolute_alt': msg.Alt,
                                'relative_alt': msg.Alt,
                                'altitude': msg.Alt,
                                'altitude_source': 'CTUN'
                            })
                    
                    elif msg_type == 'BAT':
                        if hasattr(msg, 'Volt'):
                            battery_data.append({
                                'timestamp': timestamp,
                                'voltage': msg.Volt,
                                'current': msg.Curr if hasattr(msg, 'Curr') else None,
                                'remaining': msg.CurrTot if hasattr(msg, 'CurrTot') else None,
                                'temperature': msg.Temp if hasattr(msg, 'Temp') else None
                            })
                    
                    elif msg_type == 'RCIN':
                        if hasattr(msg, 'C1'):
                            rc_data.append({
                                'timestamp': timestamp,
                                'chan1': msg.C1,
                                'chan2': msg.C2 if hasattr(msg, 'C2') else 0,
                                'chan3': msg.C3 if hasattr(msg, 'C3') else 0,
                                'chan4': msg.C4 if hasattr(msg, 'C4') else 0,
                                'rssi': 255  # Default value for DataFlash logs
                            })
                    
                    elif msg_type == 'ATT':
                        if hasattr(msg, 'Roll'):
                            attitude_data.append({
                                'timestamp': timestamp,
                                'roll': msg.Roll,
                                'pitch': msg.Pitch,
                                'yaw': msg.Yaw
                            })
                    
                    elif msg_type == 'MSG':
                        if hasattr(msg, 'Message'):
                            message_text = msg.Message
                            # Simple severity determination based on message content
                            severity = 6  # Info level
                            if any(word in message_text.lower() for word in ['error', 'fail', 'critical', 'emergency']):
                                severity = 2  # Critical
                            elif any(word in message_text.lower() for word in ['warning', 'warn']):
                                severity = 4  # Warning
                            
                            if severity <= 4:  # Include warnings and above
                                parsed_data["errors"].append({
                                    'timestamp': timestamp,
                                    'severity': severity,
                                    'text': message_text
                                })
                    
                    elif msg_type == 'MODE':
                        if hasattr(msg, 'Mode'):
                            modes.append({
                                'timestamp': timestamp,
                                'mode': msg.Mode,
                                'mode_num': msg.ModeNum if hasattr(msg, 'ModeNum') else 0
                            })
                            # Try to determine vehicle type from mode
                            if parsed_data["vehicle_type"] == "Unknown":
                                if hasattr(msg, 'Mode'):
                                    mode = msg.Mode
                                    if mode in ['STABILIZE', 'ACRO', 'ALT_HOLD', 'LOITER', 'AUTO']:
                                        parsed_data["vehicle_type"] = "Quadrotor"
                                    elif mode in ['MANUAL', 'CRUISE', 'FBWA', 'FBWB']:
                                        parsed_data["vehicle_type"] = "Fixed Wing"
                    
                except Exception as e:
                    logger.warning(f"Error parsing message: {e}")
                    continue
            
            # Calculate flight statistics
            if start_timestamp and end_timestamp:
                parsed_data["start_time"] = datetime.fromtimestamp(start_timestamp)
                parsed_data["end_time"] = datetime.fromtimestamp(end_timestamp)
                parsed_data["flight_duration"] = end_timestamp - start_timestamp
            
            # Analyze collected data
            parsed_data["flight_stats"] = await self._analyze_flight_data(
                altitude_data, battery_data, gps_data, rc_data, attitude_data
            )
            
            parsed_data["message_counts"] = message_counts
            parsed_data["altitude_data"] = altitude_data
            parsed_data["battery_data"] = battery_data
            parsed_data["gps_data"] = gps_data
            parsed_data["rc_data"] = rc_data
            parsed_data["attitude_data"] = attitude_data
            parsed_data["modes"] = modes
            
            logger.info(f"Parsed {sum(message_counts.values())} messages from {len(message_counts)} message types")
            logger.info(f"Flight duration: {parsed_data.get('flight_duration', 0):.1f} seconds")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing DataFlash file: {e}")
            raise

    async def _analyze_flight_data(self, altitude_data, battery_data, gps_data, rc_data, attitude_data) -> Dict[str, Any]:
        """Analyze parsed flight data to extract key metrics"""
        stats = {}
        
        # Altitude analysis
        if altitude_data:
            altitudes = [d['relative_alt'] for d in altitude_data if d['relative_alt'] is not None]
            if altitudes:
                stats['max_altitude'] = max(altitudes)
                stats['min_altitude'] = min(altitudes)
                stats['avg_altitude'] = np.mean(altitudes)
        
        # Battery analysis
        if battery_data:
            voltages = [d['voltage'] for d in battery_data if d['voltage'] is not None]
            currents = [d['current'] for d in battery_data if d['current'] is not None]
            temperatures = [d['temperature'] for d in battery_data if d['temperature'] is not None]
            
            if voltages:
                stats['max_battery_voltage'] = max(voltages)
                stats['min_battery_voltage'] = min(voltages)
            if currents:
                stats['max_current'] = max(currents)
                stats['avg_current'] = np.mean(currents)
            if temperatures:
                stats['max_battery_temp'] = max(temperatures)
        
        # GPS analysis
        if gps_data:
            gps_losses = [d for d in gps_data if d['fix_type'] < 3]  # No 3D fix
            stats['gps_loss_events'] = len(gps_losses)
            if gps_losses:
                stats['first_gps_loss'] = min(d['timestamp'] for d in gps_losses)
        
        # RC analysis
        if rc_data:
            rc_losses = [d for d in rc_data if d['rssi'] < 50]  # Weak signal
            stats['rc_loss_events'] = len(rc_losses)
            if rc_losses:
                stats['first_rc_loss'] = min(d['timestamp'] for d in rc_losses)
        
        return stats

    async def execute_query(self, flight_data: Dict[str, Any], query_type: str, parameters: Optional[Dict] = None) -> Any:
        """Execute specific queries against flight data"""
        try:
            if query_type == "max_altitude":
                return flight_data.get("flight_stats", {}).get("max_altitude", "No altitude data available")
            
            elif query_type == "flight_duration":
                duration = flight_data.get("flight_duration", 0)
                if duration > 0:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    return f"{minutes} minutes and {seconds} seconds"
                return "Flight duration not available"
            
            elif query_type == "gps_loss":
                gps_events = flight_data.get("flight_stats", {}).get("gps_loss_events", 0)
                first_loss = flight_data.get("flight_stats", {}).get("first_gps_loss")
                if gps_events > 0 and first_loss:
                    return f"GPS signal was lost {gps_events} times, first at {datetime.fromtimestamp(first_loss)}"
                return "No GPS signal loss detected"
            
            elif query_type == "battery_temp":
                max_temp = flight_data.get("flight_stats", {}).get("max_battery_temp")
                if max_temp:
                    return f"Maximum battery temperature: {max_temp}°C"
                return "No battery temperature data available"
            
            elif query_type == "critical_errors":
                errors = flight_data.get("errors", [])
                if errors:
                    critical_errors = [e for e in errors if e['severity'] <= 2]
                    if critical_errors:
                        return f"Found {len(critical_errors)} critical errors: " + \
                               "; ".join([e['text'] for e in critical_errors[:5]])
                    return "No critical errors found"
                return "No error data available"
            
            elif query_type == "rc_loss":
                rc_events = flight_data.get("flight_stats", {}).get("rc_loss_events", 0)
                first_loss = flight_data.get("flight_stats", {}).get("first_rc_loss")
                if rc_events > 0 and first_loss:
                    return f"RC signal was weak/lost {rc_events} times, first at {datetime.fromtimestamp(first_loss)}"
                return "No RC signal loss detected"
            
            else:
                return f"Unknown query type: {query_type}"
                
        except Exception as e:
            logger.error(f"Error executing query {query_type}: {e}")
            return f"Error processing query: {str(e)}"

    async def generate_summary(self, flight_data: Dict[str, Any]) -> str:
        """Generate a comprehensive flight summary"""
        try:
            stats = flight_data.get("flight_stats", {})
            start_time = flight_data.get("start_time")
            duration = flight_data.get("flight_duration", 0)
            vehicle_type = flight_data.get("vehicle_type", "Unknown")
            errors = flight_data.get("errors", [])
            
            summary_parts = []
            
            # Basic info
            summary_parts.append(f"Vehicle Type: {vehicle_type}")
            if start_time:
                summary_parts.append(f"Flight Date: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                summary_parts.append(f"Flight Duration: {minutes} minutes and {seconds} seconds")
            
            # Altitude info
            if stats.get("max_altitude"):
                summary_parts.append(f"Maximum Altitude: {stats['max_altitude']:.1f} meters")
            
            # Battery info
            if stats.get("max_battery_voltage"):
                summary_parts.append(f"Battery Voltage Range: {stats.get('min_battery_voltage', 0):.1f}V - {stats['max_battery_voltage']:.1f}V")
            
            # Issues
            critical_errors = [e for e in errors if e['severity'] <= 2]
            if critical_errors:
                summary_parts.append(f"Critical Errors: {len(critical_errors)} found")
            
            if stats.get("gps_loss_events", 0) > 0:
                summary_parts.append(f"GPS Issues: {stats['gps_loss_events']} signal loss events")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Error generating flight summary"

    async def detect_anomalies(self, flight_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect flight anomalies for LLM analysis"""
        try:
            anomalies = []
            
            # Get data arrays
            altitude_data = flight_data.get('altitude_data', [])
            battery_data = flight_data.get('battery_data', [])
            gps_data = flight_data.get('gps_data', [])
            attitude_data = flight_data.get('attitude_data', [])
            errors = flight_data.get('errors', [])
            
            # 1. Altitude anomalies
            if altitude_data:
                altitudes = [d['altitude'] for d in altitude_data if d['altitude'] is not None]
                timestamps = [d['timestamp'] for d in altitude_data if d['altitude'] is not None]
                
                if len(altitudes) > 10:
                    # Check for sudden altitude drops (exclude normal landing)
                    significant_drops = []
                    for i in range(1, len(altitudes)):
                        if i < len(timestamps):
                            time_diff = timestamps[i] - timestamps[i-1] if i > 0 else 1
                            altitude_diff = altitudes[i-1] - altitudes[i]
                            
                            # Only consider drops > 50m in less than 5 seconds as anomalies
                            if altitude_diff > 50 and time_diff < 5:
                                significant_drops.append({
                                    'altitude_drop': altitude_diff,
                                    'time_diff': time_diff,
                                    'timestamp': timestamps[i],
                                    'rate': altitude_diff / max(time_diff, 0.1)  # m/s
                                })
                    
                    # Group consecutive drops into single events
                    if significant_drops:
                        # Only report the most severe drops (top 5)
                        significant_drops.sort(key=lambda x: x['altitude_drop'], reverse=True)
                        for drop in significant_drops[:5]:
                            anomalies.append({
                                'type': 'altitude_drop',
                                'severity': 'high',
                                'description': f'Sudden altitude drop of {drop["altitude_drop"]:.1f}m in {drop["time_diff"]:.1f}s (rate: {drop["rate"]:.1f}m/s)',
                                'timestamp': drop['timestamp'],
                                'value': drop['altitude_drop']
                            })
                    
                    # Check for unusual altitude patterns
                    max_alt = max(altitudes)
                    if max_alt > 1000:  # Very high altitude
                        anomalies.append({
                            'type': 'high_altitude',
                            'severity': 'medium',
                            'description': f'Flight reached unusually high altitude: {max_alt:.1f}m',
                            'value': max_alt
                        })
            
            # 2. Battery anomalies
            if battery_data:
                voltages = [d['voltage'] for d in battery_data if d['voltage'] is not None and d['voltage'] > 0]
                if voltages:
                    min_voltage = min(voltages)
                    voltage_range = max(voltages) - min(voltages)
                    
                    if min_voltage < 10:  # Very low voltage
                        anomalies.append({
                            'type': 'low_battery',
                            'severity': 'high',
                            'description': f'Battery voltage dropped to {min_voltage:.1f}V',
                            'value': min_voltage
                        })
                    
                    if voltage_range > 30:  # Unusual voltage swing
                        anomalies.append({
                            'type': 'voltage_instability',
                            'severity': 'medium',
                            'description': f'Large battery voltage variation: {voltage_range:.1f}V range',
                            'value': voltage_range
                        })
            
            # 3. GPS anomalies
            gps_loss_count = flight_data.get('flight_stats', {}).get('gps_loss_events', 0)
            if gps_loss_count > 10:
                anomalies.append({
                    'type': 'gps_instability',
                    'severity': 'high',
                    'description': f'Frequent GPS signal loss: {gps_loss_count} events',
                    'value': gps_loss_count
                })
            
            # 4. Critical error analysis
            critical_errors = [e for e in errors if e['severity'] <= 3]
            if critical_errors:
                error_types = {}
                for error in critical_errors:
                    error_type = error['text']
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                
                for error_type, count in error_types.items():
                    anomalies.append({
                        'type': 'critical_error',
                        'severity': 'high',
                        'description': f'Critical error occurred {count} times: {error_type}',
                        'value': count,
                        'error_text': error_type
                    })
            
            # 5. Attitude anomalies (extreme angles)
            if attitude_data:
                rolls = [d['roll'] for d in attitude_data if d['roll'] is not None]
                pitches = [d['pitch'] for d in attitude_data if d['pitch'] is not None]
                
                if rolls:
                    max_roll = max(abs(r) for r in rolls)
                    if max_roll > 60:  # Extreme roll angle
                        anomalies.append({
                            'type': 'extreme_attitude',
                            'severity': 'medium',
                            'description': f'Extreme roll angle detected: {max_roll:.1f}°',
                            'value': max_roll
                        })
                
                if pitches:
                    max_pitch = max(abs(p) for p in pitches)
                    if max_pitch > 45:  # Extreme pitch angle
                        anomalies.append({
                            'type': 'extreme_attitude',
                            'severity': 'medium',
                            'description': f'Extreme pitch angle detected: {max_pitch:.1f}°',
                            'value': max_pitch
                        })
            
            # Sort by severity
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            anomalies.sort(key=lambda x: severity_order.get(x['severity'], 3))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    async def generate_anomaly_report(self, flight_data: Dict[str, Any]) -> str:
        """Generate a human-readable anomaly report for LLM analysis"""
        try:
            anomalies = await self.detect_anomalies(flight_data)
            
            if not anomalies:
                return "No significant flight anomalies detected. The flight appears to have operated within normal parameters."
            
            report_parts = []
            
            # Group by severity
            high_severity = [a for a in anomalies if a['severity'] == 'high']
            medium_severity = [a for a in anomalies if a['severity'] == 'medium']
            
            if high_severity:
                report_parts.append("HIGH SEVERITY ISSUES:")
                for anomaly in high_severity:
                    report_parts.append(f"- {anomaly['description']}")
            
            if medium_severity:
                report_parts.append("\nMEDIUM SEVERITY ISSUES:")
                for anomaly in medium_severity:
                    report_parts.append(f"- {anomaly['description']}")
            
            # Add recommendations
            report_parts.append("\nRECOMMENDATIONS:")
            if any(a['type'] == 'critical_error' for a in anomalies):
                report_parts.append("- Review system logs for critical errors and address underlying causes")
            if any(a['type'] == 'gps_instability' for a in anomalies):
                report_parts.append("- Check GPS antenna placement and interference sources")
            if any(a['type'] == 'low_battery' for a in anomalies):
                report_parts.append("- Inspect battery condition and charging system")
            if any(a['type'] == 'altitude_drop' for a in anomalies):
                report_parts.append("- Investigate flight controller performance and sensor calibration")
            
            return "\n".join(report_parts)
            
        except Exception as e:
            logger.error(f"Error generating anomaly report: {e}")
            return "Error generating anomaly analysis report." 