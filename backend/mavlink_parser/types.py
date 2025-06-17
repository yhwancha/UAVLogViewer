"""
MAVLink Type Definitions

This module contains all MAVLink message types, vehicle types, and autopilot types
based on the MAVLink common.xml specification.
"""

# reference: https://mavlink.io/en/messages/common.html

from typing import Dict, List
from enum import IntEnum

class MAVType(IntEnum):
    """MAVLink vehicle types from MAV_TYPE enum (common.xml)"""
    GENERIC = 0
    FIXED_WING = 1
    QUADROTOR = 2
    COAXIAL = 3
    HELICOPTER = 4
    ANTENNA_TRACKER = 5
    GCS = 6
    AIRSHIP = 7
    FREE_BALLOON = 8
    ROCKET = 9
    GROUND_ROVER = 10
    SURFACE_BOAT = 11
    SUBMARINE = 12
    HEXAROTOR = 13
    OCTOROTOR = 14
    TRICOPTER = 15
    FLAPPING_WING = 16
    KITE = 17
    ONBOARD_CONTROLLER = 18
    VTOL_DUOROTOR = 19
    VTOL_QUADROTOR = 20
    VTOL_TILTROTOR = 21
    VTOL_RESERVED2 = 22
    VTOL_RESERVED3 = 23
    VTOL_RESERVED4 = 24
    VTOL_RESERVED5 = 25
    GIMBAL = 26
    ADSB = 27
    PARAFOIL = 28
    SUPERCAM = 29
    FLARM = 30
    SERVO = 31
    ODID = 32
    DECARAWAVE_UWB = 33
    BATTERY = 34
    PARACHUTE = 35
    LOG = 36
    OSD = 37
    IMU = 38
    GPS = 39
    WINCH = 40

class MAVAutopilot(IntEnum):
    """MAVLink autopilot types from MAV_AUTOPILOT enum"""
    GENERIC = 0
    RESERVED = 1
    SLUGS = 2
    ARDUPILOTMEGA = 3
    OPENPILOT = 4
    GENERIC_WAYPOINTS_ONLY = 5
    GENERIC_WAYPOINTS_AND_SIMPLE_NAVIGATION_ONLY = 6
    GENERIC_MISSION_FULL = 7
    INVALID = 8
    PPZ = 9
    UDB = 10
    FP = 11
    PX4 = 12
    SMACCMPILOT = 13
    AUTOQUAD = 14
    ARMAZILA = 15
    AEROB = 16
    ASLUAV = 17
    SMARTAP = 18
    AIRRAILS = 19
    REFLEX = 20

# MAVLink vehicle type mapping
MAV_VEHICLE_TYPES: Dict[int, str] = {
    MAVType.GENERIC: "Generic",
    MAVType.FIXED_WING: "Fixed Wing",
    MAVType.QUADROTOR: "Quadrotor",
    MAVType.COAXIAL: "Coaxial Helicopter",
    MAVType.HELICOPTER: "Helicopter",
    MAVType.ANTENNA_TRACKER: "Antenna Tracker",
    MAVType.GCS: "Ground Station",
    MAVType.AIRSHIP: "Airship",
    MAVType.FREE_BALLOON: "Free Balloon",
    MAVType.ROCKET: "Rocket",
    MAVType.GROUND_ROVER: "Ground Rover",
    MAVType.SURFACE_BOAT: "Surface Boat",
    MAVType.SUBMARINE: "Submarine",
    MAVType.HEXAROTOR: "Hexarotor",
    MAVType.OCTOROTOR: "Octorotor",
    MAVType.TRICOPTER: "Tricopter",
    MAVType.FLAPPING_WING: "Flapping Wing",
    MAVType.KITE: "Kite",
    MAVType.ONBOARD_CONTROLLER: "Onboard Controller",
    MAVType.VTOL_DUOROTOR: "VTOL Duorotor",
    MAVType.VTOL_QUADROTOR: "VTOL Quadrotor",
    MAVType.VTOL_TILTROTOR: "VTOL Tiltrotor",
    MAVType.VTOL_RESERVED2: "VTOL Reserved 2",
    MAVType.VTOL_RESERVED3: "VTOL Reserved 3",
    MAVType.VTOL_RESERVED4: "VTOL Reserved 4",
    MAVType.VTOL_RESERVED5: "VTOL Reserved 5",
    MAVType.GIMBAL: "Gimbal",
    MAVType.ADSB: "ADSB",
    MAVType.PARAFOIL: "Parafoil",
    MAVType.SUPERCAM: "Supercam",
    MAVType.FLARM: "FLARM",
    MAVType.SERVO: "Servo",
    MAVType.ODID: "ODID",
    MAVType.DECARAWAVE_UWB: "Decarawave UWB",
    MAVType.BATTERY: "Battery",
    MAVType.PARACHUTE: "Parachute",
    MAVType.LOG: "Log",
    MAVType.OSD: "OSD",
    MAVType.IMU: "IMU",
    MAVType.GPS: "GPS",
    MAVType.WINCH: "Winch"
}

