from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
from firebase_client import db
from routers.session.utils import verify_session_token
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler


MEAL_SCHEDULE = {
    "Breakfast",
    "Lunch",
    "Dinner",
    "Snacks"
}

router = APIRouter()

@router.post("/check_missing_meals")
async def check_missing_meals():
    now = datetime.now(timezone.utc)
    year = str(now.year)
    month = str(now.month).zfill(2)
    day = str(now.day).zfill(2)

    users = db.collection("users").stream()
    for user in users:
        user_id = user.id
        diet_log_ref = db.collection("users").document(user_id).collection("dietLog").document(year).collection(month).document(day)

        
        logged_meals = {meal.id for meal in diet_log_ref.collection("meals").stream()}

        
        missing_meals = [meal for meal in MEAL_SCHEDULE if meal not in logged_meals]

        for missing_meal in missing_meals:
            
            diet_log_ref.collection("meals").document(missing_meal).set({
                "meal_name": missing_meal,
                "category": missing_meal,
                "calories": 0,
                "nutrients": {"carbs": 0, "protein": 0, "fats": 0},
                "logged_at": datetime.now(timezone.utc),
            })

    return JSONResponse(content={"status": "success", "message": "Checked and logged missing meals for all users."})

@router.post("/logmeal")
async def log_meal(request: Request, token_data=Depends(verify_session_token)):
    user_id = token_data.get("uid")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: User ID not found")
    
    user_doc_ref = db.collection("users").document(user_id)
    body = await request.json()
    
    # Extract meal data from request
    meal_data = {
        "meal_name": body.get("meal_name"),
        "category": body.get("category"),  # Breakfast, Lunch, etc.
        "calories": body.get("calories"),
        "nutrients": body.get("nutrients"),  # { "carbs": 50, "protein": 20, "fats": 10 }
        "ingredients": body.get("ingredients", []),  # Optional list of ingredients
        "logged_at": datetime.now(timezone.utc),
    }
    
    # Get the current date details
    now = datetime.now(timezone.utc)
    year = str(now.year)
    month = str(now.month).zfill(2)  # Ensure two-digit format
    day = str(now.day).zfill(2)  # Ensure two-digit format
    
    # Firestore document path
    diet_log_ref = (
        user_doc_ref
        .collection("dietLog")
        .document(year)
        .collection(month)
        .document(day)
        .collection("meals")
        .document(meal_data["category"])  # Use category as document ID
    )
    
    # Add meal data under the corresponding day
    diet_log_ref.set(meal_data)
    
    return JSONResponse(content={'status': 'success', 'message': 'Meal logged successfully!'})

scheduler = BackgroundScheduler()
# scheduler.add_job(check_missing_meals, "cron", hour=23, minute=59)  # Run at 11:59 PM UTC daily
scheduler.start()
