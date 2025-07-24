# Enhanced version of your existing function with ChatGPT-like features
# Keeps the same parameter structure: (user_session, message_text)

def handle_conversation_mode_chatbot_message_v3(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):
    """
    Enhanced ChatGPT-like version of your existing function
    Maintains same parameters but adds structured messaging and pattern learning
    """
    try:
        # NEW: Learn user communication patterns
        user_session.learn_user_patterns(message_text)
        
        # Check if we should start a new session based on the message
        if user_session.should_start_new_session(message_text):
            user_session.start_new_session("user_requested")
        
        # NEW: Add user message to structured conversation history
        user_session.add_message_to_conversation('user', message_text, {
            'processing_start': datetime.now().isoformat(),
            'session_id': user_session.current_session_id
        })
        
        # NEW: Start typing indicator for better UX
        user_session.start_typing_indicator()
        
        # Get the enhanced autonomous AI engine 
        ai_engine = get_enhanced_autonomous_engine(user_session)
        
        # Generate response with enhanced context
        response = ai_engine.generate_autonomous_response(message_text, user_session)
        
        # NEW: Add assistant response to structured conversation history
        user_session.add_message_to_conversation('assistant', response, {
            'processing_end': datetime.now().isoformat(),
            'response_type': 'autonomous'
        })
        
        return response
        
    except Exception as e:
        print(f"❌ Error in chatbot handler: {e}")
        
        # NEW: Add error to conversation history for debugging
        try:
            user_session.add_message_to_conversation('system', f"Error occurred: {str(e)}")
        except:
            pass
            
        # Return your existing fallback structure
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


