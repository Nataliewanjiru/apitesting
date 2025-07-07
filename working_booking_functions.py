from datetime import timedelta
import json
from typing import Optional, List, Dict, Any
from apps.appointments.functions import (
    check_health_worker_availability, 
    get_health_worker_appointment_cost, 
    send_appointment_cancellation_by_patient_notification, 
    send_appointment_creation_notifications,
    send_appointment_rescheduling_by_patient_notification
)
from apps.appointments.models import Appointment, HealthWorkerAvailability
from apps.healthworkers.functions import search_health_worker_query_set
from openai import OpenAI
import apps.whatsappplugin1.models as WHATSAPP_PLUGIN1
import apps.whatsappplugin1.utilities as UTILITIES
from django.db.models import Q
import apps.healthworkers.models as HEALTHWORKERS_MODELS
import apps.core.choices as CORE_CHOICES
import apps.utilities.functions as UTILITIES_FUNCTIONS


def create_confirmed_appointment(doctor, patient_user, appointment_start, appointment_end, mode, symptoms, organization=None, availability_record=None):
    """Create and confirm an appointment"""
    try:
        print(f"🔍 Creating confirmed appointment for {doctor.get_full_name()}")
        
        # Get cost information
        total_cost, breakdown = get_health_worker_appointment_cost(
            doctor=doctor,
            encounter_mode=mode,
            organization=organization,
        )
        
        # Get patient object
        patient = patient_user.active_patient_profile if hasattr(patient_user, 'active_patient_profile') else patient_user
        
        # Create appointment
        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            start_time=appointment_start,
            end_time=appointment_end,
            encounter_mode=mode,
            status=CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value,
            symptoms_description=symptoms,  # Correct field name
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
                f"Doctor: {doctor.title} {doctor.get_full_name()}\n"
                f"Date & Time: {appointment_time}\n"
                f"Type: {mode.title()} consultation\n"
                f"Total Cost: KES {total_cost}\n\n"
                f"You'll receive a confirmation via SMS and email. Payment can be made through the app or at the clinic.")
        
    except Exception as e:
        print(f"🔍 Error creating appointment: {e}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        return "Sorry, there was an error confirming your appointment. Please try again or contact support."


def request_booking_confirmation(doctor, appointment_start, mode, symptoms):
    """Request user confirmation before booking"""
    appointment_time = appointment_start.strftime('%A, %B %d at %I:%M %p')
    return (f"Perfect! I can book you with:\n\n"
            f"Doctor: {doctor.title} {doctor.get_full_name()}\n"
            f"Date & Time: {appointment_time}\n"
            f"Type: {mode.title()} consultation\n"
            f"Reason: {symptoms or 'General consultation'}\n\n"
            f"Shall I go ahead and confirm this appointment for you?")


def book_appointment_with_doctor(user_session, booking_details: dict) -> str:
    """Book an appointment with a specific doctor"""
    try:
        print(f"🔍 Booking appointment with details: {booking_details}")
        
        doctor_name = booking_details.get('doctor_name', '')
        date_str = booking_details.get('date', '')
        time_str = booking_details.get('time', '')
        consultation_mode = booking_details.get('consultation_mode', 'clinic_visit')
        symptoms = booking_details.get('symptoms', 'General consultation')
        
        if not doctor_name or not date_str or not time_str:
            return "Please provide doctor name, date, and time to book appointment."
        
        # Find the doctor
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        
        # Clean doctor name (remove titles)
        cleaned_doctor_name = doctor_name.strip().lower()
        titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
        for title in titles_to_remove:
            if cleaned_doctor_name.startswith(title + ' '):
                cleaned_doctor_name = cleaned_doctor_name[len(title):].strip()
            elif cleaned_doctor_name.startswith(title):
                cleaned_doctor_name = cleaned_doctor_name[len(title):].strip()
        
        doctors = search_health_worker_query_set(doctors, cleaned_doctor_name)
        
        if not doctors:
            return f"Doctor '{doctor_name}' not found. Please check the name and try again."
        
        doctor = doctors.first()
        print(f"🔍 Found doctor: {doctor.title} {doctor.get_full_name()}")
        
        # Parse date and time
        try:
            start_datetime = UTILITIES_FUNCTIONS.string_to_datetime(f"{date_str} {time_str}:00.0 +0300")
            end_datetime = start_datetime + timedelta(hours=1)
            print(f"🔍 Appointment time: {start_datetime} to {end_datetime}")
        except Exception as e:
            print(f"🔍 Date/time parsing error: {e}")
            return "Invalid date/time format. Please use YYYY-MM-DD for date and HH:MM for time."
        
        # Check availability
        print(f"🔍 Checking availability for {consultation_mode} consultation")
        is_available, availability = check_health_worker_availability(
            worker=doctor,
            start_time=start_datetime,
            end_time=end_datetime,
            mode=consultation_mode
        )
        
        if not is_available:
            return f"❌ {doctor.title} {doctor.get_full_name()} is not available on {date_str} at {time_str} for {consultation_mode} consultation. Please choose a different time or check available slots."
        
        print(f"🔍 Doctor is available, proceeding with booking")
        
        # Create the appointment
        result = create_confirmed_appointment(
            doctor=doctor,
            patient_user=user_session,
            appointment_start=start_datetime,
            appointment_end=end_datetime,
            mode=consultation_mode,
            symptoms=symptoms,
            organization=None,  # Can be enhanced later
            availability_record=availability
        )
        
        return result
               
    except Exception as e:
        print(f"🔍 Booking failed with error: {e}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        return f"Booking failed: Please try again or contact support. Error: {str(e)}"


def quick_book_from_available_slots(user_session, doctor_name: str, selected_slot: str, consultation_mode: str = "virtual", symptoms: str = "General consultation") -> str:
    """Quick booking from available time slots"""
    try:
        # Parse the selected slot (format: "2025-07-07 09:00")
        if " " not in selected_slot:
            return "Please provide the date and time in format: YYYY-MM-DD HH:MM"
        
        date_str, time_str = selected_slot.split(" ", 1)
        
        booking_details = {
            'doctor_name': doctor_name,
            'date': date_str,
            'time': time_str,
            'consultation_mode': consultation_mode,
            'symptoms': symptoms
        }
        
        return book_appointment_with_doctor(user_session, booking_details)
    
    except Exception as e:
        return f"Quick booking failed: {str(e)}"


def confirm_appointment_booking(user_session, confirmation_details: dict) -> str:
    """Confirm a pending appointment booking"""
    try:
        confirm = confirmation_details.get('confirm', '').lower()
        doctor_name = confirmation_details.get('doctor_name', '')
        appointment_time = confirmation_details.get('appointment_time', '')
        
        if confirm in ['yes', 'y', 'confirm', 'book', 'proceed']:
            # User confirmed - check if we have enough details
            if doctor_name and appointment_time:
                # Try to parse the appointment time
                if " " in appointment_time:
                    date_str, time_str = appointment_time.split(" ", 1)
                    return book_appointment_with_doctor(user_session, {
                        'doctor_name': doctor_name,
                        'date': date_str,
                        'time': time_str,
                        'consultation_mode': confirmation_details.get('consultation_mode', 'virtual'),
                        'symptoms': confirmation_details.get('symptoms', 'General consultation')
                    })
                else:
                    return "Please provide the appointment date and time to proceed with booking."
            else:
                return "Please provide the doctor name and appointment time to proceed."
        
        elif confirm in ['no', 'n', 'cancel', 'abort']:
            return "Appointment booking cancelled. Feel free to search for other available times or doctors."
        
        else:
            return "Please respond with 'yes' to confirm the booking or 'no' to cancel."
    
    except Exception as e:
        return f"Confirmation failed: {str(e)}"


# Add the new functions to your HEALTHCARE_TOOLS array
ADDITIONAL_BOOKING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "quick_book_from_available_slots",
            "description": "Quick booking when user selects a specific time slot from available times",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Name of the doctor"},
                    "selected_slot": {"type": "string", "description": "Selected time slot in format 'YYYY-MM-DD HH:MM'"},
                    "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_visit"], "description": "Type of consultation"},
                    "symptoms": {"type": "string", "description": "Reason for visit or symptoms"}
                },
                "required": ["doctor_name", "selected_slot"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_appointment_booking",
            "description": "Confirm or cancel a pending appointment booking",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation_details": {
                        "type": "object",
                        "properties": {
                            "confirm": {"type": "string", "description": "User's confirmation response (yes/no)"},
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "appointment_time": {"type": "string", "description": "Appointment time in YYYY-MM-DD HH:MM format"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_visit"]},
                            "symptoms": {"type": "string", "description": "Reason for visit"}
                        },
                        "required": ["confirm"]
                    }
                },
                "required": ["confirmation_details"]
            }
        }
    }
]