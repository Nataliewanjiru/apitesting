# IMPROVED ChatGPT-like Functions for Your WhatsApp Bot
# These enhance your existing functions with better ChatGPT-like behavior

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import json
from openai import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ENHANCED VERSION OF YOUR MAIN HANDLER
def handle_conversation_mode_chatbot_message_v3(phone_number: str, message: str) -> str:
    """
    Enhanced ChatGPT-like main entry point with structured message handling
    """
    try:
        # Get or create user session
        user_session, newly_created = WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
        
        # NEW: Learn user patterns from this message
        user_session.learn_user_patterns(message)
        
        # Check if we should start a new session based on the message
        if user_session.should_start_new_session(message):
            user_session.start_new_session("user_requested")
        
        # NEW: Add user message to structured conversation history
        user_session.add_message_to_conversation('user', message, {
            'processing_start': datetime.now().isoformat(),
            'session_id': user_session.current_session_id
        })
        
        # NEW: Start typing indicator for better UX
        user_session.start_typing_indicator()
        
        # Get the autonomous AI engine for this user
        ai_engine = get_enhanced_autonomous_engine(user_session)
        
        # Generate response with enhanced context
        response = ai_engine.generate_autonomous_response(message, user_session)
        
        # NEW: Add assistant response to structured conversation history
        user_session.add_message_to_conversation('assistant', response, {
            'processing_end': datetime.now().isoformat(),
            'response_type': 'function_call' if 'function_result' in response else 'direct'
        })
        
        return response
        
    except Exception as e:
        print(f"❌ Error in main handler: {e}")
        # NEW: Add error to conversation history for debugging
        try:
            user_session.add_message_to_conversation('system', f"Error occurred: {str(e)}")
        except:
            pass
        return "I'm sorry, I encountered an error. Please try again."


# ENHANCED SESSION MEMORY MANAGER with ChatGPT-like features
class EnhancedSessionMemoryManager:
    """Enhanced memory manager with ChatGPT-like capabilities"""
    
    def __init__(self, session_timeout_hours: int = 24):
        self.session_timeout_hours = session_timeout_hours
        self.session_memories: Dict[str, ConversationBufferMemory] = {}
        self.session_last_activity: Dict[str, datetime] = {}
        self.session_contexts: Dict[str, Dict] = {}
        # NEW: Track conversation themes and patterns
        self.conversation_themes: Dict[str, List[str]] = {}
        self.user_interaction_patterns: Dict[str, Dict] = {}
    
    def get_session_id(self, user_session) -> str:
        """Generate a unique session ID based on user session"""
        return f"{user_session.user_phone_number}_{user_session.current_session_id or user_session.id}"
    
    def get_conversation_context_for_ai(self, user_session) -> List[Dict]:
        """
        NEW: Get ChatGPT-like conversation context with system prompts and memory
        """
        context = []
        
        # 1. System context with user information
        system_context = self._build_system_context(user_session)
        context.append({
            'role': 'system',
            'content': system_context
        })
        
        # 2. Add compressed memory if available
        if user_session.long_term_memory and user_session.long_term_memory.get('compressed_history'):
            memory_summary = "; ".join([
                item['summary'] for item in user_session.long_term_memory['compressed_history'][-3:]
            ])
            context.append({
                'role': 'system',
                'content': f"Previous conversation context: {memory_summary}"
            })
        
        # 3. Add structured conversation history (ChatGPT format)
        if hasattr(user_session, 'ai_conversation_history') and user_session.ai_conversation_history:
            # If already in structured format, use directly
            if isinstance(user_session.ai_conversation_history[0], dict):
                context.extend(user_session.ai_conversation_history)
            else:
                # Convert old format to new structured format
                for i, msg in enumerate(user_session.ai_conversation_history):
                    role = 'user' if i % 2 == 0 else 'assistant'
                    context.append({
                        'role': role,
                        'content': str(msg)
                    })
        
        return context
    
    def _build_system_context(self, user_session) -> str:
        """Build comprehensive system context like ChatGPT"""
        context_parts = []
        
        # User basic info
        if user_session.get_full_name():
            context_parts.append(f"User: {user_session.get_full_name()}")
        
        # Communication preferences
        if hasattr(user_session, 'preferred_communication_style') and user_session.preferred_communication_style:
            context_parts.append(f"Communication style: {user_session.preferred_communication_style}")
        
        # Important user info
        if user_session.important_user_info:
            for key, value in user_session.important_user_info.items():
                if key not in ['user_id', 'patient_id'] and value:
                    context_parts.append(f"{key}: {value}")
        
        # Current session context
        if user_session.session_context:
            ongoing_items = []
            for key, value in user_session.session_context.items():
                if value:
                    ongoing_items.append(f"{key}: {value}")
            if ongoing_items:
                context_parts.append(f"Current session context: {'; '.join(ongoing_items)}")
        
        # Conversation patterns
        session_id = self.get_session_id(user_session)
        if session_id in self.user_interaction_patterns:
            patterns = self.user_interaction_patterns[session_id]
            if patterns.get('avg_message_length'):
                style = 'brief' if patterns['avg_message_length'] < 10 else 'detailed'
                context_parts.append(f"User prefers {style} responses")
        
        return "; ".join(context_parts) if context_parts else "New user conversation"
    
    def update_conversation_patterns(self, user_session, message: str, response: str):
        """NEW: Track conversation patterns for personalization"""
        session_id = self.get_session_id(user_session)
        
        if session_id not in self.user_interaction_patterns:
            self.user_interaction_patterns[session_id] = {
                'message_count': 0,
                'avg_message_length': 0,
                'common_topics': [],
                'response_preferences': {},
                'time_patterns': []
            }
        
        patterns = self.user_interaction_patterns[session_id]
        patterns['message_count'] += 1
        
        # Update average message length
        msg_length = len(message.split())
        current_avg = patterns['avg_message_length']
        patterns['avg_message_length'] = (current_avg * (patterns['message_count'] - 1) + msg_length) / patterns['message_count']
        
        # Track time patterns
        patterns['time_patterns'].append(datetime.now().hour)
        patterns['time_patterns'] = patterns['time_patterns'][-20:]  # Keep last 20


