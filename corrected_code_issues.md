# Issues in Your Updated Code

## 🚨 Critical Issues Found

### 1. **Syntax Error in Function**
```python
# Only serialize when conversation truly ends
if not response or not response.next_question:  # ❌ This line is incomplete
if not response:  # ❌ Duplicate if statement
```

**Problem**: Incomplete condition and duplicate `if not response:` statements.

### 2. **Wrong Memory Serialization Logic**
```python
if next_question is not None and next_question.strip() != "":
    user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)  # ❌ WRONG
    user_session.save()
    return UTILITIES.create_text_message(f"{next_question}\n")
```

**Problem**: You're serializing and saving conversation history **every time there's a next_question**. This defeats the purpose of the singleton pattern!

### 3. **ConversationManager Not Cleared Properly**
You never call `ConversationManager.clear_engine()` anywhere, so engines will never be cleaned up.

### 4. **Spacing Issues Still Present**
```python
def load_serialized_history_into_memory(self,serialized_history, memory):  # ❌ Missing space
```

## 🔧 Corrected Code

### Fixed Function:
```python
def handle_conversation_mode_chatbot_message_v2(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):
    # Reuse existing engine for this user
    ai_engine = ConversationManager.get_engine(user_session.user_id)
    
    # Only load history ONCE (when engine is first created)
    if not ai_engine.memory.chat_memory.messages:
        ai_engine.load_serialized_history_into_memory(
            user_session.ai_conversation_history, 
            ai_engine.memory
        )
    
    response, error = ai_engine.generate_response(message=message_text)
    
    # Handle error case first
    if not response:
        # Clean up engine on error
        ConversationManager.clear_engine(user_session.user_id)
        return [
            UTILITIES.create_text_message(
                "Sorry, our AI assistant is unavailable at the moment. Please try again later.\n"
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]

    next_question = response.next_question

    # If conversation continues, DON'T serialize yet
    if next_question is not None and next_question.strip() != "":
        # DON'T serialize here - keep conversation in memory
        # user_session.save()  # Only save user session state if needed
        return UTILITIES.create_text_message(f"{next_question}\n")

    # Conversation is ending - NOW serialize and clean up
    user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
    ConversationManager.clear_engine(user_session.user_id)  # Clean up engine
    
    # Reset conversation on intent completion
    user_session.reset_ai_conversation()
    user_session.set_state(
        session_state=WHATSAPP_PLUGIN1.WhatsappPlugin1UserSessionStates.DEFAULT.value
    )

    # Handle intents
    inquiry_intent = response.intent
    extracted_info = response.extracted_info or {}

    if inquiry_intent == "symptom_report":
        inquiry_obj = extracted_info.get("PromptOutputInquiry")
        symptoms = inquiry_obj.symptoms or [] if inquiry_obj else []

        if not symptoms:
            return [
                UTILITIES.create_text_message(
                    message="Error collecting symptom information. Please try again later.\n"
                ),
                PATIENTS_MESSAGES.create_home_message(user_session=user_session)
                if user_session.active_patient_profile
                else GENERAL_MESSAGES.landing_interactive_message(
                    is_existing_user=user_session.is_an_existing_user
                ),
            ]

        collected_symptoms = " ".join(symptoms)
        if inquiry_obj.additional_medical_information:
            collected_symptoms += " " + " ".join(
                inquiry_obj.additional_medical_information
            )

        return handle_doctor_recommendation_from_symptoms(
            user_session=user_session,
            symptoms=collected_symptoms
        )

    elif inquiry_intent == "booking":
        return [
            UTILITIES.create_text_message(
                handle_booking_intent(extracted_info, user=user_session.active_patient_profile)
            )
        ]

    # Handle fallback/default
    else:
        return [
            UTILITIES.create_text_message(
                response.closing_remark
                or "Thanks for chatting with us. Let us know if you need help again!"
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]
```

### Fixed AIEngine:
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

    def get_prompt(self, history_text: str):
        return ChatPromptTemplate.from_messages([
            SystemMessage(
                content=DEFAULT_CHATBOT_BASE_PROMPT.replace(
                    "[[CONVERSATION_HISTORY]]", history_text
                )
            ),
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
    
    def load_serialized_history_into_memory(self, serialized_history, memory):  # ✅ Fixed spacing
        # Clear existing memory to avoid duplication
        memory.chat_memory.clear()
        
        if not serialized_history:
            return
            
        try:
            for msg in serialized_history:
                if msg.get("type") == "user":
                    memory.chat_memory.add_message(HumanMessage(content=msg["content"]))
                elif msg.get("type") == "ai":
                    memory.chat_memory.add_message(AIMessage(content=msg["content"]))
        except Exception as e:
            log_error(f"Error loading conversation history: {str(e)}")
            memory.chat_memory.clear()  # Clear on error to prevent corruption
          
    def generate_response(self, message: str) -> Tuple[Optional[PromptOutput], Optional[str]]:
        try:
            history_text = self.format_history_for_system()
            prompt = self.get_prompt(history_text)
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


class ConversationManager:
    _engines = {} 
    
    @classmethod
    def get_engine(cls, user_id: str) -> AIEngine:
        if user_id not in cls._engines:
            cls._engines[user_id] = AIEngine()
        return cls._engines[user_id]
    
    @classmethod 
    def clear_engine(cls, user_id: str):
        """Call when conversation ends"""
        if user_id in cls._engines:
            del cls._engines[user_id]
```

## Key Changes Made:

1. **Fixed syntax error** - Removed duplicate `if not response:` 
2. **Fixed memory logic** - Only serialize when conversation truly ends
3. **Added proper cleanup** - Call `ConversationManager.clear_engine()` when appropriate
4. **Added error handling** - Clear memory on loading errors
5. **Fixed spacing** - Proper parameter spacing in methods

## Memory Flow Now:
1. **First message**: Load history from DB → Keep in memory
2. **Continuing messages**: Use memory directly (no DB operations)
3. **Last message**: Serialize to DB → Clear engine