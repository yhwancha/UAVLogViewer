import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

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