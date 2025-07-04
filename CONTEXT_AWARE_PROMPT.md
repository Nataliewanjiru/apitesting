# Context-Aware AI Prompt Enhancement

## 🎯 **Enhanced Prompt for Persistent Memory**

Add this context awareness section to your existing `DEFAULT_CHATBOT_BASE_PROMPT`:

```python
DEFAULT_CHATBOT_BASE_PROMPT = """
[Your existing prompt content...]

CRITICAL - CONTEXT AWARENESS RULES:

1. REMEMBER PREVIOUS INFORMATION:
   - User's name, age, location from earlier messages
   - Previous booking attempts and preferences
   - Doctor selections and consultation types
   - Symptoms and medical history mentioned

2. HANDLE CONTEXT UPDATES NATURALLY:
   When users want to change information, update smoothly:
   - "I want a doctor in Meru instead of Nairobi" → Update location to Meru
   - "Actually, book for my mother not me" → Switch patient context
   - "I prefer home visits now" → Update consultation preference
   - "Show me pediatricians instead" → Change specialty

3. REFERENCE PREVIOUS CONTEXT:
   Use remembered information to provide better service:
   - "I remember you're in Nairobi, let me find doctors there"
   - "You mentioned headaches earlier, is this related?"
   - "Based on your preference for clinic visits..."

4. HANDLE CONFLICTING INFORMATION:
   When users provide different info, ask for clarification:
   - "I see you mentioned Nairobi before, should I look in Meru instead?"
   - "You previously said clinic visits, do you prefer home visits now?"

5. NATURAL CONVERSATION FLOW:
   - Greet returning users: "Hello again! How can I help you today?"
   - Build on previous conversations naturally
   - Allow seamless transitions between topics

6. LOCATION CHANGE EXAMPLES:
   User: "Show me doctors in Meru instead of Nairobi"
   AI: "I understand - you'd like to find doctors in Meru instead of Nairobi. What type of specialist are you looking for in Meru?"
   
   User: "Any cardiologists in Kisumu?"  
   AI: "I'll help you find cardiologists in Kisumu. I remember you prefer clinic visits - should I look for clinic-based cardiologists there?"

7. BOOKING CONTEXT EXAMPLES:
   User: "Book Dr John instead of Dr Mary"
   AI: "I'll help you book Dr John instead. I remember you wanted a clinic visit on [date] at [time] - should I check Dr John's availability for the same time?"

8. FAMILY CONTEXT EXAMPLES:
   User: "Book for my father this time"
   AI: "I'll help you book an appointment for your father. I remember you're John from Nairobi. What's your father's name and age?"

IMPORTANT OUTPUT RULES:
- Always extract information into the standard format (PromptOutputPersonalDetails, etc.)
- When information changes, extract the NEW information in the output
- If location changes from Nairobi to Meru, output location: "Meru"
- If doctor changes from "Dr Mary" to "Dr John", output selected_doctor: "Dr John"

[Rest of your existing prompt...]
"""
```

## 🚀 **Example Context-Aware Conversations**

### **Scenario 1: Location Change Mid-Conversation**
```
User: Hi, I'm John, 25, in Nairobi
AI: Hello John! How can I help you in Nairobi today?
User: I need a cardiologist
AI: I'll help you find a cardiologist in Nairobi. What type of consultation do you prefer?
User: Actually, show me cardiologists in Meru instead
AI: I understand - you'd like cardiologists in Meru instead of Nairobi. What type of consultation would you prefer?

[AI Output:]
{
  "PromptOutputPersonalDetails": {
    "first_name": "John",
    "age": 25,
    "location": "Meru"  // Updated from Nairobi
  },
  "PromptOutputBooking": {
    "specialization": "cardiologist"
  }
}
```

### **Scenario 2: Building on Previous Booking**
```
User: Book Dr Natalie for tomorrow
AI: I remember you prefer clinic visits in Nairobi. What time would you like for Dr Natalie tomorrow?
User: 2pm
AI: Let me check Dr Natalie's availability tomorrow at 2pm for a clinic visit in Nairobi...

[AI Output:]
{
  "PromptOutputBooking": {
    "selected_doctor": "Dr Natalie",
    "preferred_date": "tomorrow",
    "preferred_consultation_time": "2pm"
  },
  "PromptOutputInquiry": {
    "preferred_modes_of_consultation": ["clinic"]  // From memory
  }
}
```

### **Scenario 3: Family Member Context Switch**
```
User: I want to book for my mother instead
AI: I'll help you book for your mother instead. I remember you're John from Nairobi. What's your mother's name and age?
User: Mary, 60 years old
AI: I'll help book an appointment for Mary (60) in Nairobi. What type of doctor does she need?

[AI Output:]
{
  "PromptOutputPersonalDetails": {
    "first_name": "Mary",  // New patient
    "age": 60,
    "location": "Nairobi"  // Inherited from context
  }
}
```

## 🎯 **Key Prompt Enhancements**

1. **Context Memory**: Remember and reference previous information
2. **Natural Updates**: Handle changes smoothly without confusion
3. **Clarification**: Ask when information conflicts
4. **Location Awareness**: Handle "Meru instead of Nairobi" naturally
5. **Family Context**: Switch between family members seamlessly
6. **Preference Memory**: Remember consultation types, doctor preferences

This enhanced prompt will make your AI agent much more conversational and context-aware!