# MAVLink autopilot type mapping
MAV_AUTOPILOT_TYPES: Dict[int, str] = {
    MAVAutopilot.GENERIC: "Generic",
    MAVAutopilot.RESERVED: "Reserved",
    MAVAutopilot.SLUGS: "SLUGS",
    MAVAutopilot.ARDUPILOTMEGA: "ArduPilot",
    MAVAutopilot.OPENPILOT: "OpenPilot",
    MAVAutopilot.GENERIC_WAYPOINTS_ONLY: "Generic Waypoints Only",
    MAVAutopilot.GENERIC_WAYPOINTS_AND_SIMPLE_NAVIGATION_ONLY: "Generic Waypoints and Simple Navigation",
    MAVAutopilot.GENERIC_MISSION_FULL: "Generic Mission Full",
    MAVAutopilot.INVALID: "Invalid",
    MAVAutopilot.PPZ: "PPZ",
    MAVAutopilot.UDB: "UDB",
    MAVAutopilot.FP: "FlexiPilot",
    MAVAutopilot.PX4: "PX4",
    MAVAutopilot.SMACCMPILOT: "SMACCMPilot",
    MAVAutopilot.AUTOQUAD: "AutoQuad",
    MAVAutopilot.ARMAZILA: "ARMAZILA",
    MAVAutopilot.AEROB: "Aerob",
    MAVAutopilot.ASLUAV: "ASLUAV",
    MAVAutopilot.SMARTAP: "SmartAP",
    MAVAutopilot.AIRRAILS: "AirRails",
    MAVAutopilot.REFLEX: "RefleX"
}

