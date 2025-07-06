def handle_user_registration(user_session, personal_details: dict):
    """Register a new user with personal details"""
    try:
        print(f"🔍 Received personal_details: {personal_details}")
        
        # ✅ CORRECT: Access dict values with string keys in quotes
        password = personal_details.get('password')  # Note the quotes
        first_name = personal_details.get('first_name')
        last_name = personal_details.get('last_name')
        age = personal_details.get('age')
        gender = personal_details.get('gender')
        county = personal_details.get('county')
        location = personal_details.get('location')
        
        print(f"🔍 Password: {password}")
        print(f"🔍 Name: {first_name} {last_name}")
        
        # Check if we have all required fields
        missing_fields = []
        if not first_name: missing_fields.append("first name")
        if not last_name: missing_fields.append("last name")
        if not age: missing_fields.append("age") 
        if not gender: missing_fields.append("gender")
        if not county: missing_fields.append("county")
        if not location: missing_fields.append("location")
        if not password: missing_fields.append("password")
        
        if missing_fields:
            return f"I still need your {', '.join(missing_fields)}. Could you please provide these details?"
        
        # Create user + patient
        user, patient = user_session.create_user_with_patient(password=password)
        user_session.linked_user = user
        user_session.active_patient_profile = patient
        user_session.save()
        
        return f"Registration successful for {first_name}! Welcome to Rastuc."
        
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return f"Registration failed: {str(e)}"