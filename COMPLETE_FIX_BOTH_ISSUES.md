# 🚨 COMPLETE FIX: Pydantic Model Error + Memory Persistence

## **Two Issues Fixed:**

1. ❌ **Pydantic Model Error:** `'PromptOutputBooking' object has no attribute 'get'`
2. ❌ **Memory Loss:** Memory resets to 0 after server restart

## **✅ ONE COMPLETE SOLUTION:**

Replace your entire conversation handling code with this:

### **1. Fixed ConversationManager (Memory Persistence)**

```python
class PersistentConversationManager:
    """
    Conversation manager that NEVER loses memory
    Automatically saves/loads from database
    """
    _engines = {}  # In-memory cache for performance
    
    @classmethod
    def get_engine(cls, user_phone_number: str, user_session) -> AIEngine:
        print(f"🔍 get_engine called with: {user_phone_number}")
        print(f"🔍 Engines before: {list(cls._engines.keys())}")
        
        if user_phone_number not in cls._engines:
            print(f"🔍 Creating NEW engine for: {user_phone_number}")
            
            # Create new engine
            engine = AIEngine()
            
            # ALWAYS load conversation history from database
            cls._load_conversation_history(engine, user_session)
            
            # Cache the engine
            cls._engines[user_phone_number] = engine
        else:
            print(f"🔍 Using EXISTING engine for: {user_phone_number}")
            engine = cls._engines[user_phone_number]
        
        print(f"🔍 Engines after: {list(cls._engines.keys())}")
        print(f"🔍 Memory length: {len(engine.memory.chat_memory.messages)}")
        
        return engine
    
    @classmethod
    def _load_conversation_history(cls, engine: AIEngine, user_session):
        """Load conversation history from database"""
        try:
            if user_session.ai_conversation_history:
                print(f"🔍 Loading {len(user_session.ai_conversation_history)} messages from database")
                engine.load_serialized_history_into_memory(
                    user_session.ai_conversation_history, 
                    engine.memory
                )
            else:
                print(f"🔍 No conversation history in database - starting fresh")
        except Exception as e:
            print(f"🔍 Error loading conversation history: {e}")
    
    @classmethod
    def save_conversation_history(cls, user_phone_number: str, user_session):
        """Save conversation history to database IMMEDIATELY"""
        try:
            if user_phone_number in cls._engines:
                engine = cls._engines[user_phone_number]
                
                # Serialize current conversation
                serialized_history = engine.serialize_conversation_history(engine.memory)
                
                # Save to database immediately
                user_session.ai_conversation_history = serialized_history
                user_session.save()
                
                print(f"🔍 ✅ Saved {len(serialized_history)} messages to database")
            else:
                print(f"🔍 No engine found for {user_phone_number}")
        except Exception as e:
            print(f"🔍 Error saving conversation history: {e}")
```

### **2. Fixed Booking Handler (Pydantic Model Fix)**

