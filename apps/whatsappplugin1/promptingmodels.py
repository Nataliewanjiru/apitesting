# Import all the functions from the functions file
from .functions import (
    handle_onboarding_function,
    handle_user_registration,
    handle_user_login,
    handle_profile_listing,
    handle_profile_selection,
    handle_doctor_recommendation_from_symptoms_function,
    search_doctors_by_criteria,
    doctor_availability,
    create_appointment_with_doctor,
    appointment_date,
    appointment_day,
    handle_payment_time_selection,
    handle_payment_method_selection,
    handle_mobile_payment_number_prompt_choice,
    handle_mpesa_number_input,
    get_my_appointments,
    cancel_appointment,
    reschedule_appointment,
    get_appointment_details,
)

# OpenAI function definitions for ChatGPT-like interaction
HEALTHCARE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "handle_onboarding_function",
            "description": "Enables user to go through onboarding or login depending on their session state",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_user_registration",
            "description": "Register a new user when they want to create an account",
            "parameters": {
                "type": "object",
                "properties": {
                    "personal_details": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "middle_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "age": {"type": "string"},
                            "gender": {"type": "string"},
                            "password": {"type": "string"}
                        },
                        "required": ["password"]
                    }
                },
                "required": ["personal_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_profile_selection",
            "description": "The function is used after a user has selected their preferred profile",
            "parameters": {
                "type": "object",
                "properties": {
                    "selection_number": {
                        "type": "integer"
                    }
                },
                "required": ["selection_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_profile_listing",
            "description": "List the user's profiles without requiring them to select in numbers form",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_user_login",
            "description": "Login an existing user",
            "parameters": {
                "type": "object",
                "properties": {
                    "credentials": {
                        "type": "object",
                        "properties": {
                            "password": {"type": "string"}
                        },
                        "required": ["password"]
                    }
                },
                "required": ["credentials"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_doctor_recommendation_from_symptoms_function",
            "description": "Find and recommend doctors based on patient symptoms and medical conditions",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "string",
                        "description": "Combined symptoms and medical information from the patient"
                    }
                },
                "required": ["symptoms"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_doctors_by_criteria",
            "description": "Search for doctors based on specific name or medical specialization. Use this to find a doctor when user specifies a type of doctor",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_text": {
                        "type": "string",
                        "description": "This parameter can take either a medical specialization or the name of a doctor."
                    }
                },
                "required": ["search_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "doctor_availability",
            "description": "Choosing a doctor for user from the list or by name. Make sure you return the response as it is. This should always be called before booking",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_appointment_with_doctor",
            "description": "Book an appointment with a specific doctor and should be called after user has seen the doctor availability",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_details": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"]},
                        },
                        "required": ["doctor_name", "consultation_mode"]
                    }
                },
                "required": ["booking_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "appointment_date",
            "description": "Function enables users to pick month for booking a doctor",
            "parameters": {
                "type": "object",
                "properties": {
                    "selected_month_and_year": {"type": "string", "description": "month and year chosen"},
                },
                "required": ["selected_month_and_year"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "appointment_day",
            "description": "Choose a day from the existing month and year given",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_details": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"]},
                            "day": {"type": "string", "description": "The specific day in terms of 11th, 7th"}
                        },
                        "required": ["doctor_name", "consultation_mode", "day"]
                    }
                },
                "required": ["booking_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_payment_time_selection",
            "description": "Confirms when the user wants to pay for the consultation fee: now or later. Call this after the user has seen the payment options",
            "parameters": {
                "type": "object",
                "properties": {
                    "payment_choice": {
                        "type": "string",
                        "enum": ["now", "later"],
                        "description": "The user's choice for when to pay the consultation fee: 'now' to pay immediately, or 'later' to pay the service fee now"
                    }
                },
                "required": ["payment_choice"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_payment_method_selection",
            "description": "Confirms the user's preferred payment method. Call this after the user has seen the payment method options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method_name": {
                        "type": "string",
                        "description": "The name of the selected payment method (e.g., 'M-Pesa')."
                    }
                },
                "required": ["method_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_mobile_payment_number_prompt_choice",
            "description": "Handles the user's choice to use their registered number or enter a new one for mobile payment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "number_choice": {
                        "type": "string",
                        "enum": ["this number", "enter number"],
                        "description": "The user's choice: 'this number' to use their registered phone, or 'enter number' to provide a different one."
                    }
                },
                "required": ["number_choice"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_mpesa_number_input",
            "description": "Captures the user-provided M-Pesa phone number for payment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "The M-Pesa phone number provided by the user."
                    }
                },
                "required": ["phone_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_appointments",
            "description": "Get list of user's appointments with optional filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_criteria": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["all", "upcoming", "past", "cancelled"], "description": "Filter by appointment status"},
                            "date_range": {"type": "string", "enum": ["all", "today", "week", "month"], "description": "Filter by date range"}
                        }
                    }
                },
                "required": ["filter_criteria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "cancellation_details": {
                        "type": "object",
                        "properties": {
                            "appointment_identifier": {"type": "string", "description": "Doctor name or appointment details to identify the appointment"},
                            "reason": {"type": "string", "description": "Reason for cancellation"}
                        },
                        "required": ["appointment_identifier"]
                    }
                },
                "required": ["cancellation_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Reschedule an existing appointment to a new date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "reschedule_details": {
                        "type": "object",
                        "properties": {
                            "appointment_identifier": {"type": "string", "description": "Doctor name or appointment details to identify the appointment"},
                            "new_date": {"type": "string", "description": "New date in YYYY-MM-DD format"},
                            "new_time": {"type": "string", "description": "New time in HH:MM format"},
                            "reason": {"type": "string", "description": "Reason for rescheduling"}
                        },
                        "required": ["appointment_identifier", "new_date", "new_time"]
                    }
                },
                "required": ["reschedule_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_appointment_details",
            "description": "Get detailed information about a specific appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_identifier": {
                        "type": "object",
                        "properties": {
                            "identifier": {"type": "string", "description": "Doctor name, date, or other identifying information"}
                        },
                        "required": ["identifier"]
                    }
                },
                "required": ["appointment_identifier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_general_information",
            "description": "Get general information about healthcare services, pricing, insurance, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "Topic to get information about (pricing, insurance, services, hours, etc.)"}
                        },
                        "required": ["topic"]
                    }
                },
                "required": ["query"]
            }
        }
    }
]