# Expanded message types based on MAVLink common.xml specification
SUPPORTED_MESSAGE_TYPES: List[str] = [
    # Core telemetry messages
    'HEARTBEAT', 'SYS_STATUS', 'SYSTEM_TIME', 'GPS_RAW_INT', 'GPS2_RAW',
    'SCALED_PRESSURE', 'ATTITUDE', 'ATTITUDE_QUATERNION', 'LOCAL_POSITION_NED',
    'GLOBAL_POSITION_INT', 'RC_CHANNELS_RAW', 'RC_CHANNELS', 'SERVO_OUTPUT_RAW',
    'MISSION_CURRENT', 'NAV_CONTROLLER_OUTPUT', 'VFR_HUD', 'COMMAND_ACK',
    'COMMAND_LONG', 'COMMAND_INT', 'BATTERY_STATUS', 'AUTOPILOT_VERSION',
    'LANDING_TARGET', 'FENCE_STATUS', 'MAG_CAL_PROGRESS', 'EKF_STATUS_REPORT',
    'PID_TUNING', 'DEEPSTALL', 'GIMBAL_REPORT', 'GIMBAL_CONTROL',
    'MOUNT_STATUS', 'FENCE_POINT', 'FENCE_FETCH_POINT', 'FENCE_STATUS',
    'AHRS', 'SIMSTATE', 'HWSTATUS', 'RADIO', 'LIMITS_STATUS', 'WIND',
    'DATA16', 'DATA32', 'DATA64', 'DATA96', 'RANGEFINDER', 'AIRSPEED_AUTOCAL',
    'RALLY_POINT', 'RALLY_FETCH_POINT', 'COMPASSMOT_STATUS', 'AHRS2', 'CAMERA_STATUS',
    'CAMERA_FEEDBACK', 'BATTERY2', 'AHRS3', 'AUTOPILOT_VERSION_REQUEST',
    'REMOTE_LOG_DATA_BLOCK', 'REMOTE_LOG_BLOCK_STATUS', 'LED_CONTROL', 'MAG_CAL_PROGRESS',
    'MAG_CAL_REPORT', 'EKF_STATUS_REPORT', 'PID_TUNING', 'DEEPSTALL', 'GIMBAL_REPORT',
    'GIMBAL_CONTROL', 'GIMBAL_TORQUE_CMD_REPORT', 'GOPRO_HEARTBEAT', 'GOPRO_GET_REQUEST',
    'GOPRO_GET_RESPONSE', 'GOPRO_SET_REQUEST', 'GOPRO_SET_RESPONSE', 'RPM', 'ESTIMATOR_STATUS',
    'WIND_COV', 'GPS_INPUT', 'GPS_RTCM_DATA', 'HIGH_LATENCY', 'HIGH_LATENCY2', 'VIBRATION',
    'HOME_POSITION', 'SET_HOME_POSITION', 'MESSAGE_INTERVAL', 'EXTENDED_SYS_STATE',
    'ADSB_VEHICLE', 'COLLISION', 'V2_EXTENSION', 'MEMORY_VECT', 'DEBUG_VECT', 'NAMED_VALUE_FLOAT',
    'NAMED_VALUE_INT', 'STATUSTEXT', 'DEBUG', 'SETUP_SIGNING', 'BUTTON_CHANGE', 'PLAY_TUNE',
    'CAMERA_INFORMATION', 'CAMERA_SETTINGS', 'STORAGE_INFORMATION', 'CAMERA_CAPTURE_STATUS',
    'CAMERA_IMAGE_CAPTURED', 'FLIGHT_INFORMATION', 'MOUNT_ORIENTATION', 'LOGGING_DATA',
    'LOGGING_DATA_ACKED', 'LOGGING_ACK', 'VIDEO_STREAM_INFORMATION', 'VIDEO_STREAM_STATUS',
    'CAMERA_FOV_STATUS', 'CAMERA_TRACKING_IMAGE_STATUS', 'CAMERA_TRACKING_GEO_STATUS',
    'GIMBAL_MANAGER_INFORMATION', 'GIMBAL_MANAGER_STATUS', 'GIMBAL_MANAGER_SET_ATTITUDE',
    'GIMBAL_DEVICE_INFORMATION', 'GIMBAL_DEVICE_SET_ATTITUDE', 'GIMBAL_DEVICE_ATTITUDE_STATUS',
    'AUTOPILOT_STATE_FOR_GIMBAL_DEVICE', 'GIMBAL_MANAGER_SET_PITCHYAW', 'GIMBAL_MANAGER_SET_MANUAL_CONTROL',
    'ESC_INFO', 'ESC_STATUS', 'WIFI_CONFIG_AP', 'PROTOCOL_VERSION', 'AIS_VESSEL', 'UAVCAN_NODE_STATUS',
    'UAVCAN_NODE_INFO', 'PARAM_EXT_REQUEST_READ', 'PARAM_EXT_REQUEST_LIST', 'PARAM_EXT_VALUE',
    'PARAM_EXT_SET', 'PARAM_EXT_ACK', 'OBSTACLE_DISTANCE', 'ODOMETRY', 'TRAJECTORY_REPRESENTATION_WAYPOINTS',
    'TRAJECTORY_REPRESENTATION_BEZIER', 'CELLULAR_STATUS', 'ISBD_LINK_STATUS', 'CELLULAR_CONFIG',
    'RAW_RPM', 'UTM_GLOBAL_POSITION', 'DEBUG_FLOAT_ARRAY', 'ORBIT_EXECUTION_STATUS', 'BATTERY_INFO',
    'GENERATOR_STATUS', 'ACTUATOR_OUTPUT_STATUS', 'TIME_ESTIMATE_TO_TARGET', 'TUNNEL', 'CAN_FRAME',
    'CANFD_FRAME', 'CAN_FILTER_MODIFY', 'ONBOARD_COMPUTER_STATUS', 'COMPONENT_INFORMATION',
    'COMPONENT_METADATA', 'PLAY_TUNE_V2', 'SUPPORTED_TUNES', 'EVENT', 'CURRENT_EVENT_SEQUENCE',
    'REQUEST_EVENT', 'RESPONSE_EVENT_ERROR', 'WHEEL_DISTANCE', 'WINCH_STATUS',
    
    # ArduPilot specific DataFlash message types (Current)
    'GPS', 'ATT', 'CTUN', 'BAT', 'IMU', 'MAG', 'BARO', 
    'RCIN', 'RCOU', 'MODE', 'MSG', 'ERR', 'CMD', 'POS', 'AHR2',
    'PARM', 'STAT', 'EV', 'ORGN', 'RPM', 'GPA', 'GYR', 'ACC',
    'RATE', 'QTUN', 'MOTB', 'RCOU', 'RFND', 'TERR', 'UBX1', 'UBX2',
    'ESC', 'AIRSPEED', 'POWR', 'MCU', 'SRTL', 'WENC', 'ISBH', 'ISBD',
    
    # Legacy ArduPilot DataFlash message types (for older logs)
    'XKFS', 'XKQ', 'XKV1', 'XKV2', 'XKT', 'XKFM',  # Extended Kalman Filter messages
    'IOMC',  # IO MCU messages
    'MAVC',  # MAVLink messages
    'TSYN',  # Time synchronization
    'PM',    # Performance monitoring
    'RAD',   # Radio messages
    'PIDN', 'PIDE',  # PID tuning messages
    'AUXF',  # Auxiliary functions
    'NKF1', 'NKF2', 'NKF3', 'NKF4', 'NKF5',  # Navigation Kalman Filter
    'NKQ',   # Navigation Kalman Filter quaternion
    'NKT',   # Navigation Kalman Filter timing
    'XKF0', 'XKF1', 'XKF2', 'XKF3', 'XKF4',  # Extended Kalman Filter variants
    'XKFD',  # Extended Kalman Filter divergence
    'XKY0', 'XKY1', 'XKY2',  # Extended Kalman Filter innovation
    'NTUN',  # Navigation tuning
    'PSCD',  # Position control desired
    'PSCN',  # Position control north
    'PSCE',  # Position control east
    'PSCU',  # Position control up
    'TECS',  # Total Energy Control System
    'STRT',  # Startup messages
    'DFLT',  # Default parameters
    'FMTU',  # Format units
    'MULT',  # Multipliers
    'UNIT',  # Units
    'UBX1', 'UBX2',  # uBlox GPS messages
    'GRAW',  # GPS raw data
    'GRXH',  # GPS receive header
    'GRXS',  # GPS receive status
    'D16', 'D32',  # Generic data messages
    'DU16', 'DU32',  # Generic unsigned data messages
    'OF',    # Optical flow
    'FLOW',  # Optical flow
    'ARSP',  # Airspeed
    'CURR',  # Current sensor
    'MOTB',  # Motor/Battery
    'RCOU',  # RC output
    'RCIN',  # RC input
    'IMT',   # IMU temperature
    'IMT2',  # IMU temperature 2
    'IMT3',  # IMU temperature 3
    'VIBE',  # Vibration
    'IMUDT', 'IMUD2', 'IMUD3',  # IMU delta time
    'BAR2', 'BAR3',  # Barometer 2, 3
    'ALT2',  # Altitude 2
    'ASPD2', # Airspeed 2
    'KF1',   # Kalman Filter 1
    'GPS2',  # GPS 2
    'IMU2', 'IMU3',  # IMU 2, 3
    'AHR3',  # AHRS 3
    'MAG2', 'MAG3',  # Magnetometer 2, 3
    'ACC2', 'ACC3',  # Accelerometer 2, 3
    'GYR2', 'GYR3',  # Gyroscope 2, 3
    'EKF1', 'EKF2', 'EKF3', 'EKF4', 'EKF5',  # Extended Kalman Filter
    'RFRH', 'RFRN',  # Rangefinder
    'SBPH', 'SBPN',  # Swift Binary Protocol
    'RFND',  # Rangefinder
    'RNGF',  # Rangefinder
    'PROX',  # Proximity sensor
    'PRX',   # Proximity
    'BCN',   # Beacon
    'BEACON', # Beacon
    'ORGN',  # Origin
    'RPM1', 'RPM2',  # RPM sensors
    'WENC',  # Wheel encoder
    'ADSB',  # ADS-B
    'ARM',   # Arming
    'DISARM', # Disarming
    'LAND',  # Landing
    'TKOF',  # Takeoff
    'GUIDED', # Guided mode
    'AUTO',  # Auto mode
    'RALLY', # Rally point
    'FENCE', # Geofence
    'AVOID', # Avoidance
    'SIMSTATE', # Simulation state
    'WHEELENCODER', # Wheel encoder
    'ADSB_VEHICLE', # ADS-B vehicle
]

