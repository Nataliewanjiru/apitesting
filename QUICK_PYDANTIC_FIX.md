# 🚨 Quick Fix for Pydantic Model Error

## **The Problem:**
```
ERROR: 'PromptOutputBooking' object has no attribute 'get'
```

## **Root Cause:**
The enhanced code I provided uses `.get()` method on Pydantic model objects, but Pydantic models don't have `.get()` method - only dictionaries do.

## **Quick Fix (2 minutes):**

In your `handle_booking_intent` function, replace these lines:

### ❌ **WRONG (causing error):**
```python
doctor_name = booking_info.get("selected_doctor")
location = personal_info.get("location") 
specialization = booking_info.get("specialization", "general practitioner")
preferred_date = booking_info.get("preferred_date")
preferred_time = booking_info.get("preferred_consultation_time")
confirmed = booking_info.get("confirmed")
```

### ✅ **CORRECT (fixed):**
```python
doctor_name = booking_info.selected_doctor if booking_info else None
location = personal_info.location if personal_info else None
specialization = booking_info.specialization if booking_info else "general practitioner"
preferred_date = booking_info.preferred_date if booking_info else None
preferred_time = booking_info.preferred_consultation_time if booking_info else None
confirmed = booking_info.confirmed if booking_info else None
```

## **Complete Fixed Function:**

Replace your entire `handle_booking_intent` function with this:

