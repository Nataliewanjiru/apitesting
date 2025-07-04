# True Persistent Memory System

## 🎯 **Vision: Year-Long Memory Persistence**

Create a system where users are remembered across months/years with:
- ✅ **User Recognition**: "Welcome back John! Last time you booked Dr. Mary for your heart condition"
- ✅ **Preference Memory**: Remembers location, consultation type, family members
- ✅ **Medical History**: Previous symptoms, doctors visited, appointment history
- ✅ **Context Continuity**: "How did your appointment with Dr. Mary go?"

## 🏗️ **Database Schema Enhancement**

### **1. Enhanced User Session Model**

```python
# Add these fields to your existing WhatsappPlugin1UserSession model or create a new UserMemory model

class UserMemoryProfile(models.Model):
    """Long-term memory profile for users"""
    
    user_phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Personal Information
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    preferred_location = models.CharField(max_length=200, blank=True, null=True)
    preferred_consultation_mode = models.CharField(max_length=50, blank=True, null=True)
    
    # Medical History Summary
    previous_symptoms = models.JSONField(default=list, blank=True)  # ["headache", "chest pain"]
    visited_doctors = models.JSONField(default=list, blank=True)   # [{"name": "Dr. Mary", "specialty": "cardiology", "date": "2024-01-15"}]
    medical_conditions = models.JSONField(default=list, blank=True) # ["hypertension", "diabetes"]
    
    # Family Members
    family_members = models.JSONField(default=list, blank=True)    # [{"name": "Mary", "age": 65, "relation": "mother"}]
    
    # Conversation Summary
    conversation_summary = models.TextField(blank=True, null=True)  # AI-generated summary of key points
    total_conversations = models.IntegerField(default=0)
    last_conversation_date = models.DateTimeField(auto_now=True)
    
    # Raw Conversation History (for recent conversations)
    recent_conversation_history = models.TextField(blank=True, null=True)  # Last 50 messages
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_memory_profiles'


class ConversationSession(models.Model):
    """Individual conversation sessions"""
    
    user_memory = models.ForeignKey(UserMemoryProfile, on_delete=models.CASCADE, related_name='sessions')
    session_id = models.CharField(max_length=100)  # WhatsApp conversation ID
    
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    
    # Session summary
    session_type = models.CharField(max_length=50)  # "booking", "symptom_check", "general"
    key_achievements = models.JSONField(default=list)  # ["booked_dr_mary", "reported_headache"]
    
    # Full conversation history for this session
    full_conversation = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'conversation_sessions'
```

## 🔧 **Enhanced Conversation Manager**

