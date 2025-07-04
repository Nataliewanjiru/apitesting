# AI Appointment Booking Code Issues Analysis

## Problem Summary

Based on your conversation logs and code, the appointment booking system has several critical issues preventing successful bookings:

1. **Incomplete Return Statements** - Multiple functions have truncated strings
2. **DateTime Parsing Failures** - Parser failing with "hour must be in 0..23" error
3. **Availability Logic Inconsistencies** - System offers times then says they're unavailable
4. **Missing Actual Booking Creation** - Confirmations don't create real appointments

## Specific Issues Found

### 1. Incomplete Return Statements

**Problem**: Several return statements are cut off mid-sentence:

```python
# In ai_book_appointment function (line ~25)
return "I couldn't understand the date and time. Could you please specify it more clearly? For example: 'July 5th at 9am' or
# INCOMPLETE - missing closing quote and rest of message

# In handle_doctor_not_found function
return f"I couldn't find Dr. {doctor_name}. Based on your symptoms, here are some available doctors:\n\n{doctors_tex
# INCOMPLETE - missing 't' in doctors_text and closing quote

# In handle_doctor_not_found function  
return f"I couldn't find Dr. {doctor_name}. Please check the spelling or browse available doctors on our website at www.rastuc.com. 
# INCOMPLETE - missing closing quote

# In get_doctor_availability function
return f"Dr. {doctor.first_name} {doctor.last_name} is available on:\n\n{availability_text}\n\nWhich time works for you?
# INCOMPLETE - missing closing quote

# In get_sample_availability function
return f"Dr. {doctor.first_name} {doctor.last_name} typically has availability on weekdays between 9 AM - 5 PM. What date and ti
# INCOMPLETE - truncated mid-sentence

# In handle_unavailable_time_slot function
return f"Dr. {doctor.first_name} {doctor.last_name} is not available at {requested_time.strftime('%I:%M %p')} on {date_str}.
# INCOMPLETE - missing closing quote

# Multiple other incomplete statements...
```

### 2. DateTime Parsing Issues

**Problem**: The error log shows:
```
🔍 Parser parse_direct_time failed: hour must be in 0..23
```

**Analysis**: The `parse_datetime_string` function is failing to handle time formats like "9:30am" or "2pm" correctly.

### 3. Availability Logic Problems

**Problem**: The conversation shows:
- System says "Dr. Natalie Wanjiru is available on July 20th at 2pm and July 22nd at 10am"
- User selects "July 20th 2pm" 
- System then says "Dr. Natalie Wanjiru is not available at 02:00 PM on July 04"

**Issues**:
- Wrong date being checked (July 04 instead of July 20)
- Inconsistent availability data
- Offering times that aren't actually available

### 4. Missing Actual Booking Logic

**Problem**: The `create_confirmed_appointment` function may not be properly creating appointments in the database.

## Fixes Required

### Fix 1: Complete All Return Statements

```python
# Fix ai_book_appointment function
return "I couldn't understand the date and time. Could you please specify it more clearly? For example: 'July 5th at 9am' or 'tomorrow at 2pm'"

# Fix handle_doctor_not_found function
return f"I couldn't find Dr. {doctor_name}. Based on your symptoms, here are some available doctors:\n\n{doctors_text}\n\nWhich doctor would you like to book with?"

# Fix get_doctor_availability function  
return f"Dr. {doctor.first_name} {doctor.last_name} is available on:\n\n{availability_text}\n\nWhich time works for you?"

# Fix get_sample_availability function
return f"Dr. {doctor.first_name} {doctor.last_name} typically has availability on weekdays between 9 AM - 5 PM. What date and time would you prefer?"

# Complete all other truncated return statements...
```

### Fix 2: Improve DateTime Parsing

```python
def parse_datetime_string(datetime_string: str):
    """Enhanced datetime parsing with better error handling"""
    import re
    from datetime import datetime, timedelta
    
    try:
        # Clean the input
        clean_input = datetime_string.strip().lower()
        
        # Handle common patterns
        patterns = [
            # "July 20th 2pm" or "July 20th at 2pm"
            (r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)', 
             lambda m: parse_month_day_time(m.group(1), m.group(2), m.group(3), m.group(4) or '00', m.group(5))),
            
            # "9:30am" or "2pm"
            (r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)',
             lambda m: parse_time_today(m.group(1), m.group(2) or '00', m.group(3))),
        ]
        
        for pattern, parser in patterns:
            match = re.search(pattern, clean_input)
            if match:
                return parser(match)
                
        return None
        
    except Exception as e:
        print(f"🔍 DateTime parsing error: {e}")
        return None

def parse_month_day_time(month_str, day_str, hour_str, minute_str, ampm):
    """Parse month/day/time combination"""
    from datetime import datetime
    import calendar
    
    # Convert month name to number
    month_names = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
        'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
    }
    
    month = month_names.get(month_str.lower())
    if not month:
        return None
    
    day = int(day_str)
    hour = int(hour_str)
    minute = int(minute_str)
    
    # Convert 12-hour to 24-hour
    if ampm.lower() == 'pm' and hour != 12:
        hour += 12
    elif ampm.lower() == 'am' and hour == 12:
        hour = 0
    
    # Determine year (current year or next year)
    current_year = datetime.now().year
    try:
        appointment_date = datetime(current_year, month, day, hour, minute)
        if appointment_date < datetime.now():
            appointment_date = datetime(current_year + 1, month, day, hour, minute)
        return appointment_date
    except ValueError:
        return None

def parse_time_today(hour_str, minute_str, ampm):
    """Parse time for today"""
    from datetime import datetime, timedelta
    
    hour = int(hour_str)
    minute = int(minute_str)
    
    # Convert 12-hour to 24-hour
    if ampm.lower() == 'pm' and hour != 12:
        hour += 12
    elif ampm.lower() == 'am' and hour == 12:
        hour = 0
    
    today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    if today < datetime.now():
        today += timedelta(days=1)
    
    return today
```

