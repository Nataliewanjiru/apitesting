import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from apps.core.models import CORE_CHOICES
from apps.healthworkers.models import HealthWorker
from apps.appointments.models import Appointment
from .ai_book_appointment import ai_book_appointment
from .doctor_recommendations import get_health_worker_recommendation_from_symptoms, search_health_worker_query_set


def detect_booking_confirmation(message_text: str, extracted_info: Dict) -> bool:
    """
    Detects if user is confirming a booking based on their message
    """
    booking_info = extracted_info.get("PromptOutputBooking", {})
    
    # Direct confirmation phrases
    confirmation_phrases = [
        "yes", "ok", "okay", "sure", "confirm", "book", "schedule", 
        "go ahead", "proceed", "that works", "perfect", "sounds good",
        "i want", "i'll take", "book me", "confirm it"
    ]
    
    # Check for explicit time/date selection (like "5th July at 9")
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
    for pattern in time_date_patterns:
        if re.search(pattern, message_lower):
            return True
    
    # If they have doctor and time/date info, likely confirming
    if (booking_info.get("selected_doctor") and 
        (booking_info.get("preferred_date") or booking_info.get("preferred_consultation_time"))):
        return True
        
    return False


def detect_cancellation_intent(message_text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects if user wants to cancel a booking
    Returns (is_cancellation, appointment_identifier)
    """
    cancellation_phrases = [
        "cancel", "delete", "remove", "abort", "stop", "withdraw",
        "cancel my appointment", "cancel booking", "don't want",
        "changed my mind", "no longer need"
    ]
    
    message_lower = message_text.lower()
    
    for phrase in cancellation_phrases:
        if phrase in message_lower:
            # Try to extract appointment identifier (doctor name, date, etc.)
            return True, extract_appointment_identifier(message_text)
    
    return False, None


def extract_appointment_identifier(message_text: str) -> Optional[str]:
    """
    Extracts appointment identifier from cancellation message
    """
    # Look for doctor names, dates, times
    patterns = [
        r'dr\.?\s+\w+',
        r'with\s+\w+',
        r'\d{1,2}(st|nd|rd|th)?\s+\w+',
        r'appointment\s+on\s+\w+'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message_text.lower())
        if match:
            return match.group(0)
    
    return None


def handle_booking_intent(extracted_info: Dict, user, message_text: str = ""):
    """
    Enhanced booking handler with proper confirmation detection
    """
    booking_info = extracted_info.get("PromptOutputBooking", {})
    personal_info = extracted_info.get("PromptOutputPersonalDetails", {}) 
    inquiry_info = extracted_info.get("PromptOutputInquiry", {})

    doctor_name = booking_info.get("selected_doctor")
    location = personal_info.get("location")
    specialization = booking_info.get("specialization", "general practitioner")
    preferred_date = booking_info.get("preferred_date")
    preferred_time = booking_info.get("preferred_consultation_time")
    confirmed = booking_info.get("confirmed")

    print(f"🔍 Booking details: doctor={doctor_name}, location={location}, specialization={specialization}")
    print(f"🔍 Date/Time: {preferred_date} at {preferred_time}, confirmed={confirmed}")
    print(f"🔍 Message text: {message_text}")

    # Check for cancellation intent first
    is_cancellation, appointment_id = detect_cancellation_intent(message_text)
    if is_cancellation:
        return handle_appointment_cancellation(user, appointment_id)

    # Step 1: If no doctor selected, suggest doctors based on symptoms/specialization
    if not doctor_name and (specialization or inquiry_info.get("symptoms")):
        return handle_doctor_recommendation_request(specialization, location, inquiry_info)

    # Step 2: Check if user is confirming booking (improved detection)
    is_confirming = detect_booking_confirmation(message_text, extracted_info)
    
    if doctor_name and (confirmed is True or is_confirming):
        print(f"🔍 Booking confirmation detected")
        
        # Proceed with actual booking
        symptoms = ", ".join(inquiry_info.get("symptoms", [])) if inquiry_info.get("symptoms") else "general check-up"
        preferred_modes = inquiry_info.get("preferred_modes_of_consultation", [])
        mode = preferred_modes[0] if preferred_modes else "clinic"

        try:
            result = ai_book_appointment(
                doctor_name=doctor_name,
                datetime_string=f"{preferred_date or ''} {preferred_time or ''}".strip(),
                mode=mode,
                patient_user=user,
                symptoms=symptoms,
                confirmed=True  # Explicitly confirming
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
                datetime_string="",  # Empty for availability query
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

    # Default fallback
    return "Could you please provide more details about your preferred appointment time and date?"


def handle_doctor_recommendation_request(specialization: str, location: str, inquiry_info: Dict):
    """
    Handle doctor recommendations based on symptoms or specialization
    """
    try:
        symptoms = inquiry_info.get("symptoms", []) if inquiry_info else []
        
        if symptoms:
            # Use symptom-based recommendation
            symptoms_text = " ".join(symptoms)
            recommendation_result, _, error = get_health_worker_recommendation_from_symptoms(symptoms_text)
            
            if recommendation_result and recommendation_result.get("recommended_health_workers"):
                doctors = recommendation_result["recommended_health_workers"]["data"][:3]  # Top 3
                
                if doctors:
                    doctor_list = []
                    for i, doctor in enumerate(doctors, 1):
                        name = f"Dr. {doctor['first_name']} {doctor['last_name']}"
                        specialty = doctor.get('primary_specialty', {}).get('name', 'General Practice')
                        doctor_list.append(f"{i}. {name} - {specialty}")
                    
                    doctors_text = "\n".join(doctor_list)
                    return f"Based on your symptoms, I recommend these doctors:\n\n{doctors_text}\n\nWhich doctor would you like to book an appointment with?"
        
        # Fallback to specialization-based search
        if specialization and specialization != "general practitioner":
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


def handle_appointment_cancellation(user, appointment_identifier: Optional[str]):
    """
    Handle appointment cancellation requests
    """
    try:
        # Find user's pending appointments
        pending_appointments = Appointment.objects.filter(
            patient=user.patient_profile if hasattr(user, 'patient_profile') else user,
            status__in=[
                CORE_CHOICES.AppointmentStatuses.PENDING.value,
                CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
            ]
        ).order_by('-created')
        
        if not pending_appointments.exists():
            return "You don't have any upcoming appointments to cancel."
        
        # If specific identifier provided, try to match
        if appointment_identifier:
            # Try to find appointment by doctor name or date
            for appointment in pending_appointments:
                doctor_name = f"Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}".lower()
                if appointment_identifier.lower() in doctor_name:
                    return cancel_appointment(appointment)
        
        # If only one appointment, cancel it
        if pending_appointments.count() == 1:
            appointment = pending_appointments.first()
            return cancel_appointment(appointment)
        
        # Multiple appointments - show list
        appointment_list = []
        for i, appointment in enumerate(pending_appointments[:5], 1):
            doctor_name = f"Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}"
            date_time = appointment.start_time.strftime("%B %d at %I:%M %p")
            appointment_list.append(f"{i}. {doctor_name} on {date_time}")
        
        appointments_text = "\n".join(appointment_list)
        return f"You have multiple appointments:\n\n{appointments_text}\n\nWhich one would you like to cancel? Please specify the doctor's name or date."
        
    except Exception as e:
        print(f"🔍 Error handling cancellation: {e}")
        return "Sorry, I couldn't process your cancellation request. Please try again or contact support."


def cancel_appointment(appointment):
    """
    Cancel a specific appointment and send notifications
    """
    try:
        doctor_name = f"Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}"
        appointment_time = appointment.start_time.strftime("%B %d at %I:%M %p")
        
        # Update appointment status
        appointment.status = CORE_CHOICES.AppointmentStatuses.CANCELLED.value
        appointment.cancelled_by_patient = True
        appointment.save()
        
        # Send cancellation notifications
        from .appointment_functions import send_appointment_cancellation_by_patient_notification
        send_appointment_cancellation_by_patient_notification(appointment)
        
        return f"Your appointment with {doctor_name} on {appointment_time} has been cancelled successfully. The doctor has been notified."
        
    except Exception as e:
        print(f"🔍 Error cancelling appointment: {e}")
        return "Sorry, I couldn't cancel your appointment. Please try again or contact support."


def get_user_appointments(user, status_filter: str = "upcoming"):
    """
    Get user's appointments with optional status filtering
    """
    try:
        patient = user.patient_profile if hasattr(user, 'patient_profile') else user
        
        if status_filter == "upcoming":
            appointments = Appointment.objects.filter(
                patient=patient,
                status__in=[
                    CORE_CHOICES.AppointmentStatuses.PENDING.value,
                    CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
                ],
                start_time__gte=datetime.now()
            ).order_by('start_time')
        elif status_filter == "past":
            appointments = Appointment.objects.filter(
                patient=patient,
                status__in=[
                    CORE_CHOICES.AppointmentStatuses.COMPLETED.value,
                    CORE_CHOICES.AppointmentStatuses.CANCELLED.value
                ]
            ).order_by('-start_time')
        else:
            appointments = Appointment.objects.filter(
                patient=patient
            ).order_by('-start_time')
        
        return appointments[:10]  # Limit to 10 most relevant
        
    except Exception as e:
        print(f"🔍 Error getting appointments: {e}")
        return []


def format_appointment_list(appointments, include_status: bool = False):
    """
    Format appointments into a readable list
    """
    if not appointments:
        return "You have no appointments."
    
    appointment_list = []
    for i, appointment in enumerate(appointments, 1):
        doctor_name = f"Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}"
        date_time = appointment.start_time.strftime("%B %d at %I:%M %p")
        
        line = f"{i}. {doctor_name} on {date_time}"
        if include_status:
            status = appointment.get_status_display()
            line += f" ({status})"
        
        appointment_list.append(line)
    
    return "\n".join(appointment_list)