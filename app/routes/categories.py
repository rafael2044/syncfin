from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.routes.auth import get_current_user, has_permission
from app.templates_config import templates

router = APIRouter()


@router.get("/categories", response_class=HTMLResponse)
async def list_categories(request: Request, db: Session = Depends(get_db), page: int = Query(1), per_page: int = Query(20)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    query = db.query(Category)
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    categories = query.order_by(Category.name).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse(
        "categories/list.html",
        {
            "request": request,
            "categories": categories,
            "user": user,
            "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages},
        },
    )


@router.get("/categories/new", response_class=HTMLResponse)
async def new_category_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "create", db):
        return RedirectResponse(url="/categories", status_code=303)
    return templates.TemplateResponse(
        "categories/form.html", {"request": request, "edit_category": None, "user": user}
    )


@router.post("/categories/new")
async def create_category(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "create", db):
        return RedirectResponse(url="/categories", status_code=303)

    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        return templates.TemplateResponse(
            "categories/form.html",
            {"request": request, "edit_category": None, "error": "Categoria já existe", "user": user},
        )

    category = Category(name=name)
    db.add(category)
    db.commit()
    return RedirectResponse(url="/categories", status_code=303)


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def edit_category_form(category_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "edit", db):
        return RedirectResponse(url="/categories", status_code=303)
    category = db.query(Category).get(category_id)
    return templates.TemplateResponse(
        "categories/form.html", {"request": request, "edit_category": category, "user": user}
    )


@router.post("/categories/{category_id}/edit")
async def update_category(
    category_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "edit", db):
        return RedirectResponse(url="/categories", status_code=303)

    category = db.query(Category).get(category_id)
    if category:
        existing = db.query(Category).filter(Category.name == name, Category.id != category_id).first()
        if existing:
            return templates.TemplateResponse(
                "categories/form.html",
                {"request": request, "edit_category": category, "error": "Categoria já existe", "user": user},
            )
        category.name = name
        db.commit()
    return RedirectResponse(url="/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
async def delete_category(category_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "delete", db):
        return RedirectResponse(url="/categories", status_code=303)
    category = db.query(Category).get(category_id)
    if category:
        db.delete(category)
        db.commit()
    return RedirectResponse(url="/categories", status_code=303)
