def handle_doctor_recommendation_from_symptoms(user_session, symptoms) -> str:
    """Find doctor recommendations based on symptoms"""
    try:
        print(f"🔍 Received symptoms: {symptoms}")
        
        # Handle different symptom input formats (dict, list, or string)
        processed_symptoms = []
        
        if isinstance(symptoms, dict):
            # Extract symptoms from dictionary (assuming it has a 'symptoms' key or similar)
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
        
        # Check if we have any symptoms to work with
        if not processed_symptoms or all(not symptom.strip() for symptom in processed_symptoms if isinstance(symptom, str)):
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
        
        # Combine all symptoms into a single string for processing
        collected_symptoms = " ".join(str(symptom) for symptom in processed_symptoms if symptom)
        
        # Get additional medical information from user session if available
        if hasattr(user_session, 'inquiry_data') and user_session.inquiry_data:
            if hasattr(user_session.inquiry_data, 'additional_medical_information') and user_session.inquiry_data.additional_medical_information:
                additional_info = user_session.inquiry_data.additional_medical_information
                if isinstance(additional_info, list):
                    collected_symptoms += " " + " ".join(additional_info)
                elif isinstance(additional_info, str):
                    collected_symptoms += " " + additional_info
        
        print(f"🔍 Final collected symptoms: {collected_symptoms}")
        
        # TODO: Add actual doctor recommendation logic here
        # This should call your doctor matching service/API
        
        # For now, return a placeholder response
        return [
            UTILITIES.create_text_message(
                message=f"Based on your symptoms: {collected_symptoms}\n\nI'm searching for suitable healthcare providers for you. Please wait a moment..."
            ),
            # Add actual doctor recommendation messages here
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