from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import User
from app.models.role import Role
from app.routes.auth import get_current_user, has_permission
from app.services.flash import toast_url
from app.templates_config import templates

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/users", response_class=HTMLResponse)
async def list_users(request: Request, db: Session = Depends(get_db), page: int = Query(1), per_page: int = Query(20)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "users", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    query = db.query(User)
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    users = query.order_by(User.username).offset((page - 1) * per_page).limit(per_page).all()
    roles = db.query(Role).all()
    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "users": users,
            "roles": roles,
            "user": user,
            "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages},
        },
    )


@router.get("/users/new", response_class=HTMLResponse)
async def new_user_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "users", "create", db):
        return RedirectResponse(url="/users", status_code=303)
    roles = db.query(Role).all()
    return templates.TemplateResponse(
        "users/form.html", {"request": request, "roles": roles, "edit_user": None, "user": user}
    )


@router.post("/users/new")
async def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(""),
    password: str = Form(...),
    role_id: int = Form(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "users", "create", db):
        return RedirectResponse(url="/users", status_code=303)

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "users/form.html",
            {"request": request, "roles": roles, "edit_user": None, "error": "Usuário já existe", "user": user},
        )

    new_user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=pwd_context.hash(password),
        role_id=role_id,
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url=toast_url("/users", f"Usuário {username} criado com sucesso"), status_code=303)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "users", "edit", db):
        return RedirectResponse(url="/users", status_code=303)
    edit_user = db.query(User).get(user_id)
    roles = db.query(Role).all()
    return templates.TemplateResponse(
        "users/form.html", {"request": request, "roles": roles, "edit_user": edit_user, "user": user}
    )


@router.post("/users/{user_id}/edit")
async def update_user(
    user_id: int,
    request: Request,
    email: str = Form(...),
    full_name: str = Form(""),
    role_id: int = Form(None),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "users", "edit", db):
        return RedirectResponse(url="/users", status_code=303)
    edit_user = db.query(User).get(user_id)
    if edit_user:
        edit_user.email = email
        edit_user.full_name = full_name
        edit_user.role_id = role_id
        edit_user.is_active = is_active
        db.commit()
    return RedirectResponse(url=toast_url("/users", "Usuário atualizado com sucesso"), status_code=303)


@router.post("/users/{user_id}/delete")
async def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "users", "delete", db):
        return RedirectResponse(url="/users", status_code=303)
    edit_user = db.query(User).get(user_id)
    if edit_user:
        db.delete(edit_user)
        db.commit()
    return RedirectResponse(url=toast_url("/users", "Usuário excluído com sucesso"), status_code=303)


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    request: Request,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(current_user, "users", "edit", db):
        return RedirectResponse(url="/users", status_code=303)

    target_user = db.query(User).get(user_id)
    if not target_user:
        return RedirectResponse(url=toast_url("/users", "Usuário não encontrado", "error"), status_code=303)

    if len(new_password) < 6:
        return RedirectResponse(url=toast_url("/users", "A senha deve ter pelo menos 6 caracteres", "error"), status_code=303)

    target_user.hashed_password = pwd_context.hash(new_password)
    target_user.reset_token = None
    target_user.reset_token_expires = None
    db.commit()
    return RedirectResponse(url=toast_url("/users", f"Senha de {target_user.username} resetada com sucesso"), status_code=303)
