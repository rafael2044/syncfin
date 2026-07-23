from fastapi import APIRouter, Request, Depends, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.models.fornecedor import Fornecedor, FornecedorCNPJ
from app.models.nota_fiscal import NotaFiscal
from app.models.boleto import Boleto
from app.routes.auth import get_current_user, has_permission
from app.services.storage import upload_file
from app.services.audit import log_action
from app.services.flash import toast_url
from app.templates_config import templates

router = APIRouter()


@router.get("/fornecedores", response_class=HTMLResponse)
async def list_fornecedores(request: Request, db: Session = Depends(get_db), page: int = Query(1), per_page: int = Query(20)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    query = db.query(Fornecedor)
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    fornecedores = query.order_by(Fornecedor.name).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse(
        "fornecedores/list.html",
        {
            "request": request,
            "fornecedores": fornecedores,
            "user": user,
            "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages},
        },
    )


@router.get("/fornecedores/new", response_class=HTMLResponse)
async def new_fornecedor_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "create", db):
        return RedirectResponse(url="/fornecedores", status_code=303)
    return templates.TemplateResponse(
        "fornecedores/form.html", {"request": request, "edit_fornecedor": None, "user": user}
    )


@router.post("/fornecedores/new")
async def create_fornecedor(
    request: Request,
    name: str = Form(...),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    cnpjs: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "create", db):
        return RedirectResponse(url="/fornecedores", status_code=303)

    fornecedor = Fornecedor(name=name, address=address, phone=phone, email=email)
    db.add(fornecedor)
    db.flush()

    cnpj_list = [c.strip() for c in cnpjs.split(",") if c.strip()]
    for cnpj in cnpj_list:
        db.add(FornecedorCNPJ(fornecedor_id=fornecedor.id, cnpj=cnpj))

    db.commit()
    log_action(db, user.id, "create", "fornecedor", fornecedor.id, f"Fornecedor {fornecedor.name} criado")
    return RedirectResponse(url=toast_url("/fornecedores", f"Fornecedor {name} criado com sucesso"), status_code=303)


@router.get("/fornecedores/{fornecedor_id}", response_class=HTMLResponse)
async def view_fornecedor(fornecedor_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "read", db):
        return RedirectResponse(url="/fornecedores", status_code=303)

    fornecedor = db.query(Fornecedor).get(fornecedor_id)
    if not fornecedor:
        return RedirectResponse(url="/fornecedores", status_code=303)

    notas = db.query(NotaFiscal).filter(NotaFiscal.fornecedor_id == fornecedor_id).order_by(NotaFiscal.data_emissao.desc()).all()

    return templates.TemplateResponse(
        "fornecedores/detail.html",
        {"request": request, "fornecedor": fornecedor, "notas": notas, "user": user},
    )


@router.get("/fornecedores/{fornecedor_id}/edit", response_class=HTMLResponse)
async def edit_fornecedor_form(fornecedor_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "edit", db):
        return RedirectResponse(url="/fornecedores", status_code=303)
    fornecedor = db.query(Fornecedor).get(fornecedor_id)
    if not fornecedor:
        return RedirectResponse(url="/fornecedores", status_code=303)
    return templates.TemplateResponse(
        "fornecedores/form.html", {"request": request, "edit_fornecedor": fornecedor, "user": user}
    )


@router.post("/fornecedores/{fornecedor_id}/edit")
async def update_fornecedor(
    fornecedor_id: int,
    request: Request,
    name: str = Form(...),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    cnpjs: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "edit", db):
        return RedirectResponse(url="/fornecedores", status_code=303)
    fornecedor = db.query(Fornecedor).get(fornecedor_id)
    if fornecedor:
        fornecedor.name = name
        fornecedor.address = address
        fornecedor.phone = phone
        fornecedor.email = email

        existing_cnpjs = {c.cnpj for c in fornecedor.cnpjs}
        new_cnpjs = {c.strip() for c in cnpjs.split(",") if c.strip()}

        for cnpj in existing_cnpjs - new_cnpjs:
            cnpj_obj = db.query(FornecedorCNPJ).filter(FornecedorCNPJ.fornecedor_id == fornecedor_id, FornecedorCNPJ.cnpj == cnpj).first()
            if cnpj_obj:
                db.delete(cnpj_obj)

        for cnpj in new_cnpjs - existing_cnpjs:
            db.add(FornecedorCNPJ(fornecedor_id=fornecedor_id, cnpj=cnpj))

        db.commit()
        log_action(db, user.id, "update", "fornecedor", fornecedor.id, f"Fornecedor {fornecedor.name} atualizado")
    return RedirectResponse(url=toast_url(f"/fornecedores/{fornecedor_id}", "Fornecedor atualizado com sucesso"), status_code=303)


