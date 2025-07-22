from datetime import timedelta
import json
from typing import Optional, List, Dict, Any
from apps.appointments.functions import check_health_worker_availability, get_health_worker_appointment_cost, send_appointment_cancellation_by_patient_notification
from apps.appointments.models import Appointment, HealthWorkerAvailability
from apps.healthworkers.functions import get_health_worker_recommendation_from_symptoms, search_health_worker_query_set
from apps.whatsappplugin1.handlers.functions import handle_create_appointment_request
from apps.whatsappplugin1.logging import log_error
from openai import OpenAI
import apps.whatsappplugin1.models as WHATSAPP_PLUGIN1
import apps.whatsappplugin1.utilities as UTILITIES
from .operation_functions import handle_doctor_recommendation_from_symptoms
from django.db.models import Q
import apps.healthworkers.models as HEALTHWORKERS_MODELS
import apps.core.choices as CORE_CHOICES
import apps.utilities.functions as UTILITIES_FUNCTIONS
import apps.patients.models as PATIENTS
import apps.whatsappplugin1.messages.patients as PATIENTS_MESSAGES
import apps.whatsappplugin1.ai_functions as AI_FUNCTIONS


def handle_onboarding_function(user_session):
    """Handle user onboarding process"""
    # This would contain your onboarding logic
    return "Welcome to Rastuc! Let's get you set up."


def handle_user_registration(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, personal_details):
    """Handle user registration"""
    try:
        password = personal_details.get('password')
        first_name = personal_details.get('first_name', '')
        last_name = personal_details.get('last_name', '')
        middle_name = personal_details.get('middle_name', '')
        age = personal_details.get('age')
        gender = personal_details.get('gender')
        
        # Update session with user details
        user_session.user_first_name = first_name
        user_session.user_last_name = last_name
        user_session.user_middle_name = middle_name
        if age:
            user_session.user_age = float(age)
        user_session.user_sex = gender
        
        # Create user and patient
        user, patient = user_session.create_user_with_patient(password=password)
        user_session.active_patient_profile = patient
        user_session.save()
        
        return f"Welcome {first_name}! Your account has been created successfully."
        
    except Exception as e:
        return f"Registration failed: {str(e)}"


def handle_user_login(user_session, credentials: dict) -> str:
    """Handle user login"""
    try:
        password = credentials.get('password')
        # Add your login logic here
        return "Login successful! How can I help you today?"
    except Exception as e:
        return f"Login failed: {str(e)}"


def handle_profile_listing(user_session) -> str:
    """List user profiles"""
    # Add your profile listing logic here
    return "Here are your available profiles..."


def handle_profile_selection(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, selection_number: int):
    """Handle profile selection"""
    # Add your profile selection logic here
    return f"Profile {selection_number} selected successfully."


