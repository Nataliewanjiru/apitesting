# Persistent Memory AI Agent

## 🎯 **Concept: Never-Clearing Memory**

Instead of clearing memory after each intent, maintain persistent conversations that allow users to:
- Build on previous information
- Modify preferences naturally ("now I want a doctor in Meru instead of Nairobi")
- Continue conversations seamlessly
- Avoid re-entering personal details

## 🔧 **Modified Conversation Handler**

Replace your `handle_conversation_mode_chatbot_message_v2` with this persistent version:

```python
def handle_conversation_mode_chatbot_message_v2(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):  
    # Reuse existing engine for this user (PERSISTENT)
    ai_engine = ConversationManager.get_engine(user_session.user_phone_number)
    
    # Only load history ONCE (when engine is first created)
    if not ai_engine.memory.chat_memory.messages:
        ai_engine.load_serialized_history_into_memory(
            user_session.ai_conversation_history, 
            ai_engine.memory
        )
    
    response, error = ai_engine.generate_response(message=message_text)
    
    # Handle AI error - only clear on critical failures
    if not response:
        # Still preserve some context - save before clearing
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        ConversationManager.clear_engine(user_session.user_phone_number) 
        
        return [
            UTILITIES.create_text_message(
                "Sorry, I had a technical issue. Let me help you again - I remember our previous conversation.\n"
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

    # ✅ ALWAYS CONTINUE CONVERSATION - NEVER CLEAR ENGINE
    if next_question is not None and next_question.strip() != "":
        # Save progress to database periodically
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        return UTILITIES.create_text_message(f"{next_question}\n")
    
    # ✅ PROCESS INTENTS WITH PERSISTENT MEMORY
    
    # Handle symptom report intent
    if inquiry_intent == "symptom_report":
        print(f"🔍 SYMPTOM_REPORT INTENT TRIGGERED")
        print(f"🔍 extracted_info keys:{list(extracted_info.keys())}")
        inquiry_obj = extracted_info.get("PromptOutputInquiry")  

        if inquiry_obj:
            symptoms = inquiry_obj.symptoms or []
            print(f"🔍 Found symptoms: {symptoms}")

        symptoms = inquiry_obj.symptoms or [] if inquiry_obj else []

        if not symptoms:
            # Continue conversation even on symptom collection issues
            return [UTILITIES.create_text_message(
                "I didn't catch all the symptom details. Could you describe your symptoms again? "
                "I remember our previous conversation, so you don't need to repeat your personal information."
            )]

        # ✅ SYMPTOMS COLLECTED - CONTINUE CONVERSATION (DON'T CLEAR)
        collected_symptoms = " ".join(symptoms)
        if inquiry_obj.additional_medical_information:
            collected_symptoms += " " + " ".join(inquiry_obj.additional_medical_information)

        # Save progress and continue
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        
        return handle_doctor_recommendation_from_symptoms(
            user_session=user_session,
            symptoms=collected_symptoms
        )

    # Handle booking intent  
    elif inquiry_intent == "booking":
        print(f"🔍 BOOKING INTENT TRIGGERED")
        print(f"🔍 extracted_info keys: {list(extracted_info.keys())}")
        
        booking_result = handle_booking_intent(extracted_info, user=user_session.active_patient_profile)
        
        # ✅ ALWAYS PRESERVE MEMORY - NEVER CLEAR
        # Save conversation progress
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        
        # Add context-aware follow-up
        if any(phrase in booking_result.lower() for phrase in [
            "appointment booked successfully", "booking confirmed"
        ]):
            # Successful booking - offer additional help
            follow_up = f"{booking_result}\n\nIs there anything else I can help you with? I'll remember this conversation if you need to make changes or book another appointment."
            return [UTILITIES.create_text_message(follow_up)]
        else:
            # Booking incomplete/failed - continue naturally
            return [UTILITIES.create_text_message(booking_result)]

    # Handle other intents/general conversation
    else:
        # ✅ CONTINUE CONVERSATION (DON'T CLEAR)
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        
        # Provide helpful continuation
        if response.closing_remark:
            follow_up = f"{response.closing_remark}\n\nI'll remember our conversation. Feel free to ask me anything else or let me know if you'd like to modify any information we discussed."
            return [UTILITIES.create_text_message(follow_up)]
        else:
            return [UTILITIES.create_text_message(
                "Is there anything else I can help you with? I remember our conversation, so you can ask follow-up questions or make changes to previous requests."
            )]


# ✅ OPTIONAL: Add explicit memory clearing for user control
def handle_reset_conversation(user_session):
    """Allow users to explicitly reset their conversation"""
    ConversationManager.clear_engine(user_session.user_phone_number)
    user_session.reset_ai_conversation()
    return [UTILITIES.create_text_message(
        "I've cleared our conversation history. We can start fresh! How can I help you today?"
    )]


# ✅ OPTIONAL: Add timeout-based cleanup (run periodically)
def cleanup_stale_conversations(hours_threshold=24):
    """Clean up conversations older than threshold"""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.now() - timedelta(hours=hours_threshold)
    
    # Find stale sessions
    stale_sessions = WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession.objects.filter(
        updated_at__lt=cutoff_time
    )
    
    for session in stale_sessions:
        if session.user_phone_number:
            ConversationManager.clear_engine(session.user_phone_number)
            session.reset_ai_conversation()
    
    print(f"🔍 Cleaned up {stale_sessions.count()} stale conversations")
```

