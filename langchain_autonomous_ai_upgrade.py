# Enhanced LangChain AI with Function Calling
# This builds on your existing setup

from typing import List, Optional, Tuple
from apps.whatsappplugin1.promptingmodels import PromptOutput
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
import json

# Define your healthcare functions as LangChain tools
@tool
def register_user_tool(personal_details: dict) -> str:
    """Register a new user when they want to create an account.
    
    Args:
        personal_details: Dictionary containing first_name, last_name, age, gender, county, location, password
    """
    try:
        # Replace with your actual registration function
        name = personal_details.get('first_name', 'User')
        return f"Registration successful for {name}! Welcome to Rastuc."
    except Exception as e:
        return f"Registration failed: {str(e)}"

@tool 
def login_user_tool(password: str) -> str:
    """Login an existing user with their password.
    
    Args:
        password: User's password
    """
    try:
        # Replace with your actual login function
        return "Login successful! Welcome back to Rastuc."
    except Exception as e:
        return f"Login failed: {str(e)}"

@tool
def recommend_doctors_tool(symptoms: str) -> str:
    """Find and recommend doctors based on patient symptoms.
    
    Args:
        symptoms: Combined symptoms and medical information
    """
    try:
        # Replace with your actual doctor recommendation function
        return f"Based on your symptoms '{symptoms}', I recommend Dr. Smith (Cardiologist) and Dr. Jane (General Practitioner). Would you like to book an appointment?"
    except Exception as e:
        return f"Doctor recommendation failed: {str(e)}"

@tool
def book_appointment_tool(doctor_name: str, date: str, time: str) -> str:
    """Book an appointment with a healthcare provider.
    
    Args:
        doctor_name: Name of the selected doctor
        date: Preferred appointment date
        time: Preferred appointment time
    """
    try:
        # Replace with your actual booking function
        return f"Appointment booked with {doctor_name} on {date} at {time}. You'll receive a confirmation shortly."
    except Exception as e:
        return f"Booking failed: {str(e)}"

# List of all available tools
HEALTHCARE_TOOLS = [
    register_user_tool,
    login_user_tool, 
    recommend_doctors_tool,
    book_appointment_tool
]

