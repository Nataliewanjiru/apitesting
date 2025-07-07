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
from .operation_functions import handle_doctor_recommendation_from_symptoms
from django.db.models import Q
import apps.healthworkers.models as HEALTHWORKERS_MODELS
import apps.core.choices as CORE_CHOICES
import apps.utilities.functions as UTILITIES_FUNCTIONS


# Define all your healthcare functions
def handle_user_registration(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, personal_details: dict):
    """Register a new user with personal details"""
    try:
        password = personal_details.get("password")
        print(password)
        user_session.create_user_with_patient(password=password)
        return f"Registration successful"
    except Exception as e:
        return f"Registration failed: {str(e)}"

def handle_user_login(user_session, credentials: dict) -> str:
    """Login an existing user"""
    try:
        # Your existing login logic
        return "Login successful!"
    except Exception as e:
        return f"Login failed: {str(e)}"


def handle_doctor_recommendation_from_symptoms_function(user_session, symptoms) -> str:
    """Find doctor recommendations based on symptoms"""
    try:
        print(f"🔍 Received symptoms: {symptoms}")
        
        processed_symptoms = []
        
        if isinstance(symptoms, dict):
            if 'symptoms' in symptoms:
                processed_symptoms = symptoms['symptoms'] if isinstance(symptoms['symptoms'], list) else [symptoms['symptoms']]
            elif 'additional_medical_information' in symptoms:
                processed_symptoms = symptoms['additional_medical_information'] if isinstance(symptoms['additional_medical_information'], list) else [symptoms['additional_medical_information']]
            else:
                # If dict doesn't have expected keys, convert values to list
                processed_symptoms = [str(v) for v in symptoms.values() if v]
        elif isinstance(symptoms, list):
            processed_symptoms = symptoms
        elif isinstance(symptoms, str):
            processed_symptoms = [symptoms] if symptoms.strip() else []
        else:
            processed_symptoms = []
        
        print(f"🔍 Processed symptoms: {processed_symptoms}")
        
        # Check if we have any symptoms
        if not processed_symptoms or all(not symptom.strip() for symptom in processed_symptoms if isinstance(symptom, str)):
            return [
                UTILITIES.create_text_message(
                    message="I couldn't find any symptoms to help you with. Please describe what you're experiencing so I can recommend the right healthcare provider.\n"
                ),
            ]
        
        # Combine all symptoms into a single string for processing
        collected_symptoms = " ".join(str(symptom) for symptom in processed_symptoms if symptom)
        
        # For now, return a placeholder response
        return [
            handle_doctor_recommendation_from_symptoms(
                user_session=user_session,
                symptoms=collected_symptoms
            )
        ]
        
    except Exception as e:
        print(f"❌ Error in handle_doctor_recommendation_from_symptoms: {str(e)}")
        return [
            UTILITIES.create_text_message(
                message="I encountered an error while searching for healthcare providers. Please try again or contact support if the issue persists.\n"
            )
        ]

def strip_common_titles(text: str) -> str:
    """Remove common prefixes like 'Dr.', 'Prof.', etc. from the search text."""
    text = text.strip().lower()
    titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
    for title in titles_to_remove:
        if text.startswith(title + ' '):
            return text[len(title):].strip()
        elif text.startswith(title):
            return text[len(title):].strip()
    return text

def search_doctors_by_criteria(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, search_criteria: dict) -> str:
    """Search for doctors by name, specialty, location, etc."""
    try:
        print("Search criteria", search_criteria)
        search_text = search_criteria.get('search_text', '')
        specialty = search_criteria.get('specialty', '')
        location = search_criteria.get('location', '')
        max_price = search_criteria.get('max_price')
        
        # Start with all verified health workers
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        print("Verified doctors", doctors)
        
        # Apply search filters
        if search_text:
            cleaned_text = strip_common_titles(search_text)
            doctors = search_health_worker_query_set(doctors, cleaned_text)

        if specialty:
            doctors = doctors.filter(
                Q(primary_specialty__name__icontains=specialty) |
                Q(sub_specialties__icontains=specialty)
            )
        
        if location:
            doctors = doctors.filter(
                Q(primary_clinic_practice__county__name__icontains=location) |
                Q(secondary_clinic_practice__county__name__icontains=location) |
                Q(other_clinic_practice__county__name__icontains=location)
            )
        
        if max_price:
            doctors = doctors.filter(
                Q(my_preferences__clinic_visit_price__lte=max_price) |
                Q(my_preferences__teleconsult_price__lte=max_price) |
                Q(my_preferences__homecare_price__lte=max_price)
            )
        
        # Order by recommendation points
        doctors = doctors.order_by('-recommendation_points')[:10]
        print("doctors", doctors)
        
        if doctors:
            doctor_list = []
            for doctor in doctors:
                doctor_info = {
                    'name': f"{doctor.title} {doctor.get_full_name()}",
                    'specialty': doctor.primary_specialty.name if doctor.primary_specialty else 'General',
                    'consultation_fee': getattr(doctor.my_preferences, 'clinic_visit_price', 'N/A'),
                    'location': getattr(doctor.primary_clinic_practice, 'county', {}).get('name', 'Multiple locations') if hasattr(doctor, 'primary_clinic_practice') and doctor.primary_clinic_practice else 'Multiple locations'
                }
                doctor_list.append(doctor_info)
            
            return f"Found {len(doctor_list)} doctors matching your criteria:\n" + \
                   "\n".join([f"• {doc['name']} - {doc['specialty']} - {doc['location']}" for doc in doctor_list])
        else:
            return "No doctors found matching your criteria. Please try adjusting your search parameters."
            
    except Exception as e:
        return f"Doctor search failed: {str(e)}"

