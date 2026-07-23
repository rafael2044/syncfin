from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.database import get_db
from app.models.boleto import Boleto
from app.models.company import Company
from app.models.fornecedor import Fornecedor
from app.models.tipo_material import TipoMaterial
from app.models.nota_fiscal import NotaFiscal
from app.routes.auth import get_current_user, has_permission
from app.templates_config import templates

router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "reports", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        "reports/index.html",
        {"request": request, "user": user},
    )


@router.get("/reports/boletos", response_class=HTMLResponse)
async def reports_boletos_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "reports", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    companies = db.query(Company).all()
    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()

    return templates.TemplateResponse(
        "reports/boletos.html",
        {"request": request, "companies": companies, "fornecedores": fornecedores, "tipos": tipos, "user": user},
    )


@router.get("/reports/boletos/data", response_class=HTMLResponse)
async def reports_boletos_data(
    request: Request,
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
    tipo_material_id: str = Query(None),
    fornecedor_id: str = Query(None),
    empresa_id: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "reports", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    tid = int(tipo_material_id) if tipo_material_id else None
    fid = int(fornecedor_id) if fornecedor_id else None
    eid = int(empresa_id) if empresa_id else None

    query = db.query(Boleto)

    today = date.today()
    if data_inicio:
        query = query.filter(Boleto.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(Boleto.data_vencimento <= data_fim)
    if tid:
        query = query.join(NotaFiscal, Boleto.nota_fiscal_id == NotaFiscal.id).filter(NotaFiscal.tipo_material_id == tid)
    if fid:
        query = query.join(NotaFiscal, Boleto.nota_fiscal_id == NotaFiscal.id).filter(NotaFiscal.fornecedor_id == fid)
    if eid:
        query = query.filter(Boleto.company_id == eid)
    if status:
        query = query.filter(Boleto.status == status)

    boletos = query.order_by(Boleto.data_vencimento).all()

    total_valor = sum(b.valor for b in boletos)
    total_pago = sum(b.valor for b in boletos if b.status == "pago")
    total_pendente = sum(b.valor for b in boletos if b.status == "pendente")
    total_atrasado = sum(b.valor for b in boletos if b.status == "atrasado")

    companies = db.query(Company).all()
    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()

    return templates.TemplateResponse(
        "reports/boletos.html",
        {
            "request": request,
            "companies": companies,
            "fornecedores": fornecedores,
            "tipos": tipos,
            "boletos": boletos,
            "total_valor": total_valor,
            "total_pago": total_pago,
            "total_pendente": total_pendente,
            "total_atrasado": total_atrasado,
            "filters": {
                "data_inicio": data_inicio or "",
                "data_fim": data_fim or "",
                "tipo_material_id": tipo_material_id or "",
                "fornecedor_id": fornecedor_id or "",
                "empresa_id": empresa_id or "",
                "status": status or "",
            },
            "today": today,
            "user": user,
        },
    )


@router.get("/reports/notas", response_class=HTMLResponse)
async def reports_notas_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "reports", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    companies = db.query(Company).all()
    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()

    return templates.TemplateResponse(
        "reports/notas.html",
        {"request": request, "companies": companies, "fornecedores": fornecedores, "tipos": tipos, "user": user},
    )


@router.get("/reports/notas/data", response_class=HTMLResponse)
async def reports_notas_data(
    request: Request,
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
    tipo_material_id: str = Query(None),
    fornecedor_id: str = Query(None),
    empresa_id: str = Query(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "reports", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    tid = int(tipo_material_id) if tipo_material_id else None
    fid = int(fornecedor_id) if fornecedor_id else None
    eid = int(empresa_id) if empresa_id else None

    query = db.query(NotaFiscal)

    if data_inicio:
        query = query.filter(NotaFiscal.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(NotaFiscal.data_emissao <= data_fim)
    if tid:
        query = query.filter(NotaFiscal.tipo_material_id == tid)
    if fid:
        query = query.filter(NotaFiscal.fornecedor_id == fid)
    if eid:
        query = query.filter(NotaFiscal.empresa_id == eid)

    notas = query.order_by(NotaFiscal.data_emissao.desc()).all()

    total_valor = sum(n.valor_total for n in notas)
    total_boletos = sum(len(n.boletos) for n in notas)
    boletos_pagos = sum(1 for n in notas for b in n.boletos if b.pago)
    boletos_pendentes = total_boletos - boletos_pagos

    companies = db.query(Company).all()
    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    tipos = db.query(TipoMaterial).order_by(TipoMaterial.name).all()

    return templates.TemplateResponse(
        "reports/notas.html",
        {
            "request": request,
            "companies": companies,
            "fornecedores": fornecedores,
            "tipos": tipos,
            "notas": notas,
            "total_valor": total_valor,
            "total_boletos": total_boletos,
            "boletos_pagos": boletos_pagos,
            "boletos_pendentes": boletos_pendentes,
            "filters": {
                "data_inicio": data_inicio or "",
                "data_fim": data_fim or "",
                "tipo_material_id": tipo_material_id or "",
                "fornecedor_id": fornecedor_id or "",
                "empresa_id": empresa_id or "",
            },
            "user": user,
        },
    )
