# Function-Based AI Solution with Context

## Why Function-Based Approach is Better

1. **Simpler Architecture** - No complex class hierarchies
2. **Direct Memory Management** - Clear per-user memory storage
3. **Easier Context Passing** - Function parameters are straightforward
4. **Less Overhead** - No object instantiation complexity
5. **Better for Your Use Case** - Fits registration/login flows perfectly

## Complete Implementation

### 1. Enhanced Function-Based AI with Context

```python
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from typing import Dict, Tuple, Optional

# Global memory store for all users
user_memory_store: Dict[str, ConversationBufferMemory] = {}

def get_user_memory(user_id: str) -> ConversationBufferMemory:
    """Get or create memory for a user"""
    if user_id not in user_memory_store:
        user_memory_store[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return user_memory_store[user_id]

def create_contextual_prompt(base_prompt: str, user_context: dict = None) -> str:
    """Create prompt with user context"""
    context_info = ""
    if user_context:
        if user_context.get("is_existing_user") and user_context.get("intent") == "login":
            context_info = "\nUSER STATUS: This user is already registered. For login, ONLY ask for password."
        elif user_context.get("intent") == "register" and not user_context.get("is_existing_user"):
            context_info = "\nUSER STATUS: New user registration. Collect: first_name, last_name, age, gender, county, location, password."
        elif user_context.get("should_redirect"):
            context_info = f"\nUSER STATUS: {user_context.get('redirect_message', '')}"
    
    return base_prompt + context_info

def ask_question_with_context(question: str, user_id: str, user_context: dict = None) -> PromptOutput:
    """Enhanced ask_question function with context support"""
    memory = get_user_memory(user_id)
    
    # Create contextual prompt
    contextual_prompt = create_contextual_prompt(DEFAULT_CHATBOT_BASE_PROMPT, user_context)
    
    # Create your chain with the contextual prompt
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=contextual_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    # Use your existing LLM with structured output
    llm = init_chat_model("gpt-4o", model_provider="openai", temperature=0.3).with_structured_output(PromptOutput)
    chain = prompt | llm
    
    try:
        # Get chat history
        chat_history = memory.load_memory_variables({})["chat_history"]
        
        # Invoke the chain
        result: PromptOutput = chain.invoke({
            "input": question,
            "chat_history": chat_history
        })
        
        # Create AI response text
        ai_response = f"{result.closing_remark or ''} {result.next_question or ''}".strip()
        
        # Update memory
        memory.chat_memory.add_message(HumanMessage(content=question))
        memory.chat_memory.add_message(AIMessage(content=ai_response))
        
        print(f"🔍 AI Response: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Error in AI generation: {e}")
        # Return a fallback PromptOutput
        return PromptOutput(
            next_question="",
            closing_remark="I'm sorry, I encountered an error. Please try again.",
            intent="error"
        )

def save_user_conversation_to_db(user_id: str, user_session):
    """Save conversation history to database"""
    if user_id in user_memory_store:
        memory = user_memory_store[user_id]
        history = memory.load_memory_variables({})["chat_history"]
        
        # Serialize history
        serialized = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                serialized.append({"type": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                serialized.append({"type": "ai", "content": msg.content})
        
        user_session.ai_conversation_history = serialized
        user_session.save()
        print(f"🔍 ✅ Saved {len(serialized)} messages to database")

def load_user_conversation_from_db(user_id: str, user_session):
    """Load conversation history from database"""
    if user_session.ai_conversation_history:
        memory = get_user_memory(user_id)
        memory.chat_memory.clear()
        
        try:
            for msg in user_session.ai_conversation_history:
                if msg["type"] == "user":
                    memory.chat_memory.add_message(HumanMessage(content=msg["content"]))
                elif msg["type"] == "ai":
                    memory.chat_memory.add_message(AIMessage(content=msg["content"]))
            print(f"🔍 Loaded {len(user_session.ai_conversation_history)} messages from database")
        except Exception as e:
            print(f"❌ Error loading conversation history: {e}")
            memory.chat_memory.clear()
```

### 2. Pre-AI Business Logic Functions

```python
def analyze_user_intent_and_state(message: str, user_session) -> dict:
    """Analyze message and return user context"""
    message_lower = message.lower()
    
    context = {
        "is_existing_user": user_session.is_an_existing_user,
        "user_phone": user_session.phone_number,
        "message": message
    }
    
    # Registration intent
    if any(word in message_lower for word in ["register", "sign up", "create account"]):
        context["intent"] = "register"
        if user_session.is_an_existing_user:
            context["should_redirect"] = True
            context["redirect_message"] = "User is already registered, redirect to login"
    
    # Login intent
    elif any(word in message_lower for word in ["login", "log in", "sign in"]):
        context["intent"] = "login"
        if not user_session.is_an_existing_user:
            context["should_redirect"] = True
            context["redirect_message"] = "User not registered, suggest registration"
    
    return context

def handle_pre_ai_checks(context: dict) -> Tuple[bool, str]:
    """Handle simple cases without AI"""
    
    # Existing user trying to register
    if (context.get("intent") == "register" and 
        context.get("is_existing_user") and 
        context.get("should_redirect")):
        return True, "You're already registered! Would you like to log in instead? Just send me your password."
    
    # Non-existing user trying to login
    if (context.get("intent") == "login" and 
        not context.get("is_existing_user") and 
        context.get("should_redirect")):
        return True, "I don't see you in our system yet. Would you like to register first?"
    
    return False, ""

def has_sufficient_registration_data(personal_details) -> bool:
    """Check if we have enough data for registration"""
    if not personal_details:
        return False
    
    required_fields = ['first_name', 'last_name', 'age', 'gender', 'county', 'location', 'password']
    return all(getattr(personal_details, field, None) for field in required_fields)
```