### Fix 3: Fix Availability Logic

```python
def handle_unavailable_time_slot(doctor, requested_time, mode):
    """Handle cases where the requested time slot is not available"""
    try:
        print(f"🔍 Finding alternatives for {requested_time}")
        
        # Ensure we're using the correct date
        target_date = requested_time.date()
        
        # Get alternative times for the SAME DATE
        day_start = requested_time.replace(hour=9, minute=0, second=0, microsecond=0)
        day_end = requested_time.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Check for conflicts on the correct date
        conflicting_appointments = Appointment.objects.filter(
            doctor=doctor,
            start_time__date=target_date,  # Use target_date, not requested_time.date()
            status__in=[
                CORE_CHOICES.AppointmentStatuses.PENDING.value,
                CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
            ]
        ).values_list('start_time', 'end_time')
        
        # Generate alternative slots
        alternative_slots = []
        current_time = day_start
        
        while current_time < day_end and len(alternative_slots) < 3:
            slot_end = current_time + timedelta(minutes=30)
            
            # Check if this slot conflicts with existing appointments
            is_available = True
            for conflict_start, conflict_end in conflicting_appointments:
                if (current_time < conflict_end and slot_end > conflict_start):
                    is_available = False
                    break
            
            if is_available and current_time != requested_time:
                time_str = current_time.strftime("%I:%M %p")
                alternative_slots.append(time_str)
            
            current_time += timedelta(minutes=30)
        
        if alternative_slots:
            date_str = requested_time.strftime("%B %d")
            alternatives_text = ", ".join(alternative_slots)
            return f"Dr. {doctor.first_name} {doctor.last_name} is not available at {requested_time.strftime('%I:%M %p')} on {date_str}. However, they are available at: {alternatives_text}. Which time works for you?"
        
        # If no alternatives on same day, suggest next available day
        return f"Dr. {doctor.first_name} {doctor.last_name} is not available at that time. Let me check their next available slots for you."
        
    except Exception as e:
        print(f"🔍 Error finding alternatives: {e}")
        return f"Dr. {doctor.first_name} {doctor.last_name} is not available at that time. Please choose a different time or let me show you their available slots."
```

### Fix 4: Enhance Booking Confirmation

```python
def create_confirmed_appointment(doctor, patient_user, appointment_start, appointment_end, mode, symptoms, organization, availability_record):
    """Create and confirm an appointment with better error handling"""
    try:
        print(f"🔍 Creating confirmed appointment for {appointment_start}")
        
        # Validate inputs
        if not doctor:
            raise ValueError("Doctor not found")
        if not appointment_start:
            raise ValueError("Invalid appointment time")
        
        # Get cost information
        total_cost, breakdown = get_health_worker_appointment_cost(
            doctor=doctor,
            encounter_mode=mode,
            organization=organization,
        )
        
        # Get patient object
        patient = patient_user.patient_profile if hasattr(patient_user, 'patient_profile') else patient_user
        
        # Double-check availability before creating
        available, availability_record = check_health_worker_availability(
            worker=doctor,
            start_time=appointment_start,
            end_time=appointment_end,
            mode=mode,
            organization=organization,
        )
        
        if not available:
            return f"Sorry, Dr. {doctor.first_name} {doctor.last_name} is no longer available at that time. Please choose a different slot."
        
        # Create appointment
        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            start_time=appointment_start,
            end_time=appointment_end,
            encounter_mode=mode,
            status=CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value,
            symptoms=symptoms,
            created_by_patient=True,
            cost=total_cost,
            booking_fee=50,  # Standard booking fee
            health_worker_availability=availability_record,
            organization=organization
        )
        
        print(f"🔍 Appointment created with ID: {appointment.id}")
        
        # Send notifications
        send_appointment_creation_notifications(
            appointment=appointment,
            payment_completed=False,
        )
        
        # Success response
        appointment_time = appointment_start.strftime('%A, %B %d at %I:%M %p')
        return (f"✅ Appointment confirmed!\n\n"
                f"Doctor: Dr. {doctor.first_name} {doctor.last_name}\n"
                f"Date & Time: {appointment_time}\n"
                f"Type: {mode.title()} consultation\n"
                f"Total Cost: KES {total_cost}\n\n"
                f"You'll receive a confirmation via SMS and email. Payment can be made through the app or at the clinic.")
        
    except Exception as e:
        print(f"🔍 Error creating appointment: {e}")
        return "Sorry, there was an error confirming your appointment. Please try again or contact support."
```

## Root Cause Analysis

The main issue causing the "cardiologist appointment not booked" error is:

1. **Incomplete string returns** cause functions to crash silently
2. **DateTime parsing failures** prevent proper time interpretation  
3. **Availability checking on wrong dates** leads to false unavailability
4. **Confirmation flow not reaching actual booking creation**

## Recommended Action Plan

1. **Immediate Fix**: Complete all truncated return statements
2. **DateTime Enhancement**: Implement robust datetime parsing
3. **Availability Logic**: Fix date handling in availability checks
4. **Testing**: Add comprehensive logging to track booking flow
5. **Validation**: Add input validation at each step

## Testing Strategy

Add debug logging to track the complete booking flow:

```python
def debug_booking_flow(step, data):
    """Add comprehensive debugging"""
    print(f"🔍 BOOKING_FLOW_STEP: {step}")
    print(f"🔍 DATA: {data}")
    # Log to file or database for analysis
```

This analysis should help you identify and fix the core issues preventing successful appointment bookings.