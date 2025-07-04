import re
from datetime import datetime, timedelta
from typing import Optional
import dateutil.parser as date_parser


def parse_datetime_string(datetime_string: str) -> Optional[datetime]:
    """
    Parse various datetime string formats into datetime objects
    """
    if not datetime_string or not datetime_string.strip():
        return None
    
    datetime_string = datetime_string.strip()
    
    # Common patterns to handle
    patterns = [
        # Direct time parsing
        parse_direct_time,
        # Date and time combinations
        parse_date_time_combo,
        # Relative dates
        parse_relative_dates,
        # Natural language
        parse_natural_language,
        # Standard formats
        parse_standard_formats
    ]
    
    for parser_func in patterns:
        try:
            result = parser_func(datetime_string)
            if result:
                return result
        except Exception as e:
            print(f"🔍 Parser {parser_func.__name__} failed: {e}")
            continue
    
    return None


def parse_direct_time(datetime_string: str) -> Optional[datetime]:
    """Parse direct time references like '9am', '2:30 PM'"""
    time_patterns = [
        r'(\d{1,2})\s*(am|pm)',  # 9am, 2pm
        r'(\d{1,2}):(\d{2})\s*(am|pm)?',  # 9:30, 2:30pm
        r'(\d{1,2})\.(\d{2})\s*(am|pm)?',  # 9.30am
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, datetime_string.lower())
        if match:
            if len(match.groups()) == 2:  # Hour and am/pm
                hour = int(match.group(1))
                period = match.group(2).lower()
                
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
                    
                # Default to today
                today = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
                return today
                
            elif len(match.groups()) >= 3:  # Hour, minute, optional am/pm
                hour = int(match.group(1))
                minute = int(match.group(2))
                period = match.group(3).lower() if match.group(3) else None
                
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
                
                today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                return today
    
    return None


def parse_date_time_combo(datetime_string: str) -> Optional[datetime]:
    """Parse date and time combinations like 'July 5th at 9am', '5/7 2pm'"""
    # Pattern: Month Day at Time
    month_day_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december|\w{3})\s+(\d{1,2})(st|nd|rd|th)?\s+at\s+(\d{1,2})\s*(am|pm)?'
    match = re.search(month_day_pattern, datetime_string.lower())
    
    if match:
        month_str = match.group(1)
        day = int(match.group(2))
        hour = int(match.group(4))
        period = match.group(5).lower() if match.group(5) else None
        
        # Convert month name to number
        month_map = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        
        month = month_map.get(month_str.lower()[:3])
        if not month:
            return None
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        # Assume current year
        year = datetime.now().year
        try:
            return datetime(year, month, day, hour, 0, 0)
        except ValueError:
            return None
    
    # Pattern: Numeric date with time (5/7 at 9am, 7-5 2pm)
    numeric_date_pattern = r'(\d{1,2})[\/\-](\d{1,2})\s+(?:at\s+)?(\d{1,2})\s*(am|pm)?'
    match = re.search(numeric_date_pattern, datetime_string.lower())
    
    if match:
        # Assume first number is day, second is month (adjust as needed)
        day = int(match.group(1))
        month = int(match.group(2))
        hour = int(match.group(3))
        period = match.group(4).lower() if match.group(4) else None
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        year = datetime.now().year
        try:
            return datetime(year, month, day, hour, 0, 0)
        except ValueError:
            # Try swapping day and month
            try:
                return datetime(year, day, month, hour, 0, 0)
            except ValueError:
                return None
    
    return None


def parse_relative_dates(datetime_string: str) -> Optional[datetime]:
    """Parse relative dates like 'tomorrow at 2pm', 'next Monday 9am'"""
    now = datetime.now()
    
    # Tomorrow
    if 'tomorrow' in datetime_string.lower():
        time_match = re.search(r'(\d{1,2})\s*(am|pm)', datetime_string.lower())
        if time_match:
            hour = int(time_match.group(1))
            period = time_match.group(2)
            
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Today
    if 'today' in datetime_string.lower():
        time_match = re.search(r'(\d{1,2})\s*(am|pm)', datetime_string.lower())
        if time_match:
            hour = int(time_match.group(1))
            period = time_match.group(2)
            
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            return now.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Days of the week
    day_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for day_name, day_num in day_map.items():
        if day_name in datetime_string.lower():
            time_match = re.search(r'(\d{1,2})\s*(am|pm)', datetime_string.lower())
            if time_match:
                hour = int(time_match.group(1))
                period = time_match.group(2)
                
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
                
                # Find next occurrence of this day
                days_ahead = day_num - now.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                target_date = now + timedelta(days=days_ahead)
                return target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    return None


