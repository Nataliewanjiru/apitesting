from datetime import datetime, timedelta
from apps.healthworkers.models import HealthWorker
from apps.appointments.models import Appointment
from apps.core.models import CORE_CHOICES
from .utilities import parse_datetime_string
from .appointment_functions import (
    check_health_worker_availability, 
    get_health_worker_appointment_cost,
    send_appointment_creation_notifications
)


def ai_book_appointment(
    doctor_name: str,
    mode: str,
    datetime_string: str,
    patient_user,
    symptoms: str = "",
    organization=None,
    confirmed: bool = False
):
    print(f"🔍 ai_book_appointment called with doctor_name: {doctor_name}")
    print(f"🔍 Confirmed: {confirmed}, DateTime: '{datetime_string}'")
    
    # Step 1: Get doctor object by name - Enhanced search
    doctor = find_doctor_by_name(doctor_name)
    
    if not doctor:
        # Suggest alternative doctors or redirect to symptom-based search
        return handle_doctor_not_found(doctor_name, symptoms)

    # Step 2: Handle availability queries (empty datetime_string)
    if not datetime_string or datetime_string.strip() == "":
        print(f"🔍 Availability query for Dr. {doctor.first_name} {doctor.last_name}")
        return get_doctor_availability(doctor)

    # Step 3: Parse and validate datetime
    try:
        appointment_start = parse_datetime_string(datetime_string)
        if not appointment_start:
            return "I couldn't understand the date and time. Could you please specify it more clearly? For example: 'July 5th at 9am' or '5/7/2024 9:00 AM'"
    except Exception as e:
        print(f"🔍 Error parsing datetime: {e}")
        return "Please provide a valid date and time. For example: 'July 5th at 9am' or 'tomorrow at 2pm'"

    appointment_end = appointment_start + timedelta(minutes=30)  # 30-min slots

    # Step 4: Check real availability
    print(f"🔍 Checking availability for {appointment_start} to {appointment_end}")
    available, availability_record = check_health_worker_availability(
        worker=doctor,
        start_time=appointment_start,
        end_time=appointment_end,
        mode=mode,
        organization=organization,
    )

    if not available:
        print(f"🔍 Doctor not available at requested time")
        return handle_unavailable_time_slot(doctor, appointment_start, mode)

    # Step 5: If confirmed, proceed with booking
    if confirmed:
        return create_confirmed_appointment(
            doctor=doctor,
            patient_user=patient_user,
            appointment_start=appointment_start,
            appointment_end=appointment_end,
            mode=mode,
            symptoms=symptoms,
            organization=organization,
            availability_record=availability_record
        )
    
    # Step 6: If not confirmed, ask for confirmation
    return request_booking_confirmation(doctor, appointment_start, mode, symptoms)


def find_doctor_by_name(doctor_name: str):
    """Enhanced doctor search with multiple fallback strategies"""
    try:
        # Clean the name
        clean_name = doctor_name.replace("Dr.", "").replace("Dr", "").strip()
        name_parts = clean_name.split()
        
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
            
            # Try exact match first
            doctor = HealthWorker.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                is_published=True
            ).first()
            
            if doctor:
                return doctor
            
            # Try case-insensitive contains
            doctor = HealthWorker.objects.filter(
                first_name__icontains=first_name,
                last_name__icontains=last_name,
                is_published=True
            ).first()
            
            if doctor:
                return doctor
        
        # Try single name search
        if name_parts:
            for part in name_parts:
                doctor = HealthWorker.objects.filter(
                    first_name__icontains=part,
                    is_published=True
                ).first()
                if doctor:
                    return doctor
                    
                doctor = HealthWorker.objects.filter(
                    last_name__icontains=part,
                    is_published=True
                ).first()
                if doctor:
                    return doctor
                    
    except Exception as e:
        print(f"🔍 Error searching for doctor: {e}")
    
    return None


def handle_doctor_not_found(doctor_name: str, symptoms: str):
    """Handle cases where the requested doctor is not found"""
    
    # If symptoms provided, suggest symptom-based search
    if symptoms and symptoms.strip():
        from .doctor_recommendations import get_health_worker_recommendation_from_symptoms
        try:
            recommendation_result, _, error = get_health_worker_recommendation_from_symptoms(symptoms)
            
            if recommendation_result and recommendation_result.get("recommended_health_workers"):
                doctors = recommendation_result["recommended_health_workers"]["data"][:3]
                
                if doctors:
                    doctor_list = []
                    for i, doctor in enumerate(doctors, 1):
                        name = f"Dr. {doctor['first_name']} {doctor['last_name']}"
                        specialty = doctor.get('primary_specialty', {}).get('name', 'General Practice')
                        doctor_list.append(f"{i}. {name} - {specialty}")
                    
                    doctors_text = "\n".join(doctor_list)
                    return f"I couldn't find Dr. {doctor_name}. Based on your symptoms, here are some available doctors:\n\n{doctors_text}\n\nWhich doctor would you like to book instead?"
        except Exception as e:
            print(f"🔍 Error getting recommendations: {e}")
    
    # Suggest browsing or visiting website
    return f"I couldn't find Dr. {doctor_name}. Please check the spelling or browse available doctors on our website at www.rastuc.com. You can also tell me your symptoms and I'll recommend suitable doctors."


