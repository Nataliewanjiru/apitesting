# Simple Persistent Memory Implementation

## 🎯 **Goal: Remember Users Across Months/Years**

Instead of memory that only lasts during a session, create memory that persists across:
- ✅ Days, weeks, months, even years
- ✅ User information (name, age, location, preferences)
- ✅ Medical history (previous symptoms, doctors visited)
- ✅ Family members (mother, father, children)
- ✅ Previous conversations and context

## 🏗️ **Step 1: Create Database Model**

Add this model to your Django app:

```python
# In your models.py file (e.g., apps/whatsappplugin1/models.py)

class UserMemoryProfile(models.Model):
    """Persistent memory for users across all conversations"""
    
    user_phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Personal Info
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    preferred_location = models.CharField(max_length=200, blank=True, null=True)
    preferred_consultation_mode = models.CharField(max_length=50, blank=True, null=True)
    
    # Medical History
    previous_symptoms = models.JSONField(default=list, blank=True)
    visited_doctors = models.JSONField(default=list, blank=True)
    family_members = models.JSONField(default=list, blank=True)
    
    # Conversation Data
    total_conversations = models.IntegerField(default=0)
    last_conversation_summary = models.TextField(blank=True, null=True)
    full_conversation_history = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name or 'Unknown'} ({self.user_phone_number})"
    
    class Meta:
        db_table = 'user_memory_profiles'
```

## 🔧 **Step 2: Enhanced Conversation Manager**

Replace your current `ConversationManager` with this enhanced version:

```python
# In your aiengine2.py or conversation manager file

class PersistentConversationManager:
    conversation_engines = {}
    
    @classmethod
    def get_engine(cls, phone_number):
        """Get engine with persistent memory"""
        
        if phone_number in cls.conversation_engines:
            print(f"🔍 Using existing engine for {phone_number}")
            return cls.conversation_engines[phone_number]
        
        print(f"🔍 Creating new engine with memory for {phone_number}")
        ai_engine = AIEngine()
        
        # Load persistent memory
        cls.load_user_memory(ai_engine, phone_number)
        
        cls.conversation_engines[phone_number] = ai_engine
        return ai_engine
    
    @classmethod
    def load_user_memory(cls, ai_engine, phone_number):
        """Load user's historical memory"""
        
        try:
            from apps.whatsappplugin1.models import UserMemoryProfile
            
            # Get or create user profile
            profile, created = UserMemoryProfile.objects.get_or_create(
                user_phone_number=phone_number
            )
            
            if created:
                print(f"🔍 New user profile created for {phone_number}")
                return
            
            print(f"🔍 Loading memory for returning user: {profile.first_name or 'Unknown'} ({profile.total_conversations} conversations)")
            
            # Build memory context
            memory_messages = cls.build_memory_context(profile)
            
            # Add memory to AI engine
            for message in memory_messages:
                ai_engine.memory.chat_memory.add_message(message)
            
            print(f"🔍 Loaded {len(memory_messages)} memory items")
            
        except Exception as e:
            print(f"🔍 Error loading user memory: {e}")
    
    @classmethod
    def build_memory_context(cls, profile):
        """Build memory context from user profile"""
        from langchain_core.messages import AIMessage, HumanMessage
        
        messages = []
        
        # Add user identity
        if profile.first_name:
            messages.append(HumanMessage(content=f"Hi, I'm {profile.first_name}"))
            
            context = f"Hello {profile.first_name}! I remember you"
            if profile.age:
                context += f" - you're {profile.age} years old"
            if profile.preferred_location:
                context += f" from {profile.preferred_location}"
            context += ". How can I help you today?"
            
            messages.append(AIMessage(content=context))
        
        # Add medical history
        if profile.previous_symptoms:
            recent_symptoms = profile.previous_symptoms[-3:]  # Last 3 symptoms
            messages.append(AIMessage(content=f"I remember you've mentioned: {', '.join(recent_symptoms)}"))
        
        # Add doctor history
        if profile.visited_doctors:
            recent_doctors = profile.visited_doctors[-2:]  # Last 2 doctors
            for doctor in recent_doctors:
                messages.append(AIMessage(content=f"You previously saw {doctor.get('name', 'a doctor')}"))
        
        # Add family context
        if profile.family_members:
            family_names = [member['name'] for member in profile.family_members[-3:]]
            messages.append(AIMessage(content=f"I remember your family: {', '.join(family_names)}"))
        
        return messages
    
    @classmethod
    def save_user_memory(cls, phone_number, ai_engine):
        """Save conversation to persistent memory"""
        
        try:
            from apps.whatsappplugin1.models import UserMemoryProfile
            
            profile, _ = UserMemoryProfile.objects.get_or_create(
                user_phone_number=phone_number
            )
            
            # Get conversation history
            conversation = ai_engine.serialize_conversation_history(ai_engine.memory)
            
            # Extract and save information
            cls.extract_user_info(profile, conversation)
            
            # Update conversation data
            profile.total_conversations += 1
            profile.full_conversation_history = conversation
            profile.save()
            
            print(f"🔍 Memory saved for {phone_number}")
            
        except Exception as e:
            print(f"🔍 Error saving memory: {e}")
    
    @classmethod
    def extract_user_info(cls, profile, conversation):
        """Extract key information from conversation"""
        
        if not conversation:
            return
        
        import re
        
        try:
            # Extract from conversation text
            messages = conversation.split('\n')
            
            for message in messages:
                if 'User:' in message:
                    text = message.replace('User:', '').strip().lower()
                    
                    # Extract name
                    if not profile.first_name:
                        if 'my name is' in text or 'i am' in text:
                            name_text = text.replace('my name is', '').replace('i am', '').strip()
                            name_parts = name_text.split()
                            if name_parts and name_parts[0].isalpha():
                                profile.first_name = name_parts[0].title()
                                if len(name_parts) > 1:
                                    profile.last_name = name_parts[-1].title()
                    
                    # Extract age
                    if not profile.age:
                        age_match = re.search(r'(\d{1,3})\s*(?:years?|yrs?)', text)
                        if age_match:
                            profile.age = int(age_match.group(1))
                    
                    # Extract location
                    if not profile.preferred_location:
                        locations = ['nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'meru']
                        for location in locations:
                            if location in text:
                                profile.preferred_location = location.title()
                                break
                    
                    # Extract symptoms
                    symptom_keywords = ['headache', 'fever', 'pain', 'cough', 'cold', 'chest pain', 'back pain']
                    for symptom in symptom_keywords:
                        if symptom in text and symptom not in profile.previous_symptoms:
                            profile.previous_symptoms.append(symptom)
                    
                    # Extract family members
                    family_keywords = {
                        'mother': 'mother', 'mom': 'mother', 'father': 'father', 'dad': 'father',
                        'son': 'son', 'daughter': 'daughter', 'child': 'child', 'baby': 'baby'
                    }
                    for keyword, relation in family_keywords.items():
                        if keyword in text:
                            # Try to extract name if mentioned
                            family_member = {'relation': relation, 'name': 'Unknown'}
                            if family_member not in profile.family_members:
                                profile.family_members.append(family_member)
                
                # Extract doctor names from AI responses
                elif 'AI:' in message and 'Dr.' in message:
                    text = message.replace('AI:', '').strip()
                    doctor_match = re.search(r'Dr\.?\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)', text)
                    if doctor_match:
                        doctor_name = doctor_match.group(0)
                        doctor_info = {'name': doctor_name, 'date': str(datetime.now().date())}
                        if doctor_info not in profile.visited_doctors:
                            profile.visited_doctors.append(doctor_info)
        
        except Exception as e:
            print(f"🔍 Error extracting info: {e}")
    
    @classmethod
    def clear_engine(cls, phone_number):
        """Clear engine and optionally reset memory"""
        if phone_number in cls.conversation_engines:
            del cls.conversation_engines[phone_number]
```

