from typing import Tuple
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from django.utils.dateformat import DateFormat
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.db.models import Q

from core.models import HealthWorker, Appointment
from core.choices import HealthWorkerVerificationStatuses, AppointmentStatuses
from core.utils import string_to_datetime, normalize_datetime
from core.notifications import send_appointment_rescheduling_by_patient_notification

def check_doctor_availability(user_session, availability_request: dict) -> Tuple[bool, str]:
    """Check if a doctor is available for a specific date and time"""
    try:
        doctor_name = availability_request.get('doctor_name', '')
        date_str = availability_request.get('date', '')
        time_str = availability_request.get('time', '')
        consultation_mode = availability_request.get('consultation_mode', 'clinic_visit')
        print(f"🔍 Checking availability for: {doctor_name}")

        if not time_str or not date_str:
            return False, get_doctor_available_times(user_session, availability_request)

        if not doctor_name:
            return False, "Please provide doctor name to check availability."

        doctors = HealthWorker.filter_objects(
            is_published=True,
            verification_status=HealthWorkerVerificationStatuses.VERIFIED.value
        )
        doctors = search_health_worker_query_set(doctors, doctor_name)

        if not doctors:
            return False, f"Doctor '{doctor_name}' not found."

        doctor = doctors.first()

        try:
            start_datetime = string_to_datetime(f"{date_str} {time_str}:00.0 +0300")
            end_datetime = start_datetime + timedelta(hours=1)
        except:
            return False, "Invalid date/time format. Please use YYYY-MM-DD HH:MM format."

        is_available, availability = check_health_worker_availability(
            worker=doctor,
            start_time=start_datetime,
            end_time=end_datetime,
            mode=consultation_mode
        )

        if is_available:
            return True, f"✅ {doctor.title} {doctor.get_full_name()} is available on {date_str} at {time_str} for {consultation_mode} consultation."
        else:
            return False, f"❌ {doctor.title} {doctor.get_full_name()} is not available on {date_str} at {time_str}. Please try a different time."

    except Exception as e:
        return False, f"Availability check failed: {str(e)}"


def reschedule_appointment(user_session, reschedule_details: dict) -> str:
    """Reschedule an existing appointment"""
    try:
        appointment_identifier = reschedule_details.get('appointment_identifier', '')
        new_date = reschedule_details.get('new_date', '')
        new_time = reschedule_details.get('new_time', '')
        reason = reschedule_details.get('reason', 'Patient requested reschedule')
        
        if not all([appointment_identifier, new_date, new_time]):
            return "Please provide appointment identifier, new date, and new time to reschedule."
        
        if not user_session.active_patient_profile:
            return "Please log in to reschedule appointments."
        
        # Find the appointment
        appointments = Appointment.filter_objects(
            patient=user_session.active_patient_profile,
            status__in=[
                AppointmentStatuses.PENDING.value,
                AppointmentStatuses.BOOKING_PENDING.value
            ]
        )
        print(f"🔍 Found {appointments.count()} appointments to check")
        
        matching_appointments = []
        for apt in appointments:
            if apt.doctor and appointment_identifier.lower() in apt.doctor.get_full_name().lower():
                matching_appointments.append(apt)
        
        if not matching_appointments:
            return f"No upcoming appointment found matching '{appointment_identifier}'."
        
        if len(matching_appointments) > 1:
            return "Multiple appointments found. Please be more specific with the appointment identifier."
        
        appointment = matching_appointments[0]
        print(f"🔍 Found appointment: {appointment}")
        
        # Parse new date and time
        try:
            new_start_datetime = string_to_datetime(f"{new_date} {new_time}:00.0 +0300")
            new_end_datetime = new_start_datetime + timedelta(hours=1)
        except:
            return "Invalid date/time format. Please use YYYY-MM-DD HH:MM format."
        
        # Prepare availability request - FIX: Convert doctor object to string and handle empty encounter_mode
        availability_request = {
            'doctor_name': appointment.doctor.get_full_name(),  # FIX: Convert HealthWorker object to string
            'date': new_start_datetime.strftime('%Y-%m-%d'),
            'time': new_start_datetime.strftime('%H:%M'),
            'consultation_mode': appointment.encounter_mode or 'clinic_visit'  # FIX: Provide default if empty
        }
        print(f"🔍 Checking availability with request: {availability_request}")
        
        # Check if new time is available - FIX: Handle tuple return value correctly
        is_available, availability_message = check_doctor_availability(
            user_session,
            availability_request
        )
        
        print(f"🔍 Availability result: is_available={is_available}")
        print(f"🔍 Availability message: {availability_message}")
        
        if not is_available:
            # FIX: Complete the error message and provide helpful information
            return f"❌ {appointment.doctor.title} {appointment.doctor.get_full_name()} is not available at the new time. Please choose a different time.\n\nDetails: {availability_message}"
        
        print("🔍 Doctor is available, proceeding with reschedule")
        
        # Get the actual availability record for the database
        try:
            _, availability_record = check_health_worker_availability(
                worker=appointment.doctor,
                start_time=new_start_datetime,
                end_time=new_end_datetime,
                mode=appointment.encounter_mode or 'clinic_visit'
            )
        except Exception as e:
            print(f"🔍 Warning: Could not get availability record: {e}")
            availability_record = None
        
        # Update appointment
        appointment.previous_start_time = appointment.start_time
        appointment.start_time = new_start_datetime
        appointment.end_time = new_end_datetime
        appointment.rescheduling_reason = reason
        appointment.health_worker_availability = availability_record
        appointment.save()
        
        print("🔍 Appointment updated successfully, sending notification")
        
        # Send notification
        try:
            send_appointment_rescheduling_by_patient_notification(appointment)
            print("🔍 Notification sent successfully")
        except Exception as e:
            print(f"🔍 Warning: Notification failed: {e}")
        
        return f"✅ Appointment with {appointment.doctor.title} {appointment.doctor.get_full_name()} " \
               f"has been rescheduled to {normalize_datetime(new_start_datetime)}.\n" \
               f"Reason: {reason}"
               
    except Exception as e:
        print(f"🔍 Reschedule error: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return f"Rescheduling failed: {str(e)}"