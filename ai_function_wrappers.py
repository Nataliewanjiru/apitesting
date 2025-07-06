# AI Function Wrappers for Existing Healthcare System
# These wrappers convert AI dictionary parameters to your existing function formats

import json
from typing import Optional, List, Dict, Any
from openai import OpenAI

# Create a simple object to mimic your message_text structure
class PersonalDetailsObject:
    def __init__(self, details_dict: dict):
        self.first_name = details_dict.get('first_name')
        self.middle_name = details_dict.get('middle_name')
        self.last_name = details_dict.get('last_name')
        self.age = details_dict.get('age')
        self.gender = details_dict.get('gender')
        self.county = details_dict.get('county')
        self.location = details_dict.get('location')
        self.password = details_dict.get('password')

# AI-to-App Function Wrappers
def ai_handle_user_registration(user_session, personal_details: dict) -> str:
    """Wrapper for AI registration calls"""
    try:
        # Convert AI dictionary to your expected format
        message_text = PersonalDetailsObject(personal_details)
        
        # Call your existing registration function
        from .your_registration_module import handle_user_registration  # Adjust import path
        result = handle_user_registration(user_session, message_text)
        
        # Convert result to string for AI
        if hasattr(result, 'content'):
            return result.content  # If it's a message object
        elif isinstance(result, dict):
            return result.get('text', {}).get('body', str(result))
        return str(result)
        
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return f"Registration failed: {str(e)}"

def ai_handle_user_login(user_session, credentials: dict) -> str:
    """Wrapper for AI login calls"""
    try:
        # Extract password from credentials
        password = credentials.get('password', '')
        
        # Call your existing login function
        from .your_login_module import handle_user_login  # Adjust import path
        result = handle_user_login(user_session, password)
        
        # Convert result to string for AI
        if hasattr(result, 'content'):
            return result.content
        elif isinstance(result, dict):
            return result.get('text', {}).get('body', str(result))
        return str(result)
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return f"Login failed: {str(e)}"

def ai_handle_doctor_recommendation_from_symptoms(user_session, symptoms: str) -> str:
    """Wrapper for AI doctor recommendation calls"""
    try:
        # Call your existing doctor recommendation function
        from .your_doctor_module import handle_doctor_recommendation_from_symptoms  # Adjust import path
        result = handle_doctor_recommendation_from_symptoms(user_session, symptoms)
        
        # Convert result to string for AI
        if isinstance(result, list) and result:
            # If it returns a list of message objects
            message = result[0]
            if hasattr(message, 'content'):
                return message.content
            elif isinstance(message, dict):
                return message.get('text', {}).get('body', str(message))
        elif hasattr(result, 'content'):
            return result.content
        elif isinstance(result, dict):
            return result.get('text', {}).get('body', str(result))
        
        return str(result)
        
    except Exception as e:
        print(f"❌ Doctor recommendation error: {e}")
        return f"Error finding doctors: {str(e)}"

def ai_handle_booking_intent(user_session, booking_details: dict) -> str:
    """Wrapper for AI booking calls"""
    try:
        # Convert booking_details to your expected format
        extracted_info = {
            "PromptOutputBooking": booking_details,
            "PromptOutputPersonalDetails": {},  # Add if available
            "PromptOutputInquiry": {"symptoms": []}  # Add if available
        }
        
        # Get user object (adjust based on your user model)
        user = user_session.active_patient_profile or user_session.linked_user
        
        # Create a simple message for booking detection
        message_text = f"Book appointment with {booking_details.get('selected_doctor', '')} on {booking_details.get('preferred_date', '')} at {booking_details.get('preferred_consultation_time', '')}"
        
        # Call your existing booking function
        from .your_booking_module import handle_booking_intent  # Adjust import path
        result = handle_booking_intent(extracted_info, user, message_text)
        
        # Convert result to string for AI
        if isinstance(result, list) and result:
            message = result[0]
            if hasattr(message, 'content'):
                return message.content
            elif isinstance(message, dict):
                return message.get('text', {}).get('body', str(message))
        elif hasattr(result, 'content'):
            return result.content
        elif isinstance(result, dict):
            return result.get('text', {}).get('body', str(result))
        
        return str(result)
        
    except Exception as e:
        print(f"❌ Booking error: {e}")
        return f"Booking failed: {str(e)}"

