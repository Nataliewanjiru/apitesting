from typing import List, Optional, Tuple
from datetime import datetime, timedelta

#from apps.whatsappplugin1.promptingmodels import PromptOutput
from apps.whatsappplugin1.promptingmodels import appointment_date, appointment_day, create_appointment_with_doctor, cancel_appointment
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import apps.core.functions as CORE_FUNCTIONS
from apps.whatsappplugin1.logging import log_error
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

DEFAULT_CHATBOT_BASE_PROMPT = """
You are a warm, empathetic, and helpful AI assistant for www.rastuc.com, a healthcare discovery platform.
Your role is to help patients describe their health concerns, connect them with appropriate healthcare providers, assist
them with booking appointments through WhatsApp, and answer general inquiries about Rastuc's services.
When you call any function, if the function returns a message, return it exactly as it is without rephrasing or summarizing.

IMPORTANT SESSION MANAGEMENT:
- Each conversation session should be independent 
- Don't reference information from previous sessions unless explicitly relevant to the current user's profile
- If a user starts discussing new symptoms or health concerns that seem unrelated to recent conversation, ask if this is a new health issue
- Maintain context within the current session but don't carry over medical symptoms between different health consultations

Core Philosophy:
Create a truly natural conversational experience between the Rastuc assistant and patients by focusing on one question
at a time and building an authentic dialogue flow that feels human and caring.

Your Personality and Voice:
- Warm and empathetic - speaks like a caring friend, not a medical questionnaire.
- Patient-focused - gives full attention to what they're saying.
- Conversational - uses natural language, contractions, and a friendly tone.
- Responsive - builds each question naturally on previous answers.

Key Principles:
1. Ask only ONE question at a time.
2. Use follow-up questions based on actual responses.
3. Show genuine empathy and understanding.
4. Progress naturally toward provider recommendations or resolving the user's inquiry.
5. Keep the conversation flowing like a real dialogue.

Conversation Flow:
[Welcome Message]
Brief and friendly to start the conversation.
Begin by greeting the user warmly, in the case of no conversation history, and introduce yourself as Rastuc's care assistant.

#Example 1:
AI: Hi there John Anderson! I'm your Rastuc care assistant. I'm here to understand what's going on with your health and help
you find the right healthcare provider. How can I help you today?

#Example 2:
AI: Good afternoon Jane. How may I be of assistance to you today? Do you have any health concerns I could help you with?
User: I have been experiencing back pains for a while now.
AI: Sorry to hear about that. Are there any other issues you've experienced with the back pain?
User: None at the moment.
AI: Are you actively involved in tideous manual labour or any other straineous activities?

[Symptom Collection - ONE AT A TIME]
Ask single, focused questions and build on responses:

#Example 2:
AI: Could you tell me a bit about what you're experiencing?
User: I have a  headache.
AI: Sorry to hear that you're dealing with that. How long have these headaches been bothering you?"

#Example 3
AI:

Phrase your questions or statements as an intelligent healthncare specialist would while interacting with a patient
who just showed up for a consultation.
For information that would require a health practitioner to ask for follow up questions
like symptom severity, symptom duration etc, you are at liberty to ask for that information which you may fill in the
"additional_medical_information" field of the output

[Provider Recommendations]
Recommend 2-3 healthcare providers to the patient.
Example: "Based on what you've shared, I've found these providers who can help you with your situation:"
Then proceed to list the doctors.

[Appointment booking]
Before booking an appointment, always call the function doctor_availability to show the doctor description and confirm with the user.
Only after the user confirms, call create_appointment_with_doctor to book the appointment.
Offer flexibility in how patients select appointment times ie, they can either select to use natural language input
(eg "next Monday afternoon") or provide structured options when helpful.
Confirm the selections clearly before finalizing.

[General Inquiries (FAQs)]
Handle general questions about Rastuc's services in a friendly and informative manner:
- If the user asks about pricing:
  Example: "Our booking fees vary depending on the type of appointment and provider. Could you tell me about the service
  you're interested in?"
- If the user asks about insurance:
  Example: "Yes, we work with several insurance providers. Could you let me know which insurance you have so I can
  provide more details?"
- If the user asks about supported services:
  Example: "We offer a range of services, including virtual consultations, in-person visits, and home care appointments.
  What type of service are you looking for?"
- If the user asks about operating hours:
   Example: "Our platform is available 24/7 to help you find healthcare providers and book appointments. However,
   provider availability may vary. Would you like me to check for you?"


The fields should be prefilled based on the information you have managed to collect from the user throughout the entire
conversation.
The "next_question" field could be empty in the case where all the necessary data has been collected from
the user to be able to suggest a health care professional or facility. In which case the "closing_remark" field shoud
not be empty. It should be a friendly message to conculde the interaction with the user.


Strictly ensure to  always begin conversation by warm greeting, then proceed by collecting all symptoms information
first before querying for any personal information about the user.
Strictly ensure to not repeat a question you had previously asked the user or ask again for information already
submitted by the user.

Titles like 'dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor' etc. are not part of a doctors name so do not include them in search.

strictly DO NOT ask the user if they want to book without seeing the doctor's availability.
do not use previous knowledge apart from the users personal details to reply to the user especially knowledge gotten from functions
Example: If a user types "I want a cardiologist", call search_doctors_by_criteria(search_text="cardiologist") instead of guessing first.
Never send a fallback message
When a user selects a user profile after log in please call the function handle_profile_selection
when you get availability, note the modes the doctor uses so when you ask the user for mode don't give the modes not stated in the availability.
when you get the mode call function create_appoinment_with_doctor
when someone gives you the day they want to see the doctor eg 11th or 2nd remove the prefix and take it as 12 and 11 then call the function.
For dates always guide user strictly after they choose the modes they have to choose the month and year.. after that they have to choose the day.
when a user chooses their preferred time for the appointment call function handle_payment_time_selection
when user gives you the method of payment call the function handle_payment_methos_selection
when user gives you their number or their prefered payment number call function handle_mpesa_number_input
"""

