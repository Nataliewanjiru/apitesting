# Autonomous AI with Function Calling

## Current vs Autonomous Approach

**Current Flow:**
```
Message → AI → Extract Intent → Manual Handler → Call Function
```

**Autonomous Flow:**
```
Message → AI → AI Calls Function Directly → Result
```

## Implementation Options

### 1. **OpenAI Function Calling (Recommended)**
The most powerful and direct approach using GPT-4's native function calling.

### 2. **LangChain Tools/Agents**
Use LangChain's built-in agent system with tools.

### 3. **Custom Action System**
AI returns structured actions that get executed automatically.

## Option 1: OpenAI Function Calling (Best Approach)

### 1. Define Your Functions

```python
import json
from typing import Optional, List, Dict, Any
from openai import OpenAI

# Define all your healthcare functions
def handle_user_registration(user_session, personal_details: dict) -> str:
    """Register a new user with personal details"""
    try:
        # Your existing registration logic
        return f"Registration successful for {personal_details.get('first_name', 'user')}"
    except Exception as e:
        return f"Registration failed: {str(e)}"

def handle_user_login(user_session, credentials: dict) -> str:
    """Login an existing user"""
    try:
        # Your existing login logic
        return "Login successful!"
    except Exception as e:
        return f"Login failed: {str(e)}"

def handle_doctor_recommendation_from_symptoms(user_session, symptoms: str) -> str:
    """Find doctor recommendations based on symptoms"""
    try:
        # Your existing doctor recommendation logic
        return f"Based on your symptoms '{symptoms}', I recommend Dr. Smith (Cardiologist) and Dr. Jane (General Practitioner)"
    except Exception as e:
        return f"Error finding doctors: {str(e)}"

def handle_booking_intent(user_session, booking_details: dict) -> str:
    """Book an appointment with a doctor"""
    try:
        # Your existing booking logic
        doctor = booking_details.get('selected_doctor', 'N/A')
        date = booking_details.get('preferred_date', 'N/A')
        time = booking_details.get('preferred_consultation_time', 'N/A')
        return f"Appointment booked with {doctor} on {date} at {time}"
    except Exception as e:
        return f"Booking failed: {str(e)}"

def handle_appointment_management(user_session, action_details: dict) -> str:
    """Manage existing appointments (view, cancel, reschedule)"""
    try:
        action = action_details.get('action', 'view')
        # Your existing appointment management logic
        return f"Appointment {action} completed successfully"
    except Exception as e:
        return f"Appointment management failed: {str(e)}"

def get_general_information(query_type: str, specific_question: str) -> str:
    """Get general information about Rastuc services"""
    try:
        # Your existing general info logic
        return f"Here's information about {query_type}: {specific_question}"
    except Exception as e:
        return f"Information retrieval failed: {str(e)}"
```

### 2. Define Function Schemas for OpenAI

```python
# Function definitions for OpenAI
HEALTHCARE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "handle_user_registration",
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
            "name": "handle_user_login",
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
            "name": "handle_doctor_recommendation_from_symptoms",
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
            "name": "handle_booking_intent",
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
            "name": "handle_appointment_management",
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
            "name": "get_general_information",
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

### 3. Autonomous AI Engine with Function Calling

```python
from openai import OpenAI
from typing import Dict, List, Any
import json

class AutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()  # Uses OPENAI_API_KEY from environment
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Map function names to actual functions
        self.function_map = {
            "handle_user_registration": handle_user_registration,
            "handle_user_login": handle_user_login,
            "handle_doctor_recommendation_from_symptoms": handle_doctor_recommendation_from_symptoms,
            "handle_booking_intent": handle_booking_intent,
            "handle_appointment_management": handle_appointment_management,
            "get_general_information": get_general_information,
        }

    def create_system_prompt(self, user_context: dict = None) -> str:
        base_prompt = """You are a warm, empathetic AI assistant for Rastuc healthcare platform.

Your capabilities:
- Register new users and help existing users login
- Collect symptoms and recommend appropriate doctors
- Book appointments with healthcare providers
- Manage existing appointments (view, cancel, reschedule)
- Answer general questions about Rastuc services

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
            
            # Add user_session as first parameter for all functions
            if function_name in ["handle_user_registration", "handle_user_login"]:
                result = func(user_session, arguments.get(list(arguments.keys())[0]))
            elif function_name == "handle_doctor_recommendation_from_symptoms":
                result = func(user_session, arguments.get("symptoms"))
            elif function_name in ["handle_booking_intent", "handle_appointment_management"]:
                result = func(user_session, arguments.get(list(arguments.keys())[0]))
            else:
                result = func(**arguments)
            
            return str(result)
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
                functions=HEALTHCARE_FUNCTIONS,
                function_call="auto",  # Let AI decide when to call functions
                temperature=0.3
            )

            assistant_message = response.choices[0].message

            # Check if AI wants to call a function
            if assistant_message.function_call:
                function_name = assistant_message.function_call.name
                function_args = json.loads(assistant_message.function_call.arguments)
                
                print(f"🔍 AI calling function: {function_name} with args: {function_args}")
                
                # Execute the function
                function_result = self.execute_function_call(function_name, function_args, user_session)
                
                # Add function call and result to conversation
                messages.append({
                    "role": "assistant", 
                    "content": None,
                    "function_call": {
                        "name": function_name,
                        "arguments": json.dumps(function_args)
                    }
                })
                messages.append({
                    "role": "function",
                    "name": function_name,
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

### 4. Simplified Message Handler

```python
# Global memory store for autonomous engines
autonomous_engines: Dict[str, AutonomousAIEngine] = {}

def get_autonomous_engine(user_id: str, user_session) -> AutonomousAIEngine:
    """Get or create autonomous engine for user"""
    if user_id not in autonomous_engines:
        engine = AutonomousAIEngine()
        
        # Load conversation history
        if user_session.ai_conversation_history:
            engine.memory.chat_memory.clear()
            for msg in user_session.ai_conversation_history:
                if msg["type"] == "user":
                    engine.memory.chat_memory.add_message(HumanMessage(content=msg["content"]))
                elif msg["type"] == "ai":
                    engine.memory.chat_memory.add_message(AIMessage(content=msg["content"]))
        
        autonomous_engines[user_id] = engine
    
    return autonomous_engines[user_id]

def save_autonomous_conversation(user_id: str, user_session):
    """Save conversation history"""
    if user_id in autonomous_engines:
        engine = autonomous_engines[user_id]
        history = engine.memory.load_memory_variables({})["chat_history"]
        
        serialized = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                serialized.append({"type": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                serialized.append({"type": "ai", "content": msg.content})
        
        user_session.ai_conversation_history = serialized
        user_session.save()

def handle_autonomous_message(user_session, message_text: str) -> str:
    """Completely autonomous message handling"""
    
    user_id = user_session.user_phone_number
    
    # Create user context
    user_context = {
        "is_existing_user": user_session.is_an_existing_user,
        "has_active_profile": bool(user_session.active_patient_profile)
    }
    
    # Get autonomous engine
    engine = get_autonomous_engine(user_id, user_session)
    
    # Let AI handle everything autonomously
    response = engine.generate_autonomous_response(message_text, user_session, user_context)
    
    # Save conversation
    save_autonomous_conversation(user_id, user_session)
    
    return response
```

### 5. Replace Your Current Handler

```python
def handle_conversation_mode_chatbot_message_v3(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):
    """New autonomous version - AI has full control"""
    
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

## Key Benefits

1. **Full AI Autonomy**: AI decides when and which functions to call
2. **No Manual Intent Handling**: No more `if inquiry_intent == "register"` logic
3. **Natural Conversations**: AI can gather information conversationally before calling functions
4. **Intelligent Function Selection**: AI chooses the right function based on context
5. **Error Handling**: Built-in error handling for function calls

## Example Conversations

**Registration:**
```
User: "I want to register"
AI: "I'd be happy to help you register! Let me collect some information. What's your first name?"
User: "John"
AI: "Nice to meet you, John! What's your last name?"
User: "Doe"
AI: "What's your age?"
User: "25"
AI: "Which county are you in?"
User: "Nairobi"
AI: "What's your specific location in Nairobi?"
User: "Westlands"
AI: "Are you male or female?"
User: "Male"
AI: "Finally, please create a password for your account"
User: "mypassword123"
AI: [CALLS handle_user_registration FUNCTION] "Great! Registration successful for John. You're all set!"
```

**Symptoms to Booking:**
```
User: "I have chest pains"
AI: "I'm sorry to hear about your chest pains. How long have you been experiencing this?"
User: "3 days"
AI: "Is the pain constant or does it come and go?"
User: "It comes and goes"
AI: [CALLS handle_doctor_recommendation_from_symptoms] "Based on your symptoms, I recommend Dr. Smith (Cardiologist). Would you like to book an appointment?"
User: "Yes, next Monday at 2pm"
AI: [CALLS handle_booking_intent] "Perfect! I've booked your appointment with Dr. Smith for next Monday at 2pm."
```

This approach gives your AI complete autonomy while maintaining all your existing business logic through function calls!