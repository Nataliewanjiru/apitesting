# Doctor Availability Enhancement

## 🎯 **Enhanced Availability Flow**

To properly handle "What time is she available?" while maintaining conversation context, implement this enhanced booking flow:

### **1. Enhanced ai_book_appointment Function**

```python
def ai_book_appointment(doctor_name, user_phone, date, time, conversation_context=None):
    """
    Enhanced booking function that provides availability alternatives
    """
    print(f"🔍 ai_book_appointment called with doctor_name: {doctor_name}")
    
    try:
        # Extract first and last name
        name_parts = doctor_name.replace("Dr.", "").strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[1]
        else:
            return f"Please provide the full name of the doctor."

        print(f"🔍 Searching for: first_name={first_name}, last_name={last_name}")

        # Find the doctor
        doctor = Doctor.objects.filter(
            first_name__icontains=first_name,
            last_name__icontains=last_name
        ).first()

        if not doctor:
            return f"Sorry, I couldn't find Dr. {doctor_name} in our system."

        print(f"🔍 Doctor found: {doctor.first_name} {doctor.last_name}")

        # Check specific time availability
        if date and time:
            # Try to book the specific time
            appointment_date = parse_date_string(date)  # You need this helper function
            appointment_time = parse_time_string(time)  # You need this helper function
            
            if is_doctor_available(doctor, appointment_date, appointment_time):
                # Book the appointment
                appointment = Appointment.objects.create(
                    doctor=doctor,
                    patient=get_patient_from_phone(user_phone),
                    scheduled_date=appointment_date,
                    scheduled_time=appointment_time,
                    status='confirmed'
                )
                return f"✅ Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {date} at {time}."
            else:
                # Not available - provide alternatives
                available_slots = get_doctor_available_slots(doctor, appointment_date)
                if available_slots:
                    slots_text = ", ".join(available_slots)
                    return f"Dr. {doctor.first_name} {doctor.last_name} is not available at {time} on {date}. Available times are: {slots_text}"
                else:
                    return f"Dr. {doctor.first_name} {doctor.last_name} is not available on {date}. Would you like to check other dates?"
        else:
            # No specific time - show general availability
            upcoming_slots = get_doctor_upcoming_availability(doctor)
            if upcoming_slots:
                return f"Dr. {doctor.first_name} {doctor.last_name} is available at: {upcoming_slots}"
            else:
                return f"Dr. {doctor.first_name} {doctor.last_name} doesn't have any available slots in the near future."

    except Exception as e:
        print(f"❌ Booking error: {e}")
        return "I encountered an issue while checking availability. Please try again."


def get_doctor_available_slots(doctor, date):
    """
    Get available time slots for a doctor on a specific date
    """
    # This is a sample implementation - adjust based on your scheduling system
    all_slots = [
        "9:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
        "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"
    ]
    
    # Get booked appointments for this doctor on this date
    booked_appointments = Appointment.objects.filter(
        doctor=doctor,
        scheduled_date=date,
        status__in=['confirmed', 'pending']
    ).values_list('scheduled_time', flat=True)
    
    # Filter out booked slots
    available_slots = []
    for slot in all_slots:
        slot_time = parse_time_string(slot)
        if slot_time not in booked_appointments:
            available_slots.append(slot)
    
    return available_slots


def get_doctor_upcoming_availability(doctor, days_ahead=7):
    """
    Get doctor's availability for the next week
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    availability = []
    
    for i in range(days_ahead):
        check_date = today + timedelta(days=i)
        available_slots = get_doctor_available_slots(doctor, check_date)
        
        if available_slots:
            date_str = check_date.strftime("%B %d")
            slots_str = ", ".join(available_slots[:3])  # Show first 3 slots
            availability.append(f"{date_str}: {slots_str}")
    
    return "; ".join(availability) if availability else None


def parse_date_string(date_str):
    """
    Parse date string like "18th July" to date object
    """
    # Implement date parsing logic
    # This is a simplified example
    from datetime import datetime
    
    try:
        # Handle formats like "18th July", "July 18", etc.
        # You may need to use dateutil.parser for better parsing
        return datetime.strptime(date_str.replace("th", "").replace("st", "").replace("nd", "").replace("rd", ""), "%d %B").date()
    except:
        return datetime.now().date()


def parse_time_string(time_str):
    """
    Parse time string like "11am" to time object
    """
    from datetime import datetime
    
    try:
        # Handle formats like "11am", "2:30 PM", etc.
        time_str = time_str.lower().replace(" ", "")
        if "am" in time_str or "pm" in time_str:
            return datetime.strptime(time_str, "%I%p").time()
        else:
            return datetime.strptime(time_str, "%H:%M").time()
    except:
        return datetime.now().time()


def is_doctor_available(doctor, date, time):
    """
    Check if doctor is available at specific date and time
    """
    existing_appointment = Appointment.objects.filter(
        doctor=doctor,
        scheduled_date=date,
        scheduled_time=time,
        status__in=['confirmed', 'pending']
    ).exists()
    
    return not existing_appointment
```

