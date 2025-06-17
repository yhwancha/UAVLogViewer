"""
MAVLink Parser Package

This package provides functionality for parsing MAVLink telemetry and dataflash logs
with comprehensive support for ArduPilot and PX4 flight logs.
"""

from .parser import MAVLinkParser
from .types import (
    MAVType,
    MAVAutopilot,
    MessageSeverity,
    MAV_VEHICLE_TYPES,
    MAV_AUTOPILOT_TYPES,
    SUPPORTED_MESSAGE_TYPES
)

__version__ = "1.0.0"
__author__ = "UAVLogViewer Team"

__all__ = [
    "MAVLinkParser",
    "MAVType", 
    "MAVAutopilot",
    "MessageSeverity",
    "MAV_VEHICLE_TYPES",
    "MAV_AUTOPILOT_TYPES", 
    "SUPPORTED_MESSAGE_TYPES"
] 