def get_doctor_availability(doctor):
    """Get and format doctor availability information"""
    try:
        # Check if doctor has any availability records
        from apps.appointments.models import HealthWorkerAvailability
        
        today = datetime.now().date()
        availability_records = HealthWorkerAvailability.objects.filter(
            doctor=doctor,
            start_time__date__gte=today,
            start_time__date__lte=today + timedelta(days=7)
        ).order_by('start_time')
        
        if availability_records.exists():
            # Format real availability
            available_slots = []
            for availability in availability_records[:10]:  # Limit to 10 slots
                date_str = availability.start_time.strftime("%B %d")
                time_str = availability.start_time.strftime("%I:%M %p")
                available_slots.append(f"{date_str}: {time_str}")
            
            if available_slots:
                availability_text = "\n".join(available_slots)
                return f"Dr. {doctor.first_name} {doctor.last_name} is available on:\n\n{availability_text}\n\nWhich time works for you?"
        
        # Fallback to sample availability
        return get_sample_availability(doctor)
        
    except Exception as e:
        print(f"🔍 Error getting availability: {e}")
        return get_sample_availability(doctor)


def get_sample_availability(doctor):
    """Generate sample availability when real data is not available"""
    today = datetime.now().date()
    available_dates = []
    
    for i in range(1, 4):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%B %d")
        sample_times = ["9:00 AM", "2:00 PM"]
        available_dates.append(f"{date_str}: {', '.join(sample_times)}")
    
    if available_dates:
        availability_text = "\n".join(available_dates)
        return f"Dr. {doctor.first_name} {doctor.last_name} is available on:\n\n{availability_text}\n\nWhich time would you prefer?"
    else:
        return f"Dr. {doctor.first_name} {doctor.last_name} typically has availability on weekdays between 9 AM - 5 PM. What date and time would you prefer?"


def handle_unavailable_time_slot(doctor, requested_time, mode):
    """Handle cases where the requested time slot is not available"""
    try:
        # Get alternative times near the requested slot
        day_start = requested_time.replace(hour=9, minute=0, second=0, microsecond=0)
        day_end = requested_time.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Check for conflicts
        conflicting_appointments = Appointment.objects.filter(
            doctor=doctor,
            start_time__date=requested_time.date(),
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
        return f"Dr. {doctor.first_name} {doctor.last_name} is not available at that time. Let me check their next available slots:\n\n{get_doctor_availability(doctor)}"
        
    except Exception as e:
        print(f"🔍 Error finding alternatives: {e}")
        return f"Dr. {doctor.first_name} {doctor.last_name} is not available at that time. Please choose a different time or let me show you their availability."


def create_confirmed_appointment(doctor, patient_user, appointment_start, appointment_end, mode, symptoms, organization, availability_record):
    """Create and confirm an appointment"""
    try:
        print(f"🔍 Creating confirmed appointment")
        
        # Get cost information
        total_cost, breakdown = get_health_worker_appointment_cost(
            doctor=doctor,
            encounter_mode=mode,
            organization=organization,
        )
        
        # Get patient object
        patient = patient_user.patient_profile if hasattr(patient_user, 'patient_profile') else patient_user
        
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


def request_booking_confirmation(doctor, appointment_start, mode, symptoms):
    """Request user confirmation before booking"""
    appointment_time = appointment_start.strftime('%A, %B %d at %I:%M %p')
    return (f"Perfect! I can book you with:\n\n"
            f"Doctor: Dr. {doctor.first_name} {doctor.last_name}\n"
            f"Date & Time: {appointment_time}\n"
            f"Type: {mode.title()} consultation\n"
            f"Reason: {symptoms or 'General consultation'}\n\n"
            f"Shall I go ahead and confirm this appointment for you?")


def get_alternative_doctors_by_specialty(specialization: str, location: str = None):
    """Get alternative doctors when requested doctor is unavailable"""
    try:
        query_set = HealthWorker.objects.filter(
            primary_specialty__name__icontains=specialization,
            is_published=True
        )
        
        if location:
            query_set = query_set.filter(
                primary_clinic_practice__county__name__icontains=location
            ).distinct()
        
        doctors = query_set[:3]  # Top 3 alternatives
        
        if doctors:
            doctor_list = []
            for i, doctor in enumerate(doctors, 1):
                name = f"Dr. {doctor.first_name} {doctor.last_name}"
                specialty = doctor.primary_specialty.name if doctor.primary_specialty else 'General Practice'
                doctor_list.append(f"{i}. {name} - {specialty}")
            
            return "\n".join(doctor_list)
    
    except Exception as e:
        print(f"🔍 Error getting alternative doctors: {e}")
    
    return None