def handle_doctor_recommendation_from_symptoms_function(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, symptoms: str):
    """
    Finds and displays doctor recommendations based on a combined string of patient symptoms.
    This function expects symptoms to be provided as a single string.
    """
    try:
        print("📥 Entered doctor recommendation function")
        if not user_session.is_an_existing_user or not user_session.active_patient_profile:
            onboarding_msg = handle_onboarding_function(user_session)
            return onboarding_msg

        print(f"🔍 Received symptoms as string: '{symptoms}'")

        # Store symptoms in session context
        user_session.set_session_context_value('symptoms', symptoms)

        # Directly use the symptoms string as it comes from the AI, as per the schema
        collected_symptoms_str = symptoms.strip()

        if not collected_symptoms_str:
            return [
                UTILITIES.create_text_message(
                    message="I couldn't find any symptoms to help you with. Please describe what you're experiencing so I can recommend the right healthcare provider."
                ),
            ]

        # Now, call the external function to get recommendations
        plugin_settings = WHATSAPP_PLUGIN1.WhatsappPlugin1Settings.get_instance()
        print("🔍 Getting doctor recommendation from symptoms using HEALTHWORKERS_FUNCTIONS...")

        (
            recommendation_result,
            query, # This variable is not used after assignment, consider removing if truly unused
            error,
        ) = get_health_worker_recommendation_from_symptoms(
            symptoms=collected_symptoms_str,
        )

        print("Error from get_health_worker_recommendation_from_symptoms:", error)
        print("Recommendation response received.")

        if error:
            # Handle API errors
            return [
                UTILITIES.create_text_message(
                    message="An error occurred finding a recommendation. Please try again later."
                ),
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else f"Please log in"
            ]

        recommendations = recommendation_result.get("recommended_health_workers", None)
        doctors = [t for t in recommendations.items] if recommendations and hasattr(recommendations, 'items') else []
        alternatives = recommendation_result.get("alternative_health_workers", None)
        alternative_doctors = [t for t in alternatives.items] if alternatives and hasattr(alternatives, 'items') else []

        # Store recommended doctor IDs in the session
        user_session.previous_ai_doctor_recommendations = [
            *[x.id for x in doctors],
            *[t.id for t in alternative_doctors],
        ]
        user_session.save()

        # Determine message display type based on plugin settings
        if plugin_settings.list_display_type == WHATSAPP_PLUGIN1.ListDisplayTypes.DROPDOWN_MESSAGE.value:
            message_body = recommendation_result.get("reasoning", "")
            if not message_body:
                message_body = "Here are the recommended doctors you could see.\n"
            if not doctors:
                message_body = "Sorry, no doctors match your query."

            return [
                message_body,
                PATIENTS_MESSAGES.doctors_recommendation_results(
                    doctors=doctors, list_offset=0
                ),
            ]
        else:
            user_session.previous_ai_doctor_recommendations_viewing_offset = 0
            message_body = recommendation_result.get("reasoning", "")
            if not message_body:
                message_body = "Here are the recommended doctors you could see.\n"

            return [
                message_body,
                PATIENTS_MESSAGES.my_doctors_text_only_message_v3(
                    doctors=doctors, list_offset=0
                ),
            ]

    except Exception as e:
        print(f"❌ Error in handle_doctor_recommendation_from_symptoms_function: {str(e)}")
        return [
            UTILITIES.create_text_message(
                message=f"I encountered an unexpected issue while trying to find doctor recommendations for your symptoms. Please try again later."
            ),
        ]

def doctor_profile(doctor):
    """
    Shows details and options regarding a selected HCW
    :param doctor:
    :return:
    """
    display_text = (
        f"{doctor.primary_specialty.name if doctor.primary_specialty else ''}\n\n"
    )

    preferences = doctor.my_preferences
    if preferences.offers_clinic_visit_care:
        display_text += f"Clinic visit consult price {preferences.clinic_visit_price} {preferences.currency}\n"
    if preferences.offers_teleconsult_care:
        display_text += f"Teleconsult price {preferences.teleconsult_price} {preferences.currency}\n"
    if preferences.offers_home_care:
        display_text += (
            f"Home care price {preferences.homecare_price} {preferences.currency}\n"
        )
    display_text += "\n"

    clinic_practice = (
        doctor.primary_clinic_practice
        or doctor.secondary_clinic_practice
        or doctor.other_clinic_practice
    )
    if clinic_practice:
        location_display = f"{clinic_practice.address or ''} {clinic_practice.county.name if clinic_practice.county else ''}".strip()
        if location_display:
            display_text += location_display
            display_text += "\n\n"

    if doctor.bio:
        display_text += f"{doctor.bio}"
    
    print(display_text)
    return["Here is the availability",display_text ,"Would you like to book the doctor"]

def search_doctors_by_criteria(user_session:WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, search_text: str):
    """Search for doctors by name, specialty"""
    try:
        print("Search text",search_text)
        
        # Store search criteria in session context
        user_session.set_session_context_value('search_criteria', search_text)
        
        # Start with all verified health workers
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        print("Verified doctors",doctors)
        
        doctors = search_health_worker_query_set(doctors, search_text)
        print("doctors",doctors)
        
        if doctors:
             user_session.previous_doctor_search_results = [d.id for d in doctors]
             user_session.previous_doctor_search_results_viewing_offset = 0
             return[ "Please choose your preferred doctor by entering a number so as to see more about the doctor",PATIENTS_MESSAGES.doctors_search_results(
                 doctors=doctors, list_offset=0
             )]
        else:
            return "No doctors found matching your criteria. Please try again."
            
    except Exception as e:
        return f"Doctor search failed: {str(e)}"
    
