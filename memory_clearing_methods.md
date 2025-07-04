# How to Clear All Existing Memory

## 🔄 **Methods to Start Fresh**

### 1. **Clear All Users' Memory (Complete Reset)**

Add this method to your `ConversationManager`:

```python
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
    
    @classmethod
    def clear_all_engines(cls):
        """Clear all user engines - COMPLETE RESET"""
        cls._engines.clear()
        print(f"🧹 Cleared all conversation engines")
    
    @classmethod
    def get_active_users(cls):
        """See how many users have active conversations"""
        return list(cls._engines.keys())
    
    @classmethod
    def get_engine_count(cls):
        """Get count of active engines"""
        return len(cls._engines)
```

**Usage:**
```python
# Clear everything
ConversationManager.clear_all_engines()
```

### 2. **Clear Specific User's Memory**

```python
# Clear one user's conversation
ConversationManager.clear_engine("user_123")
```

### 3. **Clear Memory Within AIEngine**

Add this method to your `AIEngine` class:

```python
class AIEngine:
    # ... existing methods ...
    
    def clear_memory(self):
        """Clear this engine's conversation memory"""
        self.memory.chat_memory.clear()
        print(f"🧹 Cleared engine memory")
    
    def reset_conversation(self):
        """Complete reset of this engine"""
        self.memory.chat_memory.clear()
        # Reinitialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        print(f"🔄 Reset conversation engine")
```

**Usage:**
```python
ai_engine = ConversationManager.get_engine("user_123")
ai_engine.clear_memory()
```

## 🚀 **Quick Reset Commands**

### **Option A: Restart Your Application**
```bash
# If you're running a server, restart it
# This will automatically clear all in-memory engines
```

### **Option B: Add Reset Function**
```python
def reset_all_conversations():
    """Complete system reset"""
    ConversationManager.clear_all_engines()
    print("✅ All conversation memory cleared!")

# Call this function
reset_all_conversations()
```

### **Option C: Manual Clear in Code**
```python
# Add this anywhere in your code to clear everything
ConversationManager._engines = {}
print("🧹 All memory cleared manually")
```

## 🔧 **For Development/Testing**

Add this debug function:

```python
def debug_memory_status():
    """Check current memory status"""
    engines = ConversationManager._engines
    print(f"📊 Memory Status:")
    print(f"   Active engines: {len(engines)}")
    print(f"   Active users: {list(engines.keys())}")
    
    for user_id, engine in engines.items():
        msg_count = len(engine.memory.chat_memory.messages)
        print(f"   User {user_id}: {msg_count} messages in memory")

# Usage
debug_memory_status()
ConversationManager.clear_all_engines()
debug_memory_status()  # Should show 0 engines
```

## 📝 **When to Clear Memory**

### **Clear All Engines When:**
- 🔄 Application restart/deployment
- 🧪 Testing new conversation flows  
- 🐛 Debugging memory issues
- 🔧 System maintenance

### **Clear Single User When:**
- ❌ User session ends naturally
- 🔚 User says "goodbye" or "stop"
- ⚠️ Error in conversation flow
- 🕐 Session timeout (optional)

### **DON'T Clear When:**
- ✅ User is still actively chatting
- ✅ Conversation has `next_question`
- ✅ User is in middle of data collection

## 🎯 **Recommended Approach**

For **immediate fresh start**:

```python
# Add this to your main code
print("🔄 Starting fresh...")
ConversationManager.clear_all_engines()
print("✅ All conversation memory cleared!")

# Now test your conversation
```

For **production use**:

```python
# Add automatic cleanup
class ConversationManager:
    # ... existing code ...
    
    @classmethod
    def cleanup_old_engines(cls, max_age_hours: int = 24):
        """Auto-cleanup old conversations"""
        # Implementation depends on how you track conversation age
        # This is a placeholder for future enhancement
        pass
```

## 💡 **Quick Test**

To verify memory is cleared:

```python
# Before clearing
print("Before:", ConversationManager.get_engine_count())

# Clear all
ConversationManager.clear_all_engines()

# After clearing  
print("After:", ConversationManager.get_engine_count())  # Should be 0
```