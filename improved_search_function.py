from django.db.models import Q
from datetime import datetime, timedelta
import apps.healthworkers.models as HEALTHWORKERS_MODELS
import apps.core.choices as CORE_CHOICES
import apps.utilities.functions as UTILITIES_FUNCTIONS
from .appointment_functions import check_health_worker_availability

def search_health_worker_query_set(query_set, search_text):
    """Enhanced search that handles doctor titles and uses OR logic for better matching"""
    
    # Clean up search text and remove common titles
    cleaned_search = search_text.strip().lower()
    
    # Remove common doctor titles
    titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
    for title in titles_to_remove:
        if cleaned_search.startswith(title + ' '):
            cleaned_search = cleaned_search[len(title):].strip()
        elif cleaned_search.startswith(title):
            cleaned_search = cleaned_search[len(title):].strip()
    
    # If after removing titles there's nothing left, return all
    if not cleaned_search:
        return query_set
    
    # Split into search terms
    search_items = list(
        filter(
            lambda x: len(x) > 0,
            map(lambda x: x.strip(), cleaned_search.split(" ")),
        )
    )
    
    if not search_items:
        return query_set
    
    # Build search query with OR logic for all terms and fields
    search_query = None
    
    for search_item in search_items:
        term_query = (
            Q(first_name__icontains=search_item) |
            Q(last_name__icontains=search_item) |
            Q(middle_name__icontains=search_item) |
            Q(primary_specialty__name__icontains=search_item)
        )
        
        # Combine with previous terms using OR (any term can match)
        if search_query is None:
            search_query = term_query
        else:
            search_query = search_query | term_query
    
    return query_set.filter(search_query)

