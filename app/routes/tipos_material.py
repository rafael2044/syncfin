from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tipo_material import TipoMaterial
from app.routes.auth import get_current_user, has_permission
from app.services.flash import toast_url
from app.templates_config import templates

router = APIRouter()


@router.get("/tipos-material", response_class=HTMLResponse)
async def list_tipos_material(request: Request, db: Session = Depends(get_db), page: int = Query(1), per_page: int = Query(20)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    query = db.query(TipoMaterial)
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    tipos = query.order_by(TipoMaterial.name).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse(
        "tipos_material/list.html",
        {
            "request": request,
            "tipos": tipos,
            "user": user,
            "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages},
        },
    )


@router.get("/tipos-material/new", response_class=HTMLResponse)
async def new_tipo_material_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "create", db):
        return RedirectResponse(url="/tipos-material", status_code=303)
    return templates.TemplateResponse(
        "tipos_material/form.html", {"request": request, "edit_tipo": None, "user": user}
    )


@router.post("/tipos-material/new")
async def create_tipo_material(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "create", db):
        return RedirectResponse(url="/tipos-material", status_code=303)

    existing = db.query(TipoMaterial).filter(TipoMaterial.name == name).first()
    if existing:
        return templates.TemplateResponse(
            "tipos_material/form.html",
            {"request": request, "edit_tipo": None, "error": "Tipo de material já existe", "user": user},
        )

    tipo = TipoMaterial(name=name)
    db.add(tipo)
    db.commit()
    return RedirectResponse(url=toast_url("/tipos-material", f"Tipo de material \"{name}\" criado com sucesso"), status_code=303)


@router.get("/tipos-material/{tipo_id}/edit", response_class=HTMLResponse)
async def edit_tipo_material_form(tipo_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "edit", db):
        return RedirectResponse(url="/tipos-material", status_code=303)
    tipo = db.query(TipoMaterial).get(tipo_id)
    return templates.TemplateResponse(
        "tipos_material/form.html", {"request": request, "edit_tipo": tipo, "user": user}
    )


@router.post("/tipos-material/{tipo_id}/edit")
async def update_tipo_material(
    tipo_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "edit", db):
        return RedirectResponse(url="/tipos-material", status_code=303)

    tipo = db.query(TipoMaterial).get(tipo_id)
    if tipo:
        existing = db.query(TipoMaterial).filter(TipoMaterial.name == name, TipoMaterial.id != tipo_id).first()
        if existing:
            return templates.TemplateResponse(
                "tipos_material/form.html",
                {"request": request, "edit_tipo": tipo, "error": "Tipo de material já existe", "user": user},
            )
        tipo.name = name
        db.commit()
    return RedirectResponse(url=toast_url("/tipos-material", "Tipo de material atualizado com sucesso"), status_code=303)


@router.post("/tipos-material/{tipo_id}/delete")
async def delete_tipo_material(tipo_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "categories", "delete", db):
        return RedirectResponse(url="/tipos-material", status_code=303)
    tipo = db.query(TipoMaterial).get(tipo_id)
    if tipo:
        db.delete(tipo)
        db.commit()
    return RedirectResponse(url=toast_url("/tipos-material", "Tipo de material excluído com sucesso"), status_code=303)