def get_doctor_available_times(user_session, availability_request: dict) -> str:
    """Get available time slots for a doctor (when user asks 'when is doctor available')"""
    try:
        doctor_name = availability_request.get('doctor_name', '')
        date_str = availability_request.get('date', '')  
        consultation_mode = availability_request.get('consultation_mode', 'virtual')
        
        if not doctor_name:
            return "Please provide doctor name to check availability."
        
        print(f"Debug: Looking for: '{doctor_name}'")
        
        # Find the doctor
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        print(f"Debug: Total verified doctors: '{doctors.count()}'")
        
        doctors = search_health_worker_query_set(doctors, doctor_name)
        print(f"Debug: doctors after search: '{doctors.count()}'")
        
        if not doctors:
            return f"Doctor '{doctor_name}' not found."
        
        doctor = doctors.first()
        print(f"Debug: Found Doctor: '{doctor.title} {doctor.get_full_name()}'")
        
        # Check if doctor has availability records
        from apps.appointments.models import HealthWorkerAvailability
        availabilities = HealthWorkerAvailability.objects.filter(doctor=doctor)
        print(f"Debug: Doctor has {availabilities.count()} availability records")
        
        for avail in availabilities:
            print(f"Debug: Availability: {avail.start_time} to {avail.end_time}, encounter_modes: {avail.encounter_modes}")
        
        # If no specific date provided, check next 7 days
        if not date_str:
            current_time = UTILITIES_FUNCTIONS.get_current_time()
            dates_to_check = [current_time + timedelta(days=i) for i in range(7)]
            print(f"Debug: Checking next 7 days starting from '{current_time}'")
        else:
            try:
                specific_date = UTILITIES_FUNCTIONS.string_to_datetime(f"{date_str} 00:00:00.0 +0300")
                dates_to_check = [specific_date]
                print(f"Debug: Checking specific date: '{specific_date}'")
            except:
                return "Invalid date format. Please use YYYY-MM-DD format."
        
        available_slots = []
        consultation_modes_to_try = [consultation_mode, 'clinic_visit', 'virtual', 'home_visit']
        successful_mode = None
        
        # Try different consultation modes if the first one doesn't work
        for mode_to_try in consultation_modes_to_try:
            print(f"Debug: Trying consultation mode: '{mode_to_try}'")
            mode_slots = []
            
            # Check common appointment times (9 AM to 5 PM)
            for check_date in dates_to_check:
                for hour in range(9, 17):  # 9 AM to 5 PM
                    start_time = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    end_time = start_time + timedelta(hours=1)
                    
                    # Skip past times
                    if start_time < UTILITIES_FUNCTIONS.get_current_time():
                        continue
                    
                    # Check if this slot is available
                    try:
                        is_available, availability = check_health_worker_availability(
                            worker=doctor,
                            start_time=start_time,
                            end_time=end_time,
                            mode=mode_to_try
                        )
                        
                        if is_available:
                            mode_slots.append({
                                'date': start_time.strftime('%Y-%m-%d'),
                                'time': start_time.strftime('%H:%M'),
                                'day': start_time.strftime('%A'),
                                'mode': mode_to_try
                            })
                            print(f"Debug: Found available slot: '{start_time.strftime('%Y-%m-%d %H:%M')}' for mode '{mode_to_try}'")
                    except Exception as e:
                        print(f"Debug: Error checking mode '{mode_to_try}' at {start_time}: {e}")
                        continue
            
            if mode_slots:
                available_slots = mode_slots
                successful_mode = mode_to_try
                print(f"Debug: SUCCESS - Found {len(mode_slots)} slots with mode '{mode_to_try}'")
                break
            else:
                print(f"Debug: No slots found with mode '{mode_to_try}'")
        
        if not available_slots:
            # Try without mode restriction (compatibility with empty encounter_modes)
            print(f"Debug: No slots found with mode restrictions. Trying without mode for '{doctor.get_full_name()}'")
            
            for check_date in dates_to_check:
                for hour in range(9, 17):
                    start_time = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    end_time = start_time + timedelta(hours=1)
                    
                    if start_time < UTILITIES_FUNCTIONS.get_current_time():
                        continue
                    
                    try:
                        # Try with empty string mode instead of None
                        is_available, availability = check_health_worker_availability(
                            worker=doctor,
                            start_time=start_time,
                            end_time=end_time,
                            mode=""  # Use empty string instead of None
                        )
                        
                        if is_available:
                            available_slots.append({
                                'date': start_time.strftime('%Y-%m-%d'),
                                'time': start_time.strftime('%H:%M'),
                                'day': start_time.strftime('%A'),
                                'mode': 'any'
                            })
                            successful_mode = 'any mode'
                            print(f"Debug: Found fallback slot: '{start_time.strftime('%Y-%m-%d %H:%M')}'")
                    except Exception as e:
                        print(f"Debug: Error with empty mode at {start_time}: {e}")
                        
                        # Try without mode parameter completely
                        try:
                            # Try calling without mode parameter at all
                            is_available, availability = check_health_worker_availability(
                                worker=doctor,
                                start_time=start_time,
                                end_time=end_time
                            )
                            
                            if is_available:
                                available_slots.append({
                                    'date': start_time.strftime('%Y-%m-%d'),
                                    'time': start_time.strftime('%H:%M'),
                                    'day': start_time.strftime('%A'),
                                    'mode': 'any'
                                })
                                successful_mode = 'any mode'
                                print(f"Debug: Found final fallback slot: '{start_time.strftime('%Y-%m-%d %H:%M')}'")
                        except Exception as e2:
                            print(f"Debug: Final fallback failed at {start_time}: {e2}")
                            continue
        
        if not available_slots:
            print(f"Debug: FINAL RESULT - NO available slots found for '{doctor.get_full_name()}'")
            return f"❌ {doctor.title} {doctor.get_full_name()} has no available slots in the next 7 days.\n" \
                   f"This might be because:\n" \
                   f"• No availability records are set up\n" \
                   f"• All slots are already booked\n" \
                   f"• Encounter modes don't match\n" \
                   f"Please contact the doctor directly or try a different time period."
        
        print(f"Debug: FINAL RESULT - Found {len(available_slots)} available slots for '{doctor.get_full_name()}'")
        
        # Format the response
        display_mode = successful_mode if successful_mode != 'any' else 'consultation'
        result = f"📅 Available times for {doctor.title} {doctor.get_full_name()} ({display_mode}):\n\n"
        
        # Group by date
        current_date = None
        for slot in available_slots[:20]:  # Limit to first 20 slots
            if slot['date'] != current_date:
                result += f"📅 {slot['day']}, {slot['date']}:\n"
                current_date = slot['date']
            result += f"   • {slot['time']}\n"
        
        result += f"\nWould you like to book any of these available times?"
        return result
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Availability check failed for {doctor_name}: {error_details}")
        return f"Availability check failed: {str(e)}"

