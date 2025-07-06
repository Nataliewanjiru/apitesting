def execute_function_call(self, function_name: str, arguments: dict, user_session) -> str:
    """Execute the function called by AI"""
    try:
        print(f"🔍 DEBUG: Executing function: {function_name}")
        print(f"🔍 DEBUG: With arguments: {arguments}")
        
        if function_name not in self.function_map:
            return f"Error: Function {function_name} not found"
        
        func = self.function_map[function_name]
        
        # Handle different function signatures properly
        if function_name in ["handle_user_registration", "handle_user_login"]:
            result = func(user_session, arguments.get(list(arguments.keys())[0]))
            
        elif function_name == "handle_doctor_recommendation_from_symptoms":
            result = func(user_session, arguments.get("symptoms"))
            
        elif function_name in ["handle_booking_intent", "handle_appointment_management"]:
            result = func(user_session, arguments.get(list(arguments.keys())[0]))
            
        # NEW: Handle all the appointment-related functions
        elif function_name == "search_doctors_by_criteria":
            result = func(user_session, arguments.get("search_criteria"))
            
        elif function_name == "check_doctor_availability":
            result = func(user_session, arguments.get("availability_request"))
            
        elif function_name == "book_appointment_with_doctor":
            result = func(user_session, arguments.get("booking_details"))
            
        elif function_name == "get_my_appointments":
            result = func(user_session, arguments.get("filter_criteria"))
            
        elif function_name == "cancel_appointment":
            result = func(user_session, arguments.get("cancellation_details"))
            
        elif function_name == "reschedule_appointment":
            result = func(user_session, arguments.get("reschedule_details"))
            
        elif function_name == "get_appointment_details":
            result = func(user_session, arguments.get("appointment_identifier"))
            
        elif function_name == "get_general_information":
            result = func(arguments.get("query"))
            
        else:
            # Fallback for any other functions
            result = func(**arguments)
        
        print(f"✅ DEBUG: Function {function_name} completed successfully")
        return str(result)
        
    except Exception as e:
        error_msg = f"Error executing {function_name}: {str(e)}"
        print(f"❌ DEBUG: {error_msg}")
        import traceback
        print(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
        return error_msg