"""
Centralized timezone utility functions.
This module provides common timezone functions used across the application.
"""
from datetime import datetime
import pytz

# Centralized timezone configuration
LOCAL_TIMEZONE = pytz.timezone('Asia/Kolkata')

def get_local_datetime():
    """Get current local datetime"""
    utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    local_now = utc_now.astimezone(LOCAL_TIMEZONE)
    return local_now

def get_local_date():
    """Get current local date"""
    return get_local_datetime().date()

def get_local_now():
    """Alias for get_local_datetime for template context"""
    return get_local_datetime()