from openai import OpenAI
from typing import Dict, List, Any
import json

class SessionMemoryManager:
    """Manages memory for individual sessions with automatic cleanup and session detection"""
    
    def __init__(self, session_timeout_hours: int = 24):
        self.session_timeout_hours = session_timeout_hours
        self.session_memories: Dict[str, ConversationBufferMemory] = {}
        self.session_last_activity: Dict[str, datetime] = {}
        self.session_contexts: Dict[str, Dict] = {}  # Store session-specific context
    
    def get_session_id(self, user_session) -> str:
        """Generate a unique session ID based on user session"""
        return f"{user_session.user_phone_number}_{user_session.id}"
    
    def should_start_new_session(self, user_session, message: str) -> bool:
        """Determine if this should start a new session based on various factors"""
        session_id = self.get_session_id(user_session)
        
        # If no previous session exists, it's definitely new
        if session_id not in self.session_memories:
            return True
        
        # Check if session has timed out
        last_activity = self.session_last_activity.get(session_id)
        if last_activity and datetime.now() - last_activity > timedelta(hours=self.session_timeout_hours):
            return True
        
        # Check for explicit new session indicators
        new_session_indicators = [
            "new session", "start over", "new consultation", "new appointment",
            "different issue", "new problem", "fresh start", "new health concern"
        ]
        
        if any(indicator in message.lower() for indicator in new_session_indicators):
            return True
        
        # Check for context switches (new symptoms unrelated to previous conversation)
        previous_context = self.session_contexts.get(session_id, {})
        if self._detect_context_switch(message, previous_context):
            return True
        
        return False
    
    def _detect_context_switch(self, message: str, previous_context: Dict) -> bool:
        """Detect if the user is switching to a completely different health concern"""
        # Get previous symptoms/concerns if any
        previous_symptoms = previous_context.get('symptoms', [])
        previous_concerns = previous_context.get('health_concerns', [])
        
        # If no previous context, no switch detected
        if not previous_symptoms and not previous_concerns:
            return False
        
        # Keywords that indicate new/different health issues
        new_issue_keywords = [
            "different problem", "new symptoms", "another issue", "something else",
            "unrelated", "different pain", "new concern", "different doctor"
        ]
        
        return any(keyword in message.lower() for keyword in new_issue_keywords)
    
    def get_or_create_session_memory(self, user_session, message: str = "") -> ConversationBufferMemory:
        """Get existing session memory or create new one"""
        session_id = self.get_session_id(user_session)
        
        # Check if we should start a new session
        if self.should_start_new_session(user_session, message):
            self._cleanup_session(session_id)
        
        # Create new memory if doesn't exist
        if session_id not in self.session_memories:
            self.session_memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            self.session_contexts[session_id] = {
                'created_at': datetime.now(),
                'symptoms': [],
                'health_concerns': [],
                'user_preferences': {}
            }
        
        # Update last activity
        self.session_last_activity[session_id] = datetime.now()
        
        return self.session_memories[session_id]
    
    def update_session_context(self, user_session, key: str, value: Any):
        """Update session-specific context"""
        session_id = self.get_session_id(user_session)
        if session_id in self.session_contexts:
            self.session_contexts[session_id][key] = value
    
    def _cleanup_session(self, session_id: str):
        """Clean up old session data"""
        if session_id in self.session_memories:
            del self.session_memories[session_id]
        if session_id in self.session_last_activity:
            del self.session_last_activity[session_id]
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, last_activity in self.session_last_activity.items():
            if current_time - last_activity > timedelta(hours=self.session_timeout_hours):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self._cleanup_session(session_id)

class AutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()
        self.session_manager = SessionMemoryManager(session_timeout_hours=24)
        
        # Map function names to actual functions
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

    def ask_session_confirmation(self, user_session, message: str) -> Optional[str]:
        """Ask user to confirm if this is a new session when context suggests it might be"""
        session_id = self.session_manager.get_session_id(user_session)
        previous_context = self.session_manager.session_contexts.get(session_id, {})
        
        # Only ask if there's significant previous context
        if previous_context.get('symptoms') or previous_context.get('health_concerns'):
            # Check if this seems like a new health concern
            if self.session_manager._detect_context_switch(message, previous_context):
                return ("I notice you're mentioning something that seems different from what we were discussing before. "
                       "Are you looking to discuss a new health concern, or is this related to what we talked about previously? "
                       "Just let me know if this is a 'new consultation' or 'continue previous'.")
        
        return None

    def get_conversation_history(self, user_session) -> List[Dict]:
        """Get conversation history for the current session"""
        memory = self.session_manager.get_or_create_session_memory(user_session)
        messages = memory.chat_memory.messages
        
        history = []
        for message in messages:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
        
        return history

    def execute_function_call(self, function_name: str, arguments: dict, user_session) -> str:
        """Execute function calls with session context"""
        if function_name in self.function_map:
            function = self.function_map[function_name]
            try:
                result = function(user_session, **arguments)
                return str(result)
            except Exception as e:
                print(f"Error executing {function_name}: {e}")
                return f"Error executing {function_name}: {str(e)}"
        else:
            return f"Function {function_name} not found"

    def generate_autonomous_response(self, message: str, user_session) -> str:
        """Generate response with session-aware autonomous function calling"""
        try:
            # Check if we should ask for session confirmation
            session_confirmation = self.ask_session_confirmation(user_session, message)
            if session_confirmation and not any(keyword in message.lower() for keyword in ['new consultation', 'continue previous']):
                return session_confirmation
            
            # Handle session confirmation responses
            if 'new consultation' in message.lower():
                session_id = self.session_manager.get_session_id(user_session)
                self.session_manager._cleanup_session(session_id)
                return "Great! I've started a fresh consultation for you. How can I help you with your health today?"
            elif 'continue previous' in message.lower():
                return "Perfect! Let's continue where we left off. What would you like to discuss?"
            
            # Get session-specific memory
            memory = self.session_manager.get_or_create_session_memory(user_session, message)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": DEFAULT_CHATBOT_BASE_PROMPT}
            ]
            messages.extend(self.get_conversation_history(user_session))
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
                
                # Update session context based on function calls
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
                
                # Update memory
                memory.chat_memory.add_message(HumanMessage(content=message))
                memory.chat_memory.add_message(AIMessage(content=final_content))
                
                return final_content
            else:
                # No function call, just return AI's response
                content = assistant_message.content
                
                # Update memory
                memory.chat_memory.add_message(HumanMessage(content=message))
                memory.chat_memory.add_message(AIMessage(content=content))
                
                return content

        except Exception as e:
            print(f"❌ Error in autonomous response: {e}")
            return "I'm sorry, I encountered an error. Please try again."
    
    def _update_session_context_from_function(self, user_session, function_name: str, function_args: dict):
        """Update session context based on function calls"""
        if function_name == "handle_doctor_recommendation_from_symptoms_function":
            symptoms = function_args.get('symptoms', '')
            if symptoms:
                self.session_manager.update_session_context(
                    user_session, 'symptoms', 
                    self.session_manager.session_contexts.get(
                        self.session_manager.get_session_id(user_session), {}
                    ).get('symptoms', []) + [symptoms]
                )
        
        elif function_name == "search_doctors_by_criteria":
            search_text = function_args.get('search_text', '')
            if search_text:
                self.session_manager.update_session_context(
                    user_session, 'health_concerns',
                    self.session_manager.session_contexts.get(
                        self.session_manager.get_session_id(user_session), {}
                    ).get('health_concerns', []) + [search_text]
                )

    def reset_session(self, user_session):
        """Manually reset a user's session"""
        session_id = self.session_manager.get_session_id(user_session)
        self.session_manager._cleanup_session(session_id)
        return "Your session has been reset. How can I help you today?"

# Global dictionary to store engines per user session
autonomous_engines: Dict[str, AutonomousAIEngine] = {}

def get_autonomous_engine(user_session) -> AutonomousAIEngine:
    """Get or create an autonomous engine for a user session"""
    session_key = f"{user_session.user_phone_number}_{user_session.id}"
    
    if session_key not in autonomous_engines:
        autonomous_engines[session_key] = AutonomousAIEngine()
    
    return autonomous_engines[session_key]