# Flight mode mappings for different vehicle types
MULTICOPTER_MODES = [
    'STABILIZE', 'ACRO', 'ALT_HOLD', 'LOITER', 'AUTO', 'LAND', 'RTL', 
    'DRIFT', 'SPORT', 'FLIP', 'AUTOTUNE', 'POSHOLD', 'BRAKE', 'THROW', 
    'AVOID_ADSB', 'GUIDED_NOGPS', 'SMART_RTL', 'FLOWHOLD', 'FOLLOW', 
    'ZIGZAG', 'SYSTEMID', 'AUTOROTATE', 'AUTO_RTL'
]

FIXED_WING_MODES = [
    'MANUAL', 'CIRCLE', 'STABILIZE', 'TRAINING', 'ACRO', 'FLY_BY_WIRE_A', 
    'FLY_BY_WIRE_B', 'CRUISE', 'AUTOTUNE', 'AUTO', 'RTL', 'LOITER', 
    'TAKEOFF', 'AVOID_ADSB', 'GUIDED', 'INITIALISING', 'QSTABILIZE', 
    'QHOVER', 'QLOITER', 'QLAND', 'QRTL', 'QAUTOTUNE', 'QACRO', 'THERMAL'
]

ROVER_MODES = [
    'MANUAL', 'ACRO', 'LEARNING', 'STEERING', 'HOLD', 'LOITER', 
    'FOLLOW', 'SIMPLE', 'AUTO', 'RTL', 'SMART_RTL', 'GUIDED', 'INITIALISING'
]

HELICOPTER_MODES = [
    'STABILIZE', 'ACRO', 'ALT_HOLD', 'AUTO', 'GUIDED', 'LOITER', 
    'RTL', 'CIRCLE', 'LAND', 'DRIFT', 'SPORT', 'FLIP', 'AUTOTUNE', 
    'POSHOLD', 'BRAKE', 'THROW', 'AVOID_ADSB', 'GUIDED_NOGPS', 
    'SMART_RTL', 'FLOWHOLD', 'FOLLOW', 'ZIGZAG', 'SYSTEMID', 
    'AUTOROTATE', 'AUTO_RTL'
]

# Message severity levels
class MessageSeverity(IntEnum):
    """MAVLink message severity levels"""
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7

SEVERITY_KEYWORDS = {
    MessageSeverity.CRITICAL: ['emergency', 'critical', 'fatal', 'crash', 'failsafe'],
    MessageSeverity.ERROR: ['error', 'fail', 'failed', 'timeout'],
    MessageSeverity.WARNING: ['warning', 'warn', 'caution'],
    MessageSeverity.NOTICE: ['notice', 'armed', 'disarmed', 'mode']
} 