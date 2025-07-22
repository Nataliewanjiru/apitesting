"""
Example integration of ChatGPT-like session management with your WhatsApp webhook

Replace your existing message handler with this approach
"""

from apps.whatsappplugin1.session_handler import handle_whatsapp_message, force_new_session, get_session_history


def whatsapp_webhook_handler(request):
    """
    Your existing WhatsApp webhook handler - updated to use session management
    """
    # Extract phone number and message from request
    phone_number = extract_phone_number(request)  # Your existing function
    message = extract_message_text(request)       # Your existing function
    
    # Handle the message with ChatGPT-like session management
    response = handle_whatsapp_message(phone_number, message)
    
    # Send response back to WhatsApp
    send_whatsapp_message(phone_number, response)  # Your existing function
    
    return JsonResponse({'status': 'success'})


# Example usage in your views or handlers:

def handle_user_message(phone_number: str, message: str):
    """
    Simple wrapper for handling user messages
    """
    return handle_whatsapp_message(phone_number, message)


def reset_user_session(phone_number: str):
    """
    Reset a user's session (useful for admin operations)
    """
    success = force_new_session(phone_number)
    if success:
        return "Session reset successfully"
    else:
        return "Failed to reset session"


def get_user_session_info(phone_number: str):
    """
    Get session information for debugging or admin purposes
    """
    return get_session_history(phone_number)


# Example test scenarios:

def test_session_scenarios():
    """
    Test various session scenarios
    """
    phone = "+254712345678"
    
    # Scenario 1: New user - should start fresh session
    print("=== New User Scenario ===")
    response1 = handle_whatsapp_message(phone, "Hello, I have a headache")
    print(f"Response: {response1}")
    
    # Scenario 2: Continue conversation - should maintain context
    print("\n=== Continue Conversation ===")
    response2 = handle_whatsapp_message(phone, "It's been hurting for 3 days")
    print(f"Response: {response2}")
    
    # Scenario 3: Different issue - should ask for confirmation
    print("\n=== Different Issue ===")
    response3 = handle_whatsapp_message(phone, "I also have stomach pain and nausea")
    print(f"Response: {response3}")
    
    # Scenario 4: Explicit new session
    print("\n=== Explicit New Session ===")
    response4 = handle_whatsapp_message(phone, "I want to start a new consultation about my back pain")
    print(f"Response: {response4}")
    
    # Get session history
    print("\n=== Session History ===")
    history = get_session_history(phone)
    print(f"Total sessions: {history['total_sessions']}")
    print(f"Current session context: {history['current_session']['context']}")


# Integration with your existing AI engine:

def update_existing_message_handler():
    """
    How to update your existing message handler
    
    BEFORE (your current approach):
    def handle_message(phone_number, message):
        user_session = get_user_session(phone_number)
        ai_engine = get_ai_engine()
        response = ai_engine.generate_response(message, user_session)
        return response
    
    AFTER (with session management):
    def handle_message(phone_number, message):
        return handle_whatsapp_message(phone_number, message)
    """
    pass


# Advanced session management:

def handle_complex_scenarios():
    """
    Handle more complex session scenarios
    """
    
    # Scenario: User books appointment today, comes back tomorrow
    phone = "+254712345678"
    
    # Day 1: Book appointment
    response1 = handle_whatsapp_message(phone, "I need to book an appointment for headaches")
    # ... booking conversation continues ...
    
    # Day 2: New issue (should detect and ask)
    response2 = handle_whatsapp_message(phone, "I have chest pain")
    # System should ask: "Is this a new consultation session?"
    
    # User confirms new session
    response3 = handle_whatsapp_message(phone, "Yes, new session")
    # System starts fresh conversation about chest pain


# Memory management example:

def demonstrate_memory_management():
    """
    Show how the system manages memory like ChatGPT
    """
    phone = "+254712345678"
    
    # Get current session info
    history = get_session_history(phone)
    
    print(f"Current session: {history['current_session']}")
    print(f"Previous sessions: {len(history['previous_sessions'])}")
    
    # Each session summary contains:
    # - session_id: unique identifier
    # - start_time/end_time: when session occurred  
    # - message_count: number of messages exchanged
    # - context: important information (symptoms, booking details, etc.)
    # - had_booking_activity: whether user was booking
    # - user_authenticated: whether user was logged in


if __name__ == "__main__":
    # Run test scenarios
    test_session_scenarios()