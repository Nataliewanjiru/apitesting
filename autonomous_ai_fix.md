# Fix: Function Import and Mapping for Autonomous AI

## The Problem
```
❌ Error in autonomous handler: name 'handle_user_registration' is not defined
```

The autonomous AI engine can't find your existing handler functions because they're not properly imported and mapped.

## Solution: Properly Import Your Existing Functions

### 1. First, Import Your Actual Handler Functions

```python
# At the top of your file where you're implementing the autonomous AI
from openai import OpenAI
from typing import Dict, List, Any
import json

# Import your existing handler functions
from your_app.handlers import (  # Replace with your actual import paths
    handle_user_registration,
    handle_user_login, 
    handle_doctor_recommendation_from_symptoms,
    handle_booking_intent,
    handle_appointment_management,
    # Add other handler imports
)

# Or if they're in the same file, make sure they're defined before the AutonomousAIEngine class
```

### 2. Fixed AutonomousAIEngine with Proper Function Mapping

```python
class AutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()  # Make sure you have OPENAI_API_KEY in environment
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Map function names to your ACTUAL functions
        self.function_map = {
            "register_user": self.handle_registration_wrapper,
            "login_user": self.handle_login_wrapper,
            "recommend_doctors": self.handle_symptoms_wrapper,
            "book_appointment": self.handle_booking_wrapper,
            "manage_appointment": self.handle_appointment_mgmt_wrapper,
            "get_info": self.handle_general_info_wrapper,
        }

    # Wrapper functions to handle the function calls properly
    def handle_registration_wrapper(self, user_session, personal_details: dict) -> str:
        """Wrapper for registration function"""
        try:
            # Call your actual registration function
            result = handle_user_registration(user_session, personal_details)
            # Convert result to string if needed
            if hasattr(result, 'content'):  # If it's a message object
                return result.content
            return str(result)
        except Exception as e:
            return f"Registration failed: {str(e)}"

    def handle_login_wrapper(self, user_session, credentials: dict) -> str:
        """Wrapper for login function"""
        try:
            result = handle_user_login(user_session, credentials)
            if hasattr(result, 'content'):
                return result.content
            return str(result)
        except Exception as e:
            return f"Login failed: {str(e)}"

    def handle_symptoms_wrapper(self, user_session, symptoms: str) -> str:
        """Wrapper for symptoms/doctor recommendation"""
        try:
            result = handle_doctor_recommendation_from_symptoms(
                user_session=user_session,
                symptoms=symptoms
            )
            if hasattr(result, 'content'):
                return result.content
            return str(result)
        except Exception as e:
            return f"Doctor recommendation failed: {str(e)}"

    def handle_booking_wrapper(self, user_session, booking_details: dict) -> str:
        """Wrapper for booking function"""
        try:
            result = handle_booking_intent(
                extracted_info={"PromptOutputBooking": booking_details},
                user=user_session.active_patient_profile,
                message_text=""  # You might need to adjust this
            )
            if hasattr(result, 'content'):
                return result.content
            return str(result)
        except Exception as e:
            return f"Booking failed: {str(e)}"

    def handle_appointment_mgmt_wrapper(self, user_session, action_details: dict) -> str:
        """Wrapper for appointment management"""
        try:
            result = handle_appointment_management(
                extracted_info={"PromptOutputAppointmentManagement": action_details},
                user=user_session.active_patient_profile,
                message_text=""
            )
            if hasattr(result, 'content'):
                return result.content
            return str(result)
        except Exception as e:
            return f"Appointment management failed: {str(e)}"

    def handle_general_info_wrapper(self, user_session, query_type: str, specific_question: str) -> str:
        """Wrapper for general information"""
        try:
            # Implement your general info logic or call existing function
            return f"Here's information about {query_type}: {specific_question}"
        except Exception as e:
            return f"Information retrieval failed: {str(e)}"

    def create_system_prompt(self, user_context: dict = None) -> str:
        base_prompt = """You are a warm, empathetic AI assistant for Rastuc healthcare platform.

Your capabilities:
- register_user: Register new users when they want to create an account
- login_user: Help existing users login with their password
- recommend_doctors: Find doctors based on patient symptoms  
- book_appointment: Book appointments with healthcare providers
- manage_appointment: View, cancel, or reschedule existing appointments
- get_info: Answer general questions about Rastuc services

IMPORTANT GUIDELINES:
1. Always be conversational and empathetic
2. Ask ONE question at a time to gather information
3. Only call functions when you have sufficient information
4. For registration: collect first_name, last_name, age, gender, county, location, password
5. For login: only ask for password if user is registered
6. For symptoms: gather detailed symptom information before recommending doctors
7. For booking: ensure you have doctor selection, date, and time preferences

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
            if function_name == "register_user":
                return func(user_session, arguments.get("personal_details", {}))
            elif function_name == "login_user":
                return func(user_session, arguments.get("credentials", {}))
            elif function_name == "recommend_doctors":
                return func(user_session, arguments.get("symptoms", ""))
            elif function_name == "book_appointment":
                return func(user_session, arguments.get("booking_details", {}))
            elif function_name == "manage_appointment":
                return func(user_session, arguments.get("action_details", {}))
            elif function_name == "get_info":
                return func(user_session, arguments.get("query_type", ""), arguments.get("specific_question", ""))
            else:
                return f"Unknown function: {function_name}"
            
        except Exception as e:
            return f"Error executing {function_name}: {str(e)}"

    def generate_autonomous_response(self, message: str, user_session, user_context: dict = None) -> str:
        """Generate response with autonomous function calling"""
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
                tools=HEALTHCARE_TOOLS,  # Updated to use 'tools' instead of 'functions'
                tool_choice="auto",      # Updated parameter name
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
                    "tool_calls": [tool_call.dict()]
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
```

