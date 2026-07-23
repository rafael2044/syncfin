from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.role import Role
from app.models.user import User
from app.models.permission import Permission
from app.routes.auth import get_current_user, has_permission
from app.services.flash import toast_url
from app.templates_config import templates

router = APIRouter()

RESOURCES = [
    ("dashboard", "Dashboard"),
    ("fornecedores", "Fornecedores"),
    ("companies", "Empresas"),
    ("categories", "Tipos de Material"),
    ("boletos", "Boletos"),
    ("users", "Usuários"),
    ("reports", "Relatórios"),
    ("permissions", "Permissões"),
]

ACTIONS = [
    ("read", "Visualizar"),
    ("create", "Criar"),
    ("edit", "Editar"),
    ("delete", "Excluir"),
]


@router.get("/permissions/roles", response_class=HTMLResponse)
async def list_roles_permissions(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "permissions", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    roles = db.query(Role).order_by(Role.name).all()
    permissions = db.query(Permission).order_by(Permission.resource, Permission.action).all()

    return templates.TemplateResponse(
        "permissions/roles.html",
        {
            "request": request,
            "user": user,
            "roles": roles,
            "permissions": permissions,
            "resources": RESOURCES,
            "actions": ACTIONS,
        },
    )


@router.post("/permissions/roles/{role_id}")
async def update_role_permissions(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "permissions", "edit", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    role = db.query(Role).get(role_id)
    if not role:
        return RedirectResponse(url="/permissions/roles", status_code=303)

    form = await request.form()
    role.permissions.clear()

    for resource_key, _ in RESOURCES:
        for action_key, _ in ACTIONS:
            field = f"{resource_key}_{action_key}"
            if form.get(field):
                perm = db.query(Permission).filter(
                    Permission.resource == resource_key, Permission.action == action_key
                ).first()
                if perm:
                    role.permissions.append(perm)

    db.commit()
    return RedirectResponse(url=toast_url("/permissions/roles", f"Permissões da role \"{role.name}\" atualizadas"), status_code=303)


@router.get("/permissions/users", response_class=HTMLResponse)
async def list_users_permissions(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "permissions", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    users = db.query(User).order_by(User.username).all()
    permissions = db.query(Permission).order_by(Permission.resource, Permission.action).all()

    return templates.TemplateResponse(
        "permissions/users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "permissions": permissions,
            "resources": RESOURCES,
            "actions": ACTIONS,
        },
    )


@router.get("/permissions/users/{user_id}", response_class=HTMLResponse)
async def edit_user_permissions(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "permissions", "edit", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    edit_user = db.query(User).get(user_id)
    if not edit_user:
        return RedirectResponse(url="/permissions/users", status_code=303)

    permissions = db.query(Permission).order_by(Permission.resource, Permission.action).all()

    return templates.TemplateResponse(
        "permissions/user_edit.html",
        {
            "request": request,
            "user": user,
            "edit_user": edit_user,
            "permissions": permissions,
            "resources": RESOURCES,
            "actions": ACTIONS,
        },
    )


@router.post("/permissions/users/{user_id}")
async def update_user_permissions(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "permissions", "edit", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    edit_user = db.query(User).get(user_id)
    if not edit_user:
        return RedirectResponse(url="/permissions/users", status_code=303)

    form = await request.form()
    edit_user.extra_permissions.clear()

    for resource_key, _ in RESOURCES:
        for action_key, _ in ACTIONS:
            field = f"{resource_key}_{action_key}"
            if form.get(field):
                perm = db.query(Permission).filter(
                    Permission.resource == resource_key, Permission.action == action_key
                ).first()
                if perm:
                    edit_user.extra_permissions.append(perm)

    db.commit()
    return RedirectResponse(url=toast_url("/permissions/users", f"Permissões de \"{edit_user.username}\" atualizadas"), status_code=303)
