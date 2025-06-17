import os
import asyncio
from typing import Dict, Any, List, Optional
from pymavlink import mavutil, DFReader
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from .types import (
    MAV_VEHICLE_TYPES, 
    MAV_AUTOPILOT_TYPES, 
    SUPPORTED_MESSAGE_TYPES,
    MULTICOPTER_MODES,
    FIXED_WING_MODES,
    ROVER_MODES,
    HELICOPTER_MODES,
    MessageSeverity,
    SEVERITY_KEYWORDS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
INT16_MAX = 32767

class MAVLinkParser:
    def __init__(self):
        # Import types from types module
        self.supported_message_types = SUPPORTED_MESSAGE_TYPES
        self.mav_vehicle_types = MAV_VEHICLE_TYPES
        self.mav_autopilot_types = MAV_AUTOPILOT_TYPES

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
                "vehicle_type": "Unknown",
                "autopilot_type": "Unknown",
                "vehicle_id": None,
                "component_id": None
            }
            
            message_counts = {}
            altitude_data = []
            battery_data = []
            gps_data = []
            rc_data = []
            attitude_data = []
            modes = []
            heartbeat_data = []
            system_status = []
            
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
                    
                    # Process HEARTBEAT messages for vehicle identification (MAVLink standard)
                    if msg_type == 'HEARTBEAT':
                        heartbeat_data.append({
                            'timestamp': timestamp,
                            'type': msg.type,
                            'autopilot': msg.autopilot,
                            'base_mode': msg.base_mode,
                            'custom_mode': msg.custom_mode,
                            'system_status': msg.system_status,
                            'mavlink_version': msg.mavlink_version
                        })
                        
                        # Determine vehicle type from HEARTBEAT message
                        if parsed_data["vehicle_type"] == "Unknown":
                            vehicle_type_id = msg.type
                            parsed_data["vehicle_type"] = self.mav_vehicle_types.get(vehicle_type_id, f"Unknown Type {vehicle_type_id}")
                            
                        # Determine autopilot type
                        if parsed_data["autopilot_type"] == "Unknown":
                            autopilot_id = msg.autopilot
                            parsed_data["autopilot_type"] = self.mav_autopilot_types.get(autopilot_id, f"Unknown Autopilot {autopilot_id}")
                    
                    # Process SYS_STATUS messages for system health
                    elif msg_type == 'SYS_STATUS':
                        system_status.append({
                            'timestamp': timestamp,
                            'onboard_control_sensors_present': msg.onboard_control_sensors_present,
                            'onboard_control_sensors_enabled': msg.onboard_control_sensors_enabled,
                            'onboard_control_sensors_health': msg.onboard_control_sensors_health,
                            'load': msg.load,
                            'voltage_battery': msg.voltage_battery,
                            'current_battery': msg.current_battery,
                            'battery_remaining': msg.battery_remaining,
                            'drop_rate_comm': msg.drop_rate_comm
                        })
                    
                    # Extract specific data based on message type
                    elif msg_type in ['GPS', 'GPS2']:
                        gps_info = self._extract_gps_data(msg, timestamp, msg_type)
                        if gps_info:
                            if gps_info.get('altitude') is not None:
                                altitude_data.append(gps_info)
                            gps_data.append(gps_info)
                    
                    elif msg_type == 'GPA':
                        gps_info = self._extract_gps_data(msg, timestamp, msg_type)
                        if gps_info:
                            if gps_info.get('hdop') is not None or gps_info.get('vdop') is not None:
                                gps_data.append(gps_info)
                    
                    elif msg_type in ['GPS_RAW_INT', 'GLOBAL_POSITION_INT']:
                        gps_info = self._extract_gps_data(msg, timestamp, msg_type)
                        if gps_info:
                            if gps_info.get('altitude') is not None:
                                altitude_data.append(gps_info)
                            gps_data.append(gps_info)
                    
                    elif msg_type in ['POS', 'LOCAL_POSITION_NED']:
                        pos_info = self._extract_position_data(msg, timestamp, msg_type)
                        if pos_info:
                            altitude_data.append(pos_info)
                    
                    elif msg_type in ['CTUN', 'NTUN']:
                        if hasattr(msg, 'Alt'):
                            altitude_data.append({
                                'timestamp': timestamp,
                                'latitude': None,
                                'longitude': None,
                                'absolute_alt': msg.Alt,
                                'relative_alt': msg.Alt,
                                'altitude': msg.Alt,
                                'altitude_source': msg_type
                            })
                    
                    elif msg_type in ['BAT', 'BATTERY_STATUS', 'CURR', 'POWR']:
                        battery_info = self._extract_battery_data(msg, timestamp, msg_type)
                        if battery_info:
                            battery_data.append(battery_info)
                    
                    elif msg_type in ['RCIN', 'RC_CHANNELS', 'RC_CHANNELS_RAW', 'RCOU']:
                        rc_info = self._extract_rc_data(msg, timestamp, msg_type)
                        if rc_info:
                            rc_data.append(rc_info)
                    
                    elif msg_type in ['ATT', 'ATTITUDE', 'AHR2', 'AHR3']:
                        attitude_info = self._extract_attitude_data(msg, timestamp, msg_type)
                        if attitude_info:
                            attitude_data.append(attitude_info)
                    
                    elif msg_type in ['MSG', 'STATUSTEXT', 'ERR']:
                        error_info = self._extract_message_data(msg, timestamp, msg_type)
                        if error_info and error_info['severity'] <= 4:  # Include warnings and above
                            parsed_data["errors"].append(error_info)
                    
                    elif msg_type == 'MODE':
                        if hasattr(msg, 'Mode'):
                            modes.append({
                                'timestamp': timestamp,
                                'mode': msg.Mode,
                                'mode_num': msg.ModeNum if hasattr(msg, 'ModeNum') else 0
                            })
                            
                            # Fallback vehicle type detection from mode (for DataFlash logs without HEARTBEAT)
                            if parsed_data["vehicle_type"] == "Unknown":
                                parsed_data["vehicle_type"] = self._determine_vehicle_type_from_mode(msg.Mode)
                    
                    # Process Extended Kalman Filter messages
                    elif msg_type in ['XKFS', 'XKQ', 'XKV1', 'XKV2', 'XKT', 'XKFM', 'NKF1', 'NKF2', 'NKF3', 'NKF4', 'NKF5']:
                        ekf_info = self._extract_ekf_data(msg, timestamp, msg_type)
                        if ekf_info:
                            # Store EKF data for analysis
                            if 'ekf_data' not in parsed_data:
                                parsed_data['ekf_data'] = []
                            parsed_data['ekf_data'].append(ekf_info)
                    
                    # Process IMU messages (including legacy variants)
                    elif msg_type in ['IMU', 'IMU2', 'IMU3', 'ACC', 'ACC2', 'ACC3', 'GYR', 'GYR2', 'GYR3']:
                        imu_info = self._extract_imu_data(msg, timestamp, msg_type)
                        if imu_info:
                            if 'imu_data' not in parsed_data:
                                parsed_data['imu_data'] = []
                            parsed_data['imu_data'].append(imu_info)
                    
                    # Process barometer messages
                    elif msg_type in ['BARO', 'BAR2', 'BAR3']:
                        baro_info = self._extract_baro_data(msg, timestamp, msg_type)
                        if baro_info:
                            if 'baro_data' not in parsed_data:
                                parsed_data['baro_data'] = []
                            parsed_data['baro_data'].append(baro_info)
                    
                    # Process magnetometer messages
                    elif msg_type in ['MAG', 'MAG2', 'MAG3']:
                        mag_info = self._extract_mag_data(msg, timestamp, msg_type)
                        if mag_info:
                            if 'mag_data' not in parsed_data:
                                parsed_data['mag_data'] = []
                            parsed_data['mag_data'].append(mag_info)
                    
                    # Process performance monitoring
                    elif msg_type == 'PM':
                        pm_info = self._extract_performance_data(msg, timestamp, msg_type)
                        if pm_info:
                            if 'performance_data' not in parsed_data:
                                parsed_data['performance_data'] = []
                            parsed_data['performance_data'].append(pm_info)
                    
                    # Process vibration data
                    elif msg_type in ['VIBE', 'VIBRATION']:
                        vibe_info = self._extract_vibration_data(msg, timestamp, msg_type)
                        if vibe_info:
                            if 'vibration_data' not in parsed_data:
                                parsed_data['vibration_data'] = []
                            parsed_data['vibration_data'].append(vibe_info)
                    
                except Exception as e:
                    logger.warning(f"Error parsing message {msg_type}: {e}")
                    continue
            
            # Calculate flight statistics
            if start_timestamp and end_timestamp:
                parsed_data["start_time"] = datetime.fromtimestamp(start_timestamp)
                parsed_data["end_time"] = datetime.fromtimestamp(end_timestamp)
                parsed_data["flight_duration"] = end_timestamp - start_timestamp
            
            # Analyze collected data
            parsed_data["flight_stats"] = await self._analyze_flight_data(
                altitude_data, battery_data, gps_data, rc_data, attitude_data, system_status
            )
            
            parsed_data["message_counts"] = message_counts
            parsed_data["altitude_data"] = altitude_data
            parsed_data["battery_data"] = battery_data
            parsed_data["gps_data"] = gps_data
            parsed_data["rc_data"] = rc_data
            parsed_data["attitude_data"] = attitude_data
            parsed_data["modes"] = modes
            parsed_data["heartbeat_data"] = heartbeat_data
            parsed_data["system_status"] = system_status
            
            logger.info(f"Parsed {sum(message_counts.values())} messages from {len(message_counts)} message types")
            logger.info(f"Vehicle Type: {parsed_data['vehicle_type']}")
            logger.info(f"Autopilot: {parsed_data['autopilot_type']}")
            logger.info(f"Flight duration: {parsed_data.get('flight_duration', 0):.1f} seconds")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing MAVLink file: {e}")
            raise

    def _extract_gps_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract GPS data from various GPS message types"""
        try:
            gps_info = {'timestamp': timestamp, 'message_type': msg_type}
            
            if msg_type in ['GPS', 'GPS2']:
                # ArduPilot DataFlash GPS message
                if hasattr(msg, 'Alt') and hasattr(msg, 'Lat') and hasattr(msg, 'Lng'):
                    gps_info.update({
                        'latitude': msg.Lat,
                        'longitude': msg.Lng,
                        'absolute_alt': msg.Alt,
                        'relative_alt': msg.RelAlt if hasattr(msg, 'RelAlt') else msg.Alt,
                        'altitude': msg.Alt,
                        'lat': msg.Lat,
                        'lon': msg.Lng,
                        'fix_type': msg.Status if hasattr(msg, 'Status') else 3,
                        'satellites': msg.NSats if hasattr(msg, 'NSats') else 0,
                        'hdop': msg.HDop if hasattr(msg, 'HDop') else None,
                        'vdop': msg.VDop if hasattr(msg, 'VDop') else None,
                        'ground_speed': msg.Spd if hasattr(msg, 'Spd') else None,
                        'ground_course': msg.GCrs if hasattr(msg, 'GCrs') else None
                    })
                    return gps_info
            
            elif msg_type == 'GPA':
                # GPS accuracy message
                if hasattr(msg, 'VDop') or hasattr(msg, 'HDop'):
                    gps_info.update({
                        'hdop': msg.HDop if hasattr(msg, 'HDop') else None,
                        'vdop': msg.VDop if hasattr(msg, 'VDop') else None,
                        'satellites': msg.SAcc if hasattr(msg, 'SAcc') else None,
                        'message_subtype': 'accuracy'
                    })
                    return gps_info
                    
            elif msg_type == 'GPS_RAW_INT':
                # MAVLink GPS_RAW_INT message
                gps_info.update({
                    'latitude': msg.lat / 1e7,
                    'longitude': msg.lon / 1e7,
                    'absolute_alt': msg.alt / 1000.0,  # Convert mm to m
                    'altitude': msg.alt / 1000.0,
                    'fix_type': msg.fix_type,
                    'satellites': msg.satellites_visible,
                    'hdop': msg.eph / 100.0 if msg.eph != 65535 else None,
                    'vdop': msg.epv / 100.0 if msg.epv != 65535 else None,
                    'ground_speed': msg.vel / 100.0 if msg.vel != 65535 else None,
                    'ground_course': msg.cog / 100.0 if msg.cog != 65535 else None
                })
                return gps_info
                
            elif msg_type == 'GLOBAL_POSITION_INT':
                # MAVLink GLOBAL_POSITION_INT message
                gps_info.update({
                    'latitude': msg.lat / 1e7,
                    'longitude': msg.lon / 1e7,
                    'absolute_alt': msg.alt / 1000.0,
                    'relative_alt': msg.relative_alt / 1000.0,
                    'altitude': msg.alt / 1000.0,
                    'ground_speed': np.sqrt(msg.vx**2 + msg.vy**2) / 100.0,
                    'vertical_speed': msg.vz / 100.0,
                    'heading': msg.hdg / 100.0 if msg.hdg != 65535 else None
                })
                return gps_info
                
        except Exception as e:
            logger.warning(f"Error extracting GPS data from {msg_type}: {e}")
        
        return None

    def _extract_position_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract position data from position messages"""
        try:
            if msg_type == 'POS' and hasattr(msg, 'Alt'):
                return {
                    'timestamp': timestamp,
                    'latitude': msg.Lat if hasattr(msg, 'Lat') else None,
                    'longitude': msg.Lng if hasattr(msg, 'Lng') else None,
                    'absolute_alt': msg.Alt,
                    'relative_alt': msg.RelAlt if hasattr(msg, 'RelAlt') else msg.Alt,
                    'altitude': msg.Alt,
                    'altitude_source': 'POS'
                }
            elif msg_type == 'LOCAL_POSITION_NED':
                return {
                    'timestamp': timestamp,
                    'latitude': None,
                    'longitude': None,
                    'absolute_alt': -msg.z,  # NED frame, z is down
                    'relative_alt': -msg.z,
                    'altitude': -msg.z,
                    'altitude_source': 'LOCAL_POSITION_NED',
                    'x': msg.x,
                    'y': msg.y,
                    'z': msg.z,
                    'vx': msg.vx,
                    'vy': msg.vy,
                    'vz': msg.vz
                }
        except Exception as e:
            logger.warning(f"Error extracting position data from {msg_type}: {e}")
        
        return None

    def _extract_battery_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract battery data from various battery message types"""
        try:
            if msg_type == 'BAT' and hasattr(msg, 'Volt'):
                return {
                    'timestamp': timestamp,
                    'voltage': msg.Volt,
                    'current': msg.Curr if hasattr(msg, 'Curr') else None,
                    'remaining': msg.CurrTot if hasattr(msg, 'CurrTot') else None,
                    'temperature': msg.Temp if hasattr(msg, 'Temp') else None,
                    'message_type': msg_type
                }
            elif msg_type == 'CURR' and hasattr(msg, 'Volt'):
                return {
                    'timestamp': timestamp,
                    'voltage': msg.Volt,
                    'current': msg.Curr if hasattr(msg, 'Curr') else None,
                    'current_total': msg.CurrTot if hasattr(msg, 'CurrTot') else None,
                    'message_type': msg_type
                }
            elif msg_type == 'POWR' and hasattr(msg, 'Vcc'):
                return {
                    'timestamp': timestamp,
                    'voltage': msg.Vcc / 1000.0 if hasattr(msg, 'Vcc') else None,  # Convert mV to V
                    'voltage_servo': msg.VServo / 1000.0 if hasattr(msg, 'VServo') else None,
                    'flags': msg.Flags if hasattr(msg, 'Flags') else None,
                    'message_type': msg_type
                }
            elif msg_type == 'BATTERY_STATUS':
                return {
                    'timestamp': timestamp,
                    'voltage': sum(msg.voltages[:msg.voltages_ext]) / 1000.0 if msg.voltages else None,
                    'current': msg.current_battery / 100.0 if msg.current_battery != -1 else None,
                    'remaining': msg.battery_remaining if msg.battery_remaining != -1 else None,
                    'temperature': msg.temperature / 100.0 if msg.temperature != INT16_MAX else None,
                    'battery_function': msg.battery_function,
                    'battery_type': msg.type,
                    'message_type': msg_type
                }
        except Exception as e:
            logger.warning(f"Error extracting battery data from {msg_type}: {e}")
        
        return None

    def _extract_rc_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract RC data from various RC message types"""
        try:
            rc_info = {'timestamp': timestamp, 'message_type': msg_type}
            
            if msg_type == 'RCIN' and hasattr(msg, 'C1'):
                rc_info.update({
                    'chan1': msg.C1,
                    'chan2': msg.C2 if hasattr(msg, 'C2') else 0,
                    'chan3': msg.C3 if hasattr(msg, 'C3') else 0,
                    'chan4': msg.C4 if hasattr(msg, 'C4') else 0,
                    'chan5': msg.C5 if hasattr(msg, 'C5') else 0,
                    'chan6': msg.C6 if hasattr(msg, 'C6') else 0,
                    'chan7': msg.C7 if hasattr(msg, 'C7') else 0,
                    'chan8': msg.C8 if hasattr(msg, 'C8') else 0,
                    'rssi': 255  # Default value for DataFlash logs
                })
                return rc_info
            
            elif msg_type == 'RCOU' and hasattr(msg, 'C1'):
                rc_info.update({
                    'chan1_out': msg.C1,
                    'chan2_out': msg.C2 if hasattr(msg, 'C2') else 0,
                    'chan3_out': msg.C3 if hasattr(msg, 'C3') else 0,
                    'chan4_out': msg.C4 if hasattr(msg, 'C4') else 0,
                    'chan5_out': msg.C5 if hasattr(msg, 'C5') else 0,
                    'chan6_out': msg.C6 if hasattr(msg, 'C6') else 0,
                    'chan7_out': msg.C7 if hasattr(msg, 'C7') else 0,
                    'chan8_out': msg.C8 if hasattr(msg, 'C8') else 0,
                    'output_type': 'servo'
                })
                return rc_info
                
            elif msg_type in ['RC_CHANNELS', 'RC_CHANNELS_RAW']:
                rc_info.update({
                    'chan1': msg.chan1_raw,
                    'chan2': msg.chan2_raw,
                    'chan3': msg.chan3_raw,
                    'chan4': msg.chan4_raw,
                    'chan5': msg.chan5_raw if hasattr(msg, 'chan5_raw') else 0,
                    'chan6': msg.chan6_raw if hasattr(msg, 'chan6_raw') else 0,
                    'chan7': msg.chan7_raw if hasattr(msg, 'chan7_raw') else 0,
                    'chan8': msg.chan8_raw if hasattr(msg, 'chan8_raw') else 0,
                    'rssi': msg.rssi if hasattr(msg, 'rssi') else 255
                })
                return rc_info
                
        except Exception as e:
            logger.warning(f"Error extracting RC data from {msg_type}: {e}")
        
        return None

    def _extract_attitude_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract attitude data from attitude messages"""
        try:
            if msg_type == 'ATT' and hasattr(msg, 'Roll'):
                return {
                    'timestamp': timestamp,
                    'roll': msg.Roll,
                    'pitch': msg.Pitch,
                    'yaw': msg.Yaw,
                    'message_type': msg_type
                }
            elif msg_type in ['AHR2', 'AHR3'] and hasattr(msg, 'Roll'):
                return {
                    'timestamp': timestamp,
                    'roll': msg.Roll,
                    'pitch': msg.Pitch,
                    'yaw': msg.Yaw,
                    'altitude': msg.Alt if hasattr(msg, 'Alt') else None,
                    'latitude': msg.Lat if hasattr(msg, 'Lat') else None,
                    'longitude': msg.Lng if hasattr(msg, 'Lng') else None,
                    'message_type': msg_type
                }
            elif msg_type == 'ATTITUDE':
                return {
                    'timestamp': timestamp,
                    'roll': msg.roll,
                    'pitch': msg.pitch,
                    'yaw': msg.yaw,
                    'rollspeed': msg.rollspeed,
                    'pitchspeed': msg.pitchspeed,
                    'yawspeed': msg.yawspeed,
                    'message_type': msg_type
                }
        except Exception as e:
            logger.warning(f"Error extracting attitude data from {msg_type}: {e}")
        
        return None

    def _extract_message_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract message/status text data"""
        try:
            if msg_type == 'MSG' and hasattr(msg, 'Message'):
                message_text = msg.Message
                severity = self._determine_message_severity(message_text)
                return {
                    'timestamp': timestamp,
                    'severity': severity,
                    'text': message_text,
                    'message_type': msg_type
                }
            elif msg_type == 'ERR' and hasattr(msg, 'Subsys'):
                # Error message with subsystem and error code
                error_text = f"Subsystem {msg.Subsys}: Error {msg.ECode}"
                return {
                    'timestamp': timestamp,
                    'severity': MessageSeverity.ERROR,
                    'text': error_text,
                    'subsystem': msg.Subsys,
                    'error_code': msg.ECode,
                    'message_type': msg_type
                }
            elif msg_type == 'STATUSTEXT':
                return {
                    'timestamp': timestamp,
                    'severity': msg.severity,
                    'text': msg.text.decode('utf-8') if isinstance(msg.text, bytes) else msg.text,
                    'message_type': msg_type
                }
        except Exception as e:
            logger.warning(f"Error extracting message data from {msg_type}: {e}")
        
        return None

    def _determine_message_severity(self, message_text: str) -> int:
        """Determine message severity based on content"""
        message_lower = message_text.lower()
        
        # Use imported severity keywords
        for severity, keywords in SEVERITY_KEYWORDS.items():
            if any(word in message_lower for word in keywords):
                return severity
        
        # Default to INFO level
        return MessageSeverity.INFO

    def _determine_vehicle_type_from_mode(self, mode: str) -> str:
        """Determine vehicle type from flight mode (fallback method)"""
        # Use imported mode lists
        if mode in MULTICOPTER_MODES:
            return "Quadrotor"
        elif mode in FIXED_WING_MODES:
            return "Fixed Wing"
        elif mode in ROVER_MODES:
            return "Ground Rover"
        elif mode in HELICOPTER_MODES:
            return "Helicopter"
        
        return "Unknown"

    async def _analyze_flight_data(self, altitude_data, battery_data, gps_data, rc_data, attitude_data, system_status) -> Dict[str, Any]:
        """Analyze parsed flight data to extract key metrics"""
        stats = {}
        
        # Altitude analysis
        if altitude_data:
            altitudes = [d.get('relative_alt') for d in altitude_data if d.get('relative_alt') is not None]
            if altitudes:
                stats['max_altitude'] = max(altitudes)
                stats['min_altitude'] = min(altitudes)
                stats['avg_altitude'] = np.mean(altitudes)
                stats['altitude_variance'] = np.var(altitudes)
        
        # Battery analysis
        if battery_data:
            voltages = [d.get('voltage') for d in battery_data if d.get('voltage') is not None]
            currents = [d.get('current') for d in battery_data if d.get('current') is not None]
            temperatures = [d.get('temperature') for d in battery_data if d.get('temperature') is not None]
            
            if voltages:
                stats['max_battery_voltage'] = max(voltages)
                stats['min_battery_voltage'] = min(voltages)
                stats['avg_battery_voltage'] = np.mean(voltages)
                stats['battery_voltage_drop'] = max(voltages) - min(voltages)
                
            if currents:
                stats['max_current'] = max(currents)
                stats['avg_current'] = np.mean(currents)
                stats['total_current_consumed'] = np.trapz(currents) if len(currents) > 1 else 0
                
            if temperatures:
                stats['max_battery_temp'] = max(temperatures)
                stats['min_battery_temp'] = min(temperatures)
        
        # GPS analysis
        if gps_data:
            gps_losses = [d for d in gps_data if d.get('fix_type', 0) < 3]  # No 3D fix
            stats['gps_loss_events'] = len(gps_losses)
            if gps_losses:
                stats['first_gps_loss'] = min(d.get('timestamp', 0) for d in gps_losses)
            
            # GPS quality metrics
            satellites = [d.get('satellites', 0) for d in gps_data if d.get('satellites') is not None]
            if satellites:
                stats['avg_satellites'] = np.mean(satellites)
                stats['min_satellites'] = min(satellites)
            
            hdops = [d.get('hdop') for d in gps_data if d.get('hdop') is not None]
            if hdops:
                stats['avg_hdop'] = np.mean(hdops)
                stats['max_hdop'] = max(hdops)
        
        # RC analysis
        if rc_data:
            rc_losses = [d for d in rc_data if d.get('rssi', 255) < 50]  # Weak signal
            stats['rc_loss_events'] = len(rc_losses)
            if rc_losses:
                stats['first_rc_loss'] = min(d.get('timestamp', 0) for d in rc_losses)
        
        # Attitude analysis
        if attitude_data:
            rolls = [d.get('roll', 0) for d in attitude_data]
            pitches = [d.get('pitch', 0) for d in attitude_data]
            
            if rolls:
                stats['max_roll'] = max(abs(r) for r in rolls)
            if pitches:
                stats['max_pitch'] = max(abs(p) for p in pitches)
        
        # System status analysis
        if system_status:
            loads = [d.get('load', 0) for d in system_status]
            if loads:
                stats['max_cpu_load'] = max(loads) / 10.0  # Convert to percentage
                stats['avg_cpu_load'] = np.mean(loads) / 10.0
        
        return stats

    async def generate_summary(self, flight_data: Dict[str, Any]) -> str:
        """Generate a comprehensive flight summary"""
        try:
            stats = flight_data.get("flight_stats", {})
            start_time = flight_data.get("start_time")
            duration = flight_data.get("flight_duration", 0)
            vehicle_type = flight_data.get("vehicle_type", "Unknown")
            autopilot_type = flight_data.get("autopilot_type", "Unknown")
            errors = flight_data.get("errors", [])
            
            summary_parts = []
            
            # Basic info
            summary_parts.append(f"Vehicle: {vehicle_type}")
            if autopilot_type != "Unknown":
                summary_parts.append(f"Autopilot: {autopilot_type}")
                
            if start_time:
                # Patch: handle both datetime and str
                if hasattr(start_time, 'strftime'):
                    summary_parts.append(f"Date: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                elif isinstance(start_time, str):
                    summary_parts.append(f"Date: {start_time}")
                    
            if duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                summary_parts.append(f"Duration: {minutes}m {seconds}s")
            
            # Performance metrics
            if stats.get("max_altitude"):
                summary_parts.append(f"Max Alt: {stats['max_altitude']:.1f}m")
            
            if stats.get("max_battery_voltage") and stats.get("min_battery_voltage"):
                summary_parts.append(f"Battery: {stats['min_battery_voltage']:.1f}V-{stats['max_battery_voltage']:.1f}V")
            
            if stats.get("avg_satellites"):
                summary_parts.append(f"GPS Sats: {stats['avg_satellites']:.0f} avg")
            
            # Issues and warnings
            critical_errors = [e for e in errors if e.get('severity', 6) <= 2]
            warnings = [e for e in errors if e.get('severity', 6) == 4]
            
            if critical_errors:
                summary_parts.append(f"Critical: {len(critical_errors)} errors")
            elif warnings:
                summary_parts.append(f"Warnings: {len(warnings)}")
            
            if stats.get("gps_loss_events", 0) > 0:
                summary_parts.append(f"GPS Issues: {stats['gps_loss_events']} events")
            
            if stats.get("rc_loss_events", 0) > 0:
                summary_parts.append(f"RC Issues: {stats['rc_loss_events']} events")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Error generating flight summary"

    def _extract_ekf_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract Extended Kalman Filter data from various EKF message types"""
        try:
            ekf_info = {'timestamp': timestamp, 'message_type': msg_type}
            
            if msg_type in ['XKFS', 'NKF1']:
                # EKF status message
                ekf_info.update({
                    'roll_innovation': msg.RI if hasattr(msg, 'RI') else None,
                    'pitch_innovation': msg.PI if hasattr(msg, 'PI') else None,
                    'yaw_innovation': msg.YI if hasattr(msg, 'YI') else None,
                    'velocity_variance': msg.VV if hasattr(msg, 'VV') else None,
                    'position_variance': msg.PV if hasattr(msg, 'PV') else None,
                    'height_variance': msg.HV if hasattr(msg, 'HV') else None,
                    'mag_variance': msg.MV if hasattr(msg, 'MV') else None,
                    'tas_ratio': msg.TR if hasattr(msg, 'TR') else None
                })
                return ekf_info
                
            elif msg_type in ['XKV1', 'XKV2']:
                # EKF velocity message
                ekf_info.update({
                    'velocity_north': msg.VN if hasattr(msg, 'VN') else None,
                    'velocity_east': msg.VE if hasattr(msg, 'VE') else None,
                    'velocity_down': msg.VD if hasattr(msg, 'VD') else None
                })
                return ekf_info
                
            elif msg_type == 'XKQ':
                # EKF quaternion message
                ekf_info.update({
                    'q1': msg.Q1 if hasattr(msg, 'Q1') else None,
                    'q2': msg.Q2 if hasattr(msg, 'Q2') else None,
                    'q3': msg.Q3 if hasattr(msg, 'Q3') else None,
                    'q4': msg.Q4 if hasattr(msg, 'Q4') else None
                })
                return ekf_info
                
        except Exception as e:
            logger.warning(f"Error extracting EKF data from {msg_type}: {e}")
        
        return None
    
    def _extract_imu_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract IMU data from various IMU message types"""
        try:
            imu_info = {'timestamp': timestamp, 'message_type': msg_type}
            
            if msg_type in ['IMU', 'IMU2', 'IMU3']:
                imu_info.update({
                    'gyro_x': msg.GyrX if hasattr(msg, 'GyrX') else None,
                    'gyro_y': msg.GyrY if hasattr(msg, 'GyrY') else None,
                    'gyro_z': msg.GyrZ if hasattr(msg, 'GyrZ') else None,
                    'accel_x': msg.AccX if hasattr(msg, 'AccX') else None,
                    'accel_y': msg.AccY if hasattr(msg, 'AccY') else None,
                    'accel_z': msg.AccZ if hasattr(msg, 'AccZ') else None,
                    'temperature': msg.T if hasattr(msg, 'T') else None
                })
                return imu_info
                
            elif msg_type in ['ACC', 'ACC2', 'ACC3']:
                imu_info.update({
                    'accel_x': msg.AccX if hasattr(msg, 'AccX') else None,
                    'accel_y': msg.AccY if hasattr(msg, 'AccY') else None,
                    'accel_z': msg.AccZ if hasattr(msg, 'AccZ') else None,
                    'sensor_type': 'accelerometer'
                })
                return imu_info
                
            elif msg_type in ['GYR', 'GYR2', 'GYR3']:
                imu_info.update({
                    'gyro_x': msg.GyrX if hasattr(msg, 'GyrX') else None,
                    'gyro_y': msg.GyrY if hasattr(msg, 'GyrY') else None,
                    'gyro_z': msg.GyrZ if hasattr(msg, 'GyrZ') else None,
                    'sensor_type': 'gyroscope'
                })
                return imu_info
                
        except Exception as e:
            logger.warning(f"Error extracting IMU data from {msg_type}: {e}")
        
        return None
    
    def _extract_baro_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract barometer data from barometer message types"""
        try:
            return {
                'timestamp': timestamp,
                'pressure': msg.Press if hasattr(msg, 'Press') else None,
                'altitude': msg.Alt if hasattr(msg, 'Alt') else None,
                'temperature': msg.Temp if hasattr(msg, 'Temp') else None,
                'climb_rate': msg.CRt if hasattr(msg, 'CRt') else None,
                'message_type': msg_type
            }
        except Exception as e:
            logger.warning(f"Error extracting barometer data from {msg_type}: {e}")
        
        return None
    
    def _extract_mag_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract magnetometer data from magnetometer message types"""
        try:
            return {
                'timestamp': timestamp,
                'mag_x': msg.MagX if hasattr(msg, 'MagX') else None,
                'mag_y': msg.MagY if hasattr(msg, 'MagY') else None,
                'mag_z': msg.MagZ if hasattr(msg, 'MagZ') else None,
                'mag_field': msg.MagField if hasattr(msg, 'MagField') else None,
                'offsets_x': msg.OfsX if hasattr(msg, 'OfsX') else None,
                'offsets_y': msg.OfsY if hasattr(msg, 'OfsY') else None,
                'offsets_z': msg.OfsZ if hasattr(msg, 'OfsZ') else None,
                'message_type': msg_type
            }
        except Exception as e:
            logger.warning(f"Error extracting magnetometer data from {msg_type}: {e}")
        
        return None
    
    def _extract_performance_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract performance monitoring data"""
        try:
            return {
                'timestamp': timestamp,
                'loop_time': msg.LTime if hasattr(msg, 'LTime') else None,
                'main_loop_count': msg.MLC if hasattr(msg, 'MLC') else None,
                'g_dt_max': msg.gDt if hasattr(msg, 'gDt') else None,
                'g_dt_min': msg.gDtMin if hasattr(msg, 'gDtMin') else None,
                'log_dropped': msg.LogDrop if hasattr(msg, 'LogDrop') else None,
                'message_type': msg_type
            }
        except Exception as e:
            logger.warning(f"Error extracting performance data from {msg_type}: {e}")
        
        return None
    
    def _extract_vibration_data(self, msg, timestamp: float, msg_type: str) -> Optional[Dict[str, Any]]:
        """Extract vibration data from vibration message types"""
        try:
            if msg_type == 'VIBE':
                return {
                    'timestamp': timestamp,
                    'vibe_x': msg.VibeX if hasattr(msg, 'VibeX') else None,
                    'vibe_y': msg.VibeY if hasattr(msg, 'VibeY') else None,
                    'vibe_z': msg.VibeZ if hasattr(msg, 'VibeZ') else None,
                    'clipping_0': msg.Clip0 if hasattr(msg, 'Clip0') else None,
                    'clipping_1': msg.Clip1 if hasattr(msg, 'Clip1') else None,
                    'clipping_2': msg.Clip2 if hasattr(msg, 'Clip2') else None,
                    'message_type': msg_type
                }
            elif msg_type == 'VIBRATION':
                return {
                    'timestamp': timestamp,
                    'vibration_x': msg.vibration_x,
                    'vibration_y': msg.vibration_y,
                    'vibration_z': msg.vibration_z,
                    'clipping_0': msg.clipping_0,
                    'clipping_1': msg.clipping_1,
                    'clipping_2': msg.clipping_2,
                    'message_type': msg_type
                }
        except Exception as e:
            logger.warning(f"Error extracting vibration data from {msg_type}: {e}")
        
        return None