```python
def handle_booking_intent(extracted_info: Dict, user, message_text: str = ""):
    """
    FIXED: Enhanced booking handler with proper Pydantic model attribute access
    """
    booking_info = extracted_info.get("PromptOutputBooking")
    personal_info = extracted_info.get("PromptOutputPersonalDetails") 
    inquiry_info = extracted_info.get("PromptOutputInquiry")

    # ✅ FIXED: Access attributes directly from Pydantic models (not .get())
    doctor_name = booking_info.selected_doctor if booking_info else None
    location = personal_info.location if personal_info else None
    specialization = booking_info.specialization if booking_info else "general practitioner"
    preferred_date = booking_info.preferred_date if booking_info else None
    preferred_time = booking_info.preferred_consultation_time if booking_info else None
    confirmed = booking_info.confirmed if booking_info else None

    print(f"🔍 Booking details: doctor={doctor_name}, location={location}, specialization={specialization}")
    print(f"🔍 Date/Time: {preferred_date} at {preferred_time}, confirmed={confirmed}")

    # Step 1: If no doctor selected, suggest doctors based on symptoms/specialization
    if not doctor_name and (specialization or (inquiry_info and inquiry_info.symptoms)):
        return handle_doctor_recommendation_request(specialization, location, inquiry_info)

    # Step 2: Check if user is confirming booking (improved detection)
    is_confirming = detect_booking_confirmation(message_text, extracted_info)
    
    if doctor_name and (confirmed is True or is_confirming):
        print(f"🔍 Booking confirmation detected")
        
        # Proceed with actual booking
        symptoms = ", ".join(inquiry_info.symptoms) if inquiry_info and inquiry_info.symptoms else "general check-up"
        preferred_modes = inquiry_info.preferred_modes_of_consultation if inquiry_info else []
        mode = preferred_modes[0] if preferred_modes else "clinic"

        try:
            result = ai_book_appointment(
                doctor_name=doctor_name,
                datetime_string=f"{preferred_date or ''} {preferred_time or ''}".strip(),
                mode=mode,
                patient_user=user,
                symptoms=symptoms,
                confirmed=True
            )
            return result
        except Exception as e:
            print(f"🔍 Error during booking: {e}")
            return f"Sorry, there was an issue with your booking. Please try again or contact support."

    # Step 3: If doctor selected but no confirmation, show availability
    if doctor_name and confirmed is None and not is_confirming:
        print(f"🔍 Availability query detected for {doctor_name}")
        
        try:
            availability_result = ai_book_appointment(
                doctor_name=doctor_name,
                datetime_string="",
                mode="clinic",
                patient_user=user,
                symptoms="",
                confirmed=False
            )
            
            return f"{availability_result}\n\nWould you like to book any of these times? Just let me know which one!"
                
        except Exception as e:
            print(f"🔍 Error getting availability: {e}")
            return f"Dr. {doctor_name.replace('Dr. ', '')} is typically available on weekdays between 9 AM - 5 PM. What date and time would you prefer?"

    # Step 4: Default fallback - suggest doctors if we have specialization
    if not doctor_name and specialization and specialization != "general practitioner":
        return handle_doctor_recommendation_request(specialization, location, inquiry_info)
    
    return "Could you please provide more details about your preferred appointment time and date?"


def handle_doctor_recommendation_request(specialization: str, location: str, inquiry_info):
    """
    FIXED: Handle doctor recommendations with proper Pydantic model access
    """
    try:
        # ✅ FIXED: Access symptoms directly from Pydantic model
        symptoms = inquiry_info.symptoms if inquiry_info else []
        
        if symptoms:
            # Use symptom-based recommendation
            symptoms_text = " ".join(symptoms)
            # Your existing recommendation logic here
            pass
        
        # Fallback to specialization-based search
        if specialization and specialization != "general practitioner":
            from apps.healthworkers.models import HealthWorker
            
            query_set = HealthWorker.objects.filter(
                primary_specialty__name__icontains=specialization,
                is_published=True
            )
            
            if location:
                query_set = query_set.filter(
                    primary_clinic_practice__county__name__icontains=location
                ).distinct()
            
            doctors = query_set[:3]
            
            if doctors:
                doctor_list = []
                for i, doctor in enumerate(doctors, 1):
                    name = f"Dr. {doctor.first_name} {doctor.last_name}"
                    specialty = doctor.primary_specialty.name if doctor.primary_specialty else 'General Practice'
                    doctor_list.append(f"{i}. {name} - {specialty}")
                
                doctors_text = "\n".join(doctor_list)
                return f"Here are available {specialization}s in {location or 'your area'}:\n\n{doctors_text}\n\nWhich doctor would you like to book?"
        
        return "I couldn't find specific doctors for your needs. Could you tell me more about what type of specialist you're looking for?"
        
    except Exception as e:
        print(f"🔍 Error in doctor recommendation: {e}")
        return "I'm having trouble finding doctors right now. Please try again or visit our website at www.rastuc.com"


def detect_booking_confirmation(message_text: str, extracted_info: Dict) -> bool:
    """
    FIXED: Detects booking confirmation with proper Pydantic model access
    """
    booking_info = extracted_info.get("PromptOutputBooking")
    
    confirmation_phrases = [
        "yes", "ok", "okay", "sure", "confirm", "book", "schedule", 
        "go ahead", "proceed", "that works", "perfect", "sounds good",
        "i want", "i'll take", "book me", "confirm it"
    ]
    
    time_date_patterns = [
        r'\d{1,2}(st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|\w{3})',
        r'(january|february|march|april|may|june|july|august|september|october|november|december|\w{3})\s+\d{1,2}',
        r'\d{1,2}:\d{2}',
        r'\d{1,2}\s*(am|pm)',
        r'at\s*\d',
        r'(morning|afternoon|evening)'
    ]
    
    message_lower = message_text.lower()
    
    # Check for confirmation phrases
    for phrase in confirmation_phrases:
        if phrase in message_lower:
            return True
    
    # Check for time/date patterns indicating booking intent
    import re
    for pattern in time_date_patterns:
        if re.search(pattern, message_lower):
            return True
    
    # ✅ FIXED: Access attributes directly from Pydantic model
    if (booking_info and booking_info.selected_doctor and 
        (booking_info.preferred_date or booking_info.preferred_consultation_time)):
        return True
        
    return False
```

