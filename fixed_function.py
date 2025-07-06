def handle_doctor_recommendation_from_symptoms(user_session, symptoms: dict) -> str:
    """Find doctor recommendations based on symptoms"""
    try:
        print(f"🔍 Received symptoms: {symptoms}")
        
        # Handle symptoms input - ensure it's properly formatted
        symptom_list = []
        if symptoms:
            if isinstance(symptoms, dict):
                # Extract symptoms from dict structure
                if 'symptoms' in symptoms:
                    symptom_list = symptoms['symptoms'] if isinstance(symptoms['symptoms'], list) else [symptoms['symptoms']]
                elif 'symptom' in symptoms:
                    symptom_list = [symptoms['symptom']] if isinstance(symptoms['symptom'], str) else symptoms['symptom']
                else:
                    # Treat the entire dict as symptoms data
                    symptom_list = [str(v) for v in symptoms.values() if v]
            elif isinstance(symptoms, list):
                symptom_list = symptoms
            elif isinstance(symptoms, str):
                symptom_list = [symptoms]
        
        print(f"🔍 Processed symptoms: {symptom_list}")
        
        # Check if we have any symptoms to work with
        if not symptom_list:
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
        
        # Collect symptoms into a string for processing
        collected_symptoms = " ".join(symptom_list)
        
        # Add additional medical information if available from user session
        # Note: inquiry_obj was undefined - accessing from user_session instead
        if hasattr(user_session, 'inquiry') and user_session.inquiry:
            inquiry = user_session.inquiry
            if hasattr(inquiry, 'additional_medical_information') and inquiry.additional_medical_information:
                additional_info = inquiry.additional_medical_information
                if isinstance(additional_info, list):
                    collected_symptoms += " " + " ".join(additional_info)
                elif isinstance(additional_info, str):
                    collected_symptoms += " " + additional_info
        
        print(f"🔍 Final collected symptoms: {collected_symptoms}")
        
        # TODO: Implement actual doctor recommendation logic here
        # This is where you would:
        # 1. Query your database for doctors based on symptoms
        # 2. Apply any filtering based on user location/preferences
        # 3. Return formatted doctor recommendations
        
        # Placeholder for actual recommendation logic
        doctor_recommendations = find_doctors_by_symptoms(collected_symptoms, user_session)
        
        return doctor_recommendations
        
    except Exception as e:
        print(f"❌ Error in handle_doctor_recommendation_from_symptoms: {str(e)}")
        return f"Error finding doctors: {str(e)}"


def find_doctors_by_symptoms(symptoms: str, user_session) -> str:
    """
    Placeholder function for finding doctors based on symptoms
    Replace this with your actual doctor matching logic
    """
    # This is where you would implement:
    # 1. Symptom analysis/categorization
    # 2. Specialty matching
    # 3. Doctor database query
    # 4. Location filtering
    # 5. Availability checking
    
    return f"Found doctors for symptoms: {symptoms}"