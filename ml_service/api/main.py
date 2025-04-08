from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth import router as auth_router
from .predictions import router as predictions_router
from .users import router as users_router
from ..database.init_db import init_db

# Инициализация базы данных
init_db()

app = FastAPI(
    title="ML Service API",
    description="API для взаимодействия с ML сервисом",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Включаем роутеры
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(predictions_router, prefix="/predictions", tags=["predictions"])
app.include_router(users_router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Welcome to ML Service API"} 