def check_doctor_availability(user_session, availability_request: dict) -> str:
    """Check if a doctor is available for a specific date and time"""
    try:
        doctor_name = availability_request.get('doctor_name', '')
        date_str = availability_request.get('date', '')
        time_str = availability_request.get('time', '')
        consultation_mode = availability_request.get('consultation_mode', 'clinic_visit')
        
        # If no specific time provided, redirect to available times function
        if not time_str or not date_str:
            return get_doctor_available_times(user_session, availability_request)
        
        if not doctor_name:
            return "Please provide doctor name to check availability."
        
        # Find the doctor
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        doctors = search_health_worker_query_set(doctors, doctor_name)
        
        if not doctors:
            return f"Doctor '{doctor_name}' not found."
        
        doctor = doctors.first()
        
        # Parse date and time
        try:
            # Assume format: YYYY-MM-DD HH:MM
            start_datetime = UTILITIES_FUNCTIONS.string_to_datetime(f"{date_str} {time_str}:00.0 +0300")
            end_datetime = start_datetime + timedelta(hours=1)  # Default 1-hour appointment
        except:
            return "Invalid date/time format. Please use YYYY-MM-DD HH:MM format."
        
        # Check availability
        is_available, availability = check_health_worker_availability(
            worker=doctor,
            start_time=start_datetime,
            end_time=end_datetime,
            mode=consultation_mode
        )
        
        if is_available:
            return f"✅ {doctor.title} {doctor.get_full_name()} is available on {date_str} at {time_str} for {consultation_mode} consultation."
        else:
            return f"❌ {doctor.title} {doctor.get_full_name()} is not available on {date_str} at {time_str}. Please try a different time."
            
    except Exception as e:
        return f"Availability check failed: {str(e)}"

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


