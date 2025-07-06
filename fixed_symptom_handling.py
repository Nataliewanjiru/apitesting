# Fixed calling code for symptom_report intent
def handle_symptom_report_intent(user_session, extracted_info):
    """Handle symptom report intent with proper data structure"""
    print(f"🔍 SYMPTOM_REPORT INTENT TRIGGERED")
    print(f"🔍 extracted_info keys: {list(extracted_info.keys())}")
    
    inquiry_obj = extracted_info.get("PromptOutputInquiry")  
    if not inquiry_obj:
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
    
    symptoms = inquiry_obj.symptoms or []
    print(f"🔍 Found symptoms: {symptoms}")
    
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
    
    # Pass the entire inquiry object instead of just concatenated strings
    return handle_doctor_recommendation_from_symptoms(
        user_session=user_session,
        inquiry_data=inquiry_obj  # Pass the structured object
    )


def handle_doctor_recommendation_from_symptoms(user_session, inquiry_data) -> list:
    """Find doctor recommendations based on symptoms and inquiry data"""
    try:
        print(f"🔍 Received inquiry_data: {inquiry_data}")
        
        # Extract symptoms from inquiry data
        symptoms = []
        additional_info = []
        consultation_preferences = []
        
        if hasattr(inquiry_data, 'symptoms') and inquiry_data.symptoms:
            symptoms = inquiry_data.symptoms if isinstance(inquiry_data.symptoms, list) else [inquiry_data.symptoms]
        
        if hasattr(inquiry_data, 'additional_medical_information') and inquiry_data.additional_medical_information:
            additional_info = inquiry_data.additional_medical_information if isinstance(inquiry_data.additional_medical_information, list) else [inquiry_data.additional_medical_information]
        
        if hasattr(inquiry_data, 'preferred_modes_of_consultation') and inquiry_data.preferred_modes_of_consultation:
            consultation_preferences = inquiry_data.preferred_modes_of_consultation if isinstance(inquiry_data.preferred_modes_of_consultation, list) else [inquiry_data.preferred_modes_of_consultation]
        
        print(f"🔍 Extracted symptoms: {symptoms}")
        print(f"🔍 Additional medical info: {additional_info}")
        print(f"🔍 Consultation preferences: {consultation_preferences}")
        
        # Validate we have symptoms
        if not symptoms or all(not str(symptom).strip() for symptom in symptoms):
            return [
                UTILITIES.create_text_message(
                    message="I couldn't find any symptoms to help you with. Please describe what you're experiencing so I can recommend the right healthcare provider.\n"
                ),
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else GENERAL_MESSAGES.landing_interactive_message(
                    is_existing_user=user_session.is_an_existing_user
                ),
            ]
        
        # Create comprehensive symptom description
        symptom_description = ", ".join(str(symptom) for symptom in symptoms if str(symptom).strip())
        
        # Add additional medical information
        if additional_info:
            additional_description = ". ".join(str(info) for info in additional_info if str(info).strip())
            if additional_description:
                symptom_description += f". Additional details: {additional_description}"
        
        # Add consultation preferences to the description
        if consultation_preferences:
            preferred_consultation = ", ".join(str(pref) for pref in consultation_preferences if str(pref).strip())
            if preferred_consultation:
                symptom_description += f". Preferred consultation type: {preferred_consultation}"
        
        print(f"🔍 Final symptom description: {symptom_description}")
        
        # TODO: Implement actual doctor recommendation logic here
        # You would typically:
        # 1. Match symptoms to medical specialties
        # 2. Find available doctors in the user's area
        # 3. Filter by consultation preferences
        # 4. Return formatted doctor recommendations
        
        # For now, return a structured response
        return [
            UTILITIES.create_text_message(
                message=f"Based on your symptoms and preferences, I'm searching for suitable healthcare providers.\n\n"
                       f"Symptoms: {', '.join(symptoms)}\n"
                       f"{'Additional info: ' + ', '.join(additional_info) if additional_info else ''}\n"
                       f"{'Preferred consultation: ' + ', '.join(consultation_preferences) if consultation_preferences else ''}\n\n"
                       f"Please wait while I find the best healthcare providers for you..."
            ),
            # Here you would add actual doctor recommendation messages
            # Example structure:
            # UTILITIES.create_doctor_recommendation_message(doctors_list),
            # UTILITIES.create_booking_options_message()
        ]
        
    except Exception as e:
        print(f"❌ Error in handle_doctor_recommendation_from_symptoms: {str(e)}")
        return [
            UTILITIES.create_text_message(
                message="I encountered an error while searching for healthcare providers. Please try again or contact support if the issue persists.\n"
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]


# Alternative version if you want to keep the original function signature
# but handle inquiry data properly:

def handle_doctor_recommendation_from_symptoms_v2(user_session, symptoms) -> list:
    """Alternative version that handles various input formats"""
    try:
        print(f"🔍 Received symptoms: {symptoms}")
        
        # Handle if symptoms is actually an inquiry object
        if hasattr(symptoms, 'symptoms'):
            # This is an inquiry object, extract properly
            inquiry_data = symptoms
            symptom_list = inquiry_data.symptoms or []
            additional_info = getattr(inquiry_data, 'additional_medical_information', []) or []
            consultation_prefs = getattr(inquiry_data, 'preferred_modes_of_consultation', []) or []
            
            # Create comprehensive description
            all_symptoms = []
            if isinstance(symptom_list, list):
                all_symptoms.extend(symptom_list)
            else:
                all_symptoms.append(str(symptom_list))
                
            if isinstance(additional_info, list):
                all_symptoms.extend(additional_info)
            else:
                all_symptoms.append(str(additional_info))
                
            processed_symptoms = [str(s) for s in all_symptoms if str(s).strip()]
            
        elif isinstance(symptoms, str):
            # Original string format
            processed_symptoms = [symptoms] if symptoms.strip() else []
            
        elif isinstance(symptoms, list):
            # List format
            processed_symptoms = [str(s) for s in symptoms if str(s).strip()]
            
        else:
            processed_symptoms = []
        
        print(f"🔍 Processed symptoms: {processed_symptoms}")
        
        if not processed_symptoms:
            return [
                UTILITIES.create_text_message(
                    message="I couldn't find any symptoms to help you with. Please describe what you're experiencing so I can recommend the right healthcare provider.\n"
                ),
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else GENERAL_MESSAGES.landing_interactive_message(
                    is_existing_user=user_session.is_an_existing_user
                ),
            ]
        
        symptom_description = ". ".join(processed_symptoms)
        print(f"🔍 Final symptom description: {symptom_description}")
        
        # TODO: Add actual doctor recommendation logic here
        return [
            UTILITIES.create_text_message(
                message=f"Based on your symptoms: {symptom_description}\n\nI'm searching for suitable healthcare providers for you. Please wait a moment..."
            ),
        ]
        
    except Exception as e:
        print(f"❌ Error in handle_doctor_recommendation_from_symptoms: {str(e)}")
        return [
            UTILITIES.create_text_message(
                message="I encountered an error while searching for healthcare providers. Please try again or contact support if the issue persists.\n"
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]