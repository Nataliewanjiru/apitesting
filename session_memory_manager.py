import asyncio
import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from langchain.memory import ConversationBufferMemory, ConversationSummaryBufferMemory
from langchain.schema import HumanMessage, AIMessage, messages_to_dict, messages_from_dict
from langchain.llms import OpenAI as LangChainOpenAI
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionState(Enum):
    """Enhanced session states"""
    INITIAL = "initial"
    COLLECTING_INFO = "collecting_info"
    SYMPTOM_ANALYSIS = "symptom_analysis"
    DOCTOR_SEARCH = "doctor_search"
    BOOKING_FLOW = "booking_flow"
    PAYMENT_FLOW = "payment_flow"
    COMPLETED = "completed"
    ERROR = "error"

class ContextType(Enum):
    """Types of context changes"""
    NEW_SYMPTOMS = "new_symptoms"
    DIFFERENT_CONDITION = "different_condition"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    GENERAL_INQUIRY = "general_inquiry"

class EnhancedSessionMemoryManager:
    """
    Production-ready session memory manager with persistence, 
    thread safety, and intelligent context detection
    """
    
    def __init__(self, session_timeout_hours: int = 24, max_memory_length: int = 4000):
        self.session_timeout_hours = session_timeout_hours
        self.max_memory_length = max_memory_length
        
        # Thread-safe storage
        self._lock = threading.RLock()
        self.session_memories: Dict[str, ConversationSummaryBufferMemory] = {}
        self.session_last_activity: Dict[str, datetime] = {}
        self.session_contexts: Dict[str, Dict] = {}
        self.session_states: Dict[str, SessionState] = {}
        
        # Health-related pattern matching
        self._initialize_health_patterns()
        
        # Background cleanup task
        self._start_cleanup_task()
    
    def _initialize_health_patterns(self):
        """Initialize patterns for health context detection"""
        self.symptom_patterns = {
            'pain': r'\b(pain|ache|hurt|sore|tender|aching|painful|hurting)\b',
            'fever': r'\b(fever|temperature|hot|feverish|chills|sweating)\b',
            'digestive': r'\b(nausea|vomit|diarrhea|constipation|stomach|belly|abdominal)\b',
            'respiratory': r'\b(cough|breath|breathing|chest|lungs|shortness|wheezing)\b',
            'mental_health': r'\b(anxiety|depression|stress|worried|panic|mental|mood)\b',
            'skin': r'\b(rash|itchy|skin|spots|bumps|swelling|red|irritation)\b',
            'head': r'\b(headache|migraine|dizzy|dizziness|head|skull)\b'
        }
        
        self.urgency_patterns = {
            'emergency': r'\b(emergency|urgent|severe|unbearable|cant breathe|chest pain|heart attack)\b',
            'high': r'\b(very|extremely|really|bad|terrible|awful|intense)\b',
            'moderate': r'\b(moderate|some|bit|little|mild)\b'
        }
        
        self.body_parts = [
            'head', 'neck', 'chest', 'back', 'stomach', 'leg', 'arm', 'foot', 
            'hand', 'eye', 'ear', 'throat', 'knee', 'shoulder', 'ankle'
        ]
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        def cleanup_worker():
            while True:
                time.sleep(3600)  # Run every hour
                try:
                    self.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def get_session_id(self, user_session) -> str:
        """Generate a unique session ID"""
        return f"{user_session.user_phone_number}_{user_session.id}"
    
    def _extract_health_context(self, message: str) -> Dict[str, Any]:
        """Extract health-related context from message using NLP patterns"""
        message_lower = message.lower()
        context = {
            'symptoms': [],
            'body_parts': [],
            'urgency': 'low',
            'context_type': ContextType.GENERAL_INQUIRY,
            'keywords': []
        }
        
        # Extract symptoms
        for symptom_type, pattern in self.symptom_patterns.items():
            if re.search(pattern, message_lower):
                context['symptoms'].append(symptom_type)
                context['keywords'].extend(re.findall(pattern, message_lower))
        
        # Extract body parts
        for body_part in self.body_parts:
            if body_part in message_lower:
                context['body_parts'].append(body_part)
        
        # Determine urgency
        for urgency_level, pattern in self.urgency_patterns.items():
            if re.search(pattern, message_lower):
                context['urgency'] = urgency_level
                break
        
        # Determine context type
        if context['symptoms']:
            if re.search(r'\b(new|different|another|unrelated)\b', message_lower):
                context['context_type'] = ContextType.NEW_SYMPTOMS
            elif context['urgency'] == 'emergency':
                context['context_type'] = ContextType.EMERGENCY
            else:
                context['context_type'] = ContextType.SYMPTOM_ANALYSIS
        
        return context
    
    def should_start_new_session(self, user_session, message: str) -> Tuple[bool, str]:
        """
        Determine if this should start a new session
        Returns (should_start_new, reason)
        """
        session_id = self.get_session_id(user_session)
        
        with self._lock:
            # If no previous session exists, it's definitely new
            if session_id not in self.session_memories:
                return True, "no_previous_session"
            
            # Check if session has timed out
            last_activity = self.session_last_activity.get(session_id)
            if last_activity and datetime.now() - last_activity > timedelta(hours=self.session_timeout_hours):
                return True, "session_timeout"
            
            # Check for explicit new session indicators
            new_session_indicators = [
                "new session", "start over", "new consultation", "new appointment",
                "different issue", "new problem", "fresh start", "new health concern",
                "something else", "unrelated"
            ]
            
            if any(indicator in message.lower() for indicator in new_session_indicators):
                return True, "explicit_request"
            
            # Enhanced context analysis
            current_context = self._extract_health_context(message)
            previous_context = self.session_contexts.get(session_id, {})
            
            # Check for significant context switch
            if self._is_significant_context_switch(current_context, previous_context):
                return True, "context_switch"
            
            # Emergency always starts new session
            if current_context.get('urgency') == 'emergency':
                return True, "emergency"
            
            return False, "continue_session"
    
    def _is_significant_context_switch(self, current_context: Dict, previous_context: Dict) -> bool:
        """Determine if there's a significant context switch"""
        if not previous_context:
            return False
        
        # Get previous symptoms and current symptoms
        prev_symptoms = set(previous_context.get('symptoms', []))
        curr_symptoms = set(current_context.get('symptoms', []))
        
        # If completely different symptoms with no overlap
        if curr_symptoms and prev_symptoms and not curr_symptoms.intersection(prev_symptoms):
            return True
        
        # If new symptoms are mentioned with "different" or "new" keywords
        if (current_context.get('context_type') == ContextType.NEW_SYMPTOMS and 
            curr_symptoms != prev_symptoms):
            return True
        
        return False
    
    def get_or_create_session_memory(self, user_session, message: str = "") -> ConversationSummaryBufferMemory:
        """Get existing session memory or create new one with enhanced management"""
        session_id = self.get_session_id(user_session)
        
        with self._lock:
            # Check if we should start a new session
            should_start_new, reason = self.should_start_new_session(user_session, message)
            
            if should_start_new:
                logger.info(f"Starting new session for {session_id}, reason: {reason}")
                self._cleanup_session(session_id)
                # Persist the session end to database
                self._persist_session_end(user_session, reason)
            
            # Create new memory if doesn't exist
            if session_id not in self.session_memories:
                # Try to load from database first
                memory = self._load_session_from_db(user_session)
                if not memory:
                    memory = ConversationSummaryBufferMemory(
                        llm=LangChainOpenAI(temperature=0),
                        max_token_limit=self.max_memory_length,
                        return_messages=True
                    )
                
                self.session_memories[session_id] = memory
                self.session_contexts[session_id] = {
                    'created_at': datetime.now(),
                    'symptoms': [],
                    'health_concerns': [],
                    'user_preferences': {},
                    'session_history': []
                }
                self.session_states[session_id] = SessionState.INITIAL
            
            # Update last activity and context
            self.session_last_activity[session_id] = datetime.now()
            
            if message:
                current_context = self._extract_health_context(message)
                self._update_session_context(session_id, current_context)
            
            return self.session_memories[session_id]
    
    def _update_session_context(self, session_id: str, current_context: Dict):
        """Update session context with new information"""
        if session_id in self.session_contexts:
            context = self.session_contexts[session_id]
            
            # Update symptoms (avoid duplicates)
            new_symptoms = current_context.get('symptoms', [])
            existing_symptoms = context.get('symptoms', [])
            context['symptoms'] = list(set(existing_symptoms + new_symptoms))
            
            # Update body parts
            new_body_parts = current_context.get('body_parts', [])
            existing_body_parts = context.get('body_parts', [])
            context['body_parts'] = list(set(existing_body_parts + new_body_parts))
            
            # Update urgency to highest level
            current_urgency = current_context.get('urgency', 'low')
            existing_urgency = context.get('urgency', 'low')
            urgency_levels = {'low': 1, 'moderate': 2, 'high': 3, 'emergency': 4}
            
            if urgency_levels.get(current_urgency, 1) > urgency_levels.get(existing_urgency, 1):
                context['urgency'] = current_urgency
            
            # Track context history
            context['session_history'].append({
                'timestamp': datetime.now().isoformat(),
                'context': current_context
            })
            
            # Update session state based on context
            self._update_session_state(session_id, current_context)
    
    def _update_session_state(self, session_id: str, context: Dict):
        """Update session state based on context"""
        context_type = context.get('context_type')
        
        if context_type == ContextType.EMERGENCY:
            self.session_states[session_id] = SessionState.ERROR  # Immediate attention needed
        elif context_type == ContextType.SYMPTOM_ANALYSIS:
            self.session_states[session_id] = SessionState.SYMPTOM_ANALYSIS
        elif context['symptoms']:
            self.session_states[session_id] = SessionState.COLLECTING_INFO
        else:
            self.session_states[session_id] = SessionState.INITIAL
    
    def _persist_session_to_db(self, user_session, memory: ConversationSummaryBufferMemory):
        """Persist session data to database"""
        try:
            session_id = self.get_session_id(user_session)
            
            # Convert memory to dict format
            conversation_data = messages_to_dict(memory.chat_memory.messages)
            
            # Update user session model
            user_session.ai_conversation_history = conversation_data
            user_session.session_context = self.session_contexts.get(session_id, {})
            user_session.last_session_state_update = datetime.now()
            
            # Save summary if available
            if hasattr(memory, 'moving_summary_buffer'):
                user_session.session_memory_summary = memory.moving_summary_buffer
            
            user_session.save()
            logger.info(f"Persisted session {session_id} to database")
            
        except Exception as e:
            logger.error(f"Error persisting session to database: {e}")
    
    def _load_session_from_db(self, user_session) -> Optional[ConversationSummaryBufferMemory]:
        """Load session data from database"""
        try:
            if user_session.ai_conversation_history:
                memory = ConversationSummaryBufferMemory(
                    llm=LangChainOpenAI(temperature=0),
                    max_token_limit=self.max_memory_length,
                    return_messages=True
                )
                
                # Load messages
                memory.chat_memory.messages = messages_from_dict(user_session.ai_conversation_history)
                
                # Load summary if available
                if user_session.session_memory_summary:
                    memory.moving_summary_buffer = user_session.session_memory_summary
                
                # Load context
                session_id = self.get_session_id(user_session)
                if user_session.session_context:
                    self.session_contexts[session_id] = user_session.session_context
                
                logger.info(f"Loaded session {session_id} from database")
                return memory
                
        except Exception as e:
            logger.error(f"Error loading session from database: {e}")
        
        return None
    
    def _persist_session_end(self, user_session, reason: str):
        """Mark session end in database"""
        try:
            user_session.start_new_session(reason)
            logger.info(f"Marked session end for {self.get_session_id(user_session)}")
        except Exception as e:
            logger.error(f"Error marking session end: {e}")
    
    def update_session_context(self, user_session, key: str, value: Any):
        """Update session-specific context"""
        session_id = self.get_session_id(user_session)
        
        with self._lock:
            if session_id in self.session_contexts:
                self.session_contexts[session_id][key] = value
                
                # Persist important updates to database
                if key in ['symptoms', 'health_concerns', 'urgency']:
                    try:
                        self._persist_session_to_db(user_session, self.session_memories[session_id])
                    except Exception as e:
                        logger.error(f"Error persisting context update: {e}")
    
    def get_session_context(self, user_session) -> Dict:
        """Get current session context"""
        session_id = self.get_session_id(user_session)
        
        with self._lock:
            return self.session_contexts.get(session_id, {}).copy()
    
    def get_session_state(self, user_session) -> SessionState:
        """Get current session state"""
        session_id = self.get_session_id(user_session)
        
        with self._lock:
            return self.session_states.get(session_id, SessionState.INITIAL)
    
    def _cleanup_session(self, session_id: str):
        """Clean up session data"""
        with self._lock:
            if session_id in self.session_memories:
                del self.session_memories[session_id]
            if session_id in self.session_last_activity:
                del self.session_last_activity[session_id]
            if session_id in self.session_contexts:
                del self.session_contexts[session_id]
            if session_id in self.session_states:
                del self.session_states[session_id]
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        with self._lock:
            for session_id, last_activity in self.session_last_activity.items():
                if current_time - last_activity > timedelta(hours=self.session_timeout_hours):
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id}")
            self._cleanup_session(session_id)
    
    def get_session_summary(self, user_session) -> Dict:
        """Get comprehensive session summary"""
        session_id = self.get_session_id(user_session)
        
        with self._lock:
            context = self.session_contexts.get(session_id, {})
            state = self.session_states.get(session_id, SessionState.INITIAL)
            last_activity = self.session_last_activity.get(session_id)
            
            return {
                'session_id': session_id,
                'state': state.value,
                'last_activity': last_activity.isoformat() if last_activity else None,
                'symptoms': context.get('symptoms', []),
                'urgency': context.get('urgency', 'low'),
                'context_type': context.get('context_type', ContextType.GENERAL_INQUIRY).value if context.get('context_type') else 'general_inquiry',
                'session_duration': (datetime.now() - context.get('created_at', datetime.now())).total_seconds() / 60 if context.get('created_at') else 0
            }