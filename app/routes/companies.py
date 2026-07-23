from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.routes.auth import get_current_user, has_permission
from app.services.audit import log_action
from app.services.flash import toast_url
from app.templates_config import templates

router = APIRouter()


@router.get("/companies", response_class=HTMLResponse)
async def list_companies(request: Request, db: Session = Depends(get_db), page: int = Query(1), per_page: int = Query(20)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "companies", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    query = db.query(Company)
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    companies = query.order_by(Company.name).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse(
        "companies/list.html",
        {
            "request": request,
            "companies": companies,
            "user": user,
            "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages},
        },
    )


@router.get("/companies/new", response_class=HTMLResponse)
async def new_company_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "companies", "create", db):
        return RedirectResponse(url="/companies", status_code=303)
    return templates.TemplateResponse(
        "companies/form.html", {"request": request, "edit_company": None, "user": user}
    )


@router.post("/companies/new")
async def create_company(
    request: Request,
    name: str = Form(...),
    cnpj: str = Form(...),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "companies", "create", db):
        return RedirectResponse(url="/companies", status_code=303)

    company = Company(name=name, cnpj=cnpj, address=address, phone=phone, email=email)
    db.add(company)
    db.commit()
    log_action(db, user.id, "create", "company", company.id, f"Empresa {company.name} criada")
    return RedirectResponse(url=toast_url("/companies", f"Empresa {name} criada com sucesso"), status_code=303)


@router.get("/companies/{company_id}", response_class=HTMLResponse)
async def view_company(company_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "companies", "read", db):
        return RedirectResponse(url="/companies", status_code=303)

    company = db.query(Company).get(company_id)
    if not company:
        return RedirectResponse(url="/companies", status_code=303)

    from app.models.nota_fiscal import NotaFiscal
    notas = db.query(NotaFiscal).filter(NotaFiscal.empresa_id == company_id).order_by(NotaFiscal.data_emissao.desc()).all()

    return templates.TemplateResponse(
        "companies/detail.html",
        {"request": request, "company": company, "notas": notas, "user": user},
    )


@router.get("/companies/{company_id}/edit", response_class=HTMLResponse)
async def edit_company_form(company_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "companies", "edit", db):
        return RedirectResponse(url="/companies", status_code=303)
    company = db.query(Company).get(company_id)
    return templates.TemplateResponse(
        "companies/form.html", {"request": request, "edit_company": company, "user": user}
    )


@router.post("/companies/{company_id}/edit")
async def update_company(
    company_id: int,
    request: Request,
    name: str = Form(...),
    cnpj: str = Form(...),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "companies", "edit", db):
        return RedirectResponse(url="/companies", status_code=303)
    company = db.query(Company).get(company_id)
    if company:
        company.name = name
        company.cnpj = cnpj
        company.address = address
        company.phone = phone
        company.email = email
        db.commit()
        log_action(db, user.id, "update", "company", company.id, f"Empresa {company.name} atualizada")
    return RedirectResponse(url=toast_url(f"/companies/{company_id}", "Empresa atualizada com sucesso"), status_code=303)


@router.post("/companies/{company_id}/delete")
async def delete_company(company_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "companies", "delete", db):
        return RedirectResponse(url="/companies", status_code=303)
    company = db.query(Company).get(company_id)
    if company:
        log_action(db, user.id, "delete", "company", company.id, f"Empresa {company.name} excluída")
        db.delete(company)
        db.commit()
    return RedirectResponse(url=toast_url("/companies", "Empresa excluída com sucesso"), status_code=303)