```python
def handle_booking_intent(extracted_info: Dict, user, message_text: str = ""):
    """
    Enhanced booking handler with proper Pydantic model attribute access
    """
    booking_info = extracted_info.get("PromptOutputBooking")
    personal_info = extracted_info.get("PromptOutputPersonalDetails") 
    inquiry_info = extracted_info.get("PromptOutputInquiry")

    # ✅ FIXED: Access attributes directly from Pydantic models
    doctor_name = booking_info.selected_doctor if booking_info else None
    location = personal_info.location if personal_info else None
    specialization = booking_info.specialization if booking_info else "general practitioner"
    preferred_date = booking_info.preferred_date if booking_info else None
    preferred_time = booking_info.preferred_consultation_time if booking_info else None
    confirmed = booking_info.confirmed if booking_info else None

    print(f"🔍 Booking details: doctor={doctor_name}, location={location}, specialization={specialization}")
    print(f"🔍 Date/Time: {preferred_date} at {preferred_time}, confirmed={confirmed}")

    # Step 1: If no doctor selected, suggest doctors based on symptoms/specialization
    if not doctor_name and (specialization or (inquiry_info and inquiry_info.symptoms)):
        return handle_doctor_recommendation_request(specialization, location, inquiry_info)

    # Step 2: Check if user is confirming booking (improved detection)
    is_confirming = detect_booking_confirmation(message_text, extracted_info)
    
    if doctor_name and (confirmed is True or is_confirming):
        print(f"🔍 Booking confirmation detected")
        
        # Proceed with actual booking
        symptoms = ", ".join(inquiry_info.symptoms) if inquiry_info and inquiry_info.symptoms else "general check-up"
        preferred_modes = inquiry_info.preferred_modes_of_consultation if inquiry_info else []
        mode = preferred_modes[0] if preferred_modes else "clinic"

        try:
            result = ai_book_appointment(
                doctor_name=doctor_name,
                datetime_string=f"{preferred_date or ''} {preferred_time or ''}".strip(),
                mode=mode,
                patient_user=user,
                symptoms=symptoms,
                confirmed=True
            )
            return result
        except Exception as e:
            print(f"🔍 Error during booking: {e}")
            return f"Sorry, there was an issue with your booking. Please try again or contact support."

    # Step 3: If doctor selected but no confirmation, show availability
    if doctor_name and confirmed is None and not is_confirming:
        print(f"🔍 Availability query detected for {doctor_name}")
        
        try:
            availability_result = ai_book_appointment(
                doctor_name=doctor_name,
                datetime_string="",
                mode="clinic",
                patient_user=user,
                symptoms="",
                confirmed=False
            )
            
            return f"{availability_result}\n\nWould you like to book any of these times? Just let me know which one!"
                
        except Exception as e:
            print(f"🔍 Error getting availability: {e}")
            return f"Dr. {doctor_name.replace('Dr. ', '')} is typically available on weekdays between 9 AM - 5 PM. What date and time would you prefer?"

    # Step 4: Collect missing information
    if doctor_name and not preferred_time:
        return "What time would you prefer for your appointment?"
    
    if doctor_name and not preferred_date:
        return "What date would you prefer for your appointment?"

    # Default fallback - but first check if we have enough info to suggest doctors
    if not doctor_name and specialization:
        return handle_doctor_recommendation_request(specialization, location, inquiry_info)
    
    return "Could you please provide more details about your preferred appointment time and date?"


def handle_doctor_recommendation_request(specialization: str, location: str, inquiry_info):
    """
    Handle doctor recommendations - FIXED for Pydantic models
    """
    try:
        # ✅ FIXED: Access symptoms directly from Pydantic model
        symptoms = inquiry_info.symptoms if inquiry_info else []
        
        if symptoms:
            # Use symptom-based recommendation
            symptoms_text = " ".join(symptoms)
            # Your existing recommendation logic here...
            pass
        
        # Fallback to specialization-based search
        if specialization and specialization != "general practitioner":
            from apps.healthworkers.models import HealthWorker
            
            query_set = HealthWorker.objects.filter(
                primary_specialty__name__icontains=specialization,
                is_published=True
            )
            
            if location:
                query_set = query_set.filter(
                    primary_clinic_practice__county__name__icontains=location
                ).distinct()
            
            doctors = query_set[:3]
            
            if doctors:
                doctor_list = []
                for i, doctor in enumerate(doctors, 1):
                    name = f"Dr. {doctor.first_name} {doctor.last_name}"
                    specialty = doctor.primary_specialty.name if doctor.primary_specialty else 'General Practice'
                    doctor_list.append(f"{i}. {name} - {specialty}")
                
                doctors_text = "\n".join(doctor_list)
                return f"Here are available {specialization}s:\n\n{doctors_text}\n\nWhich doctor would you like to book?"
        
        return "I couldn't find specific doctors for your needs. Could you tell me more about what type of specialist you're looking for?"
        
    except Exception as e:
        print(f"🔍 Error in doctor recommendation: {e}")
        return "I'm having trouble finding doctors right now. Please try again or visit our website at www.rastuc.com"


def detect_booking_confirmation(message_text: str, extracted_info: Dict) -> bool:
    """
    Detects booking confirmation - FIXED for Pydantic models
    """
    booking_info = extracted_info.get("PromptOutputBooking")
    
    confirmation_phrases = [
        "yes", "ok", "okay", "sure", "confirm", "book", "schedule", 
        "go ahead", "proceed", "that works", "perfect", "sounds good",
        "i want", "i'll take", "book me", "confirm it"
    ]
    
    time_date_patterns = [
        r'\d{1,2}(st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|\w{3})',
        r'(january|february|march|april|may|june|july|august|september|october|november|december|\w{3})\s+\d{1,2}',
        r'\d{1,2}:\d{2}',
        r'\d{1,2}\s*(am|pm)',
        r'at\s*\d',
        r'(morning|afternoon|evening)'
    ]
    
    message_lower = message_text.lower()
    
    # Check for confirmation phrases
    for phrase in confirmation_phrases:
        if phrase in message_lower:
            return True
    
    # Check for time/date patterns indicating booking intent
    import re
    for pattern in time_date_patterns:
        if re.search(pattern, message_lower):
            return True
    
    # ✅ FIXED: Access attributes directly from Pydantic model
    if (booking_info and booking_info.selected_doctor and 
        (booking_info.preferred_date or booking_info.preferred_consultation_time)):
        return True
        
    return False
```

## **Test the Fix:**

After making this change, test again:

```
User: "I am 21 and I live in Nairobi Langata"
Expected: Should suggest cardiologists in Nairobi
```

The error should be resolved and the booking flow should work properly!

## **Why This Happened:**

Pydantic models (like `PromptOutputBooking`) are objects with attributes, not dictionaries. So:
- ✅ `booking_info.selected_doctor` (correct)
- ❌ `booking_info.get("selected_doctor")` (wrong - causes error)

This fix maintains all the enhanced functionality while properly accessing Pydantic model attributes.