def parse_natural_language(datetime_string: str) -> Optional[datetime]:
    """Parse natural language like 'in 2 hours', 'next week'"""
    now = datetime.now()
    
    # In X hours/minutes
    hours_match = re.search(r'in\s+(\d+)\s+hours?', datetime_string.lower())
    if hours_match:
        hours = int(hours_match.group(1))
        return now + timedelta(hours=hours)
    
    minutes_match = re.search(r'in\s+(\d+)\s+minutes?', datetime_string.lower())
    if minutes_match:
        minutes = int(minutes_match.group(1))
        return now + timedelta(minutes=minutes)
    
    # Morning, afternoon, evening
    if 'morning' in datetime_string.lower():
        return now.replace(hour=9, minute=0, second=0, microsecond=0)
    elif 'afternoon' in datetime_string.lower():
        return now.replace(hour=14, minute=0, second=0, microsecond=0)
    elif 'evening' in datetime_string.lower():
        return now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    return None


def parse_standard_formats(datetime_string: str) -> Optional[datetime]:
    """Parse standard datetime formats using dateutil"""
    try:
        # Use dateutil parser as fallback
        return date_parser.parse(datetime_string, fuzzy=True)
    except:
        return None


def format_datetime_for_display(dt: datetime) -> str:
    """Format datetime for user-friendly display"""
    return dt.strftime('%A, %B %d at %I:%M %p')


def format_time_for_display(dt: datetime) -> str:
    """Format time for user-friendly display"""
    return dt.strftime('%I:%M %p')


def format_date_for_display(dt: datetime) -> str:
    """Format date for user-friendly display"""
    return dt.strftime('%A, %B %d')


def is_business_hours(dt: datetime) -> bool:
    """Check if datetime falls within business hours (9 AM - 5 PM, Mon-Fri)"""
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    if dt.hour < 9 or dt.hour >= 17:
        return False
    
    return True


def get_next_business_day(dt: datetime) -> datetime:
    """Get the next business day from given datetime"""
    next_day = dt + timedelta(days=1)
    
    while next_day.weekday() >= 5:  # Skip weekends
        next_day += timedelta(days=1)
    
    return next_day.replace(hour=9, minute=0, second=0, microsecond=0)


def validate_appointment_time(dt: datetime) -> tuple[bool, str]:
    """
    Validate if the proposed appointment time is valid
    Returns (is_valid, error_message)
    """
    now = datetime.now()
    
    # Check if in the past
    if dt < now:
        return False, "Appointment time cannot be in the past."
    
    # Check if too far in future (e.g., more than 6 months)
    six_months_later = now + timedelta(days=180)
    if dt > six_months_later:
        return False, "Appointments can only be scheduled up to 6 months in advance."
    
    # Check if too soon (e.g., less than 1 hour from now)
    one_hour_later = now + timedelta(hours=1)
    if dt < one_hour_later:
        return False, "Appointments must be scheduled at least 1 hour in advance."
    
    # Check business hours
    if not is_business_hours(dt):
        return False, "Appointments can only be scheduled during business hours (9 AM - 5 PM, Monday-Friday)."
    
    return True, ""


def suggest_alternative_times(requested_time: datetime, num_suggestions: int = 3) -> list[datetime]:
    """
    Suggest alternative appointment times near the requested time
    """
    alternatives = []
    
    # Try same day, different times
    base_time = requested_time.replace(minute=0)
    for hour_offset in [-1, 1, -2, 2]:
        alt_time = base_time + timedelta(hours=hour_offset)
        if is_business_hours(alt_time) and alt_time not in alternatives:
            alternatives.append(alt_time)
            if len(alternatives) >= num_suggestions:
                break
    
    # If not enough on same day, try next business day
    if len(alternatives) < num_suggestions:
        next_day = get_next_business_day(requested_time)
        for hour in [9, 10, 14, 15]:
            alt_time = next_day.replace(hour=hour)
            if alt_time not in alternatives:
                alternatives.append(alt_time)
                if len(alternatives) >= num_suggestions:
                    break
    
    return alternatives[:num_suggestions]