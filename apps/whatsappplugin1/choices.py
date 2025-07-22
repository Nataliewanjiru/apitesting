from enum import Enum


class ListDisplayTypes(Enum):
    """Display types for lists in WhatsApp messages"""
    DROPDOWN_MESSAGE = "dropdown_message"
    TEXT_MESSAGE = "text_message"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]


class WhatsappPlugin1UserSessionStates(Enum):
    """States for WhatsApp user sessions"""
    DEFAULT = "default"
    ONBOARDING = "onboarding"
    REGISTRATION = "registration"
    LOGIN = "login"
    AUTHENTICATED = "authenticated"
    BOOKING_APPOINTMENT = "booking_appointment"
    BOOKING_MPESA_NUMBER_INPUT = "booking_mpesa_number_input"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]