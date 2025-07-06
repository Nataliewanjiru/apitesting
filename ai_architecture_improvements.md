# AI Architecture Improvements for Registration/Login Flow

## Current Problems

1. **AI prompts for all personal details during registration** when it should only ask for password for existing users
2. **Business logic checks happen after AI generation** instead of before, causing unnecessary prompting
3. **No user state context passed to AI** so it doesn't know if user is already registered

## Solution Overview

Restructure the architecture to:
1. **Pre-AI Business Logic Checks** - Check user status before AI generation
2. **Contextual AI Prompting** - Pass user state to AI as context
3. **Intent-Specific Handling** - Different flows for different registration states

## Implementation Solutions

### 1. Enhanced AIEngine with Context

```python
class AIEngine:
    def __init__(self):
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.output_parser = PydanticOutputParser(pydantic_object=PromptOutput)
        self.llm = init_chat_model(
            "gpt-4o", model_provider="openai", temperature=0.3
        ).with_structured_output(PromptOutput)

    def get_prompt(self, history_text: str, user_context: dict = None):
        """Enhanced prompt with user context"""
        context_info = ""
        if user_context:
            if user_context.get("is_existing_user"):
                context_info = f"\nUSER STATUS: This user is already registered in the system. For login, only ask for password."
            elif user_context.get("intent") == "register":
                context_info = f"\nUSER STATUS: This is a new user attempting to register. Collect: first_name, last_name, age, gender, county, location, password."
            elif user_context.get("needs_minimal_info"):
                context_info = f"\nUSER STATUS: Only collect minimal required information: {user_context.get('required_fields', 'password')}."
        
        system_content = DEFAULT_CHATBOT_BASE_PROMPT.replace(
            "[[CONVERSATION_HISTORY]]", history_text
        ) + context_info
        
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=system_content),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

    def generate_response(self, message: str, user_context: dict = None) -> Tuple[Optional[PromptOutput], Optional[str]]:
        try:
            history_text = self.format_history_for_system()
            print(f"🔍 Memory length: {len(self.memory.chat_memory.messages)}")
            print(f"🔍 User context: {user_context}")
            
            prompt = self.get_prompt(history_text, user_context)
            chain = prompt | self.llm

            output: PromptOutput = chain.invoke({
                "input": message,
                "chat_history": self.memory.chat_memory.messages
            })

            ai_reply = f"{output.closing_remark or ''} {output.next_question or ''}".strip()

            self.memory.chat_memory.add_message(HumanMessage(content=message))
            self.memory.chat_memory.add_message(AIMessage(content=ai_reply))
            
            print(output)
            return output, None
        except Exception as e:
            log_error(error_message=str(e))
            return None, str(e)
```

### 2. Pre-AI Business Logic Handler

```python
class PreAIHandler:
    @staticmethod
    def analyze_intent_and_user_state(message: str, user_session) -> dict:
        """Analyze message and return user context for AI"""
        
        # Simple intent detection (you might want to use a more sophisticated method)
        message_lower = message.lower()
        
        context = {
            "is_existing_user": user_session.is_an_existing_user,
            "user_phone": user_session.phone_number,
            "has_basic_info": bool(user_session.first_name and user_session.last_name)
        }
        
        # Registration intent handling
        if any(word in message_lower for word in ["register", "sign up", "create account"]):
            context["intent"] = "register"
            if user_session.is_an_existing_user:
                context["should_redirect_to_login"] = True
                context["needs_minimal_info"] = True
                context["required_fields"] = "password"
            else:
                context["needs_minimal_info"] = False
                context["required_fields"] = "first_name,last_name,age,gender,county,location,password"
        
        # Login intent handling  
        elif any(word in message_lower for word in ["login", "log in", "sign in"]):
            context["intent"] = "login"
            context["needs_minimal_info"] = True
            context["required_fields"] = "password"
        
        return context

    @staticmethod
    def should_handle_without_ai(context: dict, message: str) -> tuple[bool, str]:
        """Check if we can handle this without AI generation"""
        
        # If existing user tries to register
        if context.get("should_redirect_to_login"):
            return True, "You're already registered! Would you like to log in instead? Just send me your password."
        
        # If user is trying to login but not registered
        if context.get("intent") == "login" and not context.get("is_existing_user"):
            return True, "I don't see you in our system yet. Would you like to register first?"
            
        return False, ""
```

### 3. Enhanced ConversationManager