def get_current_date_if_invalid(date_str: str) -> str:
    """Helper function to ensure we use current date if provided date is invalid or in the past"""
    try:
        # Parse the provided date
        provided_date = UTILITIES_FUNCTIONS.string_to_datetime(f"{date_str} 00:00:00.0 +0300")
        current_time = UTILITIES_FUNCTIONS.get_current_time()
        
        # More aggressive date correction - fix any date that's clearly wrong
        # Fix if: older than 6 months, or from wrong year (like 2023 when it's 2025)
        if (provided_date.year < current_time.year) or (provided_date < current_time - timedelta(days=180)) or (provided_date > current_time + timedelta(days=365)):
            # Use current date instead
            corrected_date = current_time.strftime('%Y-%m-%d')
            print(f"🔍 Date correction: {date_str} -> {corrected_date} (invalid/old date detected)")
            return corrected_date
        
        # If date is too far in the past (more than 1 day), use current date
        if provided_date < current_time - timedelta(days=1):
            corrected_date = current_time.strftime('%Y-%m-%d')
            print(f"🔍 Date correction: {date_str} -> {corrected_date} (past date converted to today)")
            return corrected_date
        
        return date_str
    except:
        # If date parsing fails, use current date
        corrected_date = UTILITIES_FUNCTIONS.get_current_time().strftime('%Y-%m-%d')
        print(f"🔍 Date correction: {date_str} -> {corrected_date} (parsing failed)")
        return corrected_date

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
        
        # Fix date if it's invalid or from wrong year
        corrected_date = get_current_date_if_invalid(date_str)
        if corrected_date != date_str:
            print(f"🔍 Date corrected: {date_str} -> {corrected_date}")
        date_str = corrected_date
        print(f"🔍 Using date: {date_str}")
        
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
            return f"❌ {doctor.title} {doctor.get_full_name()} is not available on {date_str} at {time_str} for {consultation_mode} consultation. Please choose a different time."
        
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


def quick_book_from_available_slots(user_session, booking_request: dict) -> str:
    """Quick booking from available time slots"""
    try:
        doctor_name = booking_request.get('doctor_name', '')
        selected_slot = booking_request.get('selected_slot', '')
        consultation_mode = booking_request.get('consultation_mode', 'virtual')
        symptoms = booking_request.get('symptoms', 'General consultation')
        
        # If no specific slot provided, get current available slots and use the first one
        if not selected_slot or selected_slot.strip() == "":
            # Get today's date and time for booking
            current_time = UTILITIES_FUNCTIONS.get_current_time()
            # Round to next hour for booking
            next_hour = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            
            date_str = next_hour.strftime('%Y-%m-%d')
            time_str = next_hour.strftime('%H:%M')
            print(f"🔍 No slot specified, using next available: {date_str} {time_str}")
        else:
            # Parse the selected slot (format: "2025-07-07 09:00" or just "09:00")
            if " " in selected_slot:
                date_str, time_str = selected_slot.split(" ", 1)
            else:
                # If only time provided, use current date
                current_time = UTILITIES_FUNCTIONS.get_current_time()
                date_str = current_time.strftime('%Y-%m-%d')
                time_str = selected_slot
                print(f"🔍 Only time provided, using current date: {date_str} {time_str}")
        
        # Ensure we have a valid date (not from the wrong year)
        date_str = get_current_date_if_invalid(date_str)
        
        booking_details = {
            'doctor_name': doctor_name,
            'date': date_str,
            'time': time_str,
            'consultation_mode': consultation_mode,
            'symptoms': symptoms
        }
        
        print(f"🔍 Quick booking with corrected details: {booking_details}")
        return book_appointment_with_doctor(user_session, booking_details)
    
    except Exception as e:
        return f"Quick booking failed: {str(e)}"