# Enhanced AI Engine that integrates with your existing architecture
class EnhancedAutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()
        self.persistent_user_data = {}
        
        # Keep your existing function mappings
        from .promptingmodels import (
            handle_onboarding_function, handle_user_registration, handle_user_login,
            handle_profile_listing, handle_profile_selection,
            handle_doctor_recommendation_from_symptoms_function, search_doctors_by_criteria,
            doctor_availability, create_appointment_with_doctor, appointment_date,
            appointment_day, handle_payment_time_selection, handle_payment_method_selection,
            handle_mpesa_number_input, get_my_appointments, cancel_appointment,
            reschedule_appointment, get_appointment_details
        )
        
        self.function_map = {
            "handle_onboarding_function": handle_onboarding_function,
            "handle_user_registration": handle_user_registration,
            "handle_user_login": handle_user_login,
            "handle_profile_listing": handle_profile_listing,
            "handle_profile_selection": handle_profile_selection,
            "handle_doctor_recommendation_from_symptoms_function": handle_doctor_recommendation_from_symptoms_function,
            "search_doctors_by_criteria": search_doctors_by_criteria,
            "doctor_availability": doctor_availability,
            "create_appointment_with_doctor": create_appointment_with_doctor,
            "appointment_date": appointment_date,
            "appointment_day": appointment_day,
            "handle_payment_time_selection": handle_payment_time_selection,
            "handle_payment_method_selection": handle_payment_method_selection,
            "handle_mpesa_number_input": handle_mpesa_number_input,
            "get_my_appointments": get_my_appointments,
            "cancel_appointment": cancel_appointment,
            "reschedule_appointment": reschedule_appointment,
            "get_appointment_details": get_appointment_details,
        }

    def get_chatgpt_context(self, user_session) -> List[Dict]:
        """
        Build ChatGPT-like context using the user_session object
        """
        context = []
        
        # 1. Start with your existing base prompt
        context.append({
            "role": "system", 
            "content": DEFAULT_CHATBOT_BASE_PROMPT
        })
        
        # 2. Add user context information
        user_info_parts = []
        
        if user_session.get_full_name():
            user_info_parts.append(f"User: {user_session.get_full_name()}")
        else:
            user_info_parts.append(f"User phone: {user_session.user_phone_number}")
        
        # Add communication preferences if learned
        if hasattr(user_session, 'preferred_communication_style') and user_session.preferred_communication_style:
            user_info_parts.append(f"Prefers {user_session.preferred_communication_style} responses")
        
        # Add important user info
        if user_session.important_user_info:
            for key, value in user_session.important_user_info.items():
                if key not in ['user_id', 'patient_id'] and value:
                    user_info_parts.append(f"{key}: {value}")
        
        # Add current session context
        if user_session.session_context:
            context_items = []
            for key, value in user_session.session_context.items():
                if value:
                    context_items.append(f"{key}: {value}")
            if context_items:
                user_info_parts.append(f"Current session: {'; '.join(context_items)}")
        
        if user_info_parts:
            context.append({
                "role": "system",
                "content": "; ".join(user_info_parts)
            })
        
        # 3. Add compressed memory if available
        if hasattr(user_session, 'long_term_memory') and user_session.long_term_memory:
            if user_session.long_term_memory.get('compressed_history'):
                memory_summary = "; ".join([
                    item['summary'] for item in user_session.long_term_memory['compressed_history'][-3:]
                ])
                context.append({
                    "role": "system",
                    "content": f"Previous conversation context: {memory_summary}"
                })
        
        # 4. Add conversation history in ChatGPT format
        if user_session.ai_conversation_history:
            if isinstance(user_session.ai_conversation_history[0], dict):
                # Already in structured format - use directly
                context.extend(user_session.ai_conversation_history)
            else:
                # Convert your existing format to ChatGPT format
                for i, msg in enumerate(user_session.ai_conversation_history):
                    role = 'user' if i % 2 == 0 else 'assistant'
                    context.append({
                        'role': role,
                        'content': str(msg)
                    })
        
        return context

    def generate_autonomous_response(self, message: str, user_session) -> str:
        """
        Enhanced response generation with ChatGPT-like context
        """
        try:
            # Build ChatGPT-like context
            messages = self.get_chatgpt_context(user_session)
            
            # Add current message if not already included
            if not messages or messages[-1].get('content') != message:
                messages.append({"role": "user", "content": message})
            
            from .promptingmodels import HEALTHCARE_TOOLS
            
            # Call OpenAI with your existing tools
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=HEALTHCARE_TOOLS,       
                tool_choice="auto",           
                temperature=0.3
            )
          
            assistant_message = response.choices[0].message

            # Handle function calling (same as your existing logic)
            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔍 AI calling function: {function_name} with args: {function_args}")
                
                # Execute the function
                function_result = self.execute_function_call(function_name, function_args, user_session)
                
                # NEW: Update session context based on function calls
                self._update_session_context_from_function(user_session, function_name, function_args)
                
                # Add function call and result to conversation
                messages.append({
                    "role": "assistant", 
                    "content": None,
                    "tool_calls": [tool_call.model_dump()]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_result
                })

                # Get AI's final response after function execution
                final_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.3
                )
                
                final_content = final_response.choices[0].message.content
                
                # NEW: Check if conversation should be compressed
                if hasattr(user_session, 'ai_conversation_history') and len(user_session.ai_conversation_history) > 20:
                    self._compress_conversation_memory(user_session)
                
                return final_content
            else:
                # No function call, just return AI's response
                return assistant_message.content

        except Exception as e:
            print(f"❌ Error in autonomous response: {e}")
            return "I'm sorry, I encountered an error. Please try again."

    def execute_function_call(self, function_name: str, arguments: dict, user_session) -> str:
        """Execute function calls (same as your existing logic)"""
        if function_name in self.function_map:
            function = self.function_map[function_name]
            try:
                result = function(user_session, **arguments)
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, str) and "issue" in item.lower():
                            print(f"Detected issue message in function result: {item}")
                            return "Sorry, I encountered an issue while processing your request. Please try again."
                return str(result)
            except Exception as e:
                print(f"Error executing {function_name}: {e}")
                return f"Error executing {function_name}: {str(e)}"
        else:
            return f"Function {function_name} not found"

    def _update_session_context_from_function(self, user_session, function_name: str, function_args: dict):
        """Update session context based on function calls"""
        if function_name == "handle_doctor_recommendation_from_symptoms_function":
            symptoms = function_args.get('symptoms', '')
            if symptoms:
                user_session.set_session_context_value('current_symptoms', symptoms)
                user_session.set_session_context_value('consultation_type', 'symptom_based')
        
        elif function_name == "search_doctors_by_criteria":
            search_text = function_args.get('search_text', '')
            if search_text:
                user_session.set_session_context_value('current_search', search_text)
                user_session.set_session_context_value('consultation_type', 'specialist_search')

    def _compress_conversation_memory(self, user_session):
        """Compress conversation memory when it gets too long"""
        if not hasattr(user_session, 'ai_conversation_history'):
            return
        
        conversation = user_session.ai_conversation_history
        if len(conversation) <= 20:
            return
        
        # Keep recent messages (last 10)
        recent_messages = conversation[-10:]
        
        # Compress older messages
        older_messages = conversation[:-10]
        summary = self._summarize_conversation_segment(older_messages)
        
        # Store in long_term_memory
        if not hasattr(user_session, 'long_term_memory') or not user_session.long_term_memory:
            user_session.long_term_memory = {}
        
        if 'compressed_history' not in user_session.long_term_memory:
            user_session.long_term_memory['compressed_history'] = []
        
        user_session.long_term_memory['compressed_history'].append({
            'summary': summary,
            'message_count': len(older_messages),
            'compressed_at': datetime.now().isoformat()
        })
        
        # Update conversation history to keep only recent messages
        user_session.ai_conversation_history = recent_messages
        user_session.save()

    def _summarize_conversation_segment(self, messages: List) -> str:
        """Summarize a segment of conversation"""
        if not messages:
            return ""
        
        # Extract key information
        topics = []
        actions = []
        
        for msg in messages:
            content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
            
            # Identify health topics
            if any(word in content.lower() for word in ['pain', 'symptom', 'doctor', 'appointment']):
                topics.append(content[:50])
            
            # Identify actions taken
            if any(word in content.lower() for word in ['booked', 'scheduled', 'selected', 'confirmed']):
                actions.append(content[:50])
        
        summary_parts = []
        if topics:
            summary_parts.append(f"Discussed: {'; '.join(topics[:3])}")
        if actions:
            summary_parts.append(f"Actions: {'; '.join(actions[:2])}")
        
        return "; ".join(summary_parts) if summary_parts else "General health consultation"


