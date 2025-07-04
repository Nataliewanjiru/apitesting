from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union


class PromptOutputBooking(BaseModel):
    selected_doctor: Optional[str] = Field(
        description="The ID or name of the doctor selected by the user."
    )
    specialization: Optional[str] = Field(
        description="The medical specialization or type of doctor the user wants to see, e.g., general practitioner, cardiologist, dentist."
    )
    preferred_consultation_time: Optional[str] = Field(
        description="Preferred consultation time as described by the user."
    )
    preferred_date: Optional[str] = Field(
        description="Preferred consultation date as described by the user."
    )
    confirmed: Optional[bool] = Field(
        description="Whether the user has confirmed the appointment."
    )
    consultation_mode: Optional[str] = Field(
        description="Preferred mode of consultation: virtual, clinic, or home visit."
    )
    urgency_level: Optional[str] = Field(
        description="Urgency of the appointment: urgent, routine, or emergency."
    )


class PromptOutputPersonalDetails(BaseModel):
    first_name: Optional[str] = Field(description="The user's first name.")
    middle_name: Optional[str] = Field(description="The user's middle name.")
    last_name: Optional[str] = Field(description="The user's last name.")
    age: Optional[str] = Field(description="The user's age.")
    county: Optional[str] = Field(description="The user's county of residence or current location.")
    location: Optional[str] = Field(description="The user's current location or address.")
    phone_number: Optional[str] = Field(description="The user's phone number.")
    email: Optional[str] = Field(description="The user's email address.")


class PromptOutputInquiry(BaseModel):
    symptoms: Optional[List[str]] = Field(
        description="The user's medical symptoms that necessitate a care provider."
    )
    additional_medical_information: Optional[List[str]] = Field(
        description="Any additional information attained from follow up questions on the user's symptoms."
    )
    preferred_modes_of_consultation: Optional[List[str]] = Field(
        description="The mode of consultation the user prefers: in-person clinic visit, home visit, or virtual."
    )
    medical_history: Optional[List[str]] = Field(
        description="Relevant medical history or conditions mentioned by the user."
    )
    current_medications: Optional[List[str]] = Field(
        description="Current medications the user is taking."
    )
    allergies: Optional[List[str]] = Field(
        description="Known allergies mentioned by the user."
    )


class PromptOutputAppointmentManagement(BaseModel):
    action: Optional[str] = Field(
        description="The requested action: view, cancel, reschedule, or modify."
    )
    appointment_identifier: Optional[str] = Field(
        description="Identifier for the specific appointment (doctor name, date, etc.)."
    )
    new_date: Optional[str] = Field(
        description="New date for rescheduling (if applicable)."
    )
    new_time: Optional[str] = Field(
        description="New time for rescheduling (if applicable)."
    )
    reason: Optional[str] = Field(
        description="Reason for cancellation or rescheduling."
    )


class PromptOutputFeedback(BaseModel):
    rating: Optional[int] = Field(
        description="Rating given by the user (1-5 scale)."
    )
    feedback_text: Optional[str] = Field(
        description="Written feedback from the user."
    )
    service_type: Optional[str] = Field(
        description="What service they're providing feedback about."
    )
    doctor_name: Optional[str] = Field(
        description="Name of the doctor being reviewed (if applicable)."
    )


class PromptOutputGeneral(BaseModel):
    query_type: Optional[str] = Field(
        description="Type of general query: pricing, insurance, services, hours, etc."
    )
    specific_question: Optional[str] = Field(
        description="The specific question or information requested."
    )


class PromptOutput(BaseModel):
    next_question: Optional[str] = Field(
        description="The follow-up question to ask the user, if needed."
    )
    closing_remark: Optional[str] = Field(
        description="The assistant's final response for this interaction."
    )
    intent: Optional[str] = Field(
        description="The recognized user intent: booking, inquiry, feedback, symptom_report, personal_info, appointment_management, general, etc."
    )
    extracted_info: Optional[Dict[str, Union[
        PromptOutputBooking,
        PromptOutputPersonalDetails,
        PromptOutputInquiry,
        PromptOutputAppointmentManagement,
        PromptOutputFeedback,
        PromptOutputGeneral
    ]]] = Field(
        description="Structured data extracted from the user message based on their intent."
    )
    confidence_score: Optional[float] = Field(
        description="Confidence score for the intent classification (0.0 to 1.0)."
    )
    requires_immediate_attention: Optional[bool] = Field(
        description="Whether this message requires immediate attention (emergency, urgent care, etc.)."
    )


# Enhanced intent examples for the AI prompt

INTENT_EXAMPLES = {
    "booking": [
        "I want to book Dr. Smith for tomorrow at 2pm",
        "Can I schedule an appointment with a cardiologist?",
        "Book me with Dr. Johnson for next Monday",
        "I need to see a dentist this week"
    ],
    
    "appointment_management": [
        "Cancel my appointment with Dr. Smith",
        "I want to reschedule my Tuesday appointment",
        "Show me my upcoming appointments",
        "Can I change my 3pm appointment to 4pm?",
        "View my appointment history"
    ],
    
    "symptom_report": [
        "I have been having headaches for 3 days",
        "I'm experiencing chest pain and shortness of breath",
        "My child has a fever and cough",
        "I need help with my back pain"
    ],
    
    "general": [
        "What are your operating hours?",
        "Do you accept my insurance?",
        "How much does a consultation cost?",
        "What services do you offer?"
    ],
    
    "feedback": [
        "I want to rate my last appointment",
        "Dr. Smith was excellent, 5 stars",
        "The service was poor, I'm not satisfied",
        "How can I leave a review?"
    ],
    
    "emergency": [
        "This is an emergency",
        "I need immediate medical attention",
        "Urgent care needed",
        "Emergency appointment required"
    ]
}


# Enhanced prompt template additions

ENHANCED_PROMPT_ADDITIONS = """

## Enhanced Intent Recognition

The system should recognize these primary intents:

1. **booking** - User wants to schedule a new appointment
2. **appointment_management** - User wants to view, cancel, or reschedule existing appointments  
3. **symptom_report** - User is describing symptoms and needs doctor recommendations
4. **general** - User has general questions about services, pricing, hours, etc.
5. **feedback** - User wants to provide feedback or reviews
6. **emergency** - User has urgent/emergency medical needs

## Appointment Management Examples

For appointment management, provide responses like:

```json
{
  "intent": "appointment_management",
  "next_question": "Which appointment would you like to cancel?",
  "extracted_info": {
    "PromptOutputAppointmentManagement": {
      "action": "cancel",
      "appointment_identifier": "Dr. Smith",
      "reason": null
    }
  }
}
```

## Emergency Handling

For emergency situations, immediately provide emergency guidance:

```json
{
  "intent": "emergency",
  "closing_remark": "For emergency medical needs, please call 911 or visit your nearest emergency room immediately.",
  "requires_immediate_attention": true
}
```

## Enhanced Booking Flow

For booking, collect all necessary information progressively:

```json
{
  "intent": "booking", 
  "next_question": "What symptoms are you experiencing?",
  "extracted_info": {
    "PromptOutputBooking": {
      "selected_doctor": "Dr. Smith",
      "preferred_date": "tomorrow",
      "preferred_consultation_time": "2pm",
      "consultation_mode": "clinic",
      "confirmed": null
    },
    "PromptOutputPersonalDetails": {
      "first_name": "John",
      "age": "25"
    }
  }
}
```

Always maintain conversation context and avoid repeating previously collected information.
"""