def get_my_appointments(user_session, filter_criteria: dict) -> str:
    """Get user's appointments with optional filtering"""
    try:
        status_filter = filter_criteria.get('status', 'all')  # all, upcoming, past, cancelled
        date_range = filter_criteria.get('date_range', 'all')  # all, today, week, month
        
        print(f"🔍 Getting appointments for: {user_session.active_patient_profile}")
        if not user_session.active_patient_profile:
            return "Please log in to view your appointments."
        
        # Get user's appointments
        appointments = Appointment.filter_objects(
            patient=user_session.active_patient_profile
        )
        print(f"🔍 Found {appointments.count()} total appointments")
        
        # Apply status filter - but be more flexible for "upcoming"
        if status_filter != 'all':
            if status_filter == 'upcoming':
                # Show active appointments (PENDING, BOOKING_PENDING) regardless of date
                # This way past-dated appointments that are still active will show
                appointments = appointments.filter(
                    status__in=[
                        CORE_CHOICES.AppointmentStatuses.PENDING.value,
                        CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
                    ]
                )
                print(f"🔍 After status filter (upcoming): {appointments.count()} appointments")
            elif status_filter == 'past':
                appointments = appointments.filter(
                    start_time__lt=UTILITIES_FUNCTIONS.get_current_time(),
                    status=CORE_CHOICES.AppointmentStatuses.COMPLETED.value
                )
            elif status_filter == 'cancelled':
                appointments = appointments.filter(
                    status=CORE_CHOICES.AppointmentStatuses.CANCELLED.value
                )
        
        # Apply date range filter only if status is not "upcoming" 
        # (to avoid filtering out active appointments with wrong dates)
        current_time = UTILITIES_FUNCTIONS.get_current_time()
        if date_range != 'all' and status_filter != 'upcoming':
            if date_range == 'today':
                appointments = appointments.filter(
                    start_time__date=current_time.date()
                )
            elif date_range == 'week':
                week_end = current_time + timedelta(days=7)
                appointments = appointments.filter(
                    start_time__gte=current_time,
                    start_time__lte=week_end
                )
            elif date_range == 'month':
                month_end = current_time + timedelta(days=30)
                appointments = appointments.filter(
                    start_time__gte=current_time,
                    start_time__lte=month_end
                )
        
        appointments = appointments.order_by('-start_time')[:20]  # Limit to 20 recent appointments
        print(f"🔍 Final appointment count: {appointments.count()}")
        
        if not appointments:
            return "You have no appointments matching the criteria."
        
        appointment_list = []
        for apt in appointments:
            print(f"🔍 Processing appointment: {apt.doctor.get_full_name()} on {apt.start_time} - Status: {apt.status}")
            apt_info = {
                'doctor': f"{apt.doctor.title} {apt.doctor.get_full_name()}" if apt.doctor else 'TBD',
                'date': UTILITIES_FUNCTIONS.normalize_date(apt.start_time),
                'time': UTILITIES_FUNCTIONS.normalize_time(apt.start_time),
                'status': apt.get_status_display() if hasattr(apt, 'get_status_display') else apt.status,
                'mode': apt.encounter_mode,
                'cost': f"KSh {apt.cost}" if apt.cost else 'TBD'
            }
            appointment_list.append(apt_info)
        
        result = f"Your appointments ({len(appointment_list)} found):\n\n"
        for i, apt in enumerate(appointment_list, 1):
            result += f"{i}. {apt['doctor']}\n"
            result += f"   📅 {apt['date']} at {apt['time']}\n"
            result += f"   📋 Status: {apt['status']}\n"
            result += f"   💰 Cost: {apt['cost']}\n"
            result += f"   🏥 Mode: {apt['mode']}\n\n"
        
        return result
        
    except Exception as e:
        print(f"🔍 Error in get_my_appointments: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return f"Failed to get appointments: {str(e)}"

def cancel_appointment(user_session, cancellation_details: dict) -> str:
    """Cancel an existing appointment"""
    try:
        appointment_identifier = cancellation_details.get('appointment_identifier', '')
        reason = cancellation_details.get('reason', 'Patient cancellation')
        
        if not appointment_identifier:
            return "Please provide appointment details to cancel (doctor name and date)."
        
        if not user_session.active_patient_profile:
            return "Please log in to cancel appointments."
        
        # Find the appointment (search by doctor name and date)
        appointments = Appointment.filter_objects(
            patient=user_session.active_patient_profile,
            status__in=[
                CORE_CHOICES.AppointmentStatuses.PENDING.value,
                CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
            ]
        )
        
        # Try to find appointment by doctor name in identifier
        matching_appointments = []
        for apt in appointments:
            if apt.doctor and appointment_identifier.lower() in apt.doctor.get_full_name().lower():
                matching_appointments.append(apt)
        
        if not matching_appointments:
            return f"No upcoming appointment found matching '{appointment_identifier}'. Please check the details."
        
        if len(matching_appointments) > 1:
            apt_list = "\n".join([
                f"• {apt.doctor.get_full_name()} on {UTILITIES_FUNCTIONS.normalize_datetime(apt.start_time)}"
                for apt in matching_appointments
            ])
            return f"Multiple appointments found:\n{apt_list}\n\nPlease be more specific."
        
        appointment = matching_appointments[0]
        
        # Check if appointment can be cancelled (e.g., not too close to start time)
        time_until_appointment = appointment.start_time - UTILITIES_FUNCTIONS.get_current_time()
        if time_until_appointment < timedelta(hours=2):
            return "Cannot cancel appointment less than 2 hours before the scheduled time. Please contact the doctor directly."
        
        # Cancel the appointment
        appointment.status = CORE_CHOICES.AppointmentStatuses.CANCELLED.value
        appointment.cancellation_reason = reason
        appointment.cancelled_by_patient = True
        appointment.save()
        
        # Send notification
        send_appointment_cancellation_by_patient_notification(appointment)
        
        return f"✅ Appointment with {appointment.doctor.title} {appointment.doctor.get_full_name()} " \
               f"on {UTILITIES_FUNCTIONS.normalize_datetime(appointment.start_time)} has been cancelled.\n" \
               f"Reason: {reason}"
               
    except Exception as e:
        return f"Cancellation failed: {str(e)}"

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
                CORE_CHOICES.AppointmentStatuses.PENDING.value,
                CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
            ]
        )
        
        matching_appointments = []
        for apt in appointments:
            if apt.doctor and appointment_identifier.lower() in apt.doctor.get_full_name().lower():
                matching_appointments.append(apt)
        
        if not matching_appointments:
            return f"No upcoming appointment found matching '{appointment_identifier}'."
        
        if len(matching_appointments) > 1:
            return "Multiple appointments found. Please be more specific with the appointment identifier."
        
        appointment = matching_appointments[0]
        
        # Parse new date and time
        try:
            new_start_datetime = UTILITIES_FUNCTIONS.string_to_datetime(f"{new_date} {new_time}:00.0 +0300")
            new_end_datetime = new_start_datetime + timedelta(hours=1)
        except:
            return "Invalid date/time format. Please use YYYY-MM-DD HH:MM format."
        
        # Check if new time is available
        is_available, availability = check_health_worker_availability(
            worker=appointment.doctor,
            start_time=new_start_datetime,
            end_time=new_end_datetime,
            mode=appointment.encounter_mode
        )
        
        if not is_available:
            return f"❌ {appointment.doctor.title} {appointment.doctor.get_full_name()} is not available at the new time. Please choose a different time."
        
        # Update appointment
        appointment.previous_start_time = appointment.start_time
        appointment.start_time = new_start_datetime
        appointment.end_time = new_end_datetime
        appointment.rescheduling_reason = reason
        appointment.health_worker_availability = availability
        appointment.save()
        
        # Send notification
        send_appointment_rescheduling_by_patient_notification(appointment)
        
        return f"✅ Appointment with {appointment.doctor.title} {appointment.doctor.get_full_name()} " \
               f"has been rescheduled to {UTILITIES_FUNCTIONS.normalize_datetime(new_start_datetime)}.\n" \
               f"Reason: {reason}"
               
    except Exception as e:
        return f"Rescheduling failed: {str(e)}"

