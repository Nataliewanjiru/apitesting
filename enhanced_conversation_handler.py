from typing import Dict, List, Optional
from apps.whatsappplugin1 import models as WHATSAPP_PLUGIN1
from apps.whatsappplugin1.handle_booking_intent import (
    handle_booking_intent, 
    detect_cancellation_intent,
    handle_appointment_cancellation,
    get_user_appointments,
    format_appointment_list
)
from apps.whatsappplugin1.aiengine2 import ConversationManager
import apps.whatsappplugin1.messages.patients as PATIENTS_MESSAGES
import apps.whatsappplugin1.messages.general as GENERAL_MESSAGES
import apps.whatsappplugin1.utilities as UTILITIES


def handle_conversation_mode_chatbot_message_v2(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):  
    
    # Check for direct appointment management commands first
    direct_response = handle_direct_appointment_commands(message_text, user_session)
    if direct_response:
        return direct_response
    
    # CRITICAL FIX: Pass user_session to get_engine for memory persistence
    ai_engine = ConversationManager.get_engine(user_session.user_phone_number, user_session)
    
    # Memory is automatically loaded in get_engine method
    
    response, error = ai_engine.generate_response(message=message_text)
    
    # Always save after each conversation exchange
    user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
    user_session.save()  # CRITICAL: Save to database immediately
    
    if not response:
        return [
            UTILITIES.create_text_message(
                "Sorry, our AI assistant is unavailable at the moment. Please try again later.\n"
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]

    next_question = response.next_question
    inquiry_intent = response.intent
    extracted_info = response.extracted_info or {}
    
    # Continue conversation if there's a next question
    if next_question is not None and next_question.strip() != "":
        return UTILITIES.create_text_message(f"{next_question}\n")
    

    if inquiry_intent == "symptom_report":
        print(f"🔍 SYMPTOM_REPORT INTENT TRIGGERED")
        print(f"🔍 extracted_info keys:{list(extracted_info.keys())}")
        inquiry_obj = extracted_info.get("PromptOutputInquiry")  

        if inquiry_obj:
            # FIXED: Direct attribute access instead of .get()
            symptoms = inquiry_obj.symptoms or []
            print(f"🔍 Found symptoms: {symptoms}")

        symptoms = inquiry_obj.symptoms or [] if inquiry_obj else []
         

        if not symptoms:
            return [
                UTILITIES.create_text_message(
                    message="Error collecting symptom information. Please try again later.\n"
                ),
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else GENERAL_MESSAGES.landing_interactive_message(
                    is_existing_user=user_session.is_an_existing_user
                ),
            ]

        collected_symptoms = " ".join(symptoms)
        # FIXED: Direct attribute access instead of .get()
        if inquiry_obj.additional_medical_information:
            collected_symptoms += " " + " ".join(
                inquiry_obj.additional_medical_information
            )

        return handle_doctor_recommendation_from_symptoms(
            user_session=user_session,
            symptoms=collected_symptoms
        )
    
    elif inquiry_intent == "booking":
        # Enhanced booking handler with message text
        booking_result = handle_booking_intent(
            extracted_info=extracted_info, 
            user=user_session.active_patient_profile,
            message_text=message_text  # Pass the actual message for better detection
        )
        
        # Continue conversation regardless of result
        return [UTILITIES.create_text_message(booking_result)]

    elif inquiry_intent == "appointment_management":
        # Handle appointment viewing, cancellation, rescheduling
        management_result = handle_appointment_management(
            extracted_info=extracted_info,
            user=user_session.active_patient_profile,
            message_text=message_text
        )
        
        return [UTILITIES.create_text_message(management_result)]                              

    # Handle fallback/default
    else:
        return [
            UTILITIES.create_text_message(
                response.closing_remark
                or "Thanks for chatting with us. Let us know if you need help again!"
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]


def handle_direct_appointment_commands(message_text: str, user_session):
    """
    Handle direct appointment-related commands without going through AI
    """
    message_lower = message_text.lower().strip()
    
    # View appointments commands
    view_commands = [
        "my appointments", "view appointments", "show appointments", 
        "appointment list", "upcoming appointments", "check appointments"
    ]
    
    for command in view_commands:
        if command in message_lower:
            return handle_view_appointments_request(user_session.active_patient_profile)
    
    # Quick cancellation commands
    cancel_commands = [
        "cancel my appointment", "cancel appointment", "delete appointment"
    ]
    
    for command in cancel_commands:
        if command in message_lower:
            return [UTILITIES.create_text_message(
                handle_appointment_cancellation(user_session.active_patient_profile, None)
            )]
    
    # Emergency/urgent appointment requests
    urgent_commands = [
        "emergency", "urgent", "need doctor now", "immediate appointment"
    ]
    
    for command in urgent_commands:
        if command in message_lower:
            return handle_urgent_appointment_request(user_session.active_patient_profile)
    
    return None


def handle_view_appointments_request(user):
    """
    Handle requests to view user's appointments
    """
    try:
        # Get upcoming appointments
        upcoming = get_user_appointments(user, "upcoming")
        
        if not upcoming:
            return [UTILITIES.create_text_message(
                "You don't have any upcoming appointments.\n\n"
                "Would you like to book a new appointment? Just tell me your symptoms or the type of doctor you need!"
            )]
        
        appointments_text = format_appointment_list(upcoming, include_status=True)
        
        response = f"Your upcoming appointments:\n\n{appointments_text}\n\n"
        
        if len(upcoming) == 1:
            response += "Would you like to cancel or reschedule this appointment?"
        else:
            response += "Would you like to cancel or reschedule any of these appointments?"
        
        return [UTILITIES.create_text_message(response)]
        
    except Exception as e:
        print(f"🔍 Error viewing appointments: {e}")
        return [UTILITIES.create_text_message(
            "Sorry, I couldn't retrieve your appointments right now. Please try again later."
        )]


def handle_appointment_management(extracted_info: Dict, user, message_text: str):
    """
    Handle appointment management intents (view, cancel, reschedule)
    """
    try:
        # Check for cancellation intent
        is_cancellation, appointment_id = detect_cancellation_intent(message_text)
        if is_cancellation:
            return handle_appointment_cancellation(user, appointment_id)
        
        # Check for view/list intent
        view_keywords = ["show", "view", "list", "my appointments", "upcoming"]
        if any(keyword in message_text.lower() for keyword in view_keywords):
            upcoming = get_user_appointments(user, "upcoming")
            
            if not upcoming:
                return "You don't have any upcoming appointments. Would you like to book a new appointment?"
            
            appointments_text = format_appointment_list(upcoming, include_status=True)
            return f"Your upcoming appointments:\n\n{appointments_text}\n\nNeed to make any changes?"
        
        # Check for rescheduling intent
        reschedule_keywords = ["reschedule", "change time", "move appointment", "different time"]
        if any(keyword in message_text.lower() for keyword in reschedule_keywords):
            return handle_reschedule_request(user, message_text)
        
        # Default management response
        return "I can help you view, cancel, or reschedule your appointments. What would you like to do?"
        
    except Exception as e:
        print(f"🔍 Error in appointment management: {e}")
        return "Sorry, I couldn't process your appointment request. Please try again."


def handle_urgent_appointment_request(user):
    """
    Handle urgent/emergency appointment requests
    """
    try:
        # Look for available doctors with immediate slots
        message = ("For urgent medical needs, I recommend:\n\n"
                  "🚨 **Emergency**: Call 911 or visit the nearest hospital\n"
                  "🏥 **Urgent Care**: Contact your nearest clinic\n"
                  "📞 **Telemedicine**: I can help you find doctors available for immediate virtual consultations\n\n"
                  "What type of urgent care do you need?")
        
        return [UTILITIES.create_text_message(message)]
        
    except Exception as e:
        print(f"🔍 Error handling urgent request: {e}")
        return [UTILITIES.create_text_message(
            "For urgent medical needs, please contact your healthcare provider or visit the nearest emergency room."
        )]


def handle_reschedule_request(user, message_text: str):
    """
    Handle appointment rescheduling requests
    """
    try:
        upcoming = get_user_appointments(user, "upcoming")
        
        if not upcoming:
            return "You don't have any appointments to reschedule."
        
        if len(upcoming) == 1:
            appointment = upcoming[0]
            doctor_name = f"Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}"
            current_time = appointment.start_time.strftime('%A, %B %d at %I:%M %p')
            
            return (f"I can help you reschedule your appointment with {doctor_name} "
                   f"currently scheduled for {current_time}.\n\n"
                   f"What new date and time would you prefer?")
        else:
            appointments_text = format_appointment_list(upcoming)
            return (f"You have multiple appointments:\n\n{appointments_text}\n\n"
                   f"Which appointment would you like to reschedule? Please specify the doctor's name.")
        
    except Exception as e:
        print(f"🔍 Error handling reschedule: {e}")
        return "Sorry, I couldn't process your rescheduling request. Please try again."


def handle_calendar_integration_request(user, appointment):
    """
    Handle requests to add appointments to calendar
    """
    try:
        from apps.whatsappplugin1.appointment_functions import create_and_save_icalendar_event
        
        # Create calendar event
        icalendar_file = create_and_save_icalendar_event(
            name=f"Appointment with Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}",
            description=f"Medical appointment for {appointment.symptoms or 'consultation'}",
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            attendees=[],
            location="Virtual" if appointment.encounter_mode == "virtual" else "Clinic"
        )
        
        if icalendar_file:
            appointment_time = appointment.start_time.strftime('%A, %B %d at %I:%M %p')
            return f"Calendar event created for your appointment with Dr. {appointment.doctor.first_name} {appointment.doctor.last_name} on {appointment_time}. You should receive it via email."
        else:
            return "Sorry, I couldn't create the calendar event. You can manually add the appointment to your calendar."
            
    except Exception as e:
        print(f"🔍 Error creating calendar event: {e}")
        return "Sorry, I couldn't create the calendar event right now."


def handle_notification_preferences(user, message_text: str):
    """
    Handle user preferences for appointment notifications
    """
    try:
        message_lower = message_text.lower()
        
        if "turn off" in message_lower or "disable" in message_lower or "stop" in message_lower:
            # Logic to disable notifications
            return "I've noted that you'd like to reduce notifications. You can manage detailed notification settings in the app."
        
        elif "turn on" in message_lower or "enable" in message_lower or "reminder" in message_lower:
            # Logic to enable notifications
            return "I've noted that you'd like to receive appointment reminders. You'll get notifications via SMS and email before your appointments."
        
        return "You can manage your notification preferences for appointments in the app settings. Would you like me to help you with anything else?"
        
    except Exception as e:
        print(f"🔍 Error handling notification preferences: {e}")
        return "Sorry, I couldn't update your notification preferences right now."


def handle_doctor_recommendation_from_symptoms(user_session, symptoms: str):
    """
    Handle doctor recommendations based on symptoms - FIXED PYDANTIC ERROR
    """
    try:
        from apps.whatsappplugin1.ai_functions import get_health_worker_recommendation_from_symptoms
        
        # Get AI-powered recommendations
        recommendation_result, specialty_query, error = get_health_worker_recommendation_from_symptoms(symptoms)
        
        if error:
            print(f"🔍 Error in doctor recommendation: {error}")
            return [
                UTILITIES.create_text_message(
                    "I'm having trouble finding doctors right now. Please try again or visit our website at www.rastuc.com"
                ),
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else GENERAL_MESSAGES.landing_interactive_message(
                    is_existing_user=user_session.is_an_existing_user
                ),
            ]
        
        if recommendation_result and recommendation_result.get("recommended_health_workers"):
            doctors = recommendation_result["recommended_health_workers"]["data"][:5]  # Top 5
            
            if doctors:
                doctor_list = []
                for i, doctor in enumerate(doctors, 1):
                    name = f"Dr. {doctor['first_name']} {doctor['last_name']}"
                    specialty = doctor.get('primary_specialty', {}).get('name', 'General Practice')
                    location = doctor.get('primary_clinic_practice', {}).get('county', {}).get('name', 'Location not specified')
                    doctor_list.append(f"{i}. {name} - {specialty} ({location})")
                
                doctors_text = "\n".join(doctor_list)
                
                message = (f"Based on your symptoms, I recommend these healthcare providers:\n\n"
                          f"{doctors_text}\n\n"
                          f"Which doctor would you like to book an appointment with? "
                          f"Just tell me the doctor's name or number.")
                
                return [UTILITIES.create_text_message(message)]
        
        # Alternative doctors if no AI recommendations
        return [
            UTILITIES.create_text_message(
                "I couldn't find specific recommendations for your symptoms right now. "
                "Would you like me to help you find a general practitioner or a specific type of specialist?"
            )
        ]
        
    except Exception as e:
        print(f"🔍 Error in doctor recommendations: {e}")
        return [
            UTILITIES.create_text_message(
                "Sorry, I'm having trouble with recommendations right now. "
                "Please visit www.rastuc.com to browse available doctors."
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]