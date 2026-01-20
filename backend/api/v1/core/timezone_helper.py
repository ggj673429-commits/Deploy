"""
Timezone Helper for Client Device Timezone Support
Reads X-Client-Timezone and X-Client-TZ-Offset headers from requests
and provides date range calculations in client's local timezone
"""
from datetime import datetime, timedelta, timezone as tz
from typing import Tuple, Optional, List
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

# Try to import zoneinfo (Python 3.9+), fallback to pytz
try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False
    try:
        import pytz
        HAS_PYTZ = True
    except ImportError:
        HAS_PYTZ = False


def get_client_timezone(request: Request) -> Optional[str]:
    """
    Extract client timezone from request headers.
    Returns IANA timezone string (e.g., 'America/New_York') or None.
    """
    tz_header = request.headers.get('X-Client-Timezone')
    if tz_header:
        return tz_header
    return None


def get_client_tz_offset(request: Request) -> Optional[int]:
    """
    Extract client timezone offset from request headers.
    Returns offset in minutes (note: JavaScript's getTimezoneOffset() 
    returns positive values for west of UTC, negative for east).
    """
    offset_header = request.headers.get('X-Client-TZ-Offset')
    if offset_header:
        try:
            return int(offset_header)
        except (ValueError, TypeError):
            pass
    return None


def get_timezone_obj(tz_name: str):
    """
    Get a timezone object from IANA timezone name.
    Returns None if timezone is invalid or libraries unavailable.
    """
    if not tz_name:
        return None
    
    if HAS_ZONEINFO:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            logger.warning(f"Invalid timezone: {tz_name}")
            return None
    elif HAS_PYTZ:
        try:
            return pytz.timezone(tz_name)
        except Exception:
            logger.warning(f"Invalid timezone: {tz_name}")
            return None
    
    return None


def get_client_today_range(request: Request) -> Tuple[datetime, datetime]:
    """
    Calculate the start and end of "today" in the client's timezone,
    converted to UTC for database queries.
    
    Returns (start_of_today_utc, end_of_today_utc)
    """
    now_utc = datetime.now(tz.utc)
    
    client_tz_name = get_client_timezone(request)
    client_offset = get_client_tz_offset(request)
    
    # Try to use IANA timezone first
    if client_tz_name:
        tz_obj = get_timezone_obj(client_tz_name)
        if tz_obj:
            # Get current time in client's timezone
            if HAS_ZONEINFO:
                client_now = now_utc.astimezone(tz_obj)
            else:  # pytz
                client_now = now_utc.astimezone(tz_obj)
            
            # Get start of day in client's timezone
            start_of_day_client = client_now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day_client = client_now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Convert back to UTC
            start_utc = start_of_day_client.astimezone(tz.utc)
            end_utc = end_of_day_client.astimezone(tz.utc)
            
            return (start_utc, end_utc)
    
    # Fallback to offset-based calculation
    if client_offset is not None:
        # JavaScript offset is in minutes, positive for west of UTC
        # Convert to timedelta (reverse the sign)
        offset_delta = timedelta(minutes=-client_offset)
        
        # Calculate client's current local time
        client_now = now_utc + offset_delta
        
        # Get start and end of day in client's local time (as UTC-equivalent)
        start_of_day = datetime(
            client_now.year, client_now.month, client_now.day,
            0, 0, 0, tzinfo=tz.utc
        )
        end_of_day = datetime(
            client_now.year, client_now.month, client_now.day,
            23, 59, 59, 999999, tzinfo=tz.utc
        )
        
        # Convert back to actual UTC
        start_utc = start_of_day - offset_delta
        end_utc = end_of_day - offset_delta
        
        return (start_utc, end_utc)
    
    # Fallback to UTC
    start_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    end_utc = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return (start_utc, end_utc)


def get_last_n_days_ranges(
    request: Request, 
    days: int = 30
) -> List[Tuple[datetime, datetime, str]]:
    """
    Calculate date ranges for the last N days in client's timezone.
    Returns list of (start_utc, end_utc, date_label) tuples.
    
    Each tuple represents one day's boundaries converted to UTC.
    date_label is the date string in client's local timezone (YYYY-MM-DD).
    """
    ranges = []
    now_utc = datetime.now(tz.utc)
    
    client_tz_name = get_client_timezone(request)
    client_offset = get_client_tz_offset(request)
    
    tz_obj = None
    offset_delta = None
    
    if client_tz_name:
        tz_obj = get_timezone_obj(client_tz_name)
    
    if not tz_obj and client_offset is not None:
        offset_delta = timedelta(minutes=-client_offset)
    
    for i in range(days):
        if tz_obj:
            # Using IANA timezone
            if HAS_ZONEINFO:
                client_now = now_utc.astimezone(tz_obj)
            else:
                client_now = now_utc.astimezone(tz_obj)
            
            target_day = client_now - timedelta(days=i)
            start_of_day = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_day.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            start_utc = start_of_day.astimezone(tz.utc)
            end_utc = end_of_day.astimezone(tz.utc)
            date_label = start_of_day.strftime('%Y-%m-%d')
            
        elif offset_delta is not None:
            # Using offset
            client_now = now_utc + offset_delta
            target_day = client_now - timedelta(days=i)
            
            start_of_day = datetime(
                target_day.year, target_day.month, target_day.day,
                0, 0, 0, tzinfo=tz.utc
            )
            end_of_day = datetime(
                target_day.year, target_day.month, target_day.day,
                23, 59, 59, 999999, tzinfo=tz.utc
            )
            
            start_utc = start_of_day - offset_delta
            end_utc = end_of_day - offset_delta
            date_label = target_day.strftime('%Y-%m-%d')
            
        else:
            # Fallback to UTC
            target_day = now_utc - timedelta(days=i)
            start_utc = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_utc = target_day.replace(hour=23, minute=59, second=59, microsecond=999999)
            date_label = start_utc.strftime('%Y-%m-%d')
        
        ranges.append((start_utc, end_utc, date_label))
    
    # Return in chronological order (oldest first)
    return list(reversed(ranges))


def get_rolling_window(request: Request, days: int = 7) -> Tuple[datetime, datetime]:
    """
    Get a rolling window from now minus N days to now.
    Useful for "active in last 7 days" queries.
    
    Returns (start_utc, end_utc)
    """
    now_utc = datetime.now(tz.utc)
    start_utc = now_utc - timedelta(days=days)
    return (start_utc, now_utc)


def get_last_24h_range() -> Tuple[datetime, datetime]:
    """
    Get the last 24 hours range in UTC.
    Used for risk metrics that don't depend on client timezone.
    
    Returns (start_utc, end_utc)
    """
    now_utc = datetime.now(tz.utc)
    start_utc = now_utc - timedelta(hours=24)
    return (start_utc, now_utc)