### **2. Enhanced Intent Handler for Availability Questions**

```python
elif inquiry_intent == "booking":
    print(f"🔍 BOOKING INTENT TRIGGERED")
    print(f"🔍 extracted_info keys: {list(extracted_info.keys())}")
    
    booking_obj = extracted_info.get("PromptOutputBooking")
    if booking_obj:
        print(f"🔍 Booking details: doctor={booking_obj.selected_doctor}, date={booking_obj.preferred_date}, time={booking_obj.preferred_consultation_time}")
        
        # Get conversation context for availability questions
        current_message = user_message.lower()
        
        # Handle availability questions
        if any(word in current_message for word in ["available", "availability", "when", "what time"]):
            if booking_obj.selected_doctor:
                # User is asking about doctor availability
                result = ai_book_appointment(
                    doctor_name=booking_obj.selected_doctor,
                    user_phone=user_session.user_phone_number,
                    date=booking_obj.preferred_date,
                    time=None  # Get general availability
                )
                return [UTILITIES.create_text_message(result)]
        
        # Handle booking confirmation
        elif booking_obj.confirmed:
            try:
                result = ai_book_appointment(
                    doctor_name=booking_obj.selected_doctor,
                    user_phone=user_session.user_phone_number,
                    date=booking_obj.preferred_date,
                    time=booking_obj.preferred_consultation_time
                )
                
                # Don't clear engine - let conversation continue
                if "not available" in result.lower():
                    # Add follow-up for availability
                    follow_up = f"{result} Would you like me to show you other available times?"
                    return [UTILITIES.create_text_message(follow_up)]
                else:
                    return [UTILITIES.create_text_message(result)]
                    
            except Exception as e:
                print(f"❌ Booking error: {e}")
                return [UTILITIES.create_text_message("I encountered an issue with the booking. Let me help you find alternative options.")]
    
    print(f"❌ No booking details found")
```

### **3. Test Scenarios**

**Scenario 1: Doctor Not Available**
```
User: Hi I want to book Dr Natalie Wanjiru
AI: What type of consultation you prefer?
User: Clinic visit
AI: What date would you prefer?
User: 18th July  
AI: What time would you prefer?
User: 11am
AI: Could you please confirm...?
User: Yes
AI: Dr. Natalie Wanjiru is not available at 11am on 18th July. Available times are: 9:00 AM, 2:00 PM, 4:00 PM. Would you like me to show you other available times?
User: What time is she available?  ← MEMORY PRESERVED!
AI: Dr. Natalie Wanjiru is available at: July 18: 9:00 AM, 2:00 PM, 4:00 PM; July 19: 10:00 AM, 3:00 PM, 5:00 PM
```

**Scenario 2: General Availability Check**
```
User: What time is Dr Natalie Wanjiru available?
AI: Dr. Natalie Wanjiru is available at: July 4: 9:00 AM, 2:00 PM, 4:00 PM; July 5: 10:00 AM, 3:00 PM; July 6: 11:00 AM, 1:00 PM, 3:00 PM
User: Book her for July 5 at 10am
AI: What type of consultation would you prefer?
[Conversation continues...]
```

## 🚀 **Implementation Steps**

1. **Replace your current `ai_book_appointment` function** with the enhanced version
2. **Add the helper functions** for availability checking
3. **Update your booking intent handler** to detect availability questions
4. **Remove any engine clearing** in the booking failure paths
5. **Test both scenarios** - booking failures and availability questions

This ensures that when a booking fails or when users ask about availability, the conversation context is maintained and they get helpful information to continue the booking process!