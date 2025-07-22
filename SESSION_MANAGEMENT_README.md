# ChatGPT-Like Session Management for WhatsApp AI Agent

This implementation adds lasting memory and session management to your WhatsApp AI agent, similar to how ChatGPT handles conversations.

## 🎯 Problem Solved

**Before**: Your agent would mix up conversations from different days/sessions. If someone booked an appointment today and messaged tomorrow about a different issue, it would still use symptoms from today.

**After**: The agent now:
- ✅ Automatically detects new sessions
- ✅ Separates different conversations  
- ✅ Maintains context within a session
- ✅ Asks for confirmation when topics change
- ✅ Manages memory like ChatGPT (keeps important info, forgets irrelevant details)

## 🚀 Quick Setup

### 1. Apply Database Migration
```bash
python manage.py makemigrations whatsappplugin1 --name add_session_management
python manage.py migrate
```

### 2. Update Your Message Handler
Replace your existing WhatsApp message handler with:

```python
from apps.whatsappplugin1.session_handler import handle_whatsapp_message

def whatsapp_webhook_handler(request):
    phone_number = extract_phone_number(request)
    message = extract_message_text(request)
    
    # This one line handles everything: session detection, memory management, AI response
    response = handle_whatsapp_message(phone_number, message)
    
    send_whatsapp_message(phone_number, response)
    return JsonResponse({'status': 'success'})
```

### 3. That's it! 🎉

## 📋 How It Works

### Session Detection
The system automatically starts new sessions when:

1. **Time-based**: 2+ hours of inactivity
2. **Explicit keywords**: "new session", "start over", "new consultation"
3. **Context mismatch**: User mentions completely different symptoms
4. **New users**: First-time users always get a fresh session

### Smart Context Detection
```python
# Day 1: User talks about headaches
"I have a terrible headache"
# System: Stores context about headaches, builds conversation

# Day 2: User mentions different issue  
"I have chest pain and shortness of breath"
# System: Detects different medical context, asks for confirmation
# "I notice you're mentioning different health concerns. Is this a new consultation session?"
```

### Memory Management
Like ChatGPT, the system:
- **Compresses old conversations** into summaries
- **Keeps recent messages** for context (last 20 messages)
- **Stores important context** (symptoms, booking status, authentication)
- **Archives completed sessions** with metadata

## 📊 Session Data Structure

Each session stores:
```python
{
    'session_id': 'uuid-string',
    'start_time': '2024-01-15T10:30:00',
    'end_time': '2024-01-15T11:45:00', 
    'message_count': 15,
    'context': {
        'symptoms_mentioned': ['headache', 'nausea'],
        'booking_intent': True,
        'user_authenticated': True
    },
    'had_booking_activity': True,
    'user_authenticated': True
}
```

## 🔧 API Functions

### Main Handler
```python
response = handle_whatsapp_message(phone_number, message)
```

### Force New Session
```python
# Useful for admin operations
success = force_new_session("+254712345678")
```

### Get Session History
```python
history = get_session_history("+254712345678")
print(f"Total sessions: {history['total_sessions']}")
print(f"Current context: {history['current_session']['context']}")
```

## 🎭 Example Scenarios

### Scenario 1: Normal Conversation
```
User: "I have a headache"
AI: "Sorry to hear that. How long have you been experiencing this headache?"

User: "About 3 days"  
AI: "That sounds concerning. Have you noticed any other symptoms?"
# ✅ Context maintained within session
```

### Scenario 2: Context Change Detection
```
# After discussing headaches...
User: "I also have severe stomach pain and vomiting"
AI: "I notice you're mentioning different health concerns. Is this a new consultation session, or are you continuing from our previous discussion?"

User: "New session"
AI: "Starting a new consultation session. How can I help you today?"
# ✅ Fresh session started, previous symptoms cleared
```

### Scenario 3: Explicit New Session
```
User: "I want to start a new consultation about my back pain"
AI: "Starting a new session. How can I assist you today?"
# ✅ Immediate new session, no confirmation needed
```

### Scenario 4: Session Timeout
```
# User was discussing headaches 3 hours ago, now returns
User: "Hello"
AI: "I understand you'd like to start a new consultation. How can I help you today?"
# ✅ Automatic new session due to timeout
```

## ⚙️ Configuration Options

In `SessionManager` class, you can adjust:

```python
class SessionManager:
    def __init__(self):
        self.session_timeout = timedelta(hours=2)  # Session expiry time
        self.max_memory_messages = 20              # Messages to keep in context
        self.important_context_keywords = [        # Keywords for context detection
            'symptom', 'pain', 'appointment', 'doctor', 'booking'
        ]
```

## 🔍 Debugging & Monitoring

### Check Session Status
```python
history = get_session_history("+254712345678")
print(f"Current session ID: {history['current_session']['session_id']}")
print(f"Session started: {history['current_session']['start_time']}")
print(f"Messages in session: {history['current_session']['message_count']}")
```

### View Session Context
```python
user_session, _ = WhatsappPlugin1UserSession.get_for_phone_number("+254712345678")
print(f"Current symptoms: {user_session.get_session_context('symptoms_mentioned', [])}")
print(f"Booking in progress: {user_session.get_session_context('booking_intent', False)}")
```

## 🧠 Memory Compression

The system automatically:
1. **Keeps last 20 messages** in active memory
2. **Summarizes older sessions** with key metadata
3. **Limits session history** to last 10 sessions per user
4. **Preserves user profile data** across all sessions

## 🔄 Migration from Old System

Your existing data will be preserved. The new fields will be:
- `current_session_id`: Auto-generated for existing sessions
- `last_activity_time`: Set to current time
- `session_start_time`: Set to session creation time
- `conversation_sessions`: Empty initially, will populate as new sessions are created

## 🚨 Important Notes

1. **User profile data** (name, authentication status) persists across sessions
2. **Booking state** is reset with each new session 
3. **Symptoms and context** are session-specific
4. **AI function calls** work the same as before
5. **Database performance** is optimized with JSON field compression

## 📈 Benefits

- ✅ **No more mixed conversations** - each session is independent
- ✅ **Smart session detection** - automatic and manual triggers
- ✅ **Memory efficiency** - keeps only relevant context
- ✅ **User-friendly** - asks for confirmation when uncertain
- ✅ **ChatGPT-like experience** - familiar conversation flow
- ✅ **Backwards compatible** - existing code continues to work

## 🎉 Result

Now your agent behaves like ChatGPT:
- Remembers important information within a session
- Forgets irrelevant details from previous sessions  
- Asks users when it's unclear if they want a new session
- Provides a natural, contextual conversation experience

The user experience will be much more natural and professional! 🚀