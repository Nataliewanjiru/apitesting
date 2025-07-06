def handle_doctor_recommendation_from_symptoms(user_session, symptoms: dict) -> str:
    """Find doctor recommendations based on symptoms for the autonomous AI system"""
    try:
        print(f"🔍 Received symptoms: {symptoms}")
        
        # Handle symptoms input - ensure it's properly formatted
        symptom_list = []
        additional_info = []
        
        if symptoms:
            if isinstance(symptoms, dict):
                # Handle the expected AI output format from the prompt
                if 'PromptOutputInquiry' in symptoms:
                    inquiry_data = symptoms['PromptOutputInquiry']
                    if 'symptoms' in inquiry_data and inquiry_data['symptoms']:
                        symptom_list = inquiry_data['symptoms']
                    if 'additional_medical_information' in inquiry_data and inquiry_data['additional_medical_information']:
                        additional_info = inquiry_data['additional_medical_information']
                elif 'symptoms' in symptoms:
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
        print(f"🔍 Additional info: {additional_info}")
        
        # Check if we have any symptoms to work with
        if not symptom_list:
            return json.dumps({
                "status": "error",
                "message": "No symptoms provided for doctor recommendation",
                "suggested_action": "Please describe your symptoms first"
            })
        
        # Collect symptoms into a comprehensive description
        collected_symptoms = " ".join(symptom_list)
        if additional_info:
            collected_symptoms += " " + " ".join(additional_info)
        
        # Get user location for filtering doctors
        user_location = None
        if user_session.active_patient_profile:
            user_location = getattr(user_session.active_patient_profile, 'location', None)
        
        print(f"🔍 Final collected symptoms: {collected_symptoms}")
        print(f"🔍 User location: {user_location}")
        
        # Find doctors based on symptoms
        doctor_recommendations = find_doctors_by_symptoms_and_location(
            symptoms=collected_symptoms, 
            location=user_location,
            user_session=user_session
        )
        
        return doctor_recommendations
        
    except Exception as e:
        print(f"❌ Error in handle_doctor_recommendation_from_symptoms: {str(e)}")
        return json.dumps({
            "status": "error", 
            "message": f"Error finding doctors: {str(e)}",
            "suggested_action": "Please try again or contact support"
        })


def find_doctors_by_symptoms_and_location(symptoms: str, location: str, user_session) -> str:
    """
    Find doctors based on symptoms and user location
    Returns JSON formatted response for the AI system
    """
    try:
        # TODO: Replace with actual database queries
        # This is where you would:
        # 1. Analyze symptoms to determine medical specialties needed
        # 2. Query doctor database by specialty and location
        # 3. Filter by availability, ratings, etc.
        # 4. Format response for the AI chatbot
        
        # Sample mock data - replace with real implementation
        mock_doctors = [
            {
                "name": "Dr. Sarah Johnson",
                "specialty": "Internal Medicine",
                "location": location or "Nairobi",
                "rating": 4.8,
                "availability": "Available today",
                "consultation_fee": "KSH 2,500"
            },
            {
                "name": "Dr. Michael Ochieng",
                "specialty": "Family Medicine", 
                "location": location or "Nairobi",
                "rating": 4.6,
                "availability": "Next available: Tomorrow",
                "consultation_fee": "KSH 2,000"
            }
        ]
        
        # Format response for the autonomous AI system
        response = {
            "status": "success",
            "message": f"Found {len(mock_doctors)} doctors for your symptoms: {symptoms}",
            "doctors": mock_doctors,
            "suggested_action": "Select a doctor to book an appointment",
            "symptoms_analyzed": symptoms,
            "location_searched": location or "All locations"
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        print(f"❌ Error in find_doctors_by_symptoms_and_location: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Error during doctor search: {str(e)}",
            "suggested_action": "Please try again"
        })


def analyze_symptoms_for_specialty(symptoms: str) -> list:
    """
    Analyze symptoms to determine relevant medical specialties
    This is a helper function for better doctor matching
    """
    # TODO: Implement AI-based symptom analysis
    # You could use NLP or a medical knowledge base here
    
    symptom_keywords = {
        'cardiology': ['chest pain', 'heart', 'palpitations', 'shortness of breath'],
        'dermatology': ['skin', 'rash', 'acne', 'mole', 'itching'],
        'orthopedics': ['bone', 'joint', 'back pain', 'muscle', 'injury'],
        'neurology': ['headache', 'dizziness', 'seizure', 'memory'],
        'gastroenterology': ['stomach', 'nausea', 'digestive', 'abdominal'],
        'internal_medicine': ['fever', 'fatigue', 'general', 'cold', 'flu']
    }
    
    relevant_specialties = []
    symptoms_lower = symptoms.lower()
    
    for specialty, keywords in symptom_keywords.items():
        if any(keyword in symptoms_lower for keyword in keywords):
            relevant_specialties.append(specialty)
    
    # Default to internal medicine if no specific specialty identified
    if not relevant_specialties:
        relevant_specialties = ['internal_medicine']
    
    return relevant_specialties


# Import statement you'll need to add to your main file
import json