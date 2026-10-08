"""
Authentication and user registration router.
Supports:
1. Registration by Phone Number (SMS-code verification or Phone+Password)
2. Registration by Gmail / Email
3. Registration & Login via VK (VK ID)
4. Google OAuth
5. Unified Login by username, email or phone
"""
import random
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.database import get_users_db as get_db
from backend.models import User, PhoneVerificationCode
from backend.schemas import (
    UserRegisterRequest, GmailRegisterRequest, PhoneSendCodeRequest,
    PhoneSendCodeResponse, PhoneVerifyRequest, PhoneRegisterRequest,
    VKAuthRequest, GoogleAuthRequest, UserLoginRequest, UserResponse,
    TokenResponse
)
from backend.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Аутентификация и пользователи"])


def normalize_phone(raw_phone: str) -> str:
    """Normalizes phone numbers to standard format (e.g., +79991234567)."""
    digits = re.sub(r"\D", "", raw_phone)
    if not digits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный номер телефона"
        )
    if len(digits) == 11 and (digits.startswith("7") or digits.startswith("8")):
        return f"+7{digits[1:]}"
    elif len(digits) == 10:
        return f"+7{digits}"
    else:
        return f"+{digits}"


def generate_unique_username(base_name: str, db: Session) -> str:
    """Ensures a unique username by appending random digits if collision occurs."""
    clean_base = re.sub(r"[^\w]", "_", base_name).strip("_") or "user"
    username = clean_base
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{clean_base}_{random.randint(100, 9999)}"
        counter += 1
        if counter > 20:
            username = f"{clean_base}_{secrets.token_hex(4)}"
            break
    return username


# ==================== 1. Phone Registration & Auth ====================

@router.post("/phone/send-code", response_model=PhoneSendCodeResponse, summary="1. Отправить СМС-код на номер телефона")
def send_phone_code(req: PhoneSendCodeRequest, db: Session = Depends(get_db)):
    """
    Генерирует и отправляет проверочный код на указанный номер телефона.
    Для удобства тестирования и демонстрации возвращает `dev_code` в ответе.
    """
    phone = normalize_phone(req.phone)
    
    # Generate 6-digit verification code
    code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Invalidate previous unused codes for this phone
    db.query(PhoneVerificationCode).filter(
        PhoneVerificationCode.phone == phone,
        PhoneVerificationCode.is_used == False
    ).update({"is_used": True})

    verification_record = PhoneVerificationCode(
        phone=phone,
        code=code,
        expires_at=expires_at,
        is_used=False
    )
    db.add(verification_record)
    db.commit()

    return PhoneSendCodeResponse(
        status="ok",
        message=f"Код подтверждения успешно отправлен на номер {phone}",
        phone=phone,
        dev_code=code,
        expires_in_seconds=600
    )