def get_appointment_details(user_session, appointment_identifier: dict) -> str:
    """Get detailed information about a specific appointment"""
    try:
        identifier = appointment_identifier.get('identifier', '')
        
        if not identifier:
            return "Please provide appointment identifier (doctor name or date)."
        
        if not user_session.active_patient_profile:
            return "Please log in to view appointment details."
        
        # Find the appointment
        appointments = Appointment.filter_objects(
            patient=user_session.active_patient_profile
        ).order_by('-start_time')
        
        matching_appointments = []
        for apt in appointments:
            if (apt.doctor and identifier.lower() in apt.doctor.get_full_name().lower()) or \
               identifier in UTILITIES_FUNCTIONS.normalize_datetime(apt.start_time):
                matching_appointments.append(apt)
        
        if not matching_appointments:
            return f"No appointment found matching '{identifier}'."
        
        if len(matching_appointments) > 1:
            apt_list = "\n".join([
                f"• {apt.doctor.get_full_name()} on {UTILITIES_FUNCTIONS.normalize_datetime(apt.start_time)}"
                for apt in matching_appointments[:5]
            ])
            return f"Multiple appointments found:\n{apt_list}\n\nPlease be more specific."
        
        appointment = matching_appointments[0]
        
        # Format detailed information
        details = f"📋 Appointment Details\n\n"
        details += f"👨‍⚕️ Doctor: {appointment.doctor.title} {appointment.doctor.get_full_name()}\n"
        details += f"🏥 Specialty: {appointment.doctor.primary_specialty.name if appointment.doctor.primary_specialty else 'General'}\n"
        details += f"📅 Date & Time: {UTILITIES_FUNCTIONS.normalize_datetime(appointment.start_time)} to {UTILITIES_FUNCTIONS.normalize_time(appointment.end_time)}\n"
        details += f"📍 Mode: {appointment.encounter_mode}\n"
        details += f"📋 Status: {appointment.get_status_display() if hasattr(appointment, 'get_status_display') else appointment.status}\n"
        details += f"💰 Cost: KSh {appointment.cost}\n"
        details += f"💳 Booking Fee: KSh {appointment.booking_fee}\n"
        
        if appointment.symptoms_description:
            details += f"🩺 Symptoms: {appointment.symptoms_description}\n"
        
        if appointment.organization:
            details += f"🏢 Organization: {appointment.organization.name}\n"
        
        if appointment.cancellation_reason:
            details += f"❌ Cancellation Reason: {appointment.cancellation_reason}\n"
        
        if appointment.rescheduling_reason:
            details += f"🔄 Rescheduling Reason: {appointment.rescheduling_reason}\n"
        
        return details
        
    except Exception as e:
        return f"Failed to get appointment details: {str(e)}"