```python
class ConversationManager:
    _engines = {}
    
    @classmethod
    def get_engine(cls, user_phone_number: str, user_session) -> AIEngine:
        print(f"🔍 get_engine called with: {user_phone_number}")
        
        if user_phone_number not in cls._engines:
            print(f"🔍 Creating NEW engine for: {user_phone_number}")
            engine = AIEngine()
            
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
    def process_message_with_context(cls, message: str, user_session) -> str:
        """Main entry point with pre-AI business logic"""
        
        # Step 1: Analyze intent and user state
        context = PreAIHandler.analyze_intent_and_user_state(message, user_session)
        
        # Step 2: Check if we can handle without AI
        should_handle, direct_response = PreAIHandler.should_handle_without_ai(context, message)
        if should_handle:
            return direct_response
        
        # Step 3: Generate AI response with context
        engine = cls.get_engine(user_session.phone_number, user_session)
        output, error = engine.generate_response(message, context)
        
        if error:
            return "I'm sorry, I encountered an error. Please try again."
        
        # Step 4: Handle the response based on intent
        return cls.handle_ai_response(output, user_session, context)
    
    @classmethod
    def handle_ai_response(cls, output: PromptOutput, user_session, context: dict) -> str:
        """Handle AI response with business logic"""
        
        if not output or not output.intent:
            return "I'm not sure I understood. Could you please clarify what you'd like to do?"
        
        extracted_info = output.extracted_info or {}
        inquiry_intent = output.intent
        
        # Registration handling
        if inquiry_intent == "register":
            if user_session.is_an_existing_user:
                return "You're already registered. Would you like to log in to your account?"
            else:
                personal_details = extracted_info.get("PromptOutputPersonalDetails")
                if personal_details and cls.has_sufficient_registration_data(personal_details):
                    return handle_user_registration(user_session, personal_details)
                else:
                    # Continue collecting registration info
                    return output.next_question or output.closing_remark or "Please provide your registration details."
        
        # Login handling
        elif inquiry_intent == "login":
            if not user_session.is_an_existing_user:
                return "I don't see you in our system. Would you like to register first?"
            else:
                personal_details = extracted_info.get("PromptOutputPersonalDetails")
                if personal_details and personal_details.password:
                    return handle_user_login(user_session, personal_details)
                else:
                    return "Please provide your password to log in."
        
        # Other intents...
        else:
            return output.next_question or output.closing_remark or "How else can I help you?"
    
    @staticmethod
    def has_sufficient_registration_data(personal_details) -> bool:
        """Check if we have enough data for registration"""
        required_fields = ['first_name', 'last_name', 'age', 'gender', 'county', 'location', 'password']
        return all(getattr(personal_details, field, None) for field in required_fields)
```

### 4. Updated Prompt Template

Add this section to your `DEFAULT_CHATBOT_BASE_PROMPT`:

```python
# Add this section to your prompt
REGISTRATION_LOGIN_GUIDANCE = """

REGISTRATION & LOGIN SPECIFIC GUIDANCE:

When user intent is "register":
- If USER STATUS indicates they are already registered, do NOT ask for personal details
- If USER STATUS indicates new user registration, collect: first_name, last_name, age, gender, county, location, password
- Ask for ONE field at a time in a conversational manner
- Do not ask for email or phone_number during registration

When user intent is "login":  
- If USER STATUS indicates existing user, ONLY ask for password
- If USER STATUS indicates user not registered, suggest registration instead
- Do not collect any other personal details for login

IMPORTANT: Always check USER STATUS section above for specific guidance on what information to collect.
"""

# Append this to your existing DEFAULT_CHATBOT_BASE_PROMPT
DEFAULT_CHATBOT_BASE_PROMPT = """
[Your existing prompt content...]

""" + REGISTRATION_LOGIN_GUIDANCE
```

### 5. Usage in Your Main Handler

```python
# Replace your current message handling with:
def handle_whatsapp_message(message: str, user_session):
    try:
        # Use the new enhanced conversation manager
        response = ConversationManager.process_message_with_context(message, user_session)
        
        # Save conversation history
        ConversationManager.save_conversation_history(user_session.phone_number, user_session)
        
        return UTILITIES.create_text_message(response)
        
    except Exception as e:
        log_error(f"Error in handle_whatsapp_message: {str(e)}")
        return UTILITIES.create_text_message("I'm sorry, something went wrong. Please try again.")
```

## Key Benefits

1. **Pre-AI Checks**: Business logic runs before AI generation
2. **Contextual AI**: AI knows user state and asks appropriate questions  
3. **Efficient Flow**: No unnecessary prompting for existing users
4. **Better UX**: Users get immediate feedback for known states
5. **Maintainable**: Clear separation of concerns

## Testing Scenarios

1. **Existing user says "register"** → Immediate redirect to login
2. **New user says "register"** → Collect full registration details
3. **Existing user says "login"** → Only ask for password
4. **Non-existing user says "login"** → Suggest registration
5. **Ambiguous intent** → AI handles with context

This architecture ensures efficient handling of registration/login flows while maintaining the conversational AI experience for other intents.