# ENHANCED AUTONOMOUS AI ENGINE with ChatGPT-like capabilities
class EnhancedAutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()
        self.session_manager = EnhancedSessionMemoryManager(session_timeout_hours=24)
        self.persistent_user_data = {}
        
        # Map function names to actual functions (same as your original)
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

    def generate_autonomous_response(self, message: str, user_session) -> str:
        """
        Enhanced response generation with ChatGPT-like context management
        """
        try:
            # Load persistent user data
            user_phone = user_session.user_phone_number
            persistent_data = self.persistent_user_data.get(user_phone, {})
            
            # NEW: Use enhanced context builder instead of basic messages
            messages = self.session_manager.get_conversation_context_for_ai(user_session)
            
            # Add current message if not already in context
            if not messages or messages[-1].get('content') != message:
                messages.append({"role": "user", "content": message})
            
            from .promptingmodels import HEALTHCARE_TOOLS
            
            # Call OpenAI with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=HEALTHCARE_TOOLS,       
                tool_choice="auto",           
                temperature=0.3
            )
          
            assistant_message = response.choices[0].message

            # Check if AI wants to call a function
            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔍 AI calling function: {function_name} with args: {function_args}")
                
                # Execute the function
                function_result = self.execute_function_call(function_name, function_args, user_session)
                
                # NEW: Update session context and patterns
                self._update_session_context_from_function(user_session, function_name, function_args)
                self.session_manager.update_conversation_patterns(user_session, message, function_result)
                
                # Update persistent user data if relevant
                self._update_persistent_user_data(user_phone, user_session)
                
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
                content = assistant_message.content
                
                # NEW: Update patterns and user data
                self.session_manager.update_conversation_patterns(user_session, message, content)
                self._update_persistent_user_data(user_phone, user_session)
                
                return content

        except Exception as e:
            print(f"❌ Error in autonomous response: {e}")
            return "I'm sorry, I encountered an error. Please try again."

    def _compress_conversation_memory(self, user_session):
        """NEW: Compress conversation memory like ChatGPT"""
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
        if not user_session.long_term_memory:
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

    def _summarize_conversation_segment(self, messages: List[Dict]) -> str:
        """NEW: Summarize a segment of conversation"""
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

    def execute_function_call(self, function_name: str, arguments: dict, user_session) -> str:
        """Execute function calls with session context (same as your original)"""
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

    def _update_persistent_user_data(self, user_phone: str, user_session):
        """Update persistent user data store (enhanced version)"""
        if not user_phone:
            return
        
        data = self.persistent_user_data.get(user_phone, {})
        
        # Update with important user info and profile details
        data.update(user_session.important_user_info or {})
        data.update({
            "user_first_name": user_session.user_first_name,
            "user_last_name": user_session.user_last_name,
            "user_middle_name": user_session.user_middle_name,
            "user_sex": user_session.user_sex,
            "user_age": user_session.user_age,
            "last_updated": datetime.now().isoformat(),
        })
        
        # NEW: Add conversation patterns to persistent data
        session_id = self.session_manager.get_session_id(user_session)
        if session_id in self.session_manager.user_interaction_patterns:
            data["interaction_patterns"] = self.session_manager.user_interaction_patterns[session_id]
        
        self.persistent_user_data[user_phone] = data
    
    def _update_session_context_from_function(self, user_session, function_name: str, function_args: dict):
        """Update session context based on function calls (enhanced version)"""
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
        
        elif function_name == "create_appointment_with_doctor":
            user_session.set_session_context_value('appointment_status', 'booking_in_progress')


