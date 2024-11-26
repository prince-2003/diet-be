from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routers.ai_adjustment.route import router as airouter
from routers.logmeal.route import router as log_mealrouter
from routers.session.route import router as sessionrouter
from routers.user.route import router as userrouter
from constants import SERVER_URL, PORT, ENV
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/')
async def root():
    return {"message": "Server is running"}

app.include_router(airouter, tags=["aiadjustment"])
app.include_router(log_mealrouter, tags=["logmeal"])
app.include_router(sessionrouter, tags=["session"])
app.include_router(userrouter, tags=["user"])


if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_URL, port=8900, reload=(ENV == "dev"))