def ai_handle_appointment_management(user_session, action_details: dict) -> str:
    """Wrapper for AI appointment management calls"""
    try:
        # Convert action_details to your expected format
        extracted_info = {
            "PromptOutputAppointmentManagement": action_details
        }
        
        # Get user object
        user = user_session.active_patient_profile or user_session.linked_user
        
        # Create message text based on action
        action = action_details.get('action', 'view')
        message_text = f"{action} appointment"
        if action_details.get('appointment_identifier'):
            message_text += f" with {action_details.get('appointment_identifier')}"
        
        # Call your existing appointment management function
        from .your_appointment_module import handle_appointment_management  # Adjust import path
        result = handle_appointment_management(extracted_info, user, message_text)
        
        # Convert result to string for AI
        if isinstance(result, list) and result:
            message = result[0]
            if hasattr(message, 'content'):
                return message.content
            elif isinstance(message, dict):
                return message.get('text', {}).get('body', str(message))
        elif hasattr(result, 'content'):
            return result.content
        elif isinstance(result, dict):
            return result.get('text', {}).get('body', str(result))
        
        return str(result)
        
    except Exception as e:
        print(f"❌ Appointment management error: {e}")
        return f"Appointment management failed: {str(e)}"

def ai_get_general_information(user_session, query_type: str, specific_question: str) -> str:
    """Wrapper for AI general information calls"""
    try:
        # You can either implement this directly or call an existing function
        general_responses = {
            "pricing": "Our booking fees vary depending on the type of appointment and provider. Consultation fees typically range from KES 500-2000.",
            "insurance": "We work with several insurance providers including AAR, Jubilee, and NHIF. Please check with your provider for coverage details.",
            "services": "We offer virtual consultations, in-person clinic visits, and home care appointments with qualified healthcare providers.",
            "hours": "Our platform is available 24/7 for booking, but provider availability varies. Most doctors are available 9 AM - 5 PM on weekdays."
        }
        
        # Try to match query_type
        for key, response in general_responses.items():
            if key.lower() in query_type.lower():
                return response
        
        # Default response
        return f"For information about {query_type}, please visit www.rastuc.com or contact our support team. Is there something specific I can help you with?"
        
    except Exception as e:
        print(f"❌ General information error: {e}")
        return "I'm sorry, I couldn't retrieve that information right now. Please try again later."

# Updated HEALTHCARE_TOOLS with correct function names
HEALTHCARE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ai_handle_user_registration",
            "description": "Register a new user when they want to create an account",
            "parameters": {
                "type": "object",
                "properties": {
                    "personal_details": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "middle_name": {"type": "string"},
                            "age": {"type": "string"},
                            "gender": {"type": "string"},
                            "county": {"type": "string"},
                            "location": {"type": "string"},
                            "password": {"type": "string"}
                        },
                        "required": ["first_name", "last_name", "password"]
                    }
                },
                "required": ["personal_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ai_handle_user_login",
            "description": "Login an existing user",
            "parameters": {
                "type": "object",
                "properties": {
                    "credentials": {
                        "type": "object",
                        "properties": {
                            "password": {"type": "string"}
                        },
                        "required": ["password"]
                    }
                },
                "required": ["credentials"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ai_handle_doctor_recommendation_from_symptoms",
            "description": "Find and recommend doctors based on patient symptoms",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "string",
                        "description": "Combined symptoms and medical information"
                    }
                },
                "required": ["symptoms"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ai_handle_booking_intent",
            "description": "Book an appointment with a healthcare provider",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_details": {
                        "type": "object",
                        "properties": {
                            "selected_doctor": {"type": "string"},
                            "specialization": {"type": "string"},
                            "preferred_date": {"type": "string"},
                            "preferred_consultation_time": {"type": "string"},
                            "consultation_mode": {"type": "string"},
                            "confirmed": {"type": "boolean"}
                        }
                    }
                },
                "required": ["booking_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ai_handle_appointment_management",
            "description": "Manage existing appointments (view, cancel, reschedule)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_details": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["view", "cancel", "reschedule", "modify"]},
                            "appointment_identifier": {"type": "string"},
                            "new_date": {"type": "string"},
                            "new_time": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "required": ["action"]
                    }
                },
                "required": ["action_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ai_get_general_information",
            "description": "Get general information about Rastuc services, pricing, insurance, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {"type": "string"},
                    "specific_question": {"type": "string"}
                },
                "required": ["query_type", "specific_question"]
            }
        }
    }
]

