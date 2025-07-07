import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI
import apps.whatsappplugin1.models as WHATSAPP_PLUGIN1
import apps.whatsappplugin1.utilities as UTILITIES
import apps.healthworkers.models as HEALTHWORKERS_MODELS
import apps.organizations.models as ORGANIZATIONS_MODELS
import apps.core.choices as CORE_CHOICES
import apps.utilities.functions as UTILITIES_FUNCTIONS
from django.db.models import Q

# Import your existing appointment functions
from .appointment_functions import (
    check_health_worker_availability,
    get_health_worker_appointment_cost,
    send_appointment_creation_notifications,
    send_appointment_cancellation_by_patient_notification,
    send_appointment_rescheduling_by_patient_notification,
    generate_booking_bill_for_appointment
)

# Import the FIXED search function that handles doctor titles properly
def search_health_worker_query_set(query_set, search_text):
    """Enhanced search that handles doctor titles and uses OR logic for better matching"""
    
    # Clean up search text and remove common titles
    cleaned_search = search_text.strip().lower()
    
    # Remove common doctor titles
    titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
    for title in titles_to_remove:
        if cleaned_search.startswith(title + ' '):
            cleaned_search = cleaned_search[len(title):].strip()
        elif cleaned_search.startswith(title):
            cleaned_search = cleaned_search[len(title):].strip()
    
    # If after removing titles there's nothing left, return all
    if not cleaned_search:
        return query_set
    
    # Split into search terms
    search_items = list(
        filter(
            lambda x: len(x) > 0,
            map(lambda x: x.strip(), cleaned_search.split(" ")),
        )
    )
    
    if not search_items:
        return query_set
    
    # Build search query with OR logic for all terms and fields
    search_query = None
    
    for search_item in search_items:
        term_query = (
            Q(first_name__icontains=search_item) |
            Q(last_name__icontains=search_item) |
            Q(middle_name__icontains=search_item) |
            Q(primary_specialty__name__icontains=search_item)
        )
        
        # Combine with previous terms using OR (any term can match)
        if search_query is None:
            search_query = term_query
        else:
            search_query = search_query | term_query
    
    return query_set.filter(search_query)
from .operation_functions import handle_doctor_recommendation_from_symptoms
from .models import Appointment, HealthWorkerAvailability

# Define all your healthcare functions
def handle_user_registration(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, personal_details: dict):
    """Register a new user"""
    try:
        password = personal_details.get('password')
        # Your existing registration logic here
        return "User registration initiated successfully"
    except Exception as e:
        return f"Registration failed: {str(e)}"

def handle_user_login(user_session, credentials: dict) -> str:
    """Login an existing user"""
    try:
        password = credentials.get('password')
        # Your existing login logic here
        return "Login successful"
    except Exception as e:
        return f"Login failed: {str(e)}"

def handle_doctor_recommendation_from_symptoms_function(user_session, symptoms) -> str:
    """Find and recommend doctors based on patient symptoms"""
    try:
        # Use your existing fixed function
        return handle_doctor_recommendation_from_symptoms(user_session, symptoms)
    except Exception as e:
        return f"Doctor search failed: {str(e)}"