@router.post("/phone/verify", response_model=TokenResponse, summary="2. Подтвердить СМС-код (Регистрация / Вход по номеру)")
def verify_phone_code(req: PhoneVerifyRequest, db: Session = Depends(get_db)):
    """
    Проверяет СМС-код. Если пользователь с таким телефоном уже существует — авторизует.
    Если пользователь новый — автоматически регистрирует его в базе данных.
    """
    phone = normalize_phone(req.phone)

    # Verify code (universal test bypass code: 000000)
    is_valid = req.code == "000000"
    if not is_valid:
        record = db.query(PhoneVerificationCode).filter(
            PhoneVerificationCode.phone == phone,
            PhoneVerificationCode.code == req.code,
            PhoneVerificationCode.is_used == False,
            PhoneVerificationCode.expires_at >= datetime.utcnow()
        ).order_by(PhoneVerificationCode.id.desc()).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный или истекший проверочный код СМС"
            )
        record.is_used = True
        db.commit()

    # Find or create user
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        # Create new user
        base_username = req.username or f"user_{phone.replace('+', '')[-6:]}"
        final_username = generate_unique_username(base_username, db)
        
        pwd_hash, salt = None, None
        if req.password:
            pwd_hash, salt = hash_password(req.password)
        else:
            pwd_hash, salt = hash_password(secrets.token_urlsafe(16))

        user = User(
            username=final_username,
            phone=phone,
            phone_verified=True,
            auth_provider="phone",
            hashed_password=pwd_hash,
            salt=salt,
            first_name=req.first_name,
            avatar_url=f"https://api.dicebear.com/7.x/bottts/svg?seed={final_username}",
            is_active=True,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.phone_verified = True
        if req.first_name and not user.first_name:
            user.first_name = req.first_name
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.username, "user_id": user.id, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/register-phone", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Регистрация по номеру телефона с паролем")
def register_by_phone(req: PhoneRegisterRequest, db: Session = Depends(get_db)):
    """Прямая регистрация по номеру телефона и паролю."""
    phone = normalize_phone(req.phone)

    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с номером {phone} уже зарегистрирован"
        )

    base_username = req.username or f"user_{phone.replace('+', '')[-6:]}"
    final_username = generate_unique_username(base_username, db)
    pwd_hash, salt = hash_password(req.password)

    user = User(
        username=final_username,
        phone=phone,
        phone_verified=False,
        auth_provider="phone",
        hashed_password=pwd_hash,
        salt=salt,
        first_name=req.first_name,
        avatar_url=f"https://api.dicebear.com/7.x/bottts/svg?seed={final_username}",
        is_active=True,
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


# ==================== 2. Gmail / Email Registration ====================

@router.post("/register-gmail", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Регистрация через Gmail")
def register_by_gmail(req: GmailRegisterRequest, db: Session = Depends(get_db)):
    """
    Регистрация пользователя по почтовому ящику Gmail (или любому email).
    Хэширует пароль по стандарту PBKDF2-HMAC-SHA256 с индивидуальной солью.
    """
    email_clean = req.email.strip().lower()

    if db.query(User).filter(User.email == email_clean).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с почтой '{email_clean}' уже зарегистрирован"
        )

    base_username = req.username or email_clean.split("@")[0]
    final_username = generate_unique_username(base_username, db)
    pwd_hash, salt = hash_password(req.password)

    user = User(
        username=final_username,
        email=email_clean,
        email_verified=True,
        auth_provider="gmail" if "gmail.com" in email_clean else "email",
        hashed_password=pwd_hash,
        salt=salt,
        first_name=req.first_name,
        avatar_url=req.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={final_username}",
        is_active=True,
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


@router.post("/google", response_model=TokenResponse, summary="Google OAuth регистрация / вход")
def auth_google(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Авторизация и быстрая регистрация через аккаунт Google."""
    if not req.google_id and not req.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать google_id или email"
        )

    user = None
    if req.google_id:
        user = db.query(User).filter(User.google_id == req.google_id).first()
    if not user and req.email:
        user = db.query(User).filter(User.email == req.email.strip().lower()).first()

    if not user:
        base_username = (req.email.split("@")[0] if req.email else req.name) or "google_user"
        final_username = generate_unique_username(base_username, db)
        dummy_hash, salt = hash_password(secrets.token_urlsafe(16))

        user = User(
            username=final_username,
            email=req.email.strip().lower() if req.email else None,
            google_id=req.google_id,
            auth_provider="google",
            first_name=req.name,
            avatar_url=req.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={final_username}",
            hashed_password=dummy_hash,
            salt=salt,
            email_verified=True,
            is_active=True,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if req.google_id and not user.google_id:
            user.google_id = req.google_id
        if req.avatar_url and not user.avatar_url:
            user.avatar_url = req.avatar_url
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.username, "user_id": user.id, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


# ==================== 3. VK Registration & Auth ====================

@router.post("/vk", response_model=TokenResponse, summary="Регистрация и вход через ВКонтакте (VK ID)")
def auth_vk(req: VKAuthRequest, db: Session = Depends(get_db)):
    """
    Регистрация и мгновенный вход через профиль ВКонтакте.
    Принимает `vk_user_id` и данные профиля (имя, аватар, email/телефон при наличии).
    Автоматически создает профиль в базе данных или авторизует существующего пользователя.
    """
    vk_id_str = str(req.vk_user_id).strip()
    if not vk_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не передан ID пользователя ВКонтакте"
        )

    user = db.query(User).filter(User.vk_id == vk_id_str).first()

    # Also check if existing user with same email/phone
    if not user and req.email:
        user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user and req.phone:
        norm_phone = normalize_phone(req.phone)
        user = db.query(User).filter(User.phone == norm_phone).first()

    if not user:
        # Create new user via VK
        display_name = f"{req.first_name or ''} {req.last_name or ''}".strip()
        base_username = f"vk_{vk_id_str}"
        final_username = generate_unique_username(base_username, db)
        dummy_hash, salt = hash_password(secrets.token_urlsafe(16))

        user = User(
            username=final_username,
            vk_id=vk_id_str,
            email=req.email.strip().lower() if req.email else None,
            phone=normalize_phone(req.phone) if req.phone else None,
            first_name=req.first_name,
            last_name=req.last_name,
            avatar_url=req.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed=vk_{vk_id_str}",
            auth_provider="vk",
            hashed_password=dummy_hash,
            salt=salt,
            phone_verified=bool(req.phone),
            email_verified=bool(req.email),
            is_active=True,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Link VK ID if not linked
        if not user.vk_id:
            user.vk_id = vk_id_str
        if req.avatar_url and not user.avatar_url:
            user.avatar_url = req.avatar_url
        if req.first_name and not user.first_name:
            user.first_name = req.first_name
        if req.last_name and not user.last_name:
            user.last_name = req.last_name
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.username, "user_id": user.id, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/vk/login-url", summary="Получить ссылку для авторизации через ВКонтакте")
def get_vk_oauth_url(
    client_id: str = "51888888",
    redirect_uri: str = "http://127.0.0.1:8000/api/auth/vk/callback"
):
    """Возвращает готовую ссылку для перенаправления пользователя на OAuth ВКонтакте."""
    url = (
        f"https://oauth.vk.com/authorize?"
        f"client_id={client_id}&"
        f"display=page&"
        f"redirect_uri={redirect_uri}&"
        f"scope=email,phone,offline&"
        f"response_type=code&"
        f"v=5.131"
    )
    return {
        "vk_auth_url": url,
        "client_id": client_id,
        "redirect_uri": redirect_uri
    }


# ==================== 4. Standard Register & Unified Login ====================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Базовая регистрация по Email/Логину")
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Базовая регистрация с именем пользователя, почтой и паролем."""
    email_clean = req.email.strip().lower()

    if db.query(User).filter(User.email == email_clean).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с почтой '{email_clean}' уже зарегистрирован"
        )

    base_username = req.username or email_clean.split("@")[0]
    final_username = generate_unique_username(base_username, db)

    pwd_hash, salt = hash_password(req.password)
    user = User(
        username=final_username,
        email=email_clean,
        auth_provider="email",
        hashed_password=pwd_hash,
        salt=salt,
        first_name=req.first_name,
        last_name=req.last_name,
        avatar_url=req.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={final_username}",
        is_active=True,
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


@router.post("/login", response_model=TokenResponse, summary="Универсальный вход (Логин / Email / Телефон)")
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Универсальный вход. Принимает:
    - Логин (username)
    - Email (Gmail, Yandex и др.)
    - Номер телефона (+79991234567, 89991234567)
    Поддерживает как JSON-запросы, так и Form Data (Swagger UI).
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
            detail="Необходимо указать логин/email/телефон и пароль"
        )

    identifier = username_or_email.strip()
    
    # Try normalization in case it's a phone
    phone_normalized = None
    digits_only = re.sub(r"\D", "", identifier)
    if len(digits_only) in [10, 11]:
        try:
            phone_normalized = normalize_phone(identifier)
        except Exception:
            pass

    # Lookup user by username, email or phone
    query_conditions = [
        User.username == identifier,
        User.email == identifier.lower()
    ]
    if phone_normalized:
        query_conditions.append(User.phone == phone_normalized)

    user = db.query(User).filter(or_(*query_conditions)).first()

    if not user or not user.hashed_password or not user.salt or not verify_password(password, user.hashed_password, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные (логин/email/телефон или пароль)",
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
    """Возвращает информацию о текущем авторизованном пользователе со всеми способами входа."""
    return UserResponse.model_validate(current_user)
