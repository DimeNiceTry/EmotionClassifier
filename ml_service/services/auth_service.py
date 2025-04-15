"""
Сервис для аутентификации и авторизации пользователей.
"""
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from ..domain.models import User
from ..repositories.interfaces import UserRepository


class AuthService:
    def __init__(
        self, 
        user_repository: UserRepository,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30
    ):
        self.user_repository = user_repository
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверяет соответствие пароля его хэшу.
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """
        Создает хэш пароля.
        """
        return self.pwd_context.hash(password)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Аутентифицирует пользователя.
        """
        user = await self.user_repository.get_by_username(username)
        if not user:
            return None
            
        # Проверяем, что у пользователя установлен пароль и он верный
        if not hasattr(user, 'hashed_password') or not user.hashed_password:
            return None
            
        if not self.verify_password(password, user.hashed_password):
            return None
            
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Создает JWT токен.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """
        Получает текущего пользователя по токену.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username = payload.get("sub")
            if username is None:
                return None
        except JWTError:
            return None
        
        user = await self.user_repository.get_by_username(username)
        return user 