"""
Маршруты для работы с пользователями.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.users import User

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Получить данные текущего пользователя.
    """
    return current_user 