## 🎯 **Enhanced AI Prompt for Context Awareness**

Update your AI prompt to handle context modifications better:

```python
PERSISTENT_CHATBOT_PROMPT = """
You are a helpful healthcare assistant. You maintain conversation context across multiple interactions.

IMPORTANT CONTEXT RULES:
1. Remember previous information provided by the user (name, age, location, preferences)
2. When users want to modify information, update your understanding naturally
3. Examples of context updates:
   - "Actually, I want a doctor in Meru instead of Nairobi" → Update location preference
   - "I prefer home visits now" → Update consultation mode
   - "I'm booking for my mother, not myself" → Switch patient context

4. If users provide conflicting information, ask for clarification:
   - "I see you mentioned Nairobi earlier, but now you want Meru. Should I look for doctors in Meru instead?"

5. Build on previous conversations naturally:
   - User: "Any cardiologists available?"
   - AI: "I remember you're in Nairobi and prefer clinic visits. Let me find cardiologists there."

CONVERSATION FLOW:
1. Greet returning users: "Hello again! How can I help you today?"
2. Reference previous context when relevant
3. Allow natural modifications of previous information
4. Continue building the conversation history

OUTPUT FORMAT: [Same as before - PromptOutputPersonalDetails, etc.]
"""
```

## 🚀 **Example Persistent Conversations**

### **Scenario 1: Location Change**
```
DAY 1:
User: Hi, I need a doctor
AI: Hello! I'd be happy to help. What's your name and where are you located?
User: I'm John, 30 years old, in Nairobi
AI: Nice to meet you John. What kind of medical help do you need?
User: I have a headache
AI: [Provides recommendations]

DAY 2:
User: Hi
AI: Hello again John! How can I help you today?
User: I want a doctor in Meru instead of Nairobi
AI: I understand - you'd like to find a doctor in Meru instead of Nairobi. What type of specialist are you looking for in Meru?
User: A cardiologist
AI: Looking for cardiologists in Meru for you, John...
```

### **Scenario 2: Building on Previous Booking**
```
CONVERSATION 1:
User: Book Dr Natalie for tomorrow 2pm
AI: Dr Natalie is not available at 2pm. Available times: 9am, 4pm, 6pm
User: Book 4pm
AI: Appointment booked successfully!

CONVERSATION 2 (Same day):
User: Can I change the time?
AI: I remember your appointment with Dr Natalie tomorrow at 4pm. What time would you prefer instead?
User: Make it 6pm
AI: I'll help you reschedule to 6pm...
```

### **Scenario 3: Family Bookings**
```
ONGOING CONVERSATION:
User: Book appointment for my mother
AI: I remember you're John from Nairobi. What's your mother's name and age?
User: Mary, 65 years old
AI: I'll help book an appointment for Mary (65) in Nairobi. What type of doctor does she need?
[Later in conversation...]
User: Actually book for my father instead
AI: I understand - you want to book for your father instead of your mother Mary. What's your father's name and age?
```

## 🔧 **Handle Context Updates in Booking**

Update your `handle_booking_intent` to be context-aware:

```python
def handle_booking_intent(extracted_info, user):
    booking_info = extracted_info.get("PromptOutputBooking")
    personal_info = extracted_info.get("PromptOutputPersonalDetails") 
    inquiry_info = extracted_info.get("PromptOutputInquiry")

    # Extract current request info
    doctor_name = booking_info.selected_doctor if booking_info else None
    current_location = personal_info.location if personal_info else None
    specialization = booking_info.specialization if booking_info else "general practitioner"
    
    # ✅ CONTEXT-AWARE LOCATION HANDLING
    # If no current location specified, this might be a location change request
    if not current_location:
        # Check if this is a location update (e.g., "doctor in Meru instead")
        # The AI should have this context in the conversation
        return "I'd be happy to help you find a doctor. Which location should I search in?"
    
    print(f"🔍 Context: doctor={doctor_name}, location={current_location}, specialization={specialization}")
    
    # Continue with your existing logic...
    # But now it can handle location changes naturally
```

## 🎯 **Benefits of Persistent Memory**

1. **Natural Conversation Flow**: "I want a doctor in Meru instead of Nairobi"
2. **No Repetition**: Users don't re-enter name, age, location every time
3. **Context Building**: Each conversation builds on previous ones
4. **Flexible Updates**: Easy to modify preferences without starting over
5. **Better UX**: Feels like talking to a human assistant who remembers

## 📋 **Implementation Steps**

1. **Replace** conversation handler with persistent version
2. **Update** AI prompt for context awareness
3. **Test** scenarios:
   - Location changes
   - Multiple bookings
   - Returning users
   - Context modifications
4. **Optional**: Add explicit reset command and timeout cleanup

This creates a much more natural, ChatGPT-like experience where the AI remembers and builds on previous conversations!