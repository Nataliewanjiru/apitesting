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
    """Settings for WhatsApp Plugin 1"""
    list_display_type = models.CharField(
        max_length=50, 
        choices=ListDisplayTypes.choices(),
        default=ListDisplayTypes.DROPDOWN_MESSAGE.value
    )
    
    @classmethod
    def get_instance(cls):
        return cls.objects.first() or cls.objects.create()


class WhatsappPlugin1UserSession(CORE_MODELS.BaseModel):
    """
    Record of conversation for each user/phone number with ChatGPT-like session management
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
    
    # Enhanced session management fields for ChatGPT-like behavior
    current_session_id = models.CharField(max_length=100, blank=True, null=True)
    last_session_reset = models.DateTimeField(null=True, blank=True)
    session_context = models.JSONField(default=dict, blank=True)  # Store current session context
    session_memory_summary = models.TextField(blank=True, null=True)  # Compressed memory
    important_user_info = models.JSONField(default=dict, blank=True)  # Persistent user data

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
        """
        if self.linked_user:
            user = self.linked_user
            if not user.is_whatsapp_authenticated:
                user.is_whatsapp_authenticated = True
                user.save()

        super().save(*args, **kwargs)

    def get_full_name(self):
        """
        Build the user full name string
        """
        return f"{self.user_first_name or ''} {self.user_middle_name or ''} {self.user_last_name or ''}".strip()

    def set_state(self, session_state: str, session_page: str = None):
        """
        Allocates a new state to the session
        """
        self.session_state = session_state
        if session_page:
            self.session_page = session_page
        self.last_session_state_update = UTILITIES_FUNCTIONS.get_current_time()
        self.save()

    def start_new_session(self, reason: str = "new_consultation"):
        """
        Start a new session while preserving important user information
        """
        # Archive current session context if it exists
        if self.session_context:
            self.previous_ai_conversations.append({
                'session_id': self.current_session_id,
                'ended_at': UTILITIES_FUNCTIONS.get_current_time().isoformat(),
                'reason': reason,
                'context': self.session_context,
                'conversation_summary': self._generate_session_summary()
            })
        
        # Generate new session ID
        self.current_session_id = f"session_{UTILITIES_FUNCTIONS.get_current_time().timestamp()}"
        self.last_session_reset = UTILITIES_FUNCTIONS.get_current_time()
        
        # Reset session-specific context but keep important user info
        self.session_context = {}
        self.ai_conversation_history = []
        
        # Reset appointment booking session
        self.reset_appointment_booking_session()
        
        # Clear previous recommendations (they're session-specific)
        self.previous_ai_doctor_recommendations = []
        self.previous_doctor_search_results = []
        self.previous_doctor_search_results_viewing_offset = 0
        
        self.save()

    def _generate_session_summary(self) -> str:
        """
        Generate a summary of the current session for future reference
        """
        if not self.session_context:
            return ""
        
        summary_parts = []
        
        # Summarize symptoms discussed
        symptoms = self.session_context.get('symptoms', [])
        if symptoms:
            summary_parts.append(f"Discussed symptoms: {', '.join(symptoms)}")
        
        # Summarize health concerns
        concerns = self.session_context.get('health_concerns', [])
        if concerns:
            summary_parts.append(f"Health concerns: {', '.join(concerns)}")
        
        # Add any appointments made
        if self.doctor_booking_selected_appointment:
            summary_parts.append(f"Appointment booked with {self.doctor_booking_selected_doctor}")
        
        return "; ".join(summary_parts)

    def update_important_user_info(self, key: str, value):
        """
        Update persistent user information that should carry across sessions
        """
        if not self.important_user_info:
            self.important_user_info = {}
        
        self.important_user_info[key] = value
        self.save()

    def get_session_context_value(self, key: str, default=None):
        """
        Get a value from the current session context
        """
        return self.session_context.get(key, default)

    def set_session_context_value(self, key: str, value):
        """
        Set a value in the current session context
        """
        if not self.session_context:
            self.session_context = {}
        
        self.session_context[key] = value
        self.save()

    def should_start_new_session(self, message: str) -> bool:
        """
        Determine if a new session should be started based on the message
        """
        # Time-based session expiration (24 hours)
        if self.last_session_reset:
            time_since_reset = UTILITIES_FUNCTIONS.get_current_time() - self.last_session_reset
            if time_since_reset.total_seconds() > 24 * 3600:  # 24 hours
                return True
        
        # Explicit new session keywords
        new_session_keywords = [
            'new session', 'start over', 'new consultation', 'new appointment',
            'different issue', 'new problem', 'fresh start', 'new health concern'
        ]
        
        return any(keyword in message.lower() for keyword in new_session_keywords)

    def reset_ai_conversation(self):
        """
        Resets the AI conversation to default while preserving session context
        """
        if self.ai_conversation_history:
            # Store in session context for potential reference
            self.session_context['previous_conversation'] = self.ai_conversation_history
            
        self.ai_conversation_history = []
        self.save()

    def reset_appointment_booking_session(self):
        """
        Resets the appointment booking attempt process to default
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
        self.save()

    def logout(self):
        """
        Logs out the session
        """
        # Start new session on logout to clear sensitive data
        self.start_new_session("logout")
        
        self.linked_user = None
        self.active_patient_profile = None
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

        # Update important user info
        self.update_important_user_info('user_id', user.id)
        self.update_important_user_info('phone_verified', True)

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

        # Update important user info
        self.update_important_user_info('patient_id', patient.id)
        self.update_important_user_info('patient_name', patient.get_full_name())

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
        session = cls.get_object(user_phone_number=phone_number)
        newly_created = False

        if not session:
            session = cls(
                user_phone_number=phone_number,
                session_state=WhatsappPlugin1UserSessionStates.DEFAULT.value,
                current_session_id=f"session_{UTILITIES_FUNCTIONS.get_current_time().timestamp()}",
                last_session_reset=UTILITIES_FUNCTIONS.get_current_time()
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