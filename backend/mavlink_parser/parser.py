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
        """Parse an ArduPilot DataFlash .bin file or MAVLink telemetry .tlog file and extract flight data"""
        try:
            logger.info(f"Starting to parse file: {file_path}")
            
            # Open the MAVLink log file (supports both .bin and .tlog formats)
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
                # Patch: handle both datetime and str
                if hasattr(start_time, 'strftime'):
                    summary_parts.append(f"Flight Date: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                elif isinstance(start_time, str):
                    summary_parts.append(f"Flight Date: {start_time}")
                else:
                    summary_parts.append(f"Flight Date: [unknown format]")
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