### 3. Main Processing Function

```python
def process_whatsapp_message(message: str, user_session) -> str:
    """Main entry point for processing WhatsApp messages"""
    
    user_id = user_session.phone_number
    
    try:
        # Load conversation history if first time
        if user_id not in user_memory_store:
            load_user_conversation_from_db(user_id, user_session)
        
        # Step 1: Analyze intent and user state
        context = analyze_user_intent_and_state(message, user_session)
        print(f"🔍 Context: {context}")
        
        # Step 2: Handle simple cases without AI
        should_handle_directly, direct_response = handle_pre_ai_checks(context)
        if should_handle_directly:
            print(f"🔍 Direct response: {direct_response}")
            # Still update memory for direct responses
            memory = get_user_memory(user_id)
            memory.chat_memory.add_message(HumanMessage(content=message))
            memory.chat_memory.add_message(AIMessage(content=direct_response))
            return direct_response
        
        # Step 3: Generate AI response with context
        ai_output = ask_question_with_context(message, user_id, context)
        
        # Step 4: Handle AI response with business logic
        final_response = handle_ai_output(ai_output, user_session, context)
        
        # Step 5: Save conversation
        save_user_conversation_to_db(user_id, user_session)
        
        return final_response
        
    except Exception as e:
        print(f"❌ Error in process_whatsapp_message: {e}")
        return "I'm sorry, something went wrong. Please try again."

def handle_ai_output(ai_output: PromptOutput, user_session, context: dict) -> str:
    """Handle AI output with business logic"""
    
    if not ai_output or not ai_output.intent:
        return "I'm not sure I understood. Could you please clarify what you'd like to do?"
    
    extracted_info = ai_output.extracted_info or {}
    intent = ai_output.intent
    
    # Registration handling
    if intent == "register":
        if user_session.is_an_existing_user:
            return "You're already registered. Would you like to log in to your account?"
        else:
            personal_details = extracted_info.get("PromptOutputPersonalDetails")
            if personal_details and has_sufficient_registration_data(personal_details):
                return handle_user_registration(user_session, personal_details)
            else:
                return ai_output.next_question or ai_output.closing_remark or "Please provide your registration details."
    
    # Login handling
    elif intent == "login":
        if not user_session.is_an_existing_user:
            return "I don't see you in our system. Would you like to register first?"
        else:
            personal_details = extracted_info.get("PromptOutputPersonalDetails")
            if personal_details and personal_details.password:
                return handle_user_login(user_session, personal_details)
            else:
                return "Please provide your password to log in."
    
    # Other intents (booking, inquiry, etc.)
    elif intent == "booking":
        # Your existing booking logic
        return handle_booking_intent(ai_output, user_session)
    
    elif intent == "symptom_report":
        # Your existing symptom logic
        return handle_symptom_report(ai_output, user_session)
    
    # Default response
    else:
        return ai_output.next_question or ai_output.closing_remark or "How else can I help you?"
```

### 4. Usage in Your WhatsApp Handler

```python
# Your main WhatsApp message handler becomes super simple:
def handle_whatsapp_message(message_body: str, user_session):
    try:
        response_text = process_whatsapp_message(message_body, user_session)
        return UTILITIES.create_text_message(response_text)
    except Exception as e:
        log_error(f"Error in handle_whatsapp_message: {str(e)}")
        return UTILITIES.create_text_message("I'm sorry, something went wrong. Please try again.")
```

## Key Benefits of This Approach

1. **Simple & Clean**: Just call `process_whatsapp_message(message, user_session)`
2. **Pre-AI Checks**: Business logic runs before AI generation
3. **Context Passing**: AI gets user state information
4. **Memory Management**: Automatic per-user conversation memory
5. **Error Handling**: Graceful fallbacks at every step
6. **Database Integration**: Automatic save/load of conversations

## Testing Examples

```python
# Existing user says "register"
context = {"intent": "register", "is_existing_user": True}
# Result: "You're already registered! Would you like to log in instead?"
# ✅ No AI generation needed

# New user says "register"  
context = {"intent": "register", "is_existing_user": False}
# Result: AI asks for registration details one by one
# ✅ AI gets context to ask for proper fields

# Existing user says "login"
context = {"intent": "login", "is_existing_user": True}
# Result: AI only asks for password
# ✅ No unnecessary personal detail collection
```

This function-based approach is much simpler than the class-based architecture and solves all your issues while being easier to maintain and extend!