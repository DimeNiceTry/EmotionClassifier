from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Optional
from ..services.dependencies import get_auth_service, get_user_service
from ..services.auth_service import AuthService
from ..services.user_service import UserService
from ..domain.models import User as UserDomain
from .models import Token, UserInfo, UserCreate

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=UserInfo)
async def register_user(
    username: str = Query(None),
    password: str = Query(None),
    email: str = Query(None),
    full_name: Optional[str] = Query(None),
    user_data: Optional[UserCreate] = None,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    # Если данные приходят из JSON тела запроса
    if user_data:
        username = user_data.username
        password = user_data.password
        email = user_data.email
        full_name = user_data.full_name
    
    # Проверяем, что необходимые поля заполнены
    if not username or not password or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username, password and email are required"
        )
    
    # Проверяем существование пользователя
    existing_user = await user_service.get_user_by_username(username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Создаем нового пользователя
    hashed_password = auth_service.get_password_hash(password)
    new_user = UserDomain(
        username=username,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name
    )
    
    created_user = await user_service.create_user(new_user)
    
    return UserInfo(
        username=created_user.username,
        email=created_user.email,
        full_name=created_user.full_name,
        disabled=created_user.disabled
    )


@router.get("/me", response_model=UserInfo)
async def read_users_me(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
):
    user = await auth_service.get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return UserInfo(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled
    )


# Функция для получения текущего пользователя
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
):
    user = await auth_service.get_current_user(token)
    if user is None or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user 