### 3. Updated Function Definitions for OpenAI (Tools Format)

```python
# Updated function definitions using the new 'tools' format
HEALTHCARE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "register_user",
            "description": "Register a new user when they want to create an account",
            "parameters": {
                "type": "object",
                "properties": {
                    "personal_details": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
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
            "name": "login_user",
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
            "name": "recommend_doctors",
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
            "name": "book_appointment",
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
            "name": "manage_appointment",
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
            "name": "get_info",
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
```

### 4. Environment Setup

Make sure you have your OpenAI API key in your environment:

```python
# In your settings or environment
import os
os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'

# Or in your .env file
OPENAI_API_KEY=your-openai-api-key-here
```

### 5. Updated Message Handler

```python
def handle_conversation_mode_chatbot_message_v3(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):
    """Fixed autonomous version"""
    
    try:
        # Check for direct commands first (optional)
        direct_response = handle_direct_appointment_commands(message_text, user_session)
        if direct_response:
            return direct_response
        
        # Let AI handle everything autonomously
        response = handle_autonomous_message(user_session, message_text)
        
        return UTILITIES.create_text_message(response)
        
    except Exception as e:
        print(f"❌ Error in autonomous handler: {e}")
        return UTILITIES.create_text_message(
            "I'm sorry, I encountered an error. Please try again later."
        )
```

## Key Fixes:

1. **✅ Proper Function Mapping**: Wrapper functions that call your existing handlers
2. **✅ Import Handling**: Clear instructions on importing your actual functions  
3. **✅ Error Handling**: Wrapper functions handle different return types
4. **✅ Updated OpenAI API**: Uses the new 'tools' format instead of deprecated 'functions'
5. **✅ Environment Setup**: Instructions for OpenAI API key

## Test the Fix:

1. Make sure your OpenAI API key is set
2. Import your actual handler functions
3. Replace the function mappings with your real functions
4. Test with a simple message like "hi"

This should resolve the `handle_user_registration is not defined` error and give your AI full autonomous control!