def doctor_availability(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, text: str):
    """Handles doctor availability by index or name input."""
    try:
        # Try to interpret the text as a number (e.g., "1")
        try:
            index = int(text) - 1
            doctors = user_session.get_previous_ai_doctor_recommendations()
            if index < 0 or index >= len(doctors):
                return "Invalid selection. Please choose a valid number from the list."
            doctor = doctors[index]
            return PATIENTS_MESSAGES.create_doctor_profile_message(
                user_session=user_session, doctor=doctor
            )

        except ValueError:
            doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
                is_published=True,
                verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
            )
            matched_doctors = search_health_worker_query_set(doctors, text)
            print(matched_doctors)
            if not matched_doctors:
                return f"Sorry, I couldn't find a doctor named '{text}'. Please try again or use the number."

            # Take the first matching doctor
            doctor = matched_doctors[0]
            print(doctor)
            print(["Here is the availability",doctor_profile(
                doctor=doctor
             )])
            return ["Here is the availability",doctor_profile(
                doctor=doctor
            )]

    except Exception as e:
        log_error(error_message=f"{e}")
        return "It seems there was an error finding the doctor. Please try again later."

def create_confirmed_appointment(doctor, patient_user, appointment_start, appointment_end, mode, organization=None, availability_record=None):
    """Create and confirm an appointment"""
    try:
        print(f"🔍 Creating confirmed appointment for {doctor.get_full_name()}")
    
        normalized_mode_key = mode.strip().upper().replace(" ", "_")

        # Safely map string to enum value
        ENCOUNTER_MODE_MAP = {
            "VIRTUAL": CORE_CHOICES.EncounterModes.VIRTUAL.value,
            "CLINIC_VISIT": CORE_CHOICES.EncounterModes.CLINIC_VISIT.value,
            "HOME_CARE": CORE_CHOICES.EncounterModes.HOME_CARE.value,
        }
        encounter_mode = ENCOUNTER_MODE_MAP.get(normalized_mode_key)
        print(encounter_mode)
        # Get cost information
        total_cost, breakdown = get_health_worker_appointment_cost(
            doctor=doctor,
            encounter_mode=encounter_mode,
            organization=organization,
        )
        
        # Get patient object
        if patient_user.active_patient_profile:
            patient = patient_user.active_patient_profile
        else:
            print("No patient profile found. Creating new one.")
            patient = patient_user.create_patient()
            patient_user.active_patient_profile = patient
            patient_user.save()

        # Create appointment
        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            start_time=appointment_start,
            end_time=appointment_end,
            encounter_mode=mode,
            status=CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value, 
            created_by_patient=True,
            cost=total_cost,
            booking_fee=50,  
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


def create_appointment_with_doctor(user_session:WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, booking_details: dict) -> str:
    """Book an appointment with a specific doctor"""
    try:
        if not user_session.is_an_existing_user or not user_session.active_patient_profile:
           onboarding_msg = handle_onboarding_function(user_session)
           return onboarding_msg
        print(f"🔍 Booking appointment with details: {booking_details}")

        # Store booking details in session context
        user_session.set_session_context_value('booking_details', booking_details)

        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
        is_published=True,
        verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
           )
        matched_doctors = search_health_worker_query_set(doctors, booking_details.get("doctor_name"))
        doctor = matched_doctors[0]
        from .ai_functions import doctor_booking_months_text_message
        return ["Choose your desired month",doctor_booking_months_text_message(
            doctor=doctor, mode=booking_details.get("consultation_mode")
        )]
              
    except Exception as e:
        print(f"Booking failed: Please choose the consultation modes listed or contact support. Error: {str(e)}")
        return f"Booking failed: Please choose the consultation modes listed or contact support. Error: {str(e)}"



