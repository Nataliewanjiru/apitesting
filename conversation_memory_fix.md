# Conversation Memory Fix

## 🚨 **Root Cause Found**

In your `handle_conversation_mode_chatbot_message_v2` function, the engine is being cleared **BEFORE** intent processing, which destroys memory on booking failures.

**Current problematic flow:**
```python
# 1. Generate response
response, error = ai_engine.generate_response(message=message_text)

# 2. If no next_question, CLEAR ENGINE IMMEDIATELY
if next_question is not None and next_question.strip() != "":
    return UTILITIES.create_text_message(f"{next_question}\n")

# 3. MEMORY ALREADY CLEARED HERE!
user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
ConversationManager.clear_engine(user_session.user_phone_number)  # ← PROBLEM!

# 4. Then process intents (but memory is gone!)
elif inquiry_intent == "booking":
    # Memory already cleared!
```

## 🔧 **The Fix**

Replace your `handle_conversation_mode_chatbot_message_v2` function with this corrected version:

```python
def handle_conversation_mode_chatbot_message_v2(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):  
    # Reuse existing engine for this user
    ai_engine = ConversationManager.get_engine(user_session.user_phone_number)
    
    # Only load history ONCE (when engine is first created)
    if not ai_engine.memory.chat_memory.messages:
        ai_engine.load_serialized_history_into_memory(
            user_session.ai_conversation_history, 
            ai_engine.memory
        )
    
    response, error = ai_engine.generate_response(message=message_text)
    
    # Handle AI error
    if not response:
        ConversationManager.clear_engine(user_session.user_phone_number) 
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

    # ✅ CONTINUE CONVERSATION - DON'T CLEAR ENGINE YET
    if next_question is not None and next_question.strip() != "":
        return UTILITIES.create_text_message(f"{next_question}\n")
    
    # ✅ PROCESS INTENTS WITH MEMORY INTACT
    
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
            # ❌ SYMPTOM COLLECTION FAILED - CLEAR ENGINE
            user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
            ConversationManager.clear_engine(user_session.user_phone_number)
            user_session.reset_ai_conversation()
            user_session.set_state(
                session_state=WHATSAPP_PLUGIN1.WhatsappPlugin1UserSessionStates.DEFAULT.value
            )
            
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

        # ✅ SYMPTOMS COLLECTED SUCCESSFULLY - CLEAR ENGINE
        collected_symptoms = " ".join(symptoms)
        if inquiry_obj.additional_medical_information:
            collected_symptoms += " " + " ".join(
                inquiry_obj.additional_medical_information
            )

        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        ConversationManager.clear_engine(user_session.user_phone_number)
        user_session.reset_ai_conversation()
        user_session.set_state(
            session_state=WHATSAPP_PLUGIN1.WhatsappPlugin1UserSessionStates.DEFAULT.value
        )

        return handle_doctor_recommendation_from_symptoms(
            user_session=user_session,
            symptoms=collected_symptoms
        )

    # Handle booking intent
    elif inquiry_intent == "booking":
        print(f"🔍 BOOKING INTENT TRIGGERED")
        print(f"🔍 extracted_info keys: {list(extracted_info.keys())}")
        
        booking_result = handle_booking_intent(extracted_info, user=user_session.active_patient_profile)
        
        # ✅ CHECK IF BOOKING WAS SUCCESSFUL OR NEEDS CONTINUATION
        if any(phrase in booking_result.lower() for phrase in [
            "not available", "error", "couldn't find", "failed", 
            "would you like", "please let me know", "here are some"
        ]):
            # ❌ BOOKING INCOMPLETE/FAILED - KEEP CONVERSATION GOING
            print(f"🔍 Booking incomplete, preserving memory")
            return [UTILITIES.create_text_message(booking_result)]
        else:
            # ✅ BOOKING SUCCESSFUL - CLEAR ENGINE
            print(f"🔍 Booking successful, clearing memory")
            user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
            ConversationManager.clear_engine(user_session.user_phone_number)
            user_session.reset_ai_conversation()
            user_session.set_state(
                session_state=WHATSAPP_PLUGIN1.WhatsappPlugin1UserSessionStates.DEFAULT.value
            )
            
            return [UTILITIES.create_text_message(booking_result)]

    # Handle other intents/fallback
    else:
        # ✅ CONVERSATION COMPLETE - CLEAR ENGINE
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        ConversationManager.clear_engine(user_session.user_phone_number)
        user_session.reset_ai_conversation()
        user_session.set_state(
            session_state=WHATSAPP_PLUGIN1.WhatsappPlugin1UserSessionStates.DEFAULT.value
        )
        
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

## 🎯 **Key Changes Made**

### **1. Moved Engine Clearing Logic**
**❌ Before:** Clear engine before processing intents
**✅ After:** Clear engine only when appropriate for each intent

### **2. Smart Booking Result Detection**
```python
# Check if booking needs continuation
if any(phrase in booking_result.lower() for phrase in [
    "not available", "error", "couldn't find", "failed", 
    "would you like", "please let me know", "here are some"
]):
    # Keep conversation going
    return [UTILITIES.create_text_message(booking_result)]
```

### **3. Memory Preservation on Failures**
- **Booking failure** → Memory preserved, conversation continues
- **Symptom failure** → Memory cleared (error case)
- **Successful completion** → Memory cleared (normal flow)

## 🚀 **Expected Results After Fix**

**Scenario 1: Booking Failure (Memory Preserved)**
```
User: Hi I want to book Dr Natalie Wanjiru
AI: What type of consultation...
[Conversation builds to 8 messages]
User: Yes (confirm booking)
AI: Natalie Wanjiru is not available at that time.
🔍 Booking incomplete, preserving memory
User: What time is she available?  ← MEMORY INTACT!
AI: [Continues with full context]
```

**Scenario 2: Successful Booking (Memory Cleared)**
```
User: Book Dr John for tomorrow 2pm
AI: What type of consultation...
User: Clinic visit
AI: Appointment booked successfully!
🔍 Booking successful, clearing memory
[Conversation ends cleanly]
```

## 📋 **Implementation Steps**

1. **Replace your entire `handle_conversation_mode_chatbot_message_v2` function** with the fixed version above
2. **Test booking failure scenario** - memory should be preserved
3. **Test successful booking** - memory should be cleared
4. **Test symptom collection** - memory clearing as appropriate

This fix ensures that **booking failures don't destroy conversation context**, allowing users to continue asking follow-up questions naturally!