def book_appointment_today(user_session, booking_request: dict) -> str:
    """Book an appointment for today or next available date with just time specified"""
    try:
        doctor_name = booking_request.get('doctor_name', '')
        time_str = booking_request.get('time', '')
        consultation_mode = booking_request.get('consultation_mode', 'virtual')
        symptoms = booking_request.get('symptoms', 'General consultation')
        
        if not doctor_name or not time_str:
            return "Please provide doctor name and time to book appointment."
        
        # Use current date
        current_time = UTILITIES_FUNCTIONS.get_current_time()
        date_str = current_time.strftime('%Y-%m-%d')
        
        # Parse time - handle various formats
        try:
            # Convert common time formats
            time_str = time_str.lower().strip()
            if 'am' in time_str or 'pm' in time_str:
                # Convert 12-hour to 24-hour format
                import datetime
                time_obj = datetime.datetime.strptime(time_str.replace(' ', ''), '%I%p')
                time_str = time_obj.strftime('%H:%M')
            elif ':' not in time_str:
                # Add :00 if just hour provided
                if len(time_str) <= 2:
                    time_str = f"{time_str.zfill(2)}:00"
        except:
            pass  # Use as-is if parsing fails
        
        booking_details = {
            'doctor_name': doctor_name,
            'date': date_str,
            'time': time_str,
            'consultation_mode': consultation_mode,
            'symptoms': symptoms
        }
        
        print(f"🔍 Booking for today with details: {booking_details}")
        return book_appointment_with_doctor(user_session, booking_details)
    
    except Exception as e:
        return f"Booking for today failed: {str(e)}"

def get_general_information(user_session, query: dict) -> str:
    """Get general information about healthcare services"""
    try:
        topic = query.get('topic', '').lower()
        
        if 'pricing' in topic or 'cost' in topic or 'fee' in topic:
            return ("💰 Healthcare Pricing Information:\n\n"
                   "• Clinic Visit: KSh 1,000 - 5,000 depending on specialty\n"
                   "• Virtual Consultation: KSh 800 - 3,000\n"
                   "• Home Visit: KSh 2,000 - 10,000 plus transport\n"
                   "• Booking Fee: KSh 50 (standard)\n\n"
                   "Prices may vary by doctor and location. Contact specific doctors for exact pricing.")
        
        elif 'insurance' in topic:
            return ("🛡️ Insurance Information:\n\n"
                   "We accept most major insurance providers including:\n"
                   "• NHIF\n"
                   "• AAR\n"
                   "• Jubilee\n"
                   "• Madison\n"
                   "• CIC\n\n"
                   "Please confirm coverage with your provider before booking.")
        
        elif 'hours' in topic or 'time' in topic:
            return ("🕐 Service Hours:\n\n"
                   "• Platform Available: 24/7\n"
                   "• Doctor Consultations: Typically 8:00 AM - 8:00 PM\n"
                   "• Emergency Support: Available through partner clinics\n\n"
                   "Individual doctor schedules may vary.")
        
        elif 'service' in topic or 'what' in topic:
            return ("🏥 Our Healthcare Services:\n\n"
                   "• Doctor Consultations (Virtual & In-Person)\n"
                   "• Specialist Referrals\n"
                   "• Home Visits\n"
                   "• Health Screening\n"
                   "• Prescription Services\n"
                   "• Lab Test Booking\n"
                   "• Health Records Management\n\n"
                   "Ask me about any specific service!")
        
        else:
            return ("ℹ️ General Healthcare Information:\n\n"
                   "I can help you with:\n"
                   "• Finding doctors by specialty or symptoms\n"
                   "• Booking appointments\n"
                   "• Checking doctor availability\n"
                   "• Managing your appointments\n"
                   "• Getting pricing information\n"
                   "• Understanding our services\n\n"
                   "What would you like to know more about?")
        
    except Exception as e:
        return f"Failed to get information: {str(e)}"


