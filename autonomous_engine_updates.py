# Updated AutonomousAIEngine class with proper function mapping

class AutonomousAIEngine:
    def __init__(self):
        self.client = OpenAI()  # Uses OPENAI_API_KEY from environment
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Map function names to actual functions
        self.function_map = {
            "handle_user_registration": handle_user_registration,
            "handle_user_login": handle_user_login,
            "handle_doctor_recommendation_from_symptoms": handle_doctor_recommendation_from_symptoms,
            "handle_booking_intent": handle_booking_intent,
            "handle_appointment_management": handle_appointment_management,
            "get_general_information": get_general_information,
        }

    def create_system_prompt(self, user_context: dict = None) -> str:
        base_prompt = DEFAULT_CHATBOT_BASE_PROMPT
        if user_context:
            if user_context.get("is_existing_user"):
                base_prompt += "\nUSER STATUS: This user is already registered in the system."
            else:
                base_prompt += "\nUSER STATUS: This user is not yet registered."
        
        return base_prompt

    def get_conversation_history(self) -> List[Dict]:
        """Convert LangChain memory to OpenAI format"""
        history = self.memory.load_memory_variables({}).get("chat_history", [])
        messages = []
        
        for msg in history:
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})
        
        return messages

    def execute_function_call(self, function_name: str, arguments: dict, user_session) -> str:
        """Execute the function called by AI"""
        try:
            if function_name not in self.function_map:
                return f"Error: Function {function_name} not found"
            
            func = self.function_map[function_name]
            
            # Handle different function signatures properly
            if function_name in ["handle_user_registration", "handle_user_login"]:
                result = func(user_session, arguments.get(list(arguments.keys())[0]))
                
            elif function_name == "handle_doctor_recommendation_from_symptoms":
                # NEW: Handle the updated function signature with inquiry_data
                inquiry_data = arguments.get("inquiry_data")
                if not inquiry_data:
                    # Fallback: try to get symptoms and create a simple object
                    symptoms = arguments.get("symptoms")
                    if symptoms:
                        # Create a simple object to maintain compatibility
                        class SimpleInquiry:
                            def __init__(self, symptoms):
                                self.symptoms = [symptoms] if isinstance(symptoms, str) else symptoms
                                self.additional_medical_information = []
                                self.preferred_modes_of_consultation = []
                        
                        inquiry_data = SimpleInquiry(symptoms)
                    else:
                        return "Error: No symptoms or inquiry data provided"
                
                result = func(user_session, inquiry_data)
                
            elif function_name in ["handle_booking_intent", "handle_appointment_management"]:
                result = func(user_session, arguments.get(list(arguments.keys())[0]))
            else:
                result = func(**arguments)
            
            return str(result)
        except Exception as e:
            return f"Error executing {function_name}: {str(e)}"

    def generate_autonomous_response(self, message: str, user_session, user_context: dict = None) -> str:
        """Generate response with autonomous function calling"""
        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": self.create_system_prompt(user_context)}
            ]
            messages.extend(self.get_conversation_history())
            messages.append({"role": "user", "content": message})
            from .promptingmodels import HEALTHCARE_TOOLS
            
            # Call OpenAI with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=HEALTHCARE_TOOLS,       
                tool_choice="auto",           
                temperature=0.3
            )

            assistant_message = response.choices[0].message

            # Check if AI wants to call a function
            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔍 AI calling function: {function_name} with args: {function_args}")
                
                # Execute the function
                function_result = self.execute_function_call(function_name, function_args, user_session)
                
                # Add function call and result to conversation
                messages.append({
                    "role": "assistant", 
                    "content": None,
                    "tool_calls": [tool_call.model_dump()]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_result
                })

                # Get AI's final response after function execution
                final_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.3
                )
                
                final_content = final_response.choices[0].message.content
                
                # Update memory
                self.memory.chat_memory.add_message(HumanMessage(content=message))
                self.memory.chat_memory.add_message(AIMessage(content=final_content))
                
                return final_content
            else:
                # No function call, just return AI's response
                content = assistant_message.content
                
                # Update memory
                self.memory.chat_memory.add_message(HumanMessage(content=message))
                self.memory.chat_memory.add_message(AIMessage(content=content))
                
                return content

        except Exception as e:
            print(f"❌ Error in autonomous response: {e}")
            return "I'm sorry, I encountered an error. Please try again."


# Alternative approach: Handle symptom extraction from AI response directly
def handle_autonomous_message_with_symptom_extraction(user_session, message_text: str) -> str:
    """Enhanced autonomous message handling with proper symptom extraction"""
    
    user_id = user_session.user_phone_number
    
    # Create user context
    user_context = {
        "is_existing_user": user_session.is_an_existing_user,
        "has_active_profile": bool(user_session.active_patient_profile)
    }
    
    # Get autonomous engine
    engine = get_autonomous_engine(user_id, user_session)
    
    # Let AI handle everything autonomously
    response = engine.generate_autonomous_response(message_text, user_session, user_context)
    
    # Check if the response contains symptom information that should trigger doctor recommendations
    try:
        # Try to parse if the response contains JSON with symptom information
        import json
        import re
        
        # Look for JSON in the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_data = json.loads(json_match.group())
            
            # Check if this is a symptom report with sufficient data for recommendations
            if (json_data.get("closing_remark") and 
                not json_data.get("next_question") and
                json_data.get("inquiry", {}).get("symptoms")):
                
                print("🔍 Detected symptom collection complete, triggering doctor recommendations...")
                
                # Extract inquiry data
                inquiry_data_dict = json_data.get("inquiry", {})
                
                # Create inquiry object
                class AIInquiryData:
                    def __init__(self, inquiry_dict):
                        self.symptoms = inquiry_dict.get("symptoms", [])
                        self.additional_medical_information = inquiry_dict.get("additional_medical_information", [])
                        self.preferred_modes_of_consultation = inquiry_dict.get("preferred_modes_of_consultation", [])
                
                inquiry_data = AIInquiryData(inquiry_data_dict)
                
                # Call doctor recommendation function directly
                doctor_recommendations = handle_doctor_recommendation_from_symptoms(
                    user_session=user_session,
                    inquiry_data=inquiry_data
                )
                
                # Convert the doctor recommendations to a string response
                if isinstance(doctor_recommendations, list):
                    recommendation_text = "\n".join([
                        msg.get("text", str(msg)) if isinstance(msg, dict) else str(msg) 
                        for msg in doctor_recommendations
                    ])
                    return recommendation_text
                else:
                    return str(doctor_recommendations)
    
    except Exception as e:
        print(f"⚠️ Could not extract symptom data from AI response: {e}")
        # Continue with normal response
    
    # Save conversation
    save_autonomous_conversation(user_id, user_session)
    
    return response