def search_doctors_by_criteria(user_session, search_criteria: dict) -> str:
    """Search for doctors by name, specialty, location, etc."""
    try:
        search_text = search_criteria.get('search_text', '')
        specialty = search_criteria.get('specialty', '')
        location = search_criteria.get('location', '')
        consultation_mode = search_criteria.get('consultation_mode', '')
        max_price = search_criteria.get('max_price')
        
        # Start with all verified health workers
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        
        # Apply search filters
        if search_text:
            doctors = search_health_worker_query_set(doctors, search_text)
        
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
        
        if doctors:
            doctor_list = []
            for doctor in doctors:
                doctor_info = {
                    'name': f"{doctor.title} {doctor.get_full_name()}",
                    'specialty': doctor.primary_specialty.name if doctor.primary_specialty else 'General',
                    'rating': getattr(doctor, 'rating', 'N/A'),
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
        date_str = availability_request.get('date', '')  # Optional - can be empty
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

def book_appointment_with_doctor(user_session, booking_details: dict) -> str:
    """Book an appointment with a specific doctor"""
    try:
        doctor_name = booking_details.get('doctor_name', '')
        date_str = booking_details.get('date', '')
        time_str = booking_details.get('time', '')
        consultation_mode = booking_details.get('consultation_mode', 'clinic_visit')
        symptoms = booking_details.get('symptoms', '')
        
        if not doctor_name or not date_str or not time_str:
            return "Please provide doctor name, date, and time to book appointment."
        
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
            start_datetime = UTILITIES_FUNCTIONS.string_to_datetime(f"{date_str} {time_str}:00.0 +0300")
            end_datetime = start_datetime + timedelta(hours=1)
        except:
            return "Invalid date/time format. Please use YYYY-MM-DD HH:MM format."
        
        # Check availability
        is_available, availability = check_health_worker_availability(
            worker=doctor,
            start_time=start_datetime,
            end_time=end_datetime,
            mode=consultation_mode
        )
        
        if not is_available:
            return f"❌ {doctor.title} {doctor.get_full_name()} is not available at that time. Please choose a different time."
        
        # Calculate cost
        total_cost, billing_details = get_health_worker_appointment_cost(
            doctor=doctor,
            encounter_mode=consultation_mode
        )
        
        # Create appointment
        appointment = Appointment(
            patient=user_session.active_patient_profile,
            doctor=doctor,
            start_time=start_datetime,
            end_time=end_datetime,
            encounter_mode=consultation_mode,
            status=CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value,
            cost=total_cost,
            billing_details=billing_details,
            booking_fee=50.0,  # Default booking fee
            symptoms_description=symptoms,
            health_worker_availability=availability
        )
        appointment.save()
        
        # Send notifications
        send_appointment_creation_notifications(appointment, payment_completed=False)
        
        return f"✅ Appointment booked with {doctor.title} {doctor.get_full_name()} on {date_str} at {time_str}.\n" \
               f"Consultation mode: {consultation_mode}\n" \
               f"Total cost: KSh {total_cost}\n" \
               f"Booking fee: KSh 50\n" \
               f"Please complete payment to confirm your appointment."
               
    except Exception as e:
        return f"Booking failed: {str(e)}"

def get_my_appointments(user_session, filter_criteria: dict) -> str:
    """Get user's appointments with optional filtering"""
    try:
        status_filter = filter_criteria.get('status', 'all')  # all, upcoming, past, cancelled
        date_range = filter_criteria.get('date_range', 'all')  # all, today, week, month
        
        if not user_session.active_patient_profile:
            return "Please log in to view your appointments."
        
        # Get user's appointments
        appointments = Appointment.filter_objects(
            patient=user_session.active_patient_profile
        )
        
        # Apply status filter
        if status_filter != 'all':
            if status_filter == 'upcoming':
                appointments = appointments.filter(
                    start_time__gte=UTILITIES_FUNCTIONS.get_current_time(),
                    status__in=[
                        CORE_CHOICES.AppointmentStatuses.PENDING.value,
                        CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
                    ]
                )
            elif status_filter == 'past':
                appointments = appointments.filter(
                    start_time__lt=UTILITIES_FUNCTIONS.get_current_time(),
                    status=CORE_CHOICES.AppointmentStatuses.COMPLETED.value
                )
            elif status_filter == 'cancelled':
                appointments = appointments.filter(
                    status=CORE_CHOICES.AppointmentStatuses.CANCELLED.value
                )
        
        # Apply date range filter
        current_time = UTILITIES_FUNCTIONS.get_current_time()
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
        
        if not appointments:
            return "You have no appointments matching the criteria."
        
        appointment_list = []
        for apt in appointments:
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

def get_general_information(query: dict) -> str:
    """Get general information about healthcare services"""
    try:
        topic = query.get('topic', '').lower()
        
        if 'pricing' in topic or 'cost' in topic or 'fee' in topic:
            return "Our pricing varies by service:\n" \
                   "• Consultation fees: KSh 500 - 3,000\n" \
                   "• Booking fee: KSh 50\n" \
                   "• Home visits: Additional KSh 500\n" \
                   "• Virtual consultations: Usually 20% less than clinic visits\n" \
                   "Contact specific doctors for exact pricing."
        
        elif 'insurance' in topic:
            return "We work with several insurance providers including:\n" \
                   "• NHIF\n• AAR Insurance\n• Jubilee Insurance\n• Madison Insurance\n" \
                   "Please confirm with your chosen healthcare provider about insurance acceptance."
        
        elif 'service' in topic or 'what' in topic:
            return "Our platform offers:\n" \
                   "• Doctor recommendations based on symptoms\n" \
                   "• Appointment booking with verified healthcare providers\n" \
                   "• Virtual consultations via video call\n" \
                   "• In-clinic appointments\n" \
                   "• Home care services\n" \
                   "• Appointment management (reschedule, cancel)\n" \
                   "• Medical records management"
        
        elif 'hour' in topic or 'time' in topic or 'available' in topic:
            return "Our platform is available 24/7 for:\n" \
                   "• Browsing doctors\n• Booking appointments\n• Managing existing appointments\n\n" \
                   "Healthcare provider availability varies. Most doctors are available:\n" \
                   "• Weekdays: 8 AM - 6 PM\n• Saturdays: 9 AM - 4 PM\n• Sundays: Limited availability\n" \
                   "Emergency services are available 24/7."
        
        else:
            return "I can help you with:\n" \
                   "• Finding doctors based on symptoms\n" \
                   "• Booking appointments\n" \
                   "• Managing existing appointments\n" \
                   "• Information about pricing and services\n" \
                   "• Insurance and payment options\n\n" \
                   "What specific information would you like to know?"
                   
    except Exception as e:
        return f"Failed to get information: {str(e)}"

# Updated function definitions for OpenAI
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
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"]},
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
            "description": "Check if a specific doctor is available at a particular date and time (only use when user provides specific time)",
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