## 🔧 **Step 3: Update Your Conversation Handler**

Update your conversation handler to use persistent memory:

```python
def handle_conversation_mode_chatbot_message_v2(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    message_text: str,
):  
    # Handle reset command
    if message_text.lower() in ["reset", "clear memory", "forget me"]:
        try:
            from apps.whatsappplugin1.models import UserMemoryProfile
            UserMemoryProfile.objects.filter(user_phone_number=user_session.user_phone_number).delete()
            PersistentConversationManager.clear_engine(user_session.user_phone_number)
            user_session.reset_ai_conversation()
            return [UTILITIES.create_text_message("I've cleared our history. Nice to meet you! How can I help?")]
        except:
            pass
    
    # Get AI engine with persistent memory
    ai_engine = PersistentConversationManager.get_engine(user_session.user_phone_number)
    
    # Load recent conversation if exists
    if not ai_engine.memory.chat_memory.messages and user_session.ai_conversation_history:
        ai_engine.load_serialized_history_into_memory(
            user_session.ai_conversation_history, 
            ai_engine.memory
        )
    
    response, error = ai_engine.generate_response(message=message_text)
    
    if not response:
        return [UTILITIES.create_text_message("Sorry, I had a technical issue. Please try again.")]

    next_question = response.next_question
    inquiry_intent = response.intent
    extracted_info = response.extracted_info or {}

    # Continue conversation
    if next_question is not None and next_question.strip() != "":
        # Save progress
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        PersistentConversationManager.save_user_memory(user_session.user_phone_number, ai_engine)
        return UTILITIES.create_text_message(f"{next_question}\n")
    
    # Process intents (your existing logic)
    if inquiry_intent == "symptom_report":
        # ... your existing symptom logic ...
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        PersistentConversationManager.save_user_memory(user_session.user_phone_number, ai_engine)
        # ... continue with symptom handling ...
    
    elif inquiry_intent == "booking":
        # ... your existing booking logic with the availability fix ...
        user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
        PersistentConversationManager.save_user_memory(user_session.user_phone_number, ai_engine)
        # ... continue with booking handling ...
    
    # Always save memory
    user_session.ai_conversation_history = ai_engine.serialize_conversation_history(ai_engine.memory)
    PersistentConversationManager.save_user_memory(user_session.user_phone_number, ai_engine)
    
    return [UTILITIES.create_text_message(
        response.closing_remark or "Is there anything else I can help you with?"
    )]
```

## 🚀 **Step 4: Database Migration**

Create and run the migration:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 🎯 **Expected Results**

### **First Time User:**
```
User: Hi
AI: Hi there! I'm your Rastuc care assistant. How can I help you today?
User: I'm John, 25, from Nairobi
AI: Nice to meet you John! How can I help you in Nairobi?
```

### **Returning User (After Months):**
```
User: Hi  
AI: Hello John! I remember you - you're 25 years old from Nairobi. How can I help you today?
User: I need a doctor
AI: I'll help you find a doctor in Nairobi. I remember you previously saw Dr. Mary. What type of doctor do you need this time?
```

### **Family Context Memory:**
```
User: Book a doctor for my mother
AI: I remember your mother. What type of doctor does she need?
User: She needs a cardiologist
AI: I'll find a cardiologist in Nairobi for your mother. Would you prefer a clinic visit like before?
```

## 📋 **Quick Implementation Steps**

1. **Add UserMemoryProfile model** to your models.py
2. **Replace ConversationManager** with PersistentConversationManager
3. **Update conversation handler** to save/load persistent memory
4. **Run migrations** to create database table
5. **Test** - have conversation, close app, reopen after time, verify memory

This creates true persistent memory that remembers users across any time period - days, months, or years!