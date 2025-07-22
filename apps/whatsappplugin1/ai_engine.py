from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json

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
- Each conversation session should be treated independently
- Don't reference information from previous sessions unless it's user profile data
- If you notice symptoms or booking details that seem unrelated to the current conversation flow, ask the user to confirm if this is a new session
- Always prioritize current session context over historical data

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
Example: If a user types "I want a cardiologist", call search_doctors_by_criteria(search_text="cardiologist") instead of guessing from previous sessions.
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

class SessionManager:
    """Manages conversation sessions and memory like ChatGPT"""
    
    def __init__(self):
        self.session_timeout = timedelta(hours=2)  # Sessions expire after 2 hours of inactivity
        self.max_memory_messages = 20  # Keep last 20 messages for context
        self.important_context_keywords = [
            'symptom', 'pain', 'appointment', 'doctor', 'booking', 
            'profile', 'login', 'register', 'payment'
        ]
    
    def detect_new_session(self, message: str, last_activity: datetime = None) -> bool:
        """Detect if this should be treated as a new session"""
        current_time = datetime.now()
        
        # Check if session has timed out
        if last_activity and (current_time - last_activity) > self.session_timeout:
            return True
        
        # Check for explicit new session indicators
        new_session_indicators = [
            'new appointment', 'different issue', 'new problem', 
            'start over', 'new session', 'new booking'
        ]
        
        message_lower = message.lower()
        for indicator in new_session_indicators:
            if indicator in message_lower:
                return True
        
        return False
    
    def should_ask_about_new_session(self, message: str, conversation_history: List) -> bool:
        """Determine if we should ask user if this is a new session"""
        if len(conversation_history) < 4:  # Too early to determine
            return False
        
        # Get last few messages to understand context
        recent_messages = conversation_history[-6:] if len(conversation_history) >= 6 else conversation_history
        recent_text = " ".join([msg.get('content', '') for msg in recent_messages if msg.get('content')])
        
        # Check if user is mentioning completely different symptoms/issues
        current_keywords = self._extract_keywords(message.lower())
        recent_keywords = self._extract_keywords(recent_text.lower())
        
        # If there's very little overlap in medical/booking context, might be new session
        overlap = len(set(current_keywords) & set(recent_keywords))
        if len(current_keywords) > 2 and overlap < 2:
            return True
        
        return False
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        keywords = []
        for keyword in self.important_context_keywords:
            if keyword in text:
                keywords.append(keyword)
        return keywords
    
    def compress_memory(self, conversation_history: List[Dict]) -> List[Dict]:
        """Compress conversation history to keep only important context"""
        if len(conversation_history) <= self.max_memory_messages:
            return conversation_history
        
        # Always keep the first message (greeting) and last max_memory_messages
        compressed = []
        
        # Keep first message if it exists
        if conversation_history:
            compressed.append(conversation_history[0])
        
        # Keep most recent messages
        recent_messages = conversation_history[-(self.max_memory_messages-1):]
        compressed.extend(recent_messages)
        
        return compressed
    
    def extract_session_summary(self, conversation_history: List[Dict]) -> Dict:
        """Extract important information from the session for context"""
        summary = {
            'symptoms_mentioned': [],
            'doctors_discussed': [],
            'booking_in_progress': False,
            'user_authenticated': False
        }
        
        for message in conversation_history:
            content = message.get('content', '').lower()
            
            # Extract symptoms
            symptom_keywords = ['pain', 'ache', 'fever', 'cough', 'headache', 'nausea']
            for symptom in symptom_keywords:
                if symptom in content and symptom not in summary['symptoms_mentioned']:
                    summary['symptoms_mentioned'].append(symptom)
            
            # Check for booking progress
            if any(word in content for word in ['appointment', 'booking', 'schedule']):
                summary['booking_in_progress'] = True
            
            # Check authentication status
            if any(word in content for word in ['login', 'logged in', 'profile selected']):
                summary['user_authenticated'] = True
        
        return summary

class AutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.session_manager = SessionManager()
        
        # Map function names to actual functions
        self.function_map = {
            # Your existing function mappings here
        }

    def start_new_session(self, user_session) -> None:
        """Start a new conversation session"""
        print("🔄 Starting new session...")
        
        # Save current session to history if it has meaningful content
        current_history = self.get_conversation_history()
        if len(current_history) > 2:  # More than just greeting
            session_summary = self.session_manager.extract_session_summary(current_history)
            
            # Store in user session's previous conversations
            if hasattr(user_session, 'previous_ai_conversations'):
                user_session.previous_ai_conversations.append({
                    'timestamp': datetime.now().isoformat(),
                    'summary': session_summary,
                    'message_count': len(current_history)
                })
                user_session.save()
        
        # Clear current memory
        self.memory.clear()
        
        # Reset any booking-related session state
        if hasattr(user_session, 'reset_appointment_booking_session'):
            user_session.reset_appointment_booking_session()

    def check_session_continuity(self, message: str, user_session) -> bool:
        """Check if we should continue current session or start new one"""
        last_activity = getattr(user_session, 'last_session_state_update', None)
        
        # Check if this should be a new session
        if self.session_manager.detect_new_session(message, last_activity):
            return False
        
        # Check if we should ask about new session
        current_history = self.get_conversation_history()
        if self.session_manager.should_ask_about_new_session(message, current_history):
            # Ask user if this is a new session
            self.memory.chat_memory.add_message(HumanMessage(content=message))
            self.memory.chat_memory.add_message(AIMessage(
                content="I notice you're mentioning different health concerns. Is this a new consultation session, or are you continuing from our previous discussion?"
            ))
            return True  # Continue current session but with clarification
        
        return True  # Continue current session

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history in the right format"""
        history = []
        if self.memory.chat_memory.messages:
            for message in self.memory.chat_memory.messages:
                if isinstance(message, HumanMessage):
                    history.append({"role": "user", "content": message.content})
                elif isinstance(message, AIMessage):
                    history.append({"role": "assistant", "content": message.content})
        
        # Compress memory if needed
        return self.session_manager.compress_memory(history)

    def execute_function_call(self, function_name: str, arguments: dict, user_session) -> str:
        """Execute function calls - your existing implementation"""
        # Your existing function execution code here
        pass

    def generate_autonomous_response(self, message: str, user_session) -> str:
        """Generate response with autonomous function calling and session management"""
        try:
            # Handle session continuity
            if not self.check_session_continuity(message, user_session):
                self.start_new_session(user_session)
                return "I understand you'd like to start a new consultation. How can I help you today?"
            
            # Check for explicit new session request
            if any(phrase in message.lower() for phrase in ['new session', 'start over', 'new consultation']):
                self.start_new_session(user_session)
                return "Starting a new session. How can I assist you today?"
            
            # Prepare messages with compressed history
            messages = [
                {"role": "system", "content": DEFAULT_CHATBOT_BASE_PROMPT}
            ]
            messages.extend(self.get_conversation_history())
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
                self.memory.chat_memory.add_message(HumanMessage(content=message))
                self.memory.chat_memory.add_message(AIMessage(content=final_content))
                
                return final_content
            else:
                # No function call, just return AI's response
                content = assistant_message.content
                
                # Update memory
                self.memory.chat_memory.add_message(HumanMessage(content=message))
                self.memory.chat_memory.add_message(AIMessage(content=content))
                
                return content

        except Exception as e:
            print(f"❌ Error in autonomous response: {e}")
            return "I'm sorry, I encountered an error. Please try again."

# Update the global engines dictionary to handle sessions properly
autonomous_engines: Dict[str, AutonomousAIEngine] = {}

def get_or_create_engine(user_session_id: str) -> AutonomousAIEngine:
    """Get or create an AI engine for a specific user session"""
    if user_session_id not in autonomous_engines:
        autonomous_engines[user_session_id] = AutonomousAIEngine()
    return autonomous_engines[user_session_id]

def cleanup_inactive_engines():
    """Clean up engines for inactive sessions"""
    # This should be called periodically to free memory
    # You can implement this based on your session tracking
    pass