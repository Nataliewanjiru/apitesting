# OPTION 1: Rename current function and create a wrapper
def _internal_get_doctor_recommendations(user_session, symptoms):
    """Internal function that does the actual doctor recommendation logic"""
    try:
        print(f"🔍 Getting doctor recommendation from symptoms: {symptoms}")
        
        # Ensure symptoms is a string
        if isinstance(symptoms, list):
            collected_symptoms = " ".join(str(s) for s in symptoms if str(s).strip())
        elif isinstance(symptoms, dict):
            # Handle dict case
            symptom_values = []
            if 'symptoms' in symptoms:
                symptom_values.extend(symptoms['symptoms'] if isinstance(symptoms['symptoms'], list) else [symptoms['symptoms']])
            if 'additional_medical_information' in symptoms:
                additional = symptoms['additional_medical_information']
                symptom_values.extend(additional if isinstance(additional, list) else [additional])
            collected_symptoms = " ".join(str(s) for s in symptom_values if str(s).strip())
        else:
            collected_symptoms = str(symptoms) if symptoms else ""
        
        if not collected_symptoms.strip():
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
        
        # YOUR ACTUAL DOCTOR RECOMMENDATION LOGIC HERE
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
        print(f"❌ Error in _internal_get_doctor_recommendations: {str(e)}")
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


def handle_doctor_recommendation_from_symptoms(user_session, symptoms) -> list:
    """Public function that routes to the internal implementation - PREVENTS RECURSION"""
    print(f"🔍 ENTRY POINT: Received symptoms: {symptoms}")
    
    # Call the internal function that does the actual work
    return _internal_get_doctor_recommendations(user_session, symptoms)


# OPTION 2: Use a flag to prevent recursion
_recursion_guard = False

def handle_doctor_recommendation_from_symptoms_with_guard(user_session, symptoms) -> list:
    """Function with recursion guard to prevent infinite loops"""
    global _recursion_guard
    
    if _recursion_guard:
        print("🚨 RECURSION DETECTED - Stopping infinite loop!")
        return [
            UTILITIES.create_text_message(
                message="Error: Detected recursion in doctor recommendation. Please contact support.\n"
            )
        ]
    
    try:
        _recursion_guard = True
        print(f"🔍 Received symptoms: {symptoms}")
        
        # Your symptom processing logic here...
        processed_symptoms = []
        
        if isinstance(symptoms, dict):
            if 'symptoms' in symptoms:
                processed_symptoms = symptoms['symptoms'] if isinstance(symptoms['symptoms'], list) else [symptoms['symptoms']]
            elif 'additional_medical_information' in symptoms:
                processed_symptoms = symptoms['additional_medical_information'] if isinstance(symptoms['additional_medical_information'], list) else [symptoms['additional_medical_information']]
            else:
                processed_symptoms = [str(v) for v in symptoms.values() if v]
        elif isinstance(symptoms, list):
            processed_symptoms = symptoms
        elif isinstance(symptoms, str):
            processed_symptoms = [symptoms] if symptoms.strip() else []
        else:
            processed_symptoms = []
        
        if not processed_symptoms:
            return [
                UTILITIES.create_text_message(
                    message="I couldn't find any symptoms to help you with. Please describe what you're experiencing.\n"
                )
            ]
        
        collected_symptoms = " ".join(str(symptom) for symptom in processed_symptoms if symptom)
        
        # Call the internal function instead of recursing
        return _internal_get_doctor_recommendations(user_session, collected_symptoms)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return [
            UTILITIES.create_text_message(
                message="I encountered an error while searching for healthcare providers. Please try again.\n"
            )
        ]
    finally:
        _recursion_guard = False


# OPTION 3: Direct route - just replace the recursive call
def handle_doctor_recommendation_from_symptoms_direct(user_session, symptoms) -> list:
    """Direct route - replace your current function with this exact code"""
    try:
        print(f"🔍 Received symptoms: {symptoms}")
        
        processed_symptoms = []
        
        if isinstance(symptoms, dict):
            if 'symptoms' in symptoms:
                processed_symptoms = symptoms['symptoms'] if isinstance(symptoms['symptoms'], list) else [symptoms['symptoms']]
            elif 'additional_medical_information' in symptoms:
                processed_symptoms = symptoms['additional_medical_information'] if isinstance(symptoms['additional_medical_information'], list) else [symptoms['additional_medical_information']]
            else:
                processed_symptoms = [str(v) for v in symptoms.values() if v]
        elif isinstance(symptoms, list):
            processed_symptoms = symptoms
        elif isinstance(symptoms, str):
            processed_symptoms = [symptoms] if symptoms.strip() else []
        else:
            processed_symptoms = []
        
        print(f"🔍 Processed symptoms: {processed_symptoms}")
        
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
        
        collected_symptoms = " ".join(str(symptom) for symptom in processed_symptoms if symptom)
        
        # 🔥 CRITICAL: Instead of calling the function recursively, 
        # call your actual doctor recommendation logic directly:
        return _internal_get_doctor_recommendations(user_session, collected_symptoms)
        
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


# OPTION 4: Simple delegation pattern
def get_doctors_for_symptoms(user_session, symptoms_string):
    """Simple function that just does doctor lookup - no recursion possible"""
    plugin_settings = WHATSAPP_PLUGIN1.WhatsappPlugin1Settings.get_instance()

    print("🔍 Getting doctor recommendation from symptoms...")

    (
        recommendation_result,
        query,
        error,
    ) = HEALTHWORKERS_FUNCTIONS.get_health_worker_recommendation_from_symptoms(
        symptoms=symptoms_string,
    )
    print(recommendation_result)
    print("🔴 Error from get_health_worker_recommendation_from_symptoms:", error)

    if error:
        return [
            UTILITIES.create_text_message(
                message="An error occurred finding recommendation. Please try again later.\n"
            )
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


def handle_doctor_recommendation_from_symptoms_delegated(user_session, symptoms) -> list:
    """Routes to simple doctor lookup function"""
    try:
        print(f"🔍 Processing symptoms: {symptoms}")
        
        # Process symptoms into string format
        if isinstance(symptoms, str):
            collected_symptoms = symptoms
        elif isinstance(symptoms, list):
            collected_symptoms = " ".join(str(s) for s in symptoms if str(s).strip())
        elif isinstance(symptoms, dict):
            symptom_parts = []
            if 'symptoms' in symptoms:
                symptom_parts.extend(symptoms['symptoms'] if isinstance(symptoms['symptoms'], list) else [symptoms['symptoms']])
            if 'additional_medical_information' in symptoms:
                additional = symptoms['additional_medical_information']
                symptom_parts.extend(additional if isinstance(additional, list) else [additional])
            collected_symptoms = " ".join(str(s) for s in symptom_parts if str(s).strip())
        else:
            collected_symptoms = str(symptoms) if symptoms else ""
        
        if not collected_symptoms.strip():
            return [
                UTILITIES.create_text_message(
                    message="I couldn't find any symptoms to help you with. Please describe what you're experiencing.\n"
                )
            ]
        
        # Call the simple doctor lookup function (no recursion risk)
        return get_doctors_for_symptoms(user_session, collected_symptoms)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return [
            UTILITIES.create_text_message(
                message="I encountered an error while searching for healthcare providers. Please try again.\n"
            )
        ]