# Enhanced engine storage (keyed by user_session.id to avoid needing phone number)
enhanced_engines: Dict[int, EnhancedAutonomousAIEngine] = {}

def get_enhanced_autonomous_engine(user_session) -> EnhancedAutonomousAIEngine:
    """Get or create an enhanced autonomous engine for a user session"""
    session_key = user_session.id  # Use session ID instead of phone number
    
    if session_key not in enhanced_engines:
        enhanced_engines[session_key] = EnhancedAutonomousAIEngine()
    
    return enhanced_engines[session_key]


# MINIMAL INTEGRATION STEPS:
"""
1. Add these fields to your WhatsappPlugin1UserSession model:
   - conversation_title = models.CharField(max_length=200, blank=True, null=True)
   - long_term_memory = models.JSONField(default=dict, blank=True)
   - conversation_patterns = models.JSONField(default=dict, blank=True) 
   - preferred_communication_style = models.CharField(max_length=100, blank=True, null=True)
   - is_waiting_for_response = models.BooleanField(default=False)

2. Add these methods to your WhatsappPlugin1UserSession model:
   - add_message_to_conversation()
   - learn_user_patterns()
   - start_typing_indicator()

3. Replace your handle_conversation_mode_chatbot_message() with the enhanced version above

4. Run: python manage.py makemigrations && python manage.py migrate

That's it! Your existing webhook structure and session creation remains unchanged.
The phone number comes from the webhook data and the session is already created.
"""