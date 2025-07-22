"""
Main handler for WhatsApp Plugin with ChatGPT-like session management
"""

from .ai_engine import get_autonomous_engine
from .models import WhatsappPlugin1UserSession


def handle_whatsapp_message(phone_number: str, message: str) -> str:
    """
    Main entry point for handling WhatsApp messages with session management
    """
    try:
        # Get or create user session
        user_session, newly_created = WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
        
        # Check if we should start a new session based on the message
        if user_session.should_start_new_session(message):
            user_session.start_new_session("new_consultation")
        
        # Get the autonomous AI engine for this user
        ai_engine = get_autonomous_engine(user_session)
        
        # Generate response
        response = ai_engine.generate_autonomous_response(message, user_session)
        
        return response
        
    except Exception as e:
        print(f"❌ Error in main handler: {e}")
        return "I'm sorry, I encountered an error. Please try again."


def reset_user_session(phone_number: str) -> str:
    """
    Manually reset a user's session
    """
    try:
        user_session, _ = WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
        user_session.start_new_session("manual_reset")
        
        ai_engine = get_autonomous_engine(user_session)
        return ai_engine.reset_session(user_session)
        
    except Exception as e:
        print(f"❌ Error resetting session: {e}")
        return "I'm sorry, I couldn't reset your session. Please try again."


def get_user_session_info(phone_number: str) -> dict:
    """
    Get information about a user's current session
    """
    try:
        user_session, _ = WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
        
        return {
            'current_session_id': user_session.current_session_id,
            'last_session_reset': user_session.last_session_reset.isoformat() if user_session.last_session_reset else None,
            'session_context': user_session.session_context,
            'important_user_info': user_session.important_user_info,
            'session_state': user_session.session_state,
            'is_authenticated': bool(user_session.linked_user),
            'has_active_patient': bool(user_session.active_patient_profile),
            'previous_sessions_count': len(user_session.previous_ai_conversations)
        }
        
    except Exception as e:
        print(f"❌ Error getting session info: {e}")
        return {'error': str(e)}


# Example usage functions for testing
def simulate_conversation():
    """
    Simulate a conversation to test session management
    """
    phone = "+254712345678"
    
    print("=== Day 1: First consultation ===")
    messages = [
        "Hi, I need help with my health",
        "I have been having headaches for the past week",
        "They are severe and happen mostly in the morning",
        "I would like to see a neurologist"
    ]
    
    for msg in messages:
        response = handle_whatsapp_message(phone, msg)
        print(f"User: {msg}")
        print(f"AI: {response}\n")
    
    print("=== Day 2: New consultation (should detect new session) ===")
    messages = [
        "Hi, I have a different problem today",
        "I'm experiencing stomach pain",
        "It started yesterday evening"
    ]
    
    for msg in messages:
        response = handle_whatsapp_message(phone, msg)
        print(f"User: {msg}")
        print(f"AI: {response}\n")
    
    print("=== Session Info ===")
    info = get_user_session_info(phone)
    print(f"Session Info: {info}")


if __name__ == "__main__":
    simulate_conversation()