def appointment_date(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, selected_month_and_year: str):
    try:
        print(selected_month_and_year)
        user = user_session.linked_user
        if not user:
            return UTILITIES.create_text_message(
                message="It seems your user session is not properly linked. Please try logging in."
            )
            
        parts = selected_month_and_year.strip().split()

        if len(parts) != 2:
            raise ValueError("Invalid month and year format. Please reply with 'Month Year' (e.g., 'July 2025').")

        month_name_input = parts[0].lower()
        year_input = parts[1]

        selected_month_num = None
        from .ai_functions import MONTHS_OF_THE_YEAR 
        for full_name, short_name, num in MONTHS_OF_THE_YEAR:
            if month_name_input == full_name.lower() or month_name_input == short_name.lower():
                selected_month_num = num
                break
        
        if selected_month_num is None:
            raise ValueError(f"Could not understand month '{parts[0]}'. Please use full month name.")
            
        try:
            selected_year = int(year_input)
        except ValueError:
            raise ValueError("Invalid year format. Please provide a valid year (e.g., '2025').")

        print(f"Parsed Month: {selected_month_num}, Year: {selected_year}")

        user_session.doctor_booking_month_selection = selected_month_num
        user_session.doctor_booking_year_selection = selected_year

        return f"Enter the date for the selected month"
    except ValueError as ve:
        # Specific error handling for parsing issues
        error_message = f"I apologize, {ve}. Could you please try again?"
        print(f"Booking failed (ValueError): {error_message}")
        return UTILITIES.create_text_message(message=error_message)
    except Exception as e:
        # General error handling for unexpected issues
        error_message = f"It seems there was an unexpected issue selecting the month. Error: {str(e)}. Please contact support or try again."
        print(f"Booking failed (General Exception): {error_message}")
        return UTILITIES.create_text_message(message=error_message)


def appointment_day(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,booking_details: dict):
 try:
    user = user_session.linked_user
    print(booking_details)
    if not user:
        return UTILITIES.create_text_message(
            message="It seems your user session is not properly linked. Please try logging in."
        )
    doctor=booking_details.get("doctor_name")
    mode=booking_details.get("consultation_mode")
    month=user_session.doctor_booking_month_selection
    print(month)
    year=user_session.doctor_booking_year_selection 
    print(year)
    day=int(booking_details.get("day"))
    doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
    is_published=True,
    verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
    )
    matched_doctor = search_health_worker_query_set(doctors, doctor)[0]
    from .ai_functions import doctor_booking_times_text_message
    return doctor_booking_times_text_message(doctor=matched_doctor,mode=mode,year=year,month=month,day=day)

 except Exception as e:
     # General error handling for unexpected issues
     error_message = f"It seems there was an unexpected issue selecting the day. Error: {str(e)}. Please contact support or try again."
     print(f"Booking failed (General Exception): {error_message}")
     return UTILITIES.create_text_message(message=error_message)




def handle_payment_time_selection(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, payment_choice: str):
    """
    Handles the user's choice to pay now or later for the consultation fee.
    """
    active_patient = user_session.active_patient_profile
    if not active_patient:
        return UTILITIES.create_text_message(message="Could not find your profile. Please log in.")

    # Convert choice to lowercase for consistency
    payment_choice_lower = payment_choice.lower()

    if payment_choice_lower == "now":
        user_session.doctor_booking_selected_payment_time = "now"
        user_session.save()
        # Transition to payment method selection
        # Assuming PATIENTS_MESSAGES is imported and contains the text message functions
        return AI_FUNCTIONS.doctor_booking_payment_method_selection_text_message()

    elif payment_choice_lower == "later":
        user_session.doctor_booking_selected_payment_time = "later"
        user_session.save()
        # Transition to payment method selection (as service fee is paid now)
        return AI_FUNCTIONS.doctor_booking_payment_method_selection_text_message()

    else:
        # Fallback for unexpected input
        return UTILITIES.create_text_message(
            message="I didn't understand your choice. Please reply with 'Pay now' or 'Pay later'."
        )
    


def handle_payment_method_selection(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, method_name: str):
    """
    Handles the user's selection of a payment method.
    """
    active_patient = user_session.active_patient_profile
    if not active_patient:
        return UTILITIES.create_text_message(message="Could not find your profile. Please log in.")

    method_name_lower = method_name.lower()

    # Assuming PaymentMethods enum is defined (M-Pesa, Airtel Money, etc.)
    if method_name_lower == AI_FUNCTIONS.PaymentMethods.MPESA.value.lower(): # Compare lowercase versions
        user_session.doctor_booking_selected_payment_method = AI_FUNCTIONS.PaymentMethods.MPESA.value # Store original case
        user_session.save()
        # Transition to asking for M-Pesa number
        # Assuming user_session.user_phone_number exists
        return PATIENTS_MESSAGES.mobile_payment_prompt_number_selection_text_message(user_session.user_phone_number)

    else:
        # For unsupported methods or unrecognized input
        return UTILITIES.create_text_message(
            message=f"'{method_name}' is currently unsupported or not recognized. "
                    f"Please reply with a valid payment method, such as '{AI_FUNCTIONS.PaymentMethods.MPESA}'. "
                    f"You can also say 'Cancel booking'."
        )


