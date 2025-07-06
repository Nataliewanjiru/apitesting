def search_doctors_by_criteria(user_session, search_criteria: dict) -> str:
    """Search for doctors by name, specialty, location, etc."""
    try:
        print(f"🔍 DEBUG: Starting doctor search with criteria: {search_criteria}")
        
        search_text = search_criteria.get('search_text', '')
        specialty = search_criteria.get('specialty', '')
        location = search_criteria.get('location', '')
        max_price = search_criteria.get('max_price')
        
        print(f"🔍 DEBUG: Parsed criteria - specialty: '{specialty}', search_text: '{search_text}', location: '{location}', max_price: {max_price}")
        
        # Start with all verified health workers
        try:
            doctors = HEALTHWORKERS_MODELS.HealthWorker.filter_objects(
                is_published=True,
                verification_status=CORE_CHOICES.HealthWorkerVerificationStatuses.VERIFIED.value
            )
            print(f"🔍 DEBUG: Found {doctors.count()} verified doctors initially")
        except Exception as e:
            print(f"❌ DEBUG: Error getting initial doctors: {str(e)}")
            return f"Database error when accessing doctors: {str(e)}"
        
        # Apply search filters
        if search_text:
            try:
                doctors = search_health_worker_query_set(doctors, search_text)
                print(f"🔍 DEBUG: After search_text filter: {doctors.count()} doctors")
            except Exception as e:
                print(f"❌ DEBUG: Error in search_text filter: {str(e)}")
                return f"Error filtering by search text: {str(e)}"
        
        if specialty:
            try:
                doctors = doctors.filter(
                    Q(primary_specialty__name__icontains=specialty) |
                    Q(sub_specialties__icontains=specialty)
                )
                print(f"🔍 DEBUG: After specialty filter '{specialty}': {doctors.count()} doctors")
            except Exception as e:
                print(f"❌ DEBUG: Error in specialty filter: {str(e)}")
                return f"Error filtering by specialty: {str(e)}"
        
        if location:
            try:
                doctors = doctors.filter(
                    Q(primary_clinic_practice__county__name__icontains=location) |
                    Q(secondary_clinic_practice__county__name__icontains=location) |
                    Q(other_clinic_practice__county__name__icontains=location)
                )
                print(f"🔍 DEBUG: After location filter '{location}': {doctors.count()} doctors")
            except Exception as e:
                print(f"❌ DEBUG: Error in location filter: {str(e)}")
                return f"Error filtering by location: {str(e)}"
        
        if max_price:
            try:
                doctors = doctors.filter(
                    Q(my_preferences__clinic_visit_price__lte=max_price) |
                    Q(my_preferences__teleconsult_price__lte=max_price) |
                    Q(my_preferences__homecare_price__lte=max_price)
                )
                print(f"🔍 DEBUG: After price filter '{max_price}': {doctors.count()} doctors")
            except Exception as e:
                print(f"❌ DEBUG: Error in price filter: {str(e)}")
                return f"Error filtering by price: {str(e)}"
        
        # Order by recommendation points and limit results
        try:
            doctors = doctors.order_by('-recommendation_points')[:10]
            doctor_count = len(doctors)
            print(f"🔍 DEBUG: Final result count: {doctor_count} doctors")
        except Exception as e:
            print(f"❌ DEBUG: Error ordering/limiting doctors: {str(e)}")
            return f"Error ordering results: {str(e)}"
        
        if doctor_count == 0:
            if specialty:
                return f"❌ No cardiologists found in our network. We currently have doctors in other specialties. Would you like me to show you general practitioners or other specialists?"
            else:
                return "❌ No doctors found matching your criteria. Please try adjusting your search parameters."
        
        # Build doctor list with safe attribute access
        doctor_list = []
        for i, doctor in enumerate(doctors):
            try:
                print(f"🔍 DEBUG: Processing doctor {i+1}: {doctor}")
                
                # Safe attribute access
                title = getattr(doctor, 'title', 'Dr.')
                first_name = getattr(doctor, 'first_name', '')
                last_name = getattr(doctor, 'last_name', '')
                full_name = f"{title} {first_name} {last_name}".strip()
                
                # Safe specialty access
                specialty_name = 'General'
                if hasattr(doctor, 'primary_specialty') and doctor.primary_specialty:
                    specialty_name = getattr(doctor.primary_specialty, 'name', 'General')
                
                # Safe preferences access
                consultation_fee = 'Contact for pricing'
                if hasattr(doctor, 'my_preferences') and doctor.my_preferences:
                    clinic_price = getattr(doctor.my_preferences, 'clinic_visit_price', None)
                    if clinic_price:
                        consultation_fee = f"KSh {clinic_price}"
                
                # Safe location access
                location_name = 'Multiple locations'
                try:
                    if hasattr(doctor, 'primary_clinic_practice') and doctor.primary_clinic_practice:
                        if hasattr(doctor.primary_clinic_practice, 'county') and doctor.primary_clinic_practice.county:
                            county_name = getattr(doctor.primary_clinic_practice.county, 'name', None)
                            if county_name:
                                location_name = county_name
                except Exception as loc_e:
                    print(f"⚠️ DEBUG: Error getting location for doctor {i+1}: {str(loc_e)}")
                    # Continue with default location
                
                doctor_info = {
                    'name': full_name,
                    'specialty': specialty_name,
                    'consultation_fee': consultation_fee,
                    'location': location_name
                }
                doctor_list.append(doctor_info)
                print(f"✅ DEBUG: Successfully processed doctor {i+1}: {doctor_info}")
                
            except Exception as doctor_e:
                print(f"❌ DEBUG: Error processing doctor {i+1}: {str(doctor_e)}")
                # Continue with next doctor
                continue
        
        if not doctor_list:
            return "❌ Found doctors but couldn't process their information. Please try again or contact support."
        
        # Format response
        if specialty.lower() == 'cardiology':
            result = f"✅ Yes! We have {len(doctor_list)} cardiologist{'s' if len(doctor_list) > 1 else ''} available:\n\n"
        else:
            result = f"✅ Found {len(doctor_list)} doctor{'s' if len(doctor_list) > 1 else ''} matching your criteria:\n\n"
        
        for i, doc in enumerate(doctor_list, 1):
            result += f"{i}. **{doc['name']}**\n"
            result += f"   🏥 Specialty: {doc['specialty']}\n"
            result += f"   💰 Consultation: {doc['consultation_fee']}\n"
            result += f"   📍 Location: {doc['location']}\n\n"
        
        result += "Would you like to book an appointment with any of these doctors or get more information?"
        
        print(f"✅ DEBUG: Successfully returning result with {len(doctor_list)} doctors")
        return result
            
    except Exception as e:
        error_msg = f"Unexpected error in doctor search: {str(e)}"
        print(f"❌ DEBUG: {error_msg}")
        import traceback
        print(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
        return f"I encountered an error while searching for doctors: {str(e)}. Please try again or contact support."


# Also create a simpler fallback version for testing
def search_doctors_by_criteria_simple(user_session, search_criteria: dict) -> str:
    """Simplified version for debugging"""
    try:
        specialty = search_criteria.get('specialty', '')
        print(f"🔍 SIMPLE DEBUG: Looking for specialty: '{specialty}'")
        
        # Try to get just basic doctor count
        doctors = HEALTHWORKERS_MODELS.HealthWorker.objects.filter(is_published=True)
        total_count = doctors.count()
        print(f"🔍 SIMPLE DEBUG: Total published doctors: {total_count}")
        
        if specialty:
            # Simple specialty filter
            cardio_doctors = doctors.filter(primary_specialty__name__icontains=specialty)
            cardio_count = cardio_doctors.count()
            print(f"🔍 SIMPLE DEBUG: Doctors with specialty '{specialty}': {cardio_count}")
            
            if cardio_count > 0:
                return f"✅ Yes! We have {cardio_count} cardiologist{'s' if cardio_count > 1 else ''} available. Would you like me to show you their details?"
            else:
                return f"❌ We currently don't have any cardiologists available. We have {total_count} other doctors available. Would you like to see general practitioners?"
        
        return f"We have {total_count} doctors available. Please specify what type of doctor you're looking for."
        
    except Exception as e:
        print(f"❌ SIMPLE DEBUG: Error: {str(e)}")
        return f"Database connection error: {str(e)}"