import google.generativeai as genai
from langchain.memory import ConversationBufferMemory
from constants import GEMINI_API_KEY
from fastapi import APIRouter, HTTPException, Request, Depends
from firebase_client import db  
from routers.session.utils import verify_session_token
from datetime import datetime, timedelta, timezone
import json

genai.configure(api_key=GEMINI_API_KEY)
router = APIRouter()

model = genai.GenerativeModel(model_name="gemini-1.5-flash")

user_memory = {}

@router.post("/ai_adjustment")
async def ai_adjustment(request: Request, token_data=Depends(verify_session_token)):
    """
    Process the user's diet plan, logged meals, and fetch AI-generated adjustments 
    from the Gemini API based on the user's input, including both today's and last week's meal logs.
    """
    user_id = token_data.get("uid")

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: User ID not found")

    # Initialize memory for the user if not already present
    if user_id not in user_memory:
        user_memory[user_id] = ConversationBufferMemory()

    memory = user_memory[user_id]
    user_ref = db.collection("users").document(user_id)
    diet_plan_ref = user_ref.collection("dietPlan")
    log_meal_ref = user_ref.collection("dietLog")

    try:
        user_profile = user_ref.get().to_dict()
        dietary_preferences = user_profile.get("dietary_preferences", [])
        diet_plan_docs = diet_plan_ref.stream()
        diet_plan = {doc.id: doc.to_dict() for doc in diet_plan_docs}

        
        now = datetime.now(timezone.utc)
        meal_logs = []

        
        today_year = str(now.year)
        today_month = str(now.month).zfill(2)
        today_day = str(now.day).zfill(2)

        meals_today_ref = (
            log_meal_ref
            .document(today_year)
            .collection(today_month)
            .document(today_day)
            .collection("meals")
        )

        ai_adjustment_ref = (
            user_ref
            .collection("aiAdjustment")
            .document(now.strftime("%Y-%m-%d"))
        )

        last_ai_adjustment = ai_adjustment_ref.get().to_dict()
        

        meal_docs_today = meals_today_ref.stream()
        for meal_doc in meal_docs_today:
            meal_data = meal_doc.to_dict()
            meal_logs.append(meal_data)

        
        for i in range(1, 7):  
            prev_day = now - timedelta(days=i)
            prev_year = str(prev_day.year)
            prev_month = str(prev_day.month).zfill(2)
            prev_day_str = str(prev_day.day).zfill(2)

            meals_ref = (
                log_meal_ref
                .document(prev_year)
                .collection(prev_month)
                .document(prev_day_str)
                .collection("meals")
            )

            meal_docs_prev = meals_ref.stream()
            for meal_doc in meal_docs_prev:
                meal_data = meal_doc.to_dict()
                meal_logs.append(meal_data)

        
        meal_logs_last_week = meal_logs  

        
        socratic_prompt = f"""
        You are an AI diet assistant designed to help a user optimize their diet plan. 
        The user has the following profile: {user_profile}.
        Their current diet plan is as follows: {diet_plan}.
        The user's meal logs for the last week and today are: {meal_logs_last_week}.
        The last AI adjustment was: {last_ai_adjustment}.

        Please review the meal logs for the past 7 days. If the user has missed any meals or if their total calorie intake and macronutrient distribution (carbs, protein, fats) are below their targets, please:
        1. If the user missed meals, compensate for the missing calories in future meals.
        2. If there are significant discrepancies in total calories and macronutrients for the week, consider:
        - **Increasing the daily calorie target for subsequent days** slightly to make up for the missed intake, but ensure that the overall diet remains balanced and not overly caloric.
        - **Alternatively**, you can suggest small adjustments to portion sizes or food choices for the missed days to avoid any drastic increase in total daily targets.
        3. Provide an adjusted **weekly meal plan** that ensures the user meets their calorie target and nutritional requirements.
        4.Return the response in a strict JSON format with the following top-level keys:
            - `"analysis"`: A summary of adherence, including missed meals or discrepancies.
            - `"adjustment"`: A summary about the stragies u adapted to make changes to the user's diet.
            - `"adjustedDietPlan"`: The adjusted diet plan for the user. 

        Please ensure the plan remains **{dietary_preferences}** and adheres to the user's preferences and nutritional goals.
        """


        # Save memory context if necessary
        static_context = memory.load_memory_variables({})
        if not static_context.get("static_context_saved"):
            memory.save_context({"input": "static_context_saved"}, {"output": "true"})

        memory.save_context({"input": f"User Diet Plan: {diet_plan}\nMeal Logs: {meal_logs_last_week}"}, {"output": ""})

        context = memory.load_memory_variables({})
        history = context.get("history", "")

        # Structure the chat prompt with context and current request
        chat_prompt = f"""
        Context:
        {history}

        Current Prompt:
        {socratic_prompt}
        """

        # Generate a response using Gemini (or your model API)
        response = model.generate_content(chat_prompt)

        # Extract the assistant's response from the candidates
        if response.candidates:
            assistant_output = response.candidates[0].content.parts[0].text.strip()
        else:
            assistant_output = "No response generated."

        # Save the assistant's response to memory
        memory.save_context({"input": socratic_prompt}, {"output": assistant_output})

        # Remove leading and trailing triple backticks if present
        if assistant_output.startswith("```json"):
            assistant_output = assistant_output[7:]
        if assistant_output.endswith("```"):
            assistant_output = assistant_output[:-3]

        # Parse the assistant's response as JSON
        try:
            assistant_output = assistant_output.strip()
            adjustment = json.loads(assistant_output)
            # Save the AI adjustment to Firestore
            ai_adjustment_ref.set(adjustment)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail="Failed to parse AI adjustment response.")

        return {"status": "success", "adjustment": adjustment}

    except Exception as e:
        # Log the error and return a failure response
        print(f"Error in processing AI adjustment: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI adjustment. Please try again.")
    
    
