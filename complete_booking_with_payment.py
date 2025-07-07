from datetime import timedelta, datetime
from typing import Dict, Any
from django.db.models import Q
import apps.whatsappplugin1.models as WHATSAPP_PLUGIN1
import apps.healthworkers.models as HEALTHWORKERS_MODELS
import apps.core.choices as CORE_CHOICES
import apps.utilities.functions as UTILITIES_FUNCTIONS

# Import all the existing appointment functions
from apps.appointments.functions import (
    check_health_worker_availability,
    get_health_worker_appointment_cost,
    send_appointment_creation_notifications,
    generate_booking_bill_for_appointment,
    send_appointment_cancellation_by_patient_notification,
    send_appointment_rescheduling_by_patient_notification
)
from apps.appointments.models import Appointment, HealthWorkerAvailability
from apps.healthworkers.functions import search_health_worker_query_set


def create_appointment_with_payment_integration(
    user_session: WHATSAPP_PLUGIN1.WhatsappPlugin1UserSession,
    doctor: HEALTHWORKERS_MODELS.HealthWorker,
    start_datetime: datetime,
    end_datetime: datetime,
    consultation_mode: str,
    symptoms: str,
    availability_record: HealthWorkerAvailability,
    organization=None,
    health_care_services=None,
    payment_completed: bool = False
) -> tuple[bool, str, Appointment]:
    """
    Create appointment with full payment and billing integration
    
    Returns:
        tuple: (success, message, appointment_object)
    """
    try:
        print(f"🔍 Creating appointment with payment integration")
        
        # Get patient profile
        patient = user_session.active_patient_profile
        if not patient:
            return False, "Please log in to book an appointment.", None
        
        # Calculate total cost and billing details
        total_cost, billing_details = get_health_worker_appointment_cost(
            doctor=doctor,
            encounter_mode=consultation_mode,
            health_care_services=health_care_services,
            organization=organization
        )
        
        print(f"🔍 Calculated cost: KES {total_cost}")
        print(f"🔍 Billing details: {billing_details}")
        
        # Create the appointment
        appointment = Appointment.objects.create(
            # Core appointment details
            doctor=doctor,
            patient=patient,
            start_time=start_datetime,
            end_time=end_datetime,
            encounter_mode=consultation_mode,
            
            # Status and payment
            status=CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value,
            payment_completed=payment_completed,
            
            # Costs and billing
            cost=total_cost,
            billing_details=billing_details,
            booking_fee=50.0,  # Standard booking fee
            is_inapp_payment=True,  # Assuming in-app payment
            
            # Additional details
            symptoms_description=symptoms,
            created_by_patient=True,
            health_worker_availability=availability_record,
            organization=organization,
            
            # Metadata
            created_at=UTILITIES_FUNCTIONS.get_current_time(),
        )
        
        print(f"🔍 Appointment created with ID: {appointment.id}")
        
        # Generate booking bill
        try:
            appointment = generate_booking_bill_for_appointment(
                health_worker=doctor,
                appointment=appointment
            )
            print(f"🔍 Booking bill generated successfully")
        except Exception as e:
            print(f"⚠️ Warning: Booking bill generation failed: {e}")
            # Don't fail the appointment creation for bill generation issues
        
        # Send notifications
        send_appointment_creation_notifications(
            appointment=appointment,
            payment_completed=payment_completed
        )
        print(f"🔍 Notifications sent")
        
        # Format response message
        appointment_time = start_datetime.strftime('%A, %B %d at %I:%M %p')
        
        if payment_completed:
            message = (
                f"✅ Appointment successfully booked!\n\n"
                f"👨‍⚕️ Doctor: {doctor.title} {doctor.get_full_name()}\n"
                f"📅 Date & Time: {appointment_time}\n"
                f"🏥 Consultation: {consultation_mode.title().replace('_', ' ')}\n"
                f"💰 Total Cost: KES {total_cost}\n"
                f"💳 Booking Fee: KES 50\n"
                f"📋 Status: Confirmed\n\n"
                f"You'll receive confirmation via SMS and email with appointment details."
            )
        else:
            message = (
                f"📋 Appointment reserved!\n\n"
                f"👨‍⚕️ Doctor: {doctor.title} {doctor.get_full_name()}\n"
                f"📅 Date & Time: {appointment_time}\n"
                f"🏥 Consultation: {consultation_mode.title().replace('_', ' ')}\n"
                f"💰 Total Cost: KES {total_cost}\n"
                f"💳 Booking Fee: KES 50\n"
                f"📋 Status: Payment Pending\n\n"
                f"⏰ Your slot is reserved for 5 minutes. Please complete payment to confirm.\n"
                f"Payment methods: M-Pesa, Credit Card, or pay at clinic."
            )
        
        return True, message, appointment
        
    except Exception as e:
        print(f"❌ Error creating appointment: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return False, f"Booking failed: {str(e)}", None


def book_appointment_with_doctor_complete(user_session, booking_details: dict) -> str:
    """
    Complete booking function with payment integration
    """
    try:
        print(f"🔍 Processing booking request: {booking_details}")
        
        # Extract booking details
        doctor_name = booking_details.get('doctor_name', '')
        date_str = booking_details.get('date', '')
        time_str = booking_details.get('time', '')
        consultation_mode = booking_details.get('consultation_mode', 'virtual')
        symptoms = booking_details.get('symptoms', 'General consultation')
        payment_method = booking_details.get('payment_method', 'pending')  # pending, mpesa, card, clinic
        health_care_services = booking_details.get('health_care_services', [])
        
        # Validation
        if not doctor_name or not date_str or not time_str:
            return "❌ Please provide doctor name, date, and time to book appointment."
        
        # Find the doctor
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        
        # Clean doctor name (remove titles)
        cleaned_doctor_name = doctor_name.strip().lower()
        titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
        for title in titles_to_remove:
            if cleaned_doctor_name.startswith(title + ' '):
                cleaned_doctor_name = cleaned_doctor_name[len(title):].strip()
            elif cleaned_doctor_name.startswith(title):
                cleaned_doctor_name = cleaned_doctor_name[len(title):].strip()
        
        doctors = search_health_worker_query_set(doctors, cleaned_doctor_name)
        
        if not doctors:
            return f"❌ Doctor '{doctor_name}' not found. Please check the name and try again."
        
        doctor = doctors.first()
        print(f"🔍 Found doctor: {doctor.title} {doctor.get_full_name()}")
        
        # Parse date and time
        try:
            start_datetime = UTILITIES_FUNCTIONS.string_to_datetime(f"{date_str} {time_str}:00.0 +0300")
            end_datetime = start_datetime + timedelta(hours=1)
            print(f"🔍 Appointment time: {start_datetime} to {end_datetime}")
        except Exception as e:
            print(f"🔍 Date/time parsing error: {e}")
            return "❌ Invalid date/time format. Please use YYYY-MM-DD for date and HH:MM for time."
        
        # Check if appointment is in the future
        current_time = UTILITIES_FUNCTIONS.get_current_time()
        if start_datetime <= current_time:
            return "❌ Cannot book appointments in the past. Please select a future date and time."
        
        # Check availability
        print(f"🔍 Checking availability for {consultation_mode} consultation")
        is_available, availability = check_health_worker_availability(
            worker=doctor,
            start_time=start_datetime,
            end_time=end_datetime,
            mode=consultation_mode
        )
        
        if not is_available:
            return (f"❌ {doctor.title} {doctor.get_full_name()} is not available on {date_str} at {time_str} "
                   f"for {consultation_mode} consultation.\n\n"
                   f"💡 Try checking available times or choose a different time slot.")
        
        print(f"🔍 Doctor is available, proceeding with booking")
        
        # Determine if payment is completed (for now, assume pending unless specified)
        payment_completed = payment_method in ['mpesa_completed', 'card_completed', 'clinic_paid']
        
        # Create the appointment with full payment integration
        success, message, appointment = create_appointment_with_payment_integration(
            user_session=user_session,
            doctor=doctor,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            consultation_mode=consultation_mode,
            symptoms=symptoms,
            availability_record=availability,
            health_care_services=health_care_services,
            payment_completed=payment_completed
        )
        
        if success:
            # Add payment instructions if payment is pending
            if not payment_completed:
                message += f"\n\n💳 Payment Options:\n"
                message += f"• M-Pesa: Pay to 123456 (Paybill)\n"
                message += f"• Credit Card: Use our secure online payment\n"
                message += f"• Clinic Payment: Pay when you arrive\n"
                message += f"\n📱 Reference: APT{appointment.id}"
            
            return message
        else:
            return message
            
    except Exception as e:
        print(f"❌ Booking failed with error: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return f"❌ Booking failed: Please try again or contact support. Error: {str(e)}"


def complete_appointment_payment(user_session, payment_details: dict) -> str:
    """
    Complete payment for a pending appointment
    """
    try:
        appointment_id = payment_details.get('appointment_id')
        payment_method = payment_details.get('payment_method', 'mpesa')
        payment_reference = payment_details.get('payment_reference', '')
        
        if not appointment_id:
            return "❌ Please provide appointment ID to complete payment."
        
        # Find the appointment
        appointment = Appointment.objects.filter(
            id=appointment_id,
            patient=user_session.active_patient_profile,
            status=CORE_CHOICES.AppointmentStatuses.BOOKING_PENDING.value
        ).first()
        
        if not appointment:
            return "❌ Appointment not found or payment already completed."
        
        # Check if appointment is still valid (not expired)
        current_time = UTILITIES_FUNCTIONS.get_current_time()
        booking_expiry = appointment.created_at + timedelta(minutes=5)  # 5-minute reservation
        
        if current_time > booking_expiry and not appointment.payment_completed:
            appointment.status = CORE_CHOICES.AppointmentStatuses.CANCELLED.value
            appointment.cancellation_reason = "Payment timeout"
            appointment.save()
            return "❌ Appointment reservation expired. Please book again."
        
        # Update payment status
        appointment.payment_completed = True
        appointment.payment_method = payment_method
        appointment.payment_reference = payment_reference
        appointment.status = CORE_CHOICES.AppointmentStatuses.PENDING.value
        appointment.save()
        
        # Send confirmation notifications
        send_appointment_creation_notifications(
            appointment=appointment,
            payment_completed=True
        )
        
        # Regenerate booking bill with payment details
        try:
            appointment = generate_booking_bill_for_appointment(
                health_worker=appointment.doctor,
                appointment=appointment
            )
        except Exception as e:
            print(f"⚠️ Warning: Updated bill generation failed: {e}")
        
        appointment_time = appointment.start_time.strftime('%A, %B %d at %I:%M %p')
        
        return (f"✅ Payment successful!\n\n"
               f"👨‍⚕️ Doctor: {appointment.doctor.title} {appointment.doctor.get_full_name()}\n"
               f"📅 Date & Time: {appointment_time}\n"
               f"🏥 Consultation: {appointment.encounter_mode.title().replace('_', ' ')}\n"
               f"💰 Amount Paid: KES {appointment.cost + appointment.booking_fee}\n"
               f"📋 Reference: {payment_reference}\n\n"
               f"📱 You'll receive SMS and email confirmation with appointment details.\n"
               f"📄 Your booking bill has been generated and emailed to you.")
        
    except Exception as e:
        print(f"❌ Payment completion failed: {e}")
        return f"❌ Payment processing failed: {str(e)}"


def quick_book_from_available_slots_complete(user_session, booking_request: dict) -> str:
    """Enhanced quick booking with payment integration"""
    try:
        doctor_name = booking_request.get('doctor_name', '')
        selected_slot = booking_request.get('selected_slot', '')
        consultation_mode = booking_request.get('consultation_mode', 'virtual')
        symptoms = booking_request.get('symptoms', 'General consultation')
        payment_method = booking_request.get('payment_method', 'pending')
        
        # Parse the selected slot (format: "2025-07-07 09:00")
        if " " not in selected_slot:
            return "❌ Please provide the date and time in format: YYYY-MM-DD HH:MM"
        
        date_str, time_str = selected_slot.split(" ", 1)
        
        booking_details = {
            'doctor_name': doctor_name,
            'date': date_str,
            'time': time_str,
            'consultation_mode': consultation_mode,
            'symptoms': symptoms,
            'payment_method': payment_method
        }
        
        return book_appointment_with_doctor_complete(user_session, booking_details)
    
    except Exception as e:
        return f"❌ Quick booking failed: {str(e)}"


# Updated HEALTHCARE_TOOLS with payment integration
COMPLETE_BOOKING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment_with_doctor_complete",
            "description": "Book an appointment with full payment integration and billing",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_details": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "time": {"type": "string", "description": "Time in HH:MM format"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_care"]},
                            "symptoms": {"type": "string", "description": "Reason for visit or symptoms"},
                            "payment_method": {"type": "string", "enum": ["pending", "mpesa", "card", "clinic"], "description": "Payment method preference"}
                        },
                        "required": ["doctor_name", "date", "time"]
                    }
                },
                "required": ["booking_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_appointment_payment",
            "description": "Complete payment for a pending appointment booking",
            "parameters": {
                "type": "object",
                "properties": {
                    "payment_details": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {"type": "integer", "description": "ID of the appointment to pay for"},
                            "payment_method": {"type": "string", "enum": ["mpesa", "card", "clinic"], "description": "Payment method used"},
                            "payment_reference": {"type": "string", "description": "Payment reference number or transaction ID"}
                        },
                        "required": ["appointment_id", "payment_method"]
                    }
                },
                "required": ["payment_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "quick_book_from_available_slots_complete",
            "description": "Quick booking from available time slots with payment integration",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_request": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "selected_slot": {"type": "string", "description": "Selected time slot in format 'YYYY-MM-DD HH:MM'"},
                            "consultation_mode": {"type": "string", "enum": ["virtual", "clinic_visit", "home_visit"]},
                            "symptoms": {"type": "string", "description": "Reason for visit or symptoms"},
                            "payment_method": {"type": "string", "enum": ["pending", "mpesa", "card", "clinic"]}
                        },
                        "required": ["doctor_name", "selected_slot"]
                    }
                },
                "required": ["booking_request"]
            }
        }
    }
]