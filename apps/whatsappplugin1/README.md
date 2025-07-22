# WhatsApp Plugin with ChatGPT-like Session Management

This WhatsApp healthcare bot has been enhanced with intelligent session management similar to ChatGPT, ensuring that users don't get confused symptoms and appointments between different consultation sessions.

## Key Features

### 🧠 Smart Session Management
- **Automatic Session Detection**: Automatically detects when a user is starting a new health consultation
- **Context Preservation**: Keeps important user information (name, profile) while clearing session-specific data
- **Time-based Expiration**: Sessions automatically expire after 24 hours
- **Manual Reset**: Users can manually start a new session

### 🔄 Session Lifecycle

1. **Session Creation**: New session automatically created for first-time users
2. **Context Tracking**: Tracks symptoms, doctor searches, and booking progress within a session
3. **Smart Reset**: Detects new consultations and resets appropriately
4. **Memory Archival**: Previous sessions are stored for reference but don't interfere

### 📋 What Gets Reset vs Preserved

#### Reset on New Session:
- Current symptoms and health concerns
- Doctor recommendations and search results
- Booking progress (appointments, payments)
- Conversation history

#### Preserved Across Sessions:
- User personal information (name, phone, profile)
- Account authentication status
- Important user preferences
- Historical appointment records

## Usage

### Basic Usage
```python
from apps.whatsappplugin1.main_handler import handle_whatsapp_message

# Handle incoming message
response = handle_whatsapp_message(phone_number="+254712345678", message="I have a headache")
```

### Manual Session Reset
```python
from apps.whatsappplugin1.main_handler import reset_user_session

# Manually reset user session
response = reset_user_session(phone_number="+254712345678")
```

### Session Information
```python
from apps.whatsappplugin1.main_handler import get_user_session_info

# Get session details
info = get_user_session_info(phone_number="+254712345678")
```

## Session Detection Triggers

The system automatically starts a new session when:

1. **Time-based**: 24 hours have passed since last activity
2. **Explicit Keywords**: User says "new session", "start over", "new consultation", etc.
3. **Context Switch**: AI detects user discussing unrelated health issues
4. **User Confirmation**: When prompted, user confirms it's a new consultation

## Example Scenarios

### Scenario 1: Same Day, Different Issues
```
Day 1 Morning:
User: "I have a headache"
AI: "Sorry to hear that. How long have you been experiencing headaches?"

Day 1 Afternoon:
User: "I have stomach pain now"
AI: "I notice you're mentioning something different from the headaches we discussed. 
     Are you looking to discuss a new health concern, or is this related? 
     Just let me know if this is a 'new consultation' or 'continue previous'."
```

### Scenario 2: Next Day Consultation
```
Day 1:
User: "I need help with back pain"
[... conversation about back pain ...]

Day 2:
User: "Hi, I have a different problem today"
AI: "Great! I've started a fresh consultation for you. How can I help you with your health today?"
```

## Database Schema

### New Fields in WhatsappPlugin1UserSession:
- `current_session_id`: Unique identifier for current session
- `last_session_reset`: Timestamp of last session reset
- `session_context`: Current session-specific data
- `session_memory_summary`: Compressed summary of previous sessions
- `important_user_info`: Persistent user data across sessions

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WhatsApp      │    │  Main Handler    │    │  AI Engine      │
│   Message       │───▶│                  │───▶│                 │
└─────────────────┘    │ - Session Check  │    │ - Memory Mgmt   │
                       │ - User Lookup    │    │ - Function Call │
                       │ - Response       │    │ - Context Track │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  User Session    │    │ Session Memory  │
                       │  Model           │    │ Manager         │
                       │                  │    │                 │
                       │ - User Data      │    │ - Conversation  │
                       │ - Session Info   │    │ - Context       │
                       │ - Booking Data   │    │ - Auto-cleanup  │
                       └──────────────────┘    └─────────────────┘
```

## Benefits

1. **No Cross-Session Confusion**: Symptoms from yesterday won't affect today's consultation
2. **Intelligent Context**: AI knows when to reset vs when to continue
3. **User-Friendly**: Automatic detection with manual override option
4. **Data Integrity**: Important user info preserved, temporary data cleaned
5. **Scalable**: Handles multiple users with independent sessions

## Migration

To migrate existing sessions to the new system:

1. Run database migration to add new fields
2. Existing sessions will automatically get session IDs
3. Previous conversation data is preserved in `previous_ai_conversations`
4. No data loss occurs during the upgrade

## Future Enhancements

- **Session Analytics**: Track session patterns and duration
- **Smart Suggestions**: Suggest new sessions based on time/context
- **Session Sharing**: Allow users to share session summaries with doctors
- **Multi-language Support**: Session management in multiple languages