# Global dictionary to store enhanced engines per user session
enhanced_autonomous_engines: Dict[str, EnhancedAutonomousAIEngine] = {}

def get_enhanced_autonomous_engine(user_session) -> EnhancedAutonomousAIEngine:
    """Get or create an enhanced autonomous engine for a user session"""
    session_key = f"{user_session.user_phone_number}_{user_session.id}"
    
    if session_key not in enhanced_autonomous_engines:
        enhanced_autonomous_engines[session_key] = EnhancedAutonomousAIEngine()
    
    return enhanced_autonomous_engines[session_key]


# ENHANCED UTILITY FUNCTIONS
def get_enhanced_user_session_info(phone_number: str) -> dict:
    """
    Enhanced version of get_user_session_info with ChatGPT-like details
    """
    try:
        user_session, _ = WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
        
        # Get conversation statistics
        conversation_stats = {
            'total_messages': len(user_session.ai_conversation_history) if user_session.ai_conversation_history else 0,
            'conversation_title': getattr(user_session, 'conversation_title', None),
            'preferred_style': getattr(user_session, 'preferred_communication_style', None),
        }
        
        # Get memory information
        memory_info = {
            'has_long_term_memory': bool(getattr(user_session, 'long_term_memory', {})),
            'compressed_sessions': len(getattr(user_session, 'long_term_memory', {}).get('compressed_history', [])),
        }
        
        return {
            'current_session_id': user_session.current_session_id,
            'last_session_reset': user_session.last_session_reset.isoformat() if user_session.last_session_reset else None,
            'session_context': user_session.session_context,
            'important_user_info': user_session.important_user_info,
            'session_state': user_session.session_state,
            'is_authenticated': bool(user_session.linked_user),
            'has_active_patient': bool(user_session.active_patient_profile),
            'previous_sessions_count': len(user_session.previous_ai_conversations),
            'conversation_stats': conversation_stats,
            'memory_info': memory_info
        }
        
    except Exception as e:
        print(f"❌ Error getting enhanced session info: {e}")
        return {'error': str(e)}


# USAGE EXAMPLE: How to integrate these enhancements
"""
# Replace your existing function calls with these enhanced versions:

# OLD:
response = handle_conversation_mode_chatbot_message_v2(message)

# NEW:
response = handle_conversation_mode_chatbot_message_v3(phone_number, message)

# Get enhanced session info:
session_info = get_enhanced_user_session_info(phone_number)

# The enhanced engine will automatically:
# 1. Use structured message format
# 2. Compress memory when needed
# 3. Learn user patterns
# 4. Provide ChatGPT-like context to AI
# 5. Track conversation themes and preferences
"""