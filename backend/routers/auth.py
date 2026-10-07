"""
Authentication and user registration router.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
from backend.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Аутентификация и пользователи"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Регистрация нового пользователя")
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Регистрирует нового пользователя с защищенным хэшированием пароля (PBKDF2-HMAC-SHA256).
    Сразу возвращает JWT-токен для автоматического входа.
    """
    # Check if username or email already exists
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с именем '{req.username}' уже существует"
        )
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с почтой '{req.email}' уже зарегистрирован"
        )

    pwd_hash, salt = hash_password(req.password)
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=pwd_hash,
        salt=salt,
        avatar_url=req.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={req.username}",
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "user_id": user.id, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse, summary="Авторизация (JSON или Form Data)")
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Авторизация пользователя. Принимает как JSON body, так и Form Data (для Swagger Docs).
    Проверяет пароль с защитой от атак по времени (timing attacks).
    """
    username_or_email = None
    password = None

    # Check content type
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            username_or_email = body.get("username_or_email") or body.get("username")
            password = body.get("password")
        except Exception:
            pass
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        username_or_email = form.get("username")
        password = form.get("password")

    if not username_or_email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать логин/email и пароль"
        )

    user = db.query(User).filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not verify_password(password, user.hashed_password, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя/email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован"
        )

    token = create_access_token({"sub": user.username, "user_id": user.id, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse, summary="Профиль текущего пользователя")
def get_me(current_user: User = Depends(get_current_user)):
    """Возвращает информацию о текущем авторизованном пользователе."""
    return UserResponse.model_validate(current_user)