# Updated AutonomousAIEngine with your actual functions
class IntegratedAutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Map function names to your wrapper functions
        self.function_map = {
            "ai_handle_user_registration": ai_handle_user_registration,
            "ai_handle_user_login": ai_handle_user_login,
            "ai_handle_doctor_recommendation_from_symptoms": ai_handle_doctor_recommendation_from_symptoms,
            "ai_handle_booking_intent": ai_handle_booking_intent,
            "ai_handle_appointment_management": ai_handle_appointment_management,
            "ai_get_general_information": ai_get_general_information,
        }

    def create_system_prompt(self, user_context: dict = None) -> str:
        base_prompt = """You are a warm, empathetic AI assistant for Rastuc healthcare platform.

Your capabilities:
- ai_handle_user_registration: Register new users (collect first_name, last_name, age, gender, county, location, password)
- ai_handle_user_login: Help existing users login (only need password)
- ai_handle_doctor_recommendation_from_symptoms: Find doctors based on symptoms
- ai_handle_booking_intent: Book appointments with healthcare providers
- ai_handle_appointment_management: View, cancel, or reschedule appointments
- ai_get_general_information: Answer questions about services, pricing, etc.

IMPORTANT GUIDELINES:
1. Always be conversational and empathetic
2. Ask ONE question at a time to gather information
3. Only call functions when you have sufficient information
4. For registration: collect all required details before calling function
5. For login: only ask for password if user is registered
6. For symptoms: gather detailed information before recommending doctors
7. For booking: ensure you have doctor selection, date, and time before calling function

"""
        
        if user_context:
            if user_context.get("is_existing_user"):
                base_prompt += "\nUSER STATUS: This user is already registered in the system."
            else:
                base_prompt += "\nUSER STATUS: This user is not yet registered."
        
        return base_prompt

    def get_conversation_history(self) -> List[Dict]:
        """Convert LangChain memory to OpenAI format"""
        history = self.memory.load_memory_variables({}).get("chat_history", [])
        messages = []
        
        for msg in history:
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})
        
        return messages

    def execute_function_call(self, function_name: str, arguments: dict, user_session) -> str:
        """Execute the function called by AI"""
        try:
            if function_name not in self.function_map:
                return f"Error: Function {function_name} not found"
            
            func = self.function_map[function_name]
            
            # Call the wrapper function with user_session and arguments
            if function_name == "ai_handle_user_registration":
                return func(user_session, arguments.get("personal_details", {}))
            elif function_name == "ai_handle_user_login":
                return func(user_session, arguments.get("credentials", {}))
            elif function_name == "ai_handle_doctor_recommendation_from_symptoms":
                return func(user_session, arguments.get("symptoms", ""))
            elif function_name == "ai_handle_booking_intent":
                return func(user_session, arguments.get("booking_details", {}))
            elif function_name == "ai_handle_appointment_management":
                return func(user_session, arguments.get("action_details", {}))
            elif function_name == "ai_get_general_information":
                return func(user_session, arguments.get("query_type", ""), arguments.get("specific_question", ""))
            else:
                return f"Unknown function: {function_name}"
            
        except Exception as e:
            print(f"❌ Error executing {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"

    def generate_autonomous_response(self, message: str, user_session, user_context: dict = None) -> str:
        """Generate response with autonomous function calling using your actual functions"""
        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": self.create_system_prompt(user_context)}
            ]
            messages.extend(self.get_conversation_history())
            messages.append({"role": "user", "content": message})

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