def handle_mobile_payment_number_prompt_choice(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, number_choice: str):
    """
    Handles the user's choice regarding the M-Pesa payment number.
    """
    active_patient = user_session.active_patient_profile
    if not active_patient:
        return UTILITIES.create_text_message(message="Could not find your profile. Please log in.")

    number_choice_lower = number_choice.lower()

    # Assuming normalize_phone_number is available
    if number_choice_lower == "this number":
        mpesa_number = UTILITIES_FUNCTIONS.normalize_phone_number(phone_number=user_session.user_phone_number)
        user_session.doctor_booking_selected_mpesa_number = mpesa_number
        user_session.save()
        # Proceed to create appointment request
        # Assuming handle_create_appointment_request is defined
        is_inapp_payment = (user_session.doctor_booking_selected_payment_time.lower() == "now")
        return handle_create_appointment_request(
            user_session=user_session,
            patient=active_patient,
            is_inapp_payment=is_inapp_payment,
        )

    elif number_choice_lower == "enter number":
        user_session.set_state(
            session_state=WHATSAPP_PLUGIN1.WhatsappPlugin1UserSessionStates.BOOKING_MPESA_NUMBER_INPUT.value
        )
        return UTILITIES.create_text_message(
            message="Please enter your M-Pesa number to receive a payment prompt."
        )

    else:
        return UTILITIES.create_text_message(
            message="I didn't understand your choice. Please reply with 'This number' or 'Enter number'."
        )
    

def handle_mpesa_number_input(user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, phone_number: str):
    """
    Handles the user providing their M-Pesa phone number.
    """
    active_patient = user_session.active_patient_profile
    if not active_patient:
        return UTILITIES.create_text_message(message="Could not find your profile. Please log in.")
    
    # Assuming normalize_phone_number is available and validates the number
    mpesa_number = UTILITIES_FUNCTIONS.normalize_phone_number(phone_number=phone_number)
    
    if not mpesa_number: # Add validation if normalize_phone_number returns None/empty for invalid numbers
        return UTILITIES.create_text_message(
            message="That doesn't look like a valid phone number. Please try again with a correct M-Pesa number."
        )

    user_session.doctor_booking_selected_mpesa_number = mpesa_number
    user_session.save()

    is_inapp_payment = (user_session.doctor_booking_selected_payment_time.lower() == "now")

    # Assuming handle_create_appointment_request is defined
    return handle_create_appointment_request(
        user_session=user_session,
        patient=active_patient,
        is_inapp_payment=is_inapp_payment,
    )




def get_my_appointments(user_session, filter_criteria: dict) -> str:
    """Get user's appointments with optional filtering"""
    try:
        status_filter = filter_criteria.get('status', 'all')  
        date_range = filter_criteria.get('date_range', 'all') 
        
        print(user_session.active_patient_profile)
        if not user_session.active_patient_profile:
            return "Please log in to view your appointments."
        
        # Get user's appointments
        appointments = Appointment.filter_objects(
            patient=user_session.active_patient_profile
        )
        print(appointments)
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
        print(appointments)
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
        
        availability_request = {
            'doctor_name': appointment.doctor,
            'date': new_start_datetime.strftime('%Y-%m-%d'),
            'time': new_start_datetime.strftime('%H:%M'),
            'consultation_mode': appointment.encounter_mode
        }
        print(availability_request)
        # Check if new time is available
        availability = check_doctor_availability(
            user_session,
            availability_request
        )
        print("is_available")
        if not availability:
            return f"{appointment.doctor.title} {appointment.doctor.get_full_name()} is not available at the new time. Please choose a different  time."
        print("Started")
        # Update appointment
        appointment.previous_start_time = appointment.start_time
        appointment.start_time = new_start_datetime
        appointment.end_time = new_end_datetime
        appointment.rescheduling_reason = reason
        appointment.health_worker_availability = availability
        appointment.save()
        
        # Send notification
        send_appointment_rescheduling_by_patient_notification(appointment)
        
        return f"Appointment with {appointment.doctor.title} {appointment.doctor.get_full_name()} " \
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