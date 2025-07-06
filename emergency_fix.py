# EMERGENCY FIX: Replace your current function with this to stop infinite recursion

def handle_doctor_recommendation_from_symptoms(user_session, symptoms) -> list:
    """Find doctor recommendations based on symptoms - FIXED VERSION"""
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
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else GENERAL_MESSAGES.landing_interactive_message(
                    is_existing_user=user_session.is_an_existing_user
                ),
            ]
        
        # Combine all symptoms into a single string for processing
        collected_symptoms = " ".join(str(symptom) for symptom in processed_symptoms if symptom)
        
        print(f"🔍 Final collected symptoms for AI: {collected_symptoms}")
        
        # ===== REPLACE THE RECURSIVE CALL WITH YOUR ACTUAL DOCTOR LOGIC =====
        # ❌ REMOVE THIS LINE: return handle_doctor_recommendation_from_symptoms(...)
        # ✅ ADD YOUR ACTUAL DOCTOR RECOMMENDATION LOGIC HERE:
        
        plugin_settings = WHATSAPP_PLUGIN1.WhatsappPlugin1Settings.get_instance()

        print("🔍 Getting doctor recommendation from symptoms...")

        (
            recommendation_result,
            query,
            error,
        ) = HEALTHWORKERS_FUNCTIONS.get_health_worker_recommendation_from_symptoms(
            symptoms=collected_symptoms,
        )
        print(recommendation_result)
        print("🔴 Error from get_health_worker_recommendation_from_symptoms:", error)

        print("✅ Recommendation response received.")
        if error:
            return [
                UTILITIES.create_text_message(
                    message="An error occurred finding recommendation. Please try again later.\n"
                ),
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else GENERAL_MESSAGES.landing_interactive_message(
                    is_existing_user=user_session.is_an_existing_user
                ),
            ]

        recommendations = recommendation_result.get("recommended_health_workers", None)
        doctors = [t for t in recommendations.items] if recommendations else []

        alternatives = recommendation_result.get("alternative_health_workers", None)
        alternative_doctors = [t for t in alternatives.items] if alternatives else []

        user_session.previous_ai_doctor_recommendations = [
            *[x.id for x in doctors],
            *[t.id for t in alternative_doctors],
        ]
        user_session.save()

        if (
            plugin_settings.list_display_type
            == WHATSAPP_PLUGIN1.ListDisplayTypes.DROPDOWN_MESSAGE.value
        ):
            return [
                UTILITIES.create_text_message(
                    message=(
                        recommendation_result.get("reasoning", None)
                        or "Here are the recommended doctors you could see.\n"
                    )
                    if doctors
                    else "Sorry no doctors match your query."
                ),
                PATIENTS_MESSAGES.doctors_recommendation_results(
                    doctors=doctors, list_offset=0
                ),
            ]

        else:
            user_session.previous_ai_doctor_recommendations_viewing_offset = 0
            user_session.set_state(
                session_state=WHATSAPP_PLUGIN1.WhatsappPlugin1UserSessionStates.VIEWING_NUMBERED_DOCTORS_AI_RECOMMENDATION_RESULTS
            )

            return [
                UTILITIES.create_text_message(
                    message=recommendation_result.get("reasoning", None)
                    or "Here are the recommended doctors you could see.\n"
                ),
                PATIENTS_MESSAGES.my_doctors_text_only_message_v3(
                    doctors=doctors, list_offset=0
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