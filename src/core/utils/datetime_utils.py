"""Datetime utilities for Academe."""

from datetime import datetime, timezone


def get_current_time() -> datetime:
    """
    Get current UTC time using modern Python API.
    
    Replaces deprecated datetime.utcnow() with timezone-aware alternative.
    
    Returns:
        Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime) -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime to format
    
    Returns:
        Formatted string (YYYY-MM-DD HH:MM:SS)
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(dt: datetime) -> str:
    """
    Format datetime as date only.
    
    Args:
        dt: Datetime to format
    
    Returns:
        Formatted string (YYYY-MM-DD)
    """
    return dt.strftime("%Y-%m-%d")


def is_expired(dt: datetime, hours: int = 24) -> bool:
    """
    Check if datetime has expired.
    
    Args:
        dt: Datetime to check
        hours: Hours until expiration
    
    Returns:
        True if expired
    """
    now = get_current_time()
    # Make dt timezone-aware if it isn't
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return (now - dt).total_seconds() > (hours * 3600)


__all__ = [
    "get_current_time",
    "format_datetime",
    "format_date",
    "is_expired"
]