def search_doctors_by_criteria(user_session, search_criteria: dict) -> str:
    """Search for doctors by name, specialty, location, etc."""
    try:
        print("Search criteria", search_criteria)
        search_text = search_criteria.get('search_text', '')
        specialty = search_criteria.get('specialty', '')
        location = search_criteria.get('location', '')
        max_price = search_criteria.get('max_price')
        
        # Start with all verified health workers
        all_doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        print("Verified doctors", all_doctors.count())
        
        doctors = all_doctors
        
        # Apply search filters
        if search_text:
            doctors = search_health_worker_query_set(doctors, search_text)
        
        # Track what filters are being applied for better feedback
        original_count = doctors.count()
        specialty_filtered = False
        location_filtered = False
        
        if specialty:
            doctors_with_specialty = doctors.filter(
                Q(primary_specialty__name__icontains=specialty) |
                Q(sub_specialties__icontains=specialty)
            )
            specialty_count = doctors_with_specialty.count()
            doctors = doctors_with_specialty
            specialty_filtered = True
            print(f"After specialty filter '{specialty}': {specialty_count} doctors")
        
        if location:
            doctors_with_location = doctors.filter(
                Q(primary_clinic_practice__county__name__icontains=location) |
                Q(secondary_clinic_practice__county__name__icontains=location) |
                Q(other_clinic_practice__county__name__icontains=location)
            )
            location_count = doctors_with_location.count()
            doctors = doctors_with_location
            location_filtered = True
            print(f"After location filter '{location}': {location_count} doctors")
        
        if max_price:
            doctors = doctors.filter(
                Q(my_preferences__clinic_visit_price__lte=max_price) |
                Q(my_preferences__teleconsult_price__lte=max_price) |
                Q(my_preferences__homecare_price__lte=max_price)
            )
        
        # Order by recommendation points
        doctors = doctors.order_by('-recommendation_points')[:10]
        print("Final doctors", doctors.count())
        
        if doctors:
            doctor_list = []
            for doctor in doctors:
                doctor_info = {
                    'name': f"{doctor.title} {doctor.get_full_name()}",
                    'specialty': doctor.primary_specialty.name if doctor.primary_specialty else 'General',
                    'consultation_fee': getattr(doctor.my_preferences, 'clinic_visit_price', 'N/A'),
                    'location': getattr(doctor.primary_clinic_practice, 'county', {}).get('name', 'Multiple locations') if hasattr(doctor, 'primary_clinic_practice') and doctor.primary_clinic_practice else 'Multiple locations'
                }
                doctor_list.append(doctor_info)
            
            # Format response based on search type
            if specialty.lower() == 'cardiology':
                result = f"✅ Yes! We have {len(doctor_list)} cardiologist{'s' if len(doctor_list) > 1 else ''} available"
                if location:
                    result += f" in {location}"
                result += ":\n\n"
            else:
                result = f"✅ Found {len(doctor_list)} doctor{'s' if len(doctor_list) > 1 else ''} matching your criteria:\n\n"
            
            for i, doc in enumerate(doctor_list, 1):
                result += f"{i}. **{doc['name']}**\n"
                result += f"   🏥 Specialty: {doc['specialty']}\n"
                result += f"   💰 Consultation: KSh {doc['consultation_fee']}\n"
                result += f"   📍 Location: {doc['location']}\n\n"
            
            result += "Would you like to book an appointment with any of these doctors or get more information?"
            return result
        
        else:
            # No doctors found - provide helpful alternatives
            
            # Check if there are cardiologists anywhere (without location filter)
            if specialty_filtered and location_filtered:
                cardiologists_anywhere = all_doctors.filter(
                    Q(primary_specialty__name__icontains=specialty) |
                    Q(sub_specialties__icontains=specialty)
                ).count()
                
                doctors_in_location = all_doctors.filter(
                    Q(primary_clinic_practice__county__name__icontains=location) |
                    Q(secondary_clinic_practice__county__name__icontains=location) |
                    Q(other_clinic_practice__county__name__icontains=location)
                ).count()
                
                if cardiologists_anywhere > 0 and doctors_in_location > 0:
                    return f"❌ We don't have cardiologists specifically in {location}, but we have:\n" \
                           f"• {cardiologists_anywhere} cardiologist{'s' if cardiologists_anywhere > 1 else ''} in other locations\n" \
                           f"• {doctors_in_location} other doctor{'s' if doctors_in_location > 1 else ''} in {location}\n\n" \
                           f"Would you like to see cardiologists in other areas or other specialists in {location}?"
                elif cardiologists_anywhere > 0:
                    return f"❌ We don't have cardiologists in {location}, but we have {cardiologists_anywhere} cardiologist{'s' if cardiologists_anywhere > 1 else ''} in other locations. " \
                           f"Would you like to see them?"
                elif doctors_in_location > 0:
                    return f"❌ We don't have cardiologists available, but we have {doctors_in_location} other doctor{'s' if doctors_in_location > 1 else ''} in {location}. " \
                           f"Would you like to see general practitioners or other specialists?"
            
            elif specialty_filtered:
                # Only specialty filter applied
                if specialty.lower() == 'cardiology':
                    return f"❌ We currently don't have any cardiologists available in our network. " \
                           f"We have {all_doctors.count()} other doctors available. " \
                           f"Would you like to see general practitioners or other specialists who might help with heart-related concerns?"
                else:
                    return f"❌ No {specialty} specialists found. We have {all_doctors.count()} other doctors available. " \
                           f"Would you like to see general practitioners?"
            
            elif location_filtered:
                # Only location filter applied  
                return f"❌ No doctors found in {location}. We have {all_doctors.count()} doctors in other locations. " \
                       f"Would you like to see doctors in nearby areas?"
            
            else:
                # No specific filters or general search failed
                return "❌ No doctors found matching your criteria. Please try adjusting your search parameters or contact us for assistance."
            
    except Exception as e:
        error_msg = f"Doctor search failed: {str(e)}"
        print(f"❌ Error in search: {error_msg}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return error_msg

def get_doctor_available_times(user_session, availability_request: dict) -> str:
    """Get available time slots for a doctor (when user asks 'when is doctor available')"""
    try:
        doctor_name = availability_request.get('doctor_name', '')
        date_str = availability_request.get('date', '')  # Optional - can be empty
        consultation_mode = availability_request.get('consultation_mode', 'virtual')
        
        if not doctor_name:
            return "Please provide doctor name to check availability."
        
        # Find the doctor
        doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
            is_published=True,
            verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
        )
        doctors = search_health_worker_query_set(doctors, doctor_name)
        
        if not doctors:
            return f"Doctor '{doctor_name}' not found."
        
        doctor = doctors.first()
        
        # If no specific date provided, check next 7 days
        if not date_str:
            current_time = UTILITIES_FUNCTIONS.get_current_time()
            dates_to_check = [current_time + timedelta(days=i) for i in range(7)]
        else:
            try:
                specific_date = UTILITIES_FUNCTIONS.string_to_datetime(f"{date_str} 00:00:00.0 +0300")
                dates_to_check = [specific_date]
            except:
                return "Invalid date format. Please use YYYY-MM-DD format."
        
        available_slots = []
        
        # Check common appointment times (9 AM to 5 PM)
        for check_date in dates_to_check:
            for hour in range(9, 17):  # 9 AM to 5 PM
                start_time = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(hours=1)
                
                # Skip past times
                if start_time < UTILITIES_FUNCTIONS.get_current_time():
                    continue
                
                # Check if this slot is available
                is_available, availability = check_health_worker_availability(
                    worker=doctor,
                    start_time=start_time,
                    end_time=end_time,
                    mode=consultation_mode
                )
                
                if is_available:
                    available_slots.append({
                        'date': start_time.strftime('%Y-%m-%d'),
                        'time': start_time.strftime('%H:%M'),
                        'day': start_time.strftime('%A')
                    })
        
        if not available_slots:
            return f"❌ {doctor.title} {doctor.get_full_name()} has no available slots in the next 7 days for {consultation_mode} consultation.\n" \
                   f"Please try a different consultation mode or contact the doctor directly."
        
        # Format the response
        result = f"📅 Available times for {doctor.title} {doctor.get_full_name()} ({consultation_mode} consultation):\n\n"
        
        # Group by date
        current_date = None
        for slot in available_slots[:20]:  # Limit to first 20 slots
            if slot['date'] != current_date:
                result += f"📅 {slot['day']}, {slot['date']}:\n"
                current_date = slot['date']
            result += f"   • {slot['time']}\n"
        
        result += f"\nWould you like to book any of these available times?"
        return result
        
    except Exception as e:
        return f"Availability check failed: {str(e)}"