from openai import OpenAI
from typing import Dict, List, Any
import json
import os
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage

# Make sure to set your OpenAI API key
# os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

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
    }
]

class AutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()  # Make sure OPENAI_API_KEY is set in environment
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Map function names to wrapper functions
        self.function_map = {
            "register_user": self.handle_registration_wrapper,
            "login_user": self.handle_login_wrapper,
            "recommend_doctors": self.handle_symptoms_wrapper,
        }

    def handle_registration_wrapper(self, user_session, personal_details: dict) -> str:
        """Wrapper for registration function"""
        try:
            # For now, return a mock response - replace with your actual function
            name = personal_details.get('first_name', 'User')
            return f"Registration successful for {name}! Welcome to Rastuc."
        except Exception as e:
            return f"Registration failed: {str(e)}"

    def handle_login_wrapper(self, user_session, credentials: dict) -> str:
        """Wrapper for login function"""
        try:
            # For now, return a mock response - replace with your actual function
            return "Login successful! Welcome back to Rastuc."
        except Exception as e:
            return f"Login failed: {str(e)}"

    def handle_symptoms_wrapper(self, user_session, symptoms: str) -> str:
        """Wrapper for symptoms/doctor recommendation"""
        try:
            # For now, return a mock response - replace with your actual function
            return f"Based on your symptoms '{symptoms}', I recommend Dr. Smith (Cardiologist) and Dr. Jane (General Practitioner). Would you like to book an appointment?"
        except Exception as e:
            return f"Doctor recommendation failed: {str(e)}"

    def create_system_prompt(self, user_context: dict = None) -> str:
        base_prompt = """You are a warm, empathetic AI assistant for Rastuc healthcare platform.

Your capabilities:
- register_user: Register new users when they want to create an account
- login_user: Help existing users login with their password
- recommend_doctors: Find doctors based on patient symptoms

IMPORTANT GUIDELINES:
1. Always be conversational and empathetic
2. Ask ONE question at a time to gather information
3. Only call functions when you have sufficient information
4. For registration: collect first_name, last_name, age, gender, county, location, password
5. For login: only ask for password if user is registered
6. For symptoms: gather detailed symptom information before recommending doctors

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

            # Call OpenAI with function calling using NEW 'tools' format
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=HEALTHCARE_TOOLS,  # Use 'tools' instead of 'functions'
                tool_choice="auto",      # Use 'tool_choice' instead of 'function_call'
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

# Global memory store for autonomous engines
autonomous_engines: Dict[str, AutonomousAIEngine] = {}

def get_autonomous_engine(user_id: str, user_session) -> AutonomousAIEngine:
    """Get or create autonomous engine for user"""
    if user_id not in autonomous_engines:
        engine = AutonomousAIEngine()
        
        # Load conversation history
        if hasattr(user_session, 'ai_conversation_history') and user_session.ai_conversation_history:
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
        "is_existing_user": getattr(user_session, 'is_an_existing_user', False),
        "has_active_profile": bool(getattr(user_session, 'active_patient_profile', None))
    }
    
    # Get autonomous engine
    engine = get_autonomous_engine(user_id, user_session)
    
    # Let AI handle everything autonomously
    response = engine.generate_autonomous_response(message_text, user_session, user_context)
    
    # Save conversation
    save_autonomous_conversation(user_id, user_session)
    
    return response

# Your updated message handler
def handle_conversation_mode_chatbot_message_v3(user_session, message_text: str):
    """New autonomous version - AI has full control"""
    
    try:
        # Let AI handle everything autonomously
        response = handle_autonomous_message(user_session, message_text)
        
        # Return the response in your expected format
        return {"messaging_product": "whatsapp", "type": "text", "text": {"preview_url": True, "body": response}}
        
    except Exception as e:
        print(f"❌ Error in autonomous handler: {e}")
        return {"messaging_product": "whatsapp", "type": "text", "text": {"preview_url": True, "body": "I'm sorry, I encountered an error. Please try again later."}}