# Function definitions for OpenAI
HEALTHCARE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "handle_user_registration",
            "description": "Register a new user when they want to create an account",
            "parameters": {
                "type": "object",
                "properties": {
                    "personal_details": {
                        "type": "object",
                        "properties": {
                            "password": {"type": "string"}
                        },
                        "required": ["password"]
                    }
                },
                "required": ["personal_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_user_login",
            "description": "Login an existing user",
            "parameters": {
                "type": "object",
                "properties": {
                    "credentials": {
                        "type": "object",
                        "properties": {
                            "password": {"type": "string"}
                        },
                        "required": ["password"]
                    }
                },
                "required": ["credentials"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_doctor_recommendation_from_symptoms_function",
            "description": "Find and recommend doctors based on patient symptoms and medical conditions",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "string",
                        "description": "Combined symptoms and medical information from the patient"
                    }
                },
                "required": ["symptoms"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_doctors_by_criteria",
            "description": "Search for doctors by name, specialty, location, or other criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_criteria": {
                        "type": "object",
                        "properties": {
                            "search_text": {"type": "string", "description": "Doctor name or general search text"},
                            "specialty": {"type": "string", "description": "Medical specialty (e.g., cardiology, dermatology)"},
                            "location": {"type": "string", "description": "Preferred location or county"},
                            "max_price": {"type": "number", "description": "Maximum consultation fee"}
                        }
                    }
                },
                "required": ["search_criteria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_available_times",
            "description": "Get available time slots for a doctor when user asks 'when is doctor available' or wants to see available times",
            "parameters": {
                "type": "object",
                "properties": {
                    "availability_request": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "date": {"type": "string", "description": "Optional specific date in YYYY-MM-DD format. If not provided, checks next 7 days"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"], "description": "Type of consultation, defaults to virtual"}
                        },
                        "required": ["doctor_name"]
                    }
                },
                "required": ["availability_request"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_doctor_availability",
            "description": "Check if a specific doctor is available at a particular date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "availability_request": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "time": {"type": "string", "description": "Time in HH:MM format"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"]}
                        },
                        "required": ["doctor_name", "date", "time"]
                    }
                },
                "required": ["availability_request"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment_with_doctor",
            "description": "Book an appointment with a specific doctor",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_details": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "time": {"type": "string", "description": "Time in HH:MM format"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"]},
                            "symptoms": {"type": "string", "description": "Brief description of symptoms or reason for visit"}
                        },
                        "required": ["doctor_name", "date", "time"]
                    }
                },
                "required": ["booking_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "quick_book_from_available_slots",
            "description": "Quick booking when user selects a specific time slot from available times",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_request": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "selected_slot": {"type": "string", "description": "Selected time slot in format 'YYYY-MM-DD HH:MM'"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_visit"], "description": "Type of consultation"},
                            "symptoms": {"type": "string", "description": "Reason for visit or symptoms"}
                        },
                        "required": ["doctor_name", "selected_slot"]
                    }
                },
                "required": ["booking_request"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment_today",
            "description": "Book an appointment for today/current date when user specifies just time (e.g. '10 AM', '14:00')",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_request": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "time": {"type": "string", "description": "Time in any format (10 AM, 14:00, 2 PM, etc.)"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"], "description": "Type of consultation"},
                            "symptoms": {"type": "string", "description": "Reason for visit or symptoms"}
                        },
                        "required": ["doctor_name", "time"]
                    }
                },
                "required": ["booking_request"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_appointments",
            "description": "Get list of user's appointments with optional filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_criteria": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["all", "upcoming", "past", "cancelled"], "description": "Filter by appointment status"},
                            "date_range": {"type": "string", "enum": ["all", "today", "week", "month"], "description": "Filter by date range"}
                        }
                    }
                },
                "required": ["filter_criteria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "cancellation_details": {
                        "type": "object",
                        "properties": {
                            "appointment_identifier": {"type": "string", "description": "Doctor name or appointment details to identify the appointment"},
                            "reason": {"type": "string", "description": "Reason for cancellation"}
                        },
                        "required": ["appointment_identifier"]
                    }
                },
                "required": ["cancellation_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Reschedule an existing appointment to a new date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "reschedule_details": {
                        "type": "object",
                        "properties": {
                            "appointment_identifier": {"type": "string", "description": "Doctor name or appointment details to identify the appointment"},
                            "new_date": {"type": "string", "description": "New date in YYYY-MM-DD format"},
                            "new_time": {"type": "string", "description": "New time in HH:MM format"},
                            "reason": {"type": "string", "description": "Reason for rescheduling"}
                        },
                        "required": ["appointment_identifier", "new_date", "new_time"]
                    }
                },
                "required": ["reschedule_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_appointment_details",
            "description": "Get detailed information about a specific appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_identifier": {
                        "type": "object",
                        "properties": {
                            "identifier": {"type": "string", "description": "Doctor name, date, or other identifying information"}
                        },
                        "required": ["identifier"]
                    }
                },
                "required": ["appointment_identifier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_general_information",
            "description": "Get general information about healthcare services, pricing, insurance, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "Topic to get information about (pricing, insurance, services, hours, etc.)"}
                        },
                        "required": ["topic"]
                    }
                },
                "required": ["query"]
            }
        }
    }
]