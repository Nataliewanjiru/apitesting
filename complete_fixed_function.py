def handle_doctor_recommendation_from_symptoms(
    user_session, inquiry_data
) -> list:
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
        
        # Create comprehensive symptom description for AI analysis
        collected_symptoms = " ".join(str(symptom) for symptom in symptoms if str(symptom).strip())
        
        # Add additional medical information to the symptoms string
        if additional_info:
            additional_description = " ".join(str(info) for info in additional_info if str(info).strip())
            if additional_description:
                collected_symptoms += " " + additional_description
        
        print(f"🔍 Final collected symptoms for AI: {collected_symptoms}")
        
        # ===== ACTUAL DOCTOR RECOMMENDATION LOGIC STARTS HERE =====
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


# Updated calling code for symptom_report intent
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
    
    # Pass the entire inquiry object to preserve all structured data
    return handle_doctor_recommendation_from_symptoms(
        user_session=user_session,
        inquiry_data=inquiry_obj
    )


# Alternative backward-compatible version that maintains original function signature
def handle_doctor_recommendation_from_symptoms_backward_compatible(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession, symptoms: str
):
    """Backward compatible version - handles both string symptoms and inquiry objects"""
    try:
        print(f"🔍 Received symptoms (backward compatible): {symptoms}")
        
        # Handle if symptoms is actually an inquiry object (for new calls)
        if hasattr(symptoms, 'symptoms'):
            # This is an inquiry object, extract properly
            inquiry_data = symptoms
            symptom_list = inquiry_data.symptoms or []
            additional_info = getattr(inquiry_data, 'additional_medical_information', []) or []
            
            # Create comprehensive description
            all_symptoms = []
            if isinstance(symptom_list, list):
                all_symptoms.extend(symptom_list)
            else:
                all_symptoms.append(str(symptom_list))
                
            if isinstance(additional_info, list):
                all_symptoms.extend(additional_info)
            else:
                if additional_info:
                    all_symptoms.append(str(additional_info))
                
            collected_symptoms = " ".join(str(s) for s in all_symptoms if str(s).strip())
            
        else:
            # Original string format - use as is
            collected_symptoms = str(symptoms) if symptoms else ""
        
        print(f"🔍 Final collected symptoms: {collected_symptoms}")
        
        if not collected_symptoms.strip():
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
        
        # ===== ACTUAL DOCTOR RECOMMENDATION LOGIC =====
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