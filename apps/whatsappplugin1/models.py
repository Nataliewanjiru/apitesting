from django.db import models
from django.db.models import Case, Q, When

from phonenumber_field.modelfields import PhoneNumberField

import apps.accounts.functions as ACCOUNTS_FUNCTIONS
import apps.accounts.models as ACCOUNTS_MODELS
import apps.core.choices as CORE_CHOICES
import apps.core.models as CORE_MODELS
import apps.healthworkers.models as HEALTHWORKERS_MODELS
import apps.patients.models as PATIENTS_MODELS
import apps.payments.choices as PAYMENTS_CHOICES
import apps.utilities.functions as UTILITIES_FUNCTIONS

from .choices import ListDisplayTypes, WhatsappPlugin1UserSessionStates


class WhatsappPlugin1Settings(CORE_MODELS.BaseModel):
    """Settings for WhatsApp Plugin"""
    list_display_type = models.CharField(
        max_length=50,
        choices=ListDisplayTypes.choices(),
        default=ListDisplayTypes.TEXT_MESSAGE.value,
    )


class WhatsappPlugin1UserSession(CORE_MODELS.BaseModel):
    """
    Record of conversation for each user/phone number with session management
    """

    user_phone_number = models.CharField(max_length=100, blank=True, null=True)
    user_first_name = models.CharField(max_length=100, blank=True, null=True)
    user_last_name = models.CharField(max_length=100, blank=True, null=True)
    user_middle_name = models.CharField(max_length=100, blank=True, null=True)
    user_sex = models.CharField(
        max_length=50, choices=CORE_CHOICES.Sexes.choices(), null=True
    )
    user_age = models.FloatField(null=True, blank=True)

    session_state = models.CharField(
        max_length=150,
        blank=True,
        choices=WhatsappPlugin1UserSessionStates.choices(),
        null=True,
    )
    last_session_state_update = models.DateTimeField(null=True, blank=True)

    # Session Management Fields
    current_session_id = models.CharField(max_length=100, blank=True, null=True)
    last_activity_time = models.DateTimeField(auto_now=True)
    session_start_time = models.DateTimeField(null=True, blank=True)
    is_new_session_pending = models.BooleanField(default=False)
    
    # Memory Management
    conversation_sessions = models.JSONField(default=list, blank=True, help_text="Stores summaries of previous conversation sessions")
    current_session_context = models.JSONField(default=dict, blank=True, help_text="Important context for current session")
    
    session_page = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=False, blank=True, null=True)

    is_an_existing_user = models.BooleanField(default=False, blank=True, null=True)
    existing_user = models.ForeignKey(
        to="accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_whatsapp_plugin1_sessions",
    )

    ai_conversation_history = models.JSONField(default=list, blank=True)

    linked_user = models.ForeignKey(
        to="accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    active_patient_profile = models.ForeignKey(
        to="patients.Patient", on_delete=models.SET_NULL, null=True, blank=True
    )

    previous_ai_doctor_recommendations = models.JSONField(default=list, blank=True)
    previous_ai_conversations = models.JSONField(default=list, blank=True)

    previous_doctor_search_results = models.JSONField(default=list, blank=True)
    previous_doctor_search_results_viewing_offset = models.IntegerField(
        default=0, blank=True
    )
    previous_ai_doctor_recommendations_viewing_offset = models.IntegerField(
        default=0, blank=True
    )

    profile_selection_viewing_offset = models.IntegerField(default=0, blank=True)

    doctor_booking_month_selection_options = models.JSONField(default=list, blank=True)
    doctor_booking_year_selection = models.IntegerField(null=True, blank=True)
    doctor_booking_month_selection = models.SmallIntegerField(null=True, blank=True)
    doctor_booking_date_selection = models.SmallIntegerField(null=True, blank=True)

    doctor_booking_time_slot_selection_options = models.JSONField(
        default=list, blank=True
    )
    doctor_booking_time_slots_viewing_offset = models.IntegerField(
        default=0, blank=True
    )

    doctor_booking_selected_doctor = models.ForeignKey(
        to="healthworkers.HealthWorker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    doctor_booking_selected_mode = models.CharField(
        max_length=1, choices=CORE_CHOICES.EncounterModes.choices(), blank=True
    )
    doctor_booking_selected_availability = models.ForeignKey(
        to="appointments.HealthWorkerAvailability",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    doctor_booking_selected_appointment = models.ForeignKey(
        to="appointments.Appointment", on_delete=models.SET_NULL, null=True, blank=True
    )

    doctor_booking_selected_payment_time = models.CharField(
        max_length=50, null=True, blank=True
    )
    doctor_booking_selected_start_time = models.DateTimeField(null=True, blank=True)
    doctor_booking_selected_end_time = models.DateTimeField(null=True, blank=True)
    doctor_booking_selected_payment_method = models.CharField(
        max_length=100,
        choices=PAYMENTS_CHOICES.PaymentMethods.choices(),
        default=PAYMENTS_CHOICES.PaymentMethods.MPESA.value,
    )
    doctor_booking_selected_mpesa_number = PhoneNumberField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Overrides the save method to link the phone number to a user
        :param args:
        :param kwargs:
        :return:
        """
        if self.linked_user:
            user = self.linked_user
            if not user.is_whatsapp_authenticated:
                user.is_whatsapp_authenticated = True
                user.save()

        # Update activity time and set session start time
        if not self.session_start_time:
            self.session_start_time = UTILITIES_FUNCTIONS.get_current_time()
        
        super().save(*args, **kwargs)

    def get_full_name(self):
        """
        Build the user full name string
        :return:
        """
        return f"{self.user_first_name or ''} {self.user_middle_name or ''} {self.user_last_name or ''}".strip()

    def start_new_conversation_session(self):
        """Start a new conversation session"""
        import uuid
        from datetime import datetime
        
        # Archive current session if it has content
        if self.ai_conversation_history and len(self.ai_conversation_history) > 1:
            session_summary = {
                'session_id': self.current_session_id or 'unknown',
                'start_time': self.session_start_time.isoformat() if self.session_start_time else None,
                'end_time': datetime.now().isoformat(),
                'message_count': len(self.ai_conversation_history),
                'context': self.current_session_context.copy() if self.current_session_context else {},
                'had_booking_activity': bool(self.doctor_booking_selected_doctor),
                'user_authenticated': bool(self.linked_user)
            }
            
            if not self.conversation_sessions:
                self.conversation_sessions = []
            self.conversation_sessions.append(session_summary)
            
            # Keep only last 10 sessions to avoid data bloat
            if len(self.conversation_sessions) > 10:
                self.conversation_sessions = self.conversation_sessions[-10:]
        
        # Reset current session
        self.current_session_id = str(uuid.uuid4())
        self.session_start_time = UTILITIES_FUNCTIONS.get_current_time()
        self.ai_conversation_history = []
        self.current_session_context = {}
        self.is_new_session_pending = False
        
        # Reset booking state
        self.reset_appointment_booking_session()
        
        self.save()

    def should_start_new_session(self, message: str = None) -> bool:
        """Determine if a new session should be started"""
        from datetime import timedelta
        
        current_time = UTILITIES_FUNCTIONS.get_current_time()
        
        # Check for session timeout (2 hours of inactivity)
        if self.last_activity_time:
            time_since_activity = current_time - self.last_activity_time
            if time_since_activity > timedelta(hours=2):
                return True
        
        # Check for explicit new session indicators in message
        if message:
            new_session_phrases = [
                'new appointment', 'different issue', 'new problem',
                'start over', 'new session', 'new consultation', 'new booking'
            ]
            message_lower = message.lower()
            for phrase in new_session_phrases:
                if phrase in message_lower:
                    return True
        
        return False

    def update_session_context(self, key: str, value: any):
        """Update context for current session"""
        if not self.current_session_context:
            self.current_session_context = {}
        self.current_session_context[key] = value
        self.save()

    def get_session_context(self, key: str, default=None):
        """Get context from current session"""
        if not self.current_session_context:
            return default
        return self.current_session_context.get(key, default)

    def set_state(self, session_state: str, session_page: str = None):
        """
        Allocates a new state to the session
        """
        self.session_state = session_state
        if session_page:
            self.session_page = session_page
        self.last_session_state_update = UTILITIES_FUNCTIONS.get_current_time()
        self.save()

    def reset_ai_conversation(self):
        """
        Resets the AI conversation to default
        :return:
        """
        if self.ai_conversation_history:
            self.previous_ai_conversations = [
                *self.previous_ai_conversations,
                self.ai_conversation_history,
            ]
        self.ai_conversation_history = []

    def reset_appointment_booking_session(self):
        """
        Resets the appointment booking attempt process to default
        :return:
        """
        self.doctor_booking_month_selection_options = []
        self.doctor_booking_year_selection = None
        self.doctor_booking_month_selection = None
        self.doctor_booking_date_selection = None
        self.doctor_booking_time_slot_selection_options = []
        self.doctor_booking_time_slots_viewing_offset = 0
        self.doctor_booking_selected_doctor = None
        self.doctor_booking_selected_availability = None
        self.doctor_booking_selected_appointment = None
        self.doctor_booking_selected_payment_time = None
        self.doctor_booking_selected_start_time = None
        self.doctor_booking_selected_end_time = None
        self.doctor_booking_selected_mpesa_number = None
        self.save()

    def logout(self):
        """
        Logs out the session
        """
        self.linked_user = None
        self.active_patient_profile = None
        self.reset_ai_conversation()
        self.previous_ai_doctor_recommendations = []
        self.previous_doctor_search_results = []
        self.previous_doctor_search_results_viewing_offset = 0
        self.session_state = WhatsappPlugin1UserSessionStates.DEFAULT.value
        self.save()

    def create_user(self, password: str):
        """
        Creates a user from the session
        """
        user = (
            ACCOUNTS_MODELS.User.filter_objects(
                phone_number=UTILITIES_FUNCTIONS.normalize_phone_number(
                    phone_number=self.user_phone_number
                )
            )
            .exclude(phone_number=None)
            .first()
        )

        if user:
            user.phone_number_verified = True
            user.save()
            self.linked_user = user
            self.save()

        else:
            user, v = ACCOUNTS_FUNCTIONS.create_user(
                phone_number=self.user_phone_number,
                email=None,
                password=password,
                send_verification_messages=False,
            )
            user.phone_number_verified = True
            user.save()
            self.linked_user = user
            self.save()

        return user

    def create_patient(self):
        """
        Creates a patient from the session
        """
        user = self.linked_user

        patient = PATIENTS_MODELS.Patient(
            user=user,
            first_name=self.user_first_name,
            last_name=self.user_last_name
            or self.user_middle_name
            or self.user_first_name,
            middle_name=self.user_middle_name,
            sex=self.user_sex,
        )
        patient.save()

        return patient

    def create_user_with_patient(self, password: str):
        """
        Creates both a user and patient from the session
        """
        user = self.create_user(password=password)
        patient = self.create_patient()

        return user, patient

    def get_previous_ai_doctor_recommendations(self):
        if not self.previous_ai_doctor_recommendations:
            return []

        ordering = Case(
            *[
                When(Q(id=id_), index_)
                for index_, id_ in enumerate(self.previous_ai_doctor_recommendations)
            ]
        )

        return [
            t
            for t in HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
                id__in=self.previous_ai_doctor_recommendations
            )
            .annotate(ordering=ordering)
            .order_by(ordering)
        ]

    def get_previous_doctor_search_results(self):
        if not self.previous_doctor_search_results:
            return []

        ordering = Case(
            *[
                When(Q(id=id_), index_)
                for index_, id_ in enumerate(self.previous_doctor_search_results)
            ]
        )

        return [
            t
            for t in HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
                id__in=self.previous_doctor_search_results
            )
            .annotate(ordering=ordering)
            .order_by(ordering)
        ]

    @classmethod
    def get_for_phone_number(cls, phone_number: str):
        """
        Gets or creates a session for a particular phone number
        """
        session = WhatsappPlugin1UserSession.get_object(user_phone_number=phone_number)
        newly_created = False

        if not session:
            session = WhatsappPlugin1UserSession(
                user_phone_number=phone_number,
                session_state=WhatsappPlugin1UserSessionStates.DEFAULT.value,
            )

            user = (
                ACCOUNTS_MODELS.User.filter_objects(
                    phone_number=UTILITIES_FUNCTIONS.normalize_phone_number(
                        phone_number=phone_number
                    )
                )
                .exclude(phone_number=None)
                .first()
            )
            if user:
                session.is_an_existing_user = True
                session.existing_user = user

            session.save()
            newly_created = True

        return session, newly_created