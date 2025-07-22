"""
Session Handler for WhatsApp Plugin - Manages conversation sessions like ChatGPT
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

from .ai_engine import get_or_create_engine
from .models import WhatsappPlugin1UserSession
import apps.utilities.functions as UTILITIES_FUNCTIONS

logger = logging.getLogger(__name__)


class ChatGPTLikeSessionHandler:
    """
    Handles conversation sessions similar to how ChatGPT manages sessions
    """
    
    def __init__(self):
        self.session_timeout = timedelta(hours=2)
        self.max_sessions_per_user = 10
    
    def handle_message(self, phone_number: str, message: str) -> str:
        """
        Main entry point for handling incoming messages with session management
        """
        try:
            # Get or create user session
            user_session, newly_created = WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
            
            # Check if we need to start a new conversation session
            should_start_new = self._should_start_new_session(user_session, message, newly_created)
            
            if should_start_new:
                logger.info(f"🔄 Starting new session for {phone_number}")
                user_session.start_new_conversation_session()
                
                # Get fresh AI engine for new session
                ai_engine = get_or_create_engine(user_session.current_session_id)
                
                # If this is a timeout or explicit new session, inform user
                if not newly_created:
                    return "I understand you'd like to start a new consultation. How can I help you today?"
            
            # Get AI engine for current session
            ai_engine = get_or_create_engine(user_session.current_session_id or str(user_session.id))
            
            # Handle the message with session context
            response = self._process_message_with_context(ai_engine, user_session, message)
            
            # Update session activity
            user_session.last_activity_time = UTILITIES_FUNCTIONS.get_current_time()
            user_session.save()
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error handling message for {phone_number}: {e}")
            return "I'm sorry, I encountered an error. Please try again."
    
    def _should_start_new_session(self, user_session: WhatsappPlugin1UserSession, 
                                 message: str, newly_created: bool) -> bool:
        """
        Determine if a new conversation session should be started
        """
        # Always start new session for new users
        if newly_created:
            return True
        
        # Check if session has timed out
        if user_session.should_start_new_session(message):
            return True
        
        # Check if user explicitly wants new session
        new_session_keywords = [
            'new session', 'start over', 'new consultation', 
            'new appointment', 'different issue', 'new problem'
        ]
        
        message_lower = message.lower()
        for keyword in new_session_keywords:
            if keyword in message_lower:
                return True
        
        # Check for context mismatch (different medical concerns)
        if self._detect_context_mismatch(user_session, message):
            user_session.is_new_session_pending = True
            user_session.save()
            return False  # Ask for confirmation first
        
        return False
    
    def _detect_context_mismatch(self, user_session: WhatsappPlugin1UserSession, 
                                message: str) -> bool:
        """
        Detect if the user is talking about something completely different
        from their current session context
        """
        # Skip if conversation is too short to determine context
        if len(user_session.ai_conversation_history) < 4:
            return False
        
        # Get current session context
        current_context = user_session.current_session_context or {}
        
        # Extract medical keywords from message
        medical_keywords = self._extract_medical_keywords(message.lower())
        
        # If no medical keywords, not a context mismatch
        if not medical_keywords:
            return False
        
        # Check against current session symptoms
        current_symptoms = current_context.get('symptoms_mentioned', [])
        
        # If there's very little overlap, might be different concern
        if current_symptoms:
            overlap = len(set(medical_keywords) & set(current_symptoms))
            if len(medical_keywords) >= 2 and overlap == 0:
                return True
        
        return False
    
    def _extract_medical_keywords(self, text: str) -> list:
        """Extract medical-related keywords from text"""
        medical_terms = [
            'pain', 'ache', 'fever', 'cough', 'headache', 'nausea', 'vomiting',
            'diarrhea', 'constipation', 'fatigue', 'weakness', 'dizziness',
            'chest pain', 'back pain', 'stomach pain', 'sore throat',
            'runny nose', 'congestion', 'shortness of breath', 'rash',
            'swelling', 'bleeding', 'infection', 'diabetes', 'hypertension',
            'depression', 'anxiety', 'insomnia', 'migraine'
        ]
        
        found_terms = []
        for term in medical_terms:
            if term in text:
                found_terms.append(term)
        
        return found_terms
    
    def _process_message_with_context(self, ai_engine, user_session: WhatsappPlugin1UserSession, 
                                    message: str) -> str:
        """
        Process message with session context management
        """
        # Handle pending new session confirmation
        if user_session.is_new_session_pending:
            if any(word in message.lower() for word in ['yes', 'new', 'different', 'start over']):
                user_session.start_new_conversation_session()
                return "Starting a new consultation session. How can I help you today?"
            elif any(word in message.lower() for word in ['no', 'continue', 'same']):
                user_session.is_new_session_pending = False
                user_session.save()
                # Continue with current session
            else:
                return ("I notice you're mentioning different health concerns. "
                       "Is this a new consultation session, or would you like to continue "
                       "with our previous discussion? Please say 'new session' or 'continue'.")
        
        # Update session context with new information
        self._update_session_context(user_session, message)
        
        # Generate AI response
        response = ai_engine.generate_autonomous_response(message, user_session)
        
        return response
    
    def _update_session_context(self, user_session: WhatsappPlugin1UserSession, message: str):
        """Update session context with information from the message"""
        medical_keywords = self._extract_medical_keywords(message.lower())
        
        if medical_keywords:
            current_symptoms = user_session.get_session_context('symptoms_mentioned', [])
            for keyword in medical_keywords:
                if keyword not in current_symptoms:
                    current_symptoms.append(keyword)
            user_session.update_session_context('symptoms_mentioned', current_symptoms)
        
        # Update other context as needed
        if any(word in message.lower() for word in ['book', 'appointment', 'schedule']):
            user_session.update_session_context('booking_intent', True)
        
        if any(word in message.lower() for word in ['cancel', 'reschedule']):
            user_session.update_session_context('modification_intent', True)


def handle_whatsapp_message(phone_number: str, message: str) -> str:
    """
    Main function to handle WhatsApp messages with ChatGPT-like session management
    
    Usage:
        response = handle_whatsapp_message("+254712345678", "I have a headache")
    """
    handler = ChatGPTLikeSessionHandler()
    return handler.handle_message(phone_number, message)


def force_new_session(phone_number: str) -> bool:
    """
    Force start a new session for a user
    
    Usage:
        success = force_new_session("+254712345678")
    """
    try:
        user_session, _ = WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
        user_session.start_new_conversation_session()
        return True
    except Exception as e:
        logger.error(f"❌ Error forcing new session for {phone_number}: {e}")
        return False


def get_session_history(phone_number: str) -> dict:
    """
    Get session history for a user
    
    Returns:
        {
            'current_session': {...},
            'previous_sessions': [...],
            'total_sessions': int
        }
    """
    try:
        user_session, _ = WhatsappPlugin1UserSession.get_for_phone_number(phone_number)
        
        return {
            'current_session': {
                'session_id': user_session.current_session_id,
                'start_time': user_session.session_start_time,
                'message_count': len(user_session.ai_conversation_history),
                'context': user_session.current_session_context
            },
            'previous_sessions': user_session.conversation_sessions,
            'total_sessions': len(user_session.conversation_sessions) + (1 if user_session.current_session_id else 0)
        }
    except Exception as e:
        logger.error(f"❌ Error getting session history for {phone_number}: {e}")
        return {
            'current_session': None,
            'previous_sessions': [],
            'total_sessions': 0
        }