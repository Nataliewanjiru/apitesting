# Enhanced Booking Handler

## 🎯 **Improved Availability Responses**

To handle "What time is she available?" questions properly, enhance your `ai_book_appointment` function:

```python
def ai_book_appointment(
    doctor_name: str,
    mode: str,
    datetime_string: str,
    patient_user,
    symptoms: str = "",
    organization=None,
):
    print(f"🔍 ai_book_appointment called with doctor_name: {doctor_name}")
    
    # Step 1: Get doctor object by name - Your existing logic
    doctor = None
    
    try:
        # Your existing doctor search logic
        name_parts = doctor_name.replace("Dr.", "").replace("Dr", "").strip().split()
        
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
            
            doctor = HealthWorker.objects.filter(
                first_name__icontains=first_name,
                last_name__icontains=last_name
            ).first()
            
            print(f"🔍 Searched for: first_name={first_name}, last_name={last_name}")
            
        # Fallback searches...
        if not doctor and name_parts:
            doctor = HealthWorker.objects.filter(
                first_name__icontains=name_parts[0]
            ).first()
            
        print(f"🔍 Doctor found: {doctor}")
        
    except Exception as e:
        print(f"🔍 Error searching for doctor: {e}")
        
    if not doctor:
        return f"Doctor named '{doctor_name}' not found. Please check the name and try again."

    # Step 2: Check if this is an availability query (no specific time)
    if not datetime_string or datetime_string.strip() in ["", "None", "none"]:
        # User is asking for general availability
        availability_info = get_doctor_availability_info(doctor, mode, organization)
        return availability_info

    # Step 3: Parse datetime for specific booking attempt
    try:
        appointment_start = parse_datetime_string(datetime_string)
        appointment_end = appointment_start + timedelta(minutes=30)
    except Exception as e:
        print(f"🔍 Error parsing datetime: {e}")
        return f"I couldn't understand the date and time '{datetime_string}'. Please provide a clearer format."

    # Step 4: Check specific time availability
    available, availability = check_health_worker_availability(
        worker=doctor,
        start_time=appointment_start,
        end_time=appointment_end,
        mode=mode,
        organization=organization,
    )
    
    if not available:
        # Doctor not available - provide alternatives
        alternative_slots = get_alternative_time_slots(doctor, appointment_start, mode, organization)
        
        if alternative_slots:
            slots_text = ", ".join(alternative_slots)
            return f"Dr. {doctor.first_name} {doctor.last_name} is not available at {appointment_start.strftime('%I:%M %p on %B %d')}. Available times are: {slots_text}. Would you like to book one of these times?"
        else:
            return f"Dr. {doctor.first_name} {doctor.last_name} is not available on {appointment_start.strftime('%B %d')}. Would you like me to check other dates?"

    # Step 5: Get cost
    total_cost, breakdown = get_health_worker_appointment_cost(
        doctor=doctor,
        encounter_mode=mode,
        organization=organization,
    )

    # Step 6: Create appointment
    appointment = Appointment.objects.create(
        doctor=doctor,
        patient=patient_user.patient_profile,
        start_time=appointment_start,
        end_time=appointment_end,
        mode=mode,
        status="BOOKING_PENDING",
        symptoms=symptoms,
        created_by_patient=True,
    )

    # Step 7: Trigger notifications
    send_appointment_creation_notifications(
        appointment=appointment,
        payment_completed=False,
    )

    # Step 8: Success response
    return f"✅ Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {appointment_start.strftime('%A, %B %d at %I:%M %p')}.\nTotal cost: KES {total_cost}"


def get_doctor_availability_info(doctor, mode="clinic", organization=None, days_ahead=7):
    """
    Get general availability information for a doctor
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    available_slots = []
    
    for i in range(1, days_ahead + 1):  # Start from tomorrow
        check_date = today + timedelta(days=i)
        daily_slots = get_daily_available_slots(doctor, check_date, mode, organization)
        
        if daily_slots:
            date_str = check_date.strftime("%A, %B %d")
            slots_str = ", ".join(daily_slots[:3])  # Show first 3 slots
            if len(daily_slots) > 3:
                slots_str += f" and {len(daily_slots) - 3} more"
            available_slots.append(f"{date_str}: {slots_str}")
        
        if len(available_slots) >= 3:  # Limit to 3 days to avoid long messages
            break
    
    if available_slots:
        availability_text = "\n".join(available_slots)
        return f"Dr. {doctor.first_name} {doctor.last_name} is available on:\n\n{availability_text}\n\nWhich date and time would you prefer?"
    else:
        return f"Dr. {doctor.first_name} {doctor.last_name} doesn't have available slots in the next {days_ahead} days. Would you like me to check further ahead or suggest other doctors?"


def get_alternative_time_slots(doctor, requested_date, mode="clinic", organization=None):
    """
    Get alternative time slots for the same day when requested time is not available
    """
    date_only = requested_date.date()
    return get_daily_available_slots(doctor, date_only, mode, organization)


def get_daily_available_slots(doctor, date, mode="clinic", organization=None):
    """
    Get all available time slots for a doctor on a specific date
    """
    from datetime import datetime, time, timedelta
    
    # Define working hours (adjust based on your system)
    working_hours = [
        time(9, 0),   # 9:00 AM
        time(10, 0),  # 10:00 AM
        time(11, 0),  # 11:00 AM
        time(14, 0),  # 2:00 PM
        time(15, 0),  # 3:00 PM
        time(16, 0),  # 4:00 PM
        time(17, 0),  # 5:00 PM
    ]
    
    available_slots = []
    
    for slot_time in working_hours:
        slot_datetime = datetime.combine(date, slot_time)
        slot_end = slot_datetime + timedelta(minutes=30)
        
        # Check availability
        try:
            available, _ = check_health_worker_availability(
                worker=doctor,
                start_time=slot_datetime,
                end_time=slot_end,
                mode=mode,
                organization=organization,
            )
            
            if available:
                available_slots.append(slot_time.strftime("%I:%M %p"))
                
        except Exception as e:
            print(f"🔍 Error checking availability for {slot_datetime}: {e}")
            continue
    
    return available_slots
```

## 🎯 **Enhanced handle_booking_intent**

Also update your `handle_booking_intent` to handle availability questions:

```python
def handle_booking_intent(extracted_info, user):
    booking_info = extracted_info.get("PromptOutputBooking")
    personal_info = extracted_info.get("PromptOutputPersonalDetails") 
    inquiry_info = extracted_info.get("PromptOutputInquiry")

    doctor_name = booking_info.selected_doctor if booking_info else None
    location = personal_info.location if personal_info else None
    specialization = booking_info.specialization if booking_info else "general practitioner"
    preferred_date = booking_info.preferred_date if booking_info else None
    preferred_time = booking_info.preferred_consultation_time if booking_info else None
    confirmed = booking_info.confirmed if booking_info else None

    print(f"🔍 Booking details: doctor={doctor_name}, location={location}, specialization={specialization}")
    print(f"🔍 Date/Time: {preferred_date} at {preferred_time}, confirmed={confirmed}")

    # Handle availability questions
    if doctor_name and not confirmed:
        # User has selected a doctor but hasn't confirmed booking
        # This might be an availability question
        if not preferred_date or not preferred_time:
            # Missing date/time info - show general availability
            result = ai_book_appointment(
                doctor_name=doctor_name,
                datetime_string="",  # Empty for availability query
                mode="clinic",
                patient_user=user,
                symptoms=""
            )
            return result

    # Step 1: If no doctor selected, suggest doctors immediately
    if not doctor_name and specialization and location:
        # Your existing doctor suggestion logic...
        try:
            available_doctors = None
            
            try:
                available_doctors = HealthWorker.objects.filter(
                    primary_specialty__name__icontains=specialization,
                    primary_clinic_practice__name__icontains=location
                ).select_related('primary_specialty', 'primary_clinic_practice')[:3]
                
                if not available_doctors.exists():
                    available_doctors = HealthWorker.objects.filter(
                        primary_specialty__name__icontains=specialization,
                        primary_clinic_practice__address__icontains=location
                    ).select_related('primary_specialty', 'primary_clinic_practice')[:3]
                    
            except Exception as e:
                print(f"🔍 First query failed: {e}")
                
            if not available_doctors or not available_doctors.exists():
                try:
                    available_doctors = HealthWorker.objects.filter(
                        primary_specialty__name__icontains=specialization
                    ).select_related('primary_specialty', 'primary_clinic_practice')[:3]
                    print(f"🔍 Found {available_doctors.count()} doctors without location filter")
                except Exception as e:
                    print(f"🔍 Second query failed: {e}")
            
            if not available_doctors or not available_doctors.exists():
                available_doctors = HealthWorker.objects.all()[:3]
                print(f"🔍 Using fallback query")

            if not available_doctors.exists():
                return f"Unfortunately, I couldn't find any {specialization}s in {location}. Would you like me to check nearby areas?"

            suggestions = "\n".join([
                f"- Dr. {doc.first_name} {doc.last_name}" + 
                (f" at {doc.primary_clinic_practice.name}" if doc.primary_clinic_practice else "")
                for doc in available_doctors
            ])

            return (
                f"Here are some {specialization}s available:\n"
                f"{suggestions}\n\n"
                "Please let me know who you would like to book with, or if you'd prefer I help you choose based on availability."
            )
            
        except Exception as e:
            print(f"🔍 All queries failed: {e}")
            return f"I found some healthcare providers but had trouble filtering by location. Let me show you available options."

    # Step 2: If doctor is selected and confirmed, proceed to booking
    if confirmed is True and doctor_name:
        symptoms = ", ".join(inquiry_info.symptoms) if inquiry_info and inquiry_info.symptoms else "general check-up"
        preferred_modes = inquiry_info.preferred_modes_of_consultation if inquiry_info else []
        mode = preferred_modes[0] if preferred_modes else "clinic"

        datetime_string = f"{preferred_date} {preferred_time}" if preferred_date and preferred_time else ""
        
        result = ai_book_appointment(
            doctor_name=doctor_name,
            datetime_string=datetime_string,
            mode=mode,
            patient_user=user,
            symptoms=symptoms
        )
        return result

    # Step 3: Ask for confirmation before booking
    return "Would you like me to go ahead and book an appointment for you?"
```

## 🚀 **Expected Results**

**Scenario 1: Availability Question**
```
User: What time is Dr Natalie Wanjiru available?
AI: Dr. Natalie Wanjiru is available on:

Tuesday, July 5: 9:00 AM, 2:00 PM, 4:00 PM and 2 more
Wednesday, July 6: 10:00 AM, 3:00 PM, 5:00 PM
Thursday, July 7: 11:00 AM, 1:00 PM, 4:00 PM and 1 more

Which date and time would you prefer?
```

**Scenario 2: Specific Time Not Available**
```
User: Book Dr Natalie for July 5 at 11am
AI: Dr. Natalie Wanjiru is not available at 11:00 AM on July 5. Available times are: 9:00 AM, 2:00 PM, 4:00 PM. Would you like to book one of these times?
```

This enhancement ensures users get helpful availability information while maintaining conversation context!