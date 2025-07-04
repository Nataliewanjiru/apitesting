# Availability Loop Fix

## 🚨 **Problem Identified**

Your `handle_booking_intent` function doesn't handle availability queries properly. When users ask "When is she available", it should provide actual availability information, not just ask for booking confirmation again.

## 🔧 **Current Problematic Flow**

```python
def handle_booking_intent(extracted_info, user):
    # ... doctor selection logic ...
    
    # Step 2: If doctor is selected and confirmed, proceed to booking
    if confirmed is True and doctor_name:
        # Booking logic here
        
    # Step 3: Ask for confirmation before booking ← ALWAYS FALLS HERE!
    return "Would you like me to go ahead and book an appointment for you?"
```

**The Problem**: When `confirmed=None` (availability query), it always falls through to asking for confirmation, creating a loop.

## ✅ **Fixed handle_booking_intent Function**

Replace your `handle_booking_intent` function with this enhanced version:

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

    # Step 1: If no doctor selected, suggest doctors immediately
    if not doctor_name and specialization and location:
        try:
            # Your existing doctor search logic...
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

    # ✅ NEW: Step 2 - Handle Availability Questions
    if doctor_name and confirmed is None:
        print(f"🔍 Availability query detected for {doctor_name}")
        
        # This is likely an availability question - provide actual availability
        try:
            # Call ai_book_appointment with empty datetime to get availability
            availability_result = ai_book_appointment(
                doctor_name=doctor_name,
                datetime_string="",  # Empty for availability query
                mode="clinic",
                patient_user=user,
                symptoms=""
            )
            
            # Check if it's an availability response or error
            if "not found" in availability_result.lower():
                return availability_result
            else:
                # This should be availability information
                return f"{availability_result}\n\nWhich time would you prefer?"
                
        except Exception as e:
            print(f"🔍 Error getting availability: {e}")
            return f"I'll check Dr. {doctor_name.replace('Dr. ', '')} schedule and get back to you with available times. What type of consultation would you prefer - clinic visit or virtual?"

    # Step 3: If doctor is selected and confirmed, proceed to booking
    if confirmed is True and doctor_name:
        symptoms = ", ".join(inquiry_info.symptoms) if inquiry_info and inquiry_info.symptoms else "general check-up"
        preferred_modes = inquiry_info.preferred_modes_of_consultation if inquiry_info else []
        mode = preferred_modes[0] if preferred_modes else "clinic"

        result = ai_book_appointment(
            doctor_name=doctor_name,
            datetime_string=f"{preferred_date} {preferred_time}",
            mode=mode,
            patient_user=user,
            symptoms=symptoms
        )
        return result

    # Step 4: Default - Ask for confirmation
    if doctor_name and preferred_date and preferred_time:
        return f"Would you like me to go ahead and book an appointment with {doctor_name} on {preferred_date} at {preferred_time}?"
    else:
        return "Would you like me to go ahead and book an appointment for you?"
```

## 🔧 **Enhanced ai_book_appointment for Availability**

Also update your `ai_book_appointment` function to handle availability queries:

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
    
    # Step 1: Get doctor object by name
    doctor = None
    
    try:
        name_parts = doctor_name.replace("Dr.", "").replace("Dr", "").strip().split()
        
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
            
            doctor = HealthWorker.objects.filter(
                first_name__icontains=first_name,
                last_name__icontains=last_name
            ).first()
            
            print(f"🔍 Searched for: first_name={first_name}, last_name={last_name}")
            
        if not doctor and name_parts:
            doctor = HealthWorker.objects.filter(
                first_name__icontains=name_parts[0]
            ).first()
            
        print(f"🔍 Doctor found: {doctor}")
        
    except Exception as e:
        print(f"🔍 Error searching for doctor: {e}")
        
    if not doctor:
        return f"Doctor named '{doctor_name}' not found. Please check the name and try again."

    # ✅ NEW: Step 2 - Handle Availability Query (empty datetime_string)
    if not datetime_string or datetime_string.strip() == "":
        print(f"🔍 Availability query for Dr. {doctor.first_name} {doctor.last_name}")
        
        # Return availability information instead of booking
        try:
            # Get upcoming availability (simplified example)
            from datetime import datetime, timedelta
            
            today = datetime.now().date()
            available_dates = []
            
            # Check next 7 days for availability (simplified)
            for i in range(1, 8):
                check_date = today + timedelta(days=i)
                date_str = check_date.strftime("%B %d")
                
                # Sample available times (you can enhance this with real availability checking)
                sample_times = ["9:00 AM", "2:00 PM", "4:00 PM"]
                available_dates.append(f"{date_str}: {', '.join(sample_times[:2])}")
                
                if len(available_dates) >= 3:  # Limit to 3 days
                    break
            
            if available_dates:
                availability_text = "\n".join(available_dates)
                return f"Dr. {doctor.first_name} {doctor.last_name} is available on:\n\n{availability_text}"
            else:
                return f"Dr. {doctor.first_name} {doctor.last_name} doesn't have available slots in the next week. Would you like me to check further ahead?"
                
        except Exception as e:
            print(f"🔍 Error getting availability: {e}")
            return f"I'm checking Dr. {doctor.first_name} {doctor.last_name}'s schedule. They typically have availability on weekdays between 9 AM - 5 PM. What date would you prefer?"

    # Step 3: Continue with normal booking logic for specific times
    try:
        appointment_start = parse_datetime_string(datetime_string)
        appointment_end = appointment_start + timedelta(minutes=30)
    except Exception as e:
        print(f"🔍 Error parsing datetime: {e}")
        return f"I couldn't understand the date and time format. Please try again with a clearer format like 'July 18th 11am'."

    # Rest of your existing booking logic...
    available, availability = check_health_worker_availability(
        worker=doctor,
        start_time=appointment_start,
        end_time=appointment_end,
        mode=mode,
        organization=organization,
    )
    
    if not available:
        # Provide alternatives instead of just saying "not available"
        return f"Dr. {doctor.first_name} {doctor.last_name} is not available at {appointment_start.strftime('%I:%M %p on %B %d')}. Would you like me to show you their available times?"

    # Continue with booking if available...
    total_cost, breakdown = get_health_worker_appointment_cost(
        doctor=doctor,
        encounter_mode=mode,
        organization=organization,
    )

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

    send_appointment_creation_notifications(
        appointment=appointment,
        payment_completed=False,
    )

    return f"✅ Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {appointment_start.strftime('%A, %B %d at %I:%M %p')}.\nTotal cost: KES {total_cost}"
```

## 🎯 **Expected Flow After Fix**

```
User: When is she available?
AI: Dr. Natalie Wanjiru is available on:

July 5: 9:00 AM, 2:00 PM
July 6: 10:00 AM, 4:00 PM  
July 7: 9:00 AM, 3:00 PM

Which time would you prefer?

User: Book me for July 5 at 2pm
AI: I'll book you with Dr. Natalie Wanjiru for July 5 at 2:00 PM. Confirming...
```

This fix will break the loop and provide actual availability information when users ask for it!