@router.post("/fornecedores/{fornecedor_id}/delete")
async def delete_fornecedor(fornecedor_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "delete", db):
        return RedirectResponse(url="/fornecedores", status_code=303)
    fornecedor = db.query(Fornecedor).get(fornecedor_id)
    if fornecedor:
        log_action(db, user.id, "delete", "fornecedor", fornecedor.id, f"Fornecedor {fornecedor.name} excluído")
        db.delete(fornecedor)
        db.commit()
    return RedirectResponse(url=toast_url("/fornecedores", "Fornecedor excluído com sucesso"), status_code=303)


@router.get("/fornecedores/{fornecedor_id}/notas/new", response_class=HTMLResponse)
async def new_nota_from_fornecedor_form(fornecedor_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "edit", db):
        return RedirectResponse(url="/fornecedores", status_code=303)

    fornecedor = db.query(Fornecedor).get(fornecedor_id)
    if not fornecedor:
        return RedirectResponse(url="/fornecedores", status_code=303)

    from app.models.tipo_material import TipoMaterial
    from app.models.company import Company
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()
    empresas = db.query(Company).order_by(Company.name).all()

    return templates.TemplateResponse(
        "fornecedores/nota_form.html",
        {"request": request, "fornecedor": fornecedor, "tipos": tipos, "empresas": empresas, "edit_nota": None, "user": user},
    )


@router.post("/fornecedores/{fornecedor_id}/notas/new")
async def create_nota_from_fornecedor(
    fornecedor_id: int,
    request: Request,
    fornecedor_cnpj: str = Form(...),
    empresa_id: int = Form(...),
    empresa_cnpj: str = Form(...),
    tipo_material_id: int = Form(...),
    numero: str = Form(...),
    descricao: str = Form(""),
    data_emissao: date = Form(...),
    valor_total: float = Form(...),
    anexo: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "edit", db):
        return RedirectResponse(url="/fornecedores", status_code=303)

    fornecedor = db.query(Fornecedor).get(fornecedor_id)
    if not fornecedor:
        return RedirectResponse(url="/fornecedores", status_code=303)

    anexo_path = None
    if anexo and anexo.filename:
        anexo_path = await upload_file(anexo, prefix="notas")

    from app.models.nota_fiscal import NotaFiscal
    nota = NotaFiscal(
        fornecedor_id=fornecedor_id,
        fornecedor_cnpj=fornecedor_cnpj,
        empresa_id=empresa_id,
        empresa_cnpj=empresa_cnpj,
        tipo_material_id=tipo_material_id,
        numero=numero,
        descricao=descricao,
        data_emissao=data_emissao,
        valor_total=valor_total,
        anexo=anexo_path,
    )
    db.add(nota)
    db.commit()
    log_action(db, user.id, "create", "nota_fiscal", nota.id, f"Nota fiscal {nota.numero} criada via fornecedor")
    return RedirectResponse(url=toast_url(f"/fornecedores/{fornecedor_id}", f"Nota fiscal {numero} criada com sucesso"), status_code=303)


@router.get("/api/fornecedor/{fornecedor_id}/cnpjs")
async def get_fornecedor_cnpjs(fornecedor_id: int, db: Session = Depends(get_db)):
    cnpjs = db.query(FornecedorCNPJ).filter(FornecedorCNPJ.fornecedor_id == fornecedor_id).all()
    return [{"id": c.id, "cnpj": c.cnpj} for c in cnpjs]