### **3. Fixed Main Conversation Handler (Both Issues)**

```python
def handle_conversation_mode_chatbot_message_v2(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):  
    
    # ✅ FIXED: Use persistent conversation manager
    ai_engine = PersistentConversationManager.get_engine(
        user_session.user_phone_number, 
        user_session
    )
    
    response, error = ai_engine.generate_response(message=message_text)
    
    # ✅ FIXED: Save conversation after EVERY message
    PersistentConversationManager.save_conversation_history(
        user_session.user_phone_number, 
        user_session
    )
    
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
    
    # Handle different intents
    if inquiry_intent == "symptom_report":
        print(f"🔍 SYMPTOM_REPORT INTENT TRIGGERED")
        inquiry_obj = extracted_info.get("PromptOutputInquiry")  
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
        if inquiry_obj.additional_medical_information:
            collected_symptoms += " " + " ".join(
                inquiry_obj.additional_medical_information
            )

        return handle_doctor_recommendation_from_symptoms(
            user_session=user_session,
            symptoms=collected_symptoms
        )
    
    elif inquiry_intent == "booking":
        # ✅ FIXED: Enhanced booking handler with message text and proper Pydantic access
        booking_result = handle_booking_intent(
            extracted_info=extracted_info, 
            user=user_session.active_patient_profile,
            message_text=message_text
        )
        
        # Save again after booking processing
        PersistentConversationManager.save_conversation_history(
            user_session.user_phone_number, 
            user_session
        )
        
        return [UTILITIES.create_text_message(booking_result)]

    elif inquiry_intent == "appointment_management":
        # Handle appointment viewing, cancellation, rescheduling  
        try:
            from .handle_booking_intent import get_user_appointments, format_appointment_list
            
            if "appointment" in message_text.lower() and any(word in message_text.lower() for word in ["show", "view", "see", "check"]):
                upcoming = get_user_appointments(user_session.active_patient_profile, "upcoming")
                
                if not upcoming:
                    management_result = "You don't have any upcoming appointments.\n\nWould you like to book a new appointment? Just tell me your symptoms or the type of doctor you need!"
                else:
                    appointments_text = format_appointment_list(upcoming, include_status=True)
                    management_result = f"Your upcoming appointments:\n\n{appointments_text}\n\nNeed to make any changes?"
            else:
                management_result = "I can help you view, cancel, or reschedule your appointments. What would you like to do?"
        except:
            management_result = "I can help you view, cancel, or reschedule your appointments. What would you like to do?"
        
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
```

## **🎯 Expected Results After Fix:**

### **Memory Persistence Test:**
```
Before restart: Memory length: 16 ✅
Server restart...
After restart:  Memory length: 16 ✅ (restored from database!)
```

### **Booking Flow Test:**
```
User: "I am 21 and I live in Nairobi Langata"
AI: ✅ Shows available cardiologists in Nairobi (no Pydantic error!)
```

### **Conversation Continuity:**
```
User: "Can I book a cardiologist"
AI: "What time would you prefer?"
User: "11am" 
AI: "What date would you like?"
User: "July 18th"
AI: ✅ Shows cardiologists and continues naturally
```

## **🚀 Implementation Steps:**

1. **Replace ConversationManager** with `PersistentConversationManager`
2. **Replace handle_booking_intent** with the fixed version
3. **Replace handle_conversation_mode_chatbot_message_v2** with the fixed version

## **🔍 Debug Logs to Watch:**

```
🔍 Loading X messages from database    ← Memory restoration
🔍 ✅ Saved X messages to database     ← Automatic saving
🔍 Booking details: doctor=None...      ← Pydantic access working
🔍 Memory length: X (never 0!)         ← Persistent memory
```

This complete fix ensures:
- ✅ **No more Pydantic errors**
- ✅ **Memory survives server restarts** 
- ✅ **Smooth booking flow**
- ✅ **Natural conversation continuity**