from fastapi import APIRouter, Request, Depends, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.models.fornecedor import Fornecedor
from app.models.company import Company
from app.models.tipo_material import TipoMaterial
from app.models.nota_fiscal import NotaFiscal
from app.models.boleto import Boleto
from app.routes.auth import get_current_user, has_permission
from app.services.storage import upload_file
from app.services.audit import log_action
from app.services.flash import toast_url
from app.templates_config import templates

router = APIRouter()


@router.get("/notas", response_class=HTMLResponse)
async def list_notas(
    request: Request,
    db: Session = Depends(get_db),
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
    fornecedor_id: str = Query(None),
    empresa_id: str = Query(None),
    tipo_material_id: str = Query(None),
    numero: str = Query(None),
    page: int = Query(1),
    per_page: int = Query(20),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    fid = int(fornecedor_id) if fornecedor_id else None
    eid = int(empresa_id) if empresa_id else None
    tid = int(tipo_material_id) if tipo_material_id else None

    query = db.query(NotaFiscal)

    if data_inicio:
        query = query.filter(NotaFiscal.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(NotaFiscal.data_emissao <= data_fim)
    if fid:
        query = query.filter(NotaFiscal.fornecedor_id == fid)
    if eid:
        query = query.filter(NotaFiscal.empresa_id == eid)
    if tid:
        query = query.filter(NotaFiscal.tipo_material_id == tid)
    if numero:
        query = query.filter(NotaFiscal.numero.ilike(f"%{numero}%"))

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    notas = query.order_by(NotaFiscal.data_emissao.desc()).offset((page - 1) * per_page).limit(per_page).all()
    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    empresas = db.query(Company).order_by(Company.name).all()
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()
    today = date.today()

    return templates.TemplateResponse(
        "notas/list.html",
        {
            "request": request,
            "notas": notas,
            "fornecedores": fornecedores,
            "empresas": empresas,
            "tipos": tipos,
            "user": user,
            "today": today,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
            "filters": {
                "data_inicio": data_inicio or "",
                "data_fim": data_fim or "",
                "fornecedor_id": fornecedor_id or "",
                "empresa_id": empresa_id or "",
                "tipo_material_id": tipo_material_id or "",
                "numero": numero or "",
            },
        },
    )


@router.get("/notas/new", response_class=HTMLResponse)
async def new_nota_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "create", db):
        return RedirectResponse(url="/notas", status_code=303)

    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    empresas = db.query(Company).order_by(Company.name).all()
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()

    return templates.TemplateResponse(
        "notas/form.html",
        {"request": request, "fornecedores": fornecedores, "empresas": empresas, "tipos": tipos, "edit_nota": None, "user": user},
    )


@router.post("/notas/new")
async def create_nota(
    request: Request,
    fornecedor_id: int = Form(...),
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
    if not has_permission(user, "fornecedores", "create", db):
        return RedirectResponse(url="/notas", status_code=303)

    anexo_path = None
    if anexo and anexo.filename:
        anexo_path = await upload_file(anexo, prefix="notas")

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
    log_action(db, user.id, "create", "nota_fiscal", nota.id, f"Nota fiscal {nota.numero} criada")
    return RedirectResponse(url=toast_url("/notas", f"Nota fiscal {numero} criada com sucesso"), status_code=303)


@router.get("/notas/{nota_id}", response_class=HTMLResponse)
async def view_nota(nota_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "read", db):
        return RedirectResponse(url="/notas", status_code=303)

    nota = db.query(NotaFiscal).get(nota_id)
    if not nota:
        return RedirectResponse(url="/notas", status_code=303)

    boletos = db.query(Boleto).filter(Boleto.nota_fiscal_id == nota_id).order_by(Boleto.data_vencimento).all()
    today = date.today()

    return templates.TemplateResponse(
        "notas/detail.html",
        {"request": request, "nota": nota, "boletos": boletos, "today": today, "user": user},
    )


@router.get("/notas/{nota_id}/edit", response_class=HTMLResponse)
async def edit_nota_form(nota_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "edit", db):
        return RedirectResponse(url="/notas", status_code=303)

    nota = db.query(NotaFiscal).get(nota_id)
    if not nota:
        return RedirectResponse(url="/notas", status_code=303)

    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    empresas = db.query(Company).order_by(Company.name).all()
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()

    return templates.TemplateResponse(
        "notas/form.html",
        {"request": request, "fornecedores": fornecedores, "empresas": empresas, "tipos": tipos, "edit_nota": nota, "user": user},
    )


@router.post("/notas/{nota_id}/edit")
async def update_nota(
    nota_id: int,
    request: Request,
    fornecedor_id: int = Form(...),
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
        return RedirectResponse(url="/notas", status_code=303)

    nota = db.query(NotaFiscal).get(nota_id)
    if nota:
        nota.fornecedor_id = fornecedor_id
        nota.fornecedor_cnpj = fornecedor_cnpj
        nota.empresa_id = empresa_id
        nota.empresa_cnpj = empresa_cnpj
        nota.tipo_material_id = tipo_material_id
        nota.numero = numero
        nota.descricao = descricao
        nota.data_emissao = data_emissao
        nota.valor_total = valor_total

        if anexo and anexo.filename:
            nota.anexo = await upload_file(anexo, prefix="notas")

        db.commit()
        log_action(db, user.id, "update", "nota_fiscal", nota.id, f"Nota fiscal #{nota.id} atualizada")
    return RedirectResponse(url=toast_url(f"/notas/{nota_id}", f"Nota fiscal {nota.numero} atualizada com sucesso"), status_code=303)


@router.post("/notas/{nota_id}/delete")
async def delete_nota(nota_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "fornecedores", "delete", db):
        return RedirectResponse(url="/notas", status_code=303)

    nota = db.query(NotaFiscal).get(nota_id)
    if nota:
        log_action(db, user.id, "delete", "nota_fiscal", nota.id, f"Nota fiscal {nota.numero} excluída")
        db.delete(nota)
        db.commit()
    return RedirectResponse(url=toast_url("/notas", "Nota fiscal excluída com sucesso"), status_code=303)


@router.get("/notas/{nota_id}/boletos/new", response_class=HTMLResponse)
async def new_boleto_from_nota_form(nota_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "create", db):
        return RedirectResponse(url="/notas", status_code=303)

    nota = db.query(NotaFiscal).get(nota_id)
    if not nota:
        return RedirectResponse(url="/notas", status_code=303)

    return templates.TemplateResponse(
        "notas/boleto_form.html",
        {"request": request, "nota": nota, "user": user},
    )


@router.post("/notas/{nota_id}/boletos/new")
async def create_boleto_from_nota(
    nota_id: int,
    request: Request,
    descricao: str = Form(""),
    valor: float = Form(...),
    data_vencimento: date = Form(...),
    anexo: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "create", db):
        return RedirectResponse(url="/notas", status_code=303)

    nota = db.query(NotaFiscal).get(nota_id)
    if not nota:
        return RedirectResponse(url="/notas", status_code=303)

    anexo_path = None
    if anexo and anexo.filename:
        anexo_path = await upload_file(anexo, prefix="boletos")

    boleto = Boleto(
        numero_nota=nota.numero,
        descricao=descricao,
        valor=valor,
        data_emissao=nota.data_emissao,
        data_vencimento=data_vencimento,
        company_id=nota.empresa_id,
        nota_fiscal_id=nota_id,
        anexo=anexo_path,
        status="atrasado" if data_vencimento < date.today() else "pendente",
    )
    db.add(boleto)
    db.commit()
    log_action(db, user.id, "create", "boleto", boleto.id, f"Boleto {boleto.numero_nota} criado via nota fiscal")
    return RedirectResponse(url=toast_url(f"/notas/{nota_id}", "Boleto criado com sucesso"), status_code=303)


@router.get("/api/fornecedor/{fornecedor_id}/cnpjs")
async def get_fornecedor_cnpjs_api(fornecedor_id: int, db: Session = Depends(get_db)):
    from app.models.fornecedor import FornecedorCNPJ
    cnpjs = db.query(FornecedorCNPJ).filter(FornecedorCNPJ.fornecedor_id == fornecedor_id).all()
    return [{"id": c.id, "cnpj": c.cnpj} for c in cnpjs]


@router.get("/api/empresa/{empresa_id}/cnpj")
async def get_empresa_cnpj_api(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(Company).get(empresa_id)
    if empresa:
        return {"cnpj": empresa.cnpj}
    return {"cnpj": ""}