```python
class PersistentConversationManager:
    """Enhanced conversation manager with long-term memory"""
    
    conversation_engines = {}  # In-memory engines
    
    @classmethod
    def get_user_memory_profile(cls, phone_number):
        """Get or create user memory profile"""
        profile, created = UserMemoryProfile.objects.get_or_create(
            user_phone_number=phone_number
        )
        
        if created:
            print(f"🔍 New user profile created for {phone_number}")
        else:
            print(f"🔍 Existing user profile found for {phone_number} - {profile.total_conversations} previous conversations")
            
        return profile, created
    
    @classmethod
    def get_engine_with_memory(cls, phone_number, user_session):
        """Get AI engine with full persistent memory loaded"""
        
        # Get or reuse existing engine
        if phone_number in cls.conversation_engines:
            print(f"🔍 Using existing engine for {phone_number}")
            return cls.conversation_engines[phone_number]
        
        # Create new engine
        print(f"🔍 Creating new engine with persistent memory for {phone_number}")
        ai_engine = AIEngine()
        
        # Load persistent memory
        cls.load_persistent_memory(ai_engine, phone_number, user_session)
        
        cls.conversation_engines[phone_number] = ai_engine
        return ai_engine
    
    @classmethod
    def load_persistent_memory(cls, ai_engine, phone_number, user_session):
        """Load user's historical memory into AI engine"""
        
        # Get user memory profile
        profile, is_new_user = cls.get_user_memory_profile(phone_number)
        
        if is_new_user:
            print(f"🔍 New user - starting fresh conversation")
            return
        
        # Build memory context from profile
        memory_context = cls.build_memory_context(profile)
        
        if memory_context:
            print(f"🔍 Loading persistent memory: {len(memory_context)} context items")
            
            # Add memory context to AI engine
            for context_item in memory_context:
                ai_engine.memory.chat_memory.add_message(context_item)
        
        # Load recent conversation history if available
        if user_session.ai_conversation_history:
            print(f"🔍 Loading recent conversation history")
            ai_engine.load_serialized_history_into_memory(
                user_session.ai_conversation_history, 
                ai_engine.memory
            )
    
    @classmethod
    def build_memory_context(cls, profile):
        """Build memory context from user profile"""
        from langchain_core.messages import AIMessage, HumanMessage
        
        memory_items = []
        
        # Add user introduction context
        if profile.first_name:
            intro_context = f"User's name is {profile.first_name}"
            if profile.last_name:
                intro_context += f" {profile.last_name}"
            if profile.age:
                intro_context += f", age {profile.age}"
            if profile.preferred_location:
                intro_context += f", from {profile.preferred_location}"
                
            memory_items.append(HumanMessage(content=f"Hi, I'm {profile.first_name}"))
            memory_items.append(AIMessage(content=f"Hello {profile.first_name}! I remember you. How can I help you today?"))
        
        # Add medical history context
        if profile.previous_symptoms:
            symptoms_text = ", ".join(profile.previous_symptoms[-3:])  # Last 3 symptoms
            memory_items.append(AIMessage(content=f"I remember you've previously mentioned: {symptoms_text}"))
        
        # Add doctor history
        if profile.visited_doctors:
            recent_doctors = profile.visited_doctors[-2:]  # Last 2 doctors
            for doctor_info in recent_doctors:
                doctor_text = f"You previously visited {doctor_info.get('name', 'a doctor')}"
                if doctor_info.get('specialty'):
                    doctor_text += f" ({doctor_info['specialty']})"
                memory_items.append(AIMessage(content=doctor_text))
        
        # Add family context
        if profile.family_members:
            family_text = ", ".join([f"{member['name']} ({member.get('relation', 'family member')})" 
                                   for member in profile.family_members[-3:]])
            memory_items.append(AIMessage(content=f"I remember your family members: {family_text}"))
        
        # Add preferences
        if profile.preferred_consultation_mode:
            memory_items.append(AIMessage(content=f"You usually prefer {profile.preferred_consultation_mode} consultations"))
        
        return memory_items
    
    @classmethod
    def save_persistent_memory(cls, phone_number, ai_engine, conversation_summary=None):
        """Save conversation to persistent memory"""
        
        try:
            profile, _ = cls.get_user_memory_profile(phone_number)
            
            # Get conversation history
            conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
            
            # Parse and extract key information
            cls.extract_and_save_information(profile, conversation_history, ai_engine)
            
            # Update conversation count
            profile.total_conversations += 1
            profile.recent_conversation_history = conversation_history
            
            # Add conversation summary if provided
            if conversation_summary:
                profile.conversation_summary = cls.update_conversation_summary(
                    profile.conversation_summary, conversation_summary
                )
            
            profile.save()
            
            print(f"🔍 Persistent memory saved for {phone_number}")
            
        except Exception as e:
            print(f"🔍 Error saving persistent memory: {e}")
    
    @classmethod
    def extract_and_save_information(cls, profile, conversation_history, ai_engine):
        """Extract and save key information from conversation"""
        
        if not conversation_history:
            return
        
        try:
            # Parse conversation for key information
            messages = conversation_history.split('\n')
            
            # Extract user information
            for message in messages:
                if 'User:' in message:
                    user_msg = message.replace('User:', '').strip()
                    
                    # Extract name (simple pattern matching)
                    if not profile.first_name and ('my name is' in user_msg.lower() or 'i am' in user_msg.lower()):
                        name_parts = user_msg.lower().replace('my name is', '').replace('i am', '').strip().split()
                        if name_parts:
                            profile.first_name = name_parts[0].title()
                            if len(name_parts) > 1:
                                profile.last_name = name_parts[-1].title()
                    
                    # Extract age
                    if not profile.age and ('years' in user_msg or 'age' in user_msg.lower()):
                        import re
                        age_match = re.search(r'\b(\d{1,3})\s*(?:years?|yrs?)\b', user_msg)
                        if age_match:
                            profile.age = int(age_match.group(1))
                    
                    # Extract location
                    if not profile.preferred_location and any(word in user_msg.lower() for word in ['from', 'in', 'live']):
                        # Simple location extraction - you can enhance this
                        common_locations = ['nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'meru', 'nyeri']
                        for location in common_locations:
                            if location in user_msg.lower():
                                profile.preferred_location = location.title()
                                break
            
            # Extract symptoms, doctors, etc.
            # You can add more sophisticated extraction here
            
        except Exception as e:
            print(f"🔍 Error extracting information: {e}")
    
    @classmethod
    def update_conversation_summary(cls, existing_summary, new_summary):
        """Update conversation summary with new information"""
        
        if not existing_summary:
            return new_summary
        
        # Simple concatenation - you can use AI to create better summaries
        return f"{existing_summary}\n\nRecent: {new_summary}"
    
    @classmethod
    def clear_user_memory(cls, phone_number):
        """Clear user's persistent memory (for reset command)"""
        
        try:
            profile = UserMemoryProfile.objects.get(user_phone_number=phone_number)
            
            # Archive old profile instead of deleting
            profile.conversation_summary = f"[RESET] Previous summary: {profile.conversation_summary}"
            profile.first_name = None
            profile.last_name = None
            profile.age = None
            profile.preferred_location = None
            profile.previous_symptoms = []
            profile.visited_doctors = []
            profile.family_members = []
            profile.recent_conversation_history = None
            profile.save()
            
            # Clear engine
            if phone_number in cls.conversation_engines:
                del cls.conversation_engines[phone_number]
            
            print(f"🔍 User memory cleared for {phone_number}")
            
        except UserMemoryProfile.DoesNotExist:
            print(f"🔍 No memory profile found for {phone_number}")
```

