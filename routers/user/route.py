from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from firebase_client import db
from routers.session.utils import verify_session_token




router = APIRouter()

@router.post("/profile")
async def add_data(request: Request, token_data=Depends(verify_session_token)):
    user_id = token_data.get("uid")  
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: User ID not found")
    
    user_doc_ref = db.collection("users").document(user_id)
    

    body = await request.json()
    
    
    profile_data = {
    "name": body.get("name"),
    "age": body.get("age"),
    "weight": body.get("weight"),  # in kg
    "height": body.get("height"),  # in cm
    "gender": body.get("gender"),  # e.g., "male", "female", "non-binary"
    "dietary_preferences": body.get("dietary_preferences"),  # e.g., "vegan", "vegetarian", "non-vegetarian"
    "goals": body.get("goals"),  # e.g., "weight loss", "muscle gain", "maintenance"
    "activity_level": body.get("activity_level"),  # e.g., "sedentary", "moderately active", "very active"
    "medical_conditions": body.get("medical_conditions", []),  # List of medical conditions, e.g., ["diabetes"]
    "allergies_or_intolerances": body.get("allergies_or_intolerances", []),  # List of food allergies or intolerances
    "preferred_cuisines": body.get("preferred_cuisines", []),  # e.g., ["Indian", "Italian"]
    "meal_frequency": body.get("meal_frequency", 3),  # Default is 3 meals per day
    "created_at": datetime.now(timezone.utc),
    }

    
    
    user_doc_ref.set(profile_data)
    return JSONResponse(content={'status': 'success', 'message': 'Profile added successfully'})

from fastapi.responses import JSONResponse
from datetime import datetime

@router.post("/dietplan")
async def add_dietplan(request: Request, token_data=Depends(verify_session_token)):
    """
    Adds a user's weekly diet plan to Firestore.
    Ensures detailed information is captured for better AI assistance.
    """
    user_id = token_data.get("uid")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: User ID not found")
    
    user_doc_ref = db.collection("users").document(user_id).collection("dietPlan")
    body = await request.json()
    
    weekly_diet_plan = body.get("weeklyDietPlan")
    if not weekly_diet_plan:
        raise HTTPException(status_code=400, detail="Weekly diet plan is required")
    
    for day_plan in weekly_diet_plan:
        day_name = day_plan.get("day")
        if not day_name:
            raise HTTPException(status_code=400, detail="Day name is required for each day plan")
        
        # Validate day-level fields
        daily_calorie_target = day_plan.get("dailyCalorieTarget")
        macronutrient_split = day_plan.get("macronutrientSplit")  # e.g., {"carbs": 40, "protein": 30, "fats": 30}
        meal_plan = day_plan.get("mealPlan")  # List of meals for the day
        
        if not daily_calorie_target or not macronutrient_split or not meal_plan:
            raise HTTPException(
                status_code=400, 
                detail=f"Each day must include 'dailyCalorieTarget', 'macronutrientSplit', and 'mealPlan'"
            )
        
        # Validate meal-level fields
        for meal in meal_plan:
            if not meal.get("type") or not meal.get("calories") or not meal.get("nutrients"):
                raise HTTPException(
                    status_code=400,
                    detail="Each meal must include 'type', 'calories', and 'nutrients' (e.g., {'carbs': x, 'protein': y, 'fats': z})"
                )
        
        # Prepare Firestore document data
        day_doc_ref = user_doc_ref.document(day_name)
        day_plan_data = {
            "dailyCalorieTarget": daily_calorie_target,
            "macronutrientSplit": macronutrient_split,
            "mealPlan": meal_plan,
            "lastUpdated": datetime.now().isoformat(),  # Timestamp for tracking updates
        }
        
        # Store the data
        day_doc_ref.set(day_plan_data)
    
    return JSONResponse(content={'status': 'success', 'message': 'Diet plan added successfully'})

