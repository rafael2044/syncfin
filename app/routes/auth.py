from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import secrets

from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.permission import Permission
from app.templates_config import templates

router = APIRouter()
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.username == username).first()
    return user


def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuário ou senha inválidos"},
        )
    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


def _get_user_permissions(user: User, db: Session) -> set:
    role_perms = set()
    if user.role:
        for p in user.role.permissions:
            role_perms.add(f"{p.resource}:{p.action}")

    extra_perms = set()
    for p in user.extra_permissions:
        extra_perms.add(f"{p.resource}:{p.action}")

    return role_perms | extra_perms


def has_permission(user: User, resource: str, action: str, db: Session) -> bool:
    if not user or not user.is_active:
        return False
    if user.role and user.role.name == "admin":
        return True
    perms = _get_user_permissions(user, db)
    return f"{resource}:{action}" in perms


def get_user_permissions_list(user: User, db: Session) -> list:
    return list(_get_user_permissions(user, db))


@router.get("/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@router.post("/auth/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse(
            "forgot_password.html",
            {"request": request, "error": "E-mail não encontrado no sistema"},
        )

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request, "success": True, "token": token},
    )


@router.get("/auth/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = ""):
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "reset_password.html", {"request": request, "token": token}
    )


@router.post("/auth/reset-password")
async def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if password != password_confirm:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "token": token, "error": "As senhas não coincidem"},
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "token": token, "error": "A senha deve ter pelo menos 6 caracteres"},
        )

    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "token": token, "error": "Token inválido"},
        )

    if user.reset_token_expires < datetime.utcnow():
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "token": token, "error": "Token expirado. Solicite um novo."},
        )

    user.hashed_password = pwd_context.hash(password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return RedirectResponse(url="/login?toast_msg=Senha+resetada+com+sucesso&toast_type=success", status_code=303)