class EnhancedAIEngine:
    def __init__(self):
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Your existing structured output setup
        self.output_parser = PydanticOutputParser(pydantic_object=PromptOutput)
        
        # Enhanced LLM with function calling capabilities
        self.llm = init_chat_model(
            "gpt-4o", model_provider="openai", temperature=0.3
        )
        
        # Structured output version (for when not using tools)
        self.structured_llm = self.llm.with_structured_output(PromptOutput)
        
        # Tool-calling version (for autonomous actions)
        self.tool_llm = self.llm.bind_tools(HEALTHCARE_TOOLS)

    def get_prompt(self, history_text: str, user_context: dict = None):
        # Enhanced prompt with function calling guidance
        context_info = ""
        if user_context:
            if user_context.get("is_existing_user"):
                context_info = "\nUSER STATUS: This user is already registered in the system."
            else:
                context_info = "\nUSER STATUS: This user is not yet registered."

        enhanced_prompt = f"""
You are a warm, empathetic AI assistant for Rastuc healthcare platform.

Your available tools:
- register_user_tool: Register new users (collect first_name, last_name, age, gender, county, location, password)
- login_user_tool: Help existing users login (only need password)
- recommend_doctors_tool: Find doctors based on symptoms
- book_appointment_tool: Book appointments with healthcare providers

IMPORTANT GUIDELINES:
1. Always be conversational and empathetic
2. Ask ONE question at a time to gather information
3. Use tools when you have sufficient information to take action
4. For registration: collect all required details before calling register_user_tool
5. For login: only ask for password if user is registered
6. For symptoms: gather detailed information before calling recommend_doctors_tool
7. For booking: ensure you have doctor selection, date, and time before calling book_appointment_tool

Current conversation history:
{history_text}

{context_info}
"""

        return ChatPromptTemplate.from_messages([
            SystemMessage(content=enhanced_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

    def format_history_for_system(self):
        history = self.memory.load_memory_variables({}).get("chat_history", [])
        formatted = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                formatted.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                formatted.append(f"AI: {msg.content}")
        return "\n".join(formatted)

    def serialize_conversation_history(self, memory):
        history = memory.load_memory_variables({}).get("chat_history", [])
        serialized = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                serialized.append({"type": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                serialized.append({"type": "ai", "content": msg.content})
        return serialized
    
    def load_serialized_history_into_memory(self, serialized_history, memory):
        memory.chat_memory.clear()
        if not serialized_history:
            return
        try:
            for msg in serialized_history:
                if msg["type"] == "user":
                    memory.chat_memory.add_message(HumanMessage(content=msg["content"]))
                elif msg["type"] == "ai":
                    memory.chat_memory.add_message(AIMessage(content=msg["content"]))
        except Exception as e:
            print(f"Error loading conversation history: {str(e)}")
            memory.chat_memory.clear()

    def should_use_tools(self, message: str, user_context: dict = None) -> bool:
        """Decide whether to use tools or structured output based on context"""
        
        # Simple intent detection - you can make this more sophisticated
        message_lower = message.lower()
        
        # Use tools for these intents
        tool_intents = [
            "register", "sign up", "create account",
            "login", "log in", "sign in", 
            "book", "appointment", "schedule",
            "symptoms", "pain", "headache", "sick", "doctor"
        ]
        
        return any(intent in message_lower for intent in tool_intents)

    def generate_autonomous_response(self, message: str, user_context: dict = None) -> Tuple[Optional[str], Optional[PromptOutput]]:
        """Generate response with autonomous function calling when appropriate"""
        try:
            history_text = self.format_history_for_system()
            print(f"🔍 Memory length: {len(self.memory.chat_memory.messages)}")
            
            # Decide whether to use tools or structured output
            use_tools = self.should_use_tools(message, user_context)
            
            if use_tools:
                print("🔍 Using tools mode")
                return self._generate_with_tools(message, history_text, user_context)
            else:
                print("🔍 Using structured output mode")
                return self._generate_with_structured_output(message, history_text, user_context)
                
        except Exception as e:
            print(f"❌ Error in autonomous response: {e}")
            return "I'm sorry, I encountered an error. Please try again.", None

    def _generate_with_tools(self, message: str, history_text: str, user_context: dict) -> Tuple[str, None]:
        """Generate response using tools (function calling)"""
        
        prompt = self.get_prompt(history_text, user_context)
        chain = prompt | self.tool_llm

        # Invoke with tool calling
        result = chain.invoke({
            "input": message,
            "chat_history": self.memory.chat_memory.messages
        })

        # Handle tool calls
        if result.tool_calls:
            print(f"🔍 AI wants to call tools: {[tc.name for tc in result.tool_calls]}")
            
            # Execute all tool calls
            tool_results = []
            for tool_call in result.tool_calls:
                try:
                    # Find and execute the tool
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Execute the tool
                    for tool in HEALTHCARE_TOOLS:
                        if tool.name == tool_name:
                            tool_result = tool.invoke(tool_args)
                            tool_results.append(tool_result)
                            print(f"🔍 Tool {tool_name} result: {tool_result}")
                            break
                    
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    tool_results.append(error_msg)
                    print(f"❌ {error_msg}")

            # Generate final response based on tool results
            final_message = result.content or ""
            if tool_results:
                # Combine AI response with tool results
                final_message = f"{final_message}\n\n{tool_results[0]}"

            # Update memory
            self.memory.chat_memory.add_message(HumanMessage(content=message))
            self.memory.chat_memory.add_message(AIMessage(content=final_message))
            
            return final_message.strip(), None
        else:
            # No tools called, just return AI response
            ai_response = result.content
            
            # Update memory
            self.memory.chat_memory.add_message(HumanMessage(content=message))
            self.memory.chat_memory.add_message(AIMessage(content=ai_response))
            
            return ai_response, None

    def _generate_with_structured_output(self, message: str, history_text: str, user_context: dict) -> Tuple[Optional[str], Optional[PromptOutput]]:
        """Generate response using structured output (your original approach)"""
        
        prompt = self.get_prompt(history_text, user_context)
        chain = prompt | self.structured_llm

        output: PromptOutput = chain.invoke({
            "input": message,
            "chat_history": self.memory.chat_memory.messages
        })

        ai_reply = f"{output.closing_remark or ''} {output.next_question or ''}".strip()

        self.memory.chat_memory.add_message(HumanMessage(content=message))
        self.memory.chat_memory.add_message(AIMessage(content=ai_reply))
        
        print(f"🔍 Structured output: {output}")
        return None, output

# Enhanced Conversation Manager
class EnhancedConversationManager:
    _engines = {}
    
    @classmethod
    def get_engine(cls, user_phone_number: str, user_session) -> EnhancedAIEngine:
        print(f"🔍 get_engine called with: {user_phone_number}")
        
        if user_phone_number not in cls._engines:
            print(f"🔍 Creating NEW enhanced engine for: {user_phone_number}")
            engine = EnhancedAIEngine()
            
            # Load conversation history
            if user_session.ai_conversation_history:
                print(f"🔍 Loading {len(user_session.ai_conversation_history)} messages from database")
                engine.load_serialized_history_into_memory(
                    user_session.ai_conversation_history, 
                    engine.memory
                )
            
            cls._engines[user_phone_number] = engine
        else:
            engine = cls._engines[user_phone_number]
        
        print(f"🔍 Memory length: {len(engine.memory.chat_memory.messages)}")
        return engine
    
    @classmethod
    def save_conversation_history(cls, user_phone_number: str, user_session):
        if user_phone_number in cls._engines:
            engine = cls._engines[user_phone_number]
            serialized_history = engine.serialize_conversation_history(engine.memory)
            user_session.ai_conversation_history = serialized_history
            user_session.save()
            print(f"🔍 ✅ Saved {len(serialized_history)} messages to database")

# Enhanced message handler
def handle_conversation_mode_chatbot_message_v4(
    user_session,
    message_text: str,
):
    """Enhanced version with both structured output AND function calling"""
    
    try:
        # Create user context
        user_context = {
            "is_existing_user": getattr(user_session, 'is_an_existing_user', False),
            "has_active_profile": bool(getattr(user_session, 'active_patient_profile', None))
        }
        
        # Get enhanced engine
        ai_engine = EnhancedConversationManager.get_engine(user_session.user_phone_number, user_session)
        
        # Generate response (will use tools or structured output as appropriate)
        tool_response, structured_response = ai_engine.generate_autonomous_response(message_text, user_context)
        
        # Save conversation
        EnhancedConversationManager.save_conversation_history(user_session.user_phone_number, user_session)
        
        # Return appropriate response
        if tool_response:
            # Tool was used - return direct response
            return UTILITIES.create_text_message(tool_response)
        elif structured_response:
            # Structured output - use your existing logic
            return handle_structured_output(structured_response, user_session, message_text)
        else:
            return UTILITIES.create_text_message("I'm here to help! What can I do for you today?")
            
    except Exception as e:
        print(f"❌ Error in enhanced handler: {e}")
        return UTILITIES.create_text_message("I'm sorry, I encountered an error. Please try again later.")

def handle_structured_output(response: PromptOutput, user_session, message_text: str):
    """Your existing structured output handling logic"""
    
    next_question = response.next_question
    inquiry_intent = response.intent
    extracted_info = response.extracted_info or {}
    
    # Continue conversation if there's a next question
    if next_question and next_question.strip():
        return UTILITIES.create_text_message(next_question)
    
    # Handle different intents with your existing logic
    if inquiry_intent == "symptom_report":
        # Your existing symptom logic
        return handle_symptom_report_logic(extracted_info, user_session)
    elif inquiry_intent == "booking":
        # Your existing booking logic
        return handle_booking_logic(extracted_info, user_session, message_text)
    # ... other intent handlers
    
    # Default response
    return UTILITIES.create_text_message(
        response.closing_remark or "Thanks for chatting with us!"
    )

# Placeholder functions - replace with your actual handlers
def handle_symptom_report_logic(extracted_info, user_session):
    return UTILITIES.create_text_message("Symptom handling logic here")

def handle_booking_logic(extracted_info, user_session, message_text):
    return UTILITIES.create_text_message("Booking logic here")