## 🔧 **Updated Conversation Handler**

```python
def handle_conversation_mode_chatbot_message_v2(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):  
    # Handle reset command
    if message_text.lower() in ["reset", "clear", "start over", "forget me"]:
        PersistentConversationManager.clear_user_memory(user_session.user_phone_number)
        user_session.reset_ai_conversation()
        return [UTILITIES.create_text_message(
            "I've cleared our conversation history. Nice to meet you! How can I help you today?"
        )]
    
    # Get AI engine with persistent memory
    ai_engine = PersistentConversationManager.get_engine_with_memory(
        user_session.user_phone_number, 
        user_session
    )
    
    response, error = ai_engine.generate_response(message=message_text)
    
    # Handle AI error
    if not response:
        return [
            UTILITIES.create_text_message(
                "Sorry, I had a technical issue. Let me try again.\n"
            ),
            PATIENTS_MESSAGES.create_home_message(user_session=user_session)
            if user_session.active_patient_profile
            else GENERAL_MESSAGES.landing_interactive_message(
                is_existing_user=user_session.is_an_existing_user
            ),
        ]

    next_question = response.next_question
    inquiry_intent = response.intent
    extracted_info = response.extracted_info or {}

    # Continue conversation
    if next_question is not None and next_question.strip() != "":
        # Save progress periodically to persistent memory
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        PersistentConversationManager.save_persistent_memory(
            user_session.user_phone_number, 
            ai_engine
        )
        return UTILITIES.create_text_message(f"{next_question}\n")
    
    # Process intents (your existing logic)
    if inquiry_intent == "symptom_report":
        # ... your existing symptom logic ...
        pass
    
    elif inquiry_intent == "booking":
        # ... your existing booking logic ...
        pass
    
    # Always save to persistent memory
    user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
    PersistentConversationManager.save_persistent_memory(
        user_session.user_phone_number, 
        ai_engine, 
        conversation_summary=response.closing_remark
    )
    
    # Continue conversation
    return [UTILITIES.create_text_message(
        response.closing_remark or "Is there anything else I can help you with?"
    )]
```

## 🚀 **Expected User Experience**

### **Scenario 1: Returning User After 6 Months**
```
User: Hi
AI: Hello John! Welcome back! I remember you - you're 25 from Nairobi. Last time we talked, you booked Dr. Mary for your heart condition. How did that appointment go?
User: It went well, but now I need a pediatrician for my daughter
AI: That's great to hear about Dr. Mary! I'll help you find a pediatrician in Nairobi. What's your daughter's name and age?
```

### **Scenario 2: Family Context Memory**
```
User: Book a doctor for my mother
AI: I remember your mother Mary (65 years old). What type of doctor does she need this time?
User: A cardiologist
AI: I'll find a cardiologist in Nairobi for your mother Mary. She previously saw Dr. Johnson for her diabetes. Would you prefer a clinic visit like before?
```

### **Scenario 3: Medical History Context**
```
User: I have chest pain
AI: I'm concerned about your chest pain, especially since you mentioned heart issues before and saw Dr. Mary for cardiology. This could be related. Would you like me to help you book an urgent appointment with a cardiologist?
```

## 📋 **Implementation Steps**

1. **Create database models** for UserMemoryProfile and ConversationSession
2. **Replace ConversationManager** with PersistentConversationManager
3. **Update conversation handler** to use persistent memory
4. **Add memory extraction logic** for names, ages, locations, medical history
5. **Test with returning users** - create profile, wait, return, verify memory

This creates true persistent memory that makes your AI feel like it genuinely knows and remembers users across any time period!