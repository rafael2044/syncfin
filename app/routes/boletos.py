from fastapi import APIRouter, Request, Depends, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
import os

from app.database import get_db
from app.models.boleto import Boleto, BoletoPayment
from app.models.company import Company
from app.models.fornecedor import Fornecedor
from app.models.nota_fiscal import NotaFiscal
from app.routes.auth import get_current_user, has_permission
from app.services.storage import upload_file
from app.services.audit import log_action
from app.services.flash import toast_url
from app.templates_config import templates

router = APIRouter()


@router.get("/boletos", response_class=HTMLResponse)
async def list_boletos(
    request: Request,
    db: Session = Depends(get_db),
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
    status: str = Query(None),
    company_id: str = Query(None),
    fornecedor_id: str = Query(None),
    numero_nota: str = Query(None),
    page: int = Query(1),
    per_page: int = Query(20),
):
    cid = int(company_id) if company_id else None
    fid = int(fornecedor_id) if fornecedor_id else None
    return await _list_boletos(request, db, data_inicio, data_fim, status, cid, fid, numero_nota, page, per_page)


async def _list_boletos(request, db, data_inicio=None, data_fim=None, status=None, company_id=None, fornecedor_id=None, numero_nota=None, page=1, per_page=20):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    query = db.query(Boleto)

    if data_inicio:
        query = query.filter(Boleto.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(Boleto.data_vencimento <= data_fim)
    if status:
        query = query.filter(Boleto.status == status)
    if company_id:
        query = query.filter(Boleto.company_id == company_id)
    if fornecedor_id:
        query = query.join(NotaFiscal, Boleto.nota_fiscal_id == NotaFiscal.id).filter(NotaFiscal.fornecedor_id == fornecedor_id)
    if numero_nota:
        query = query.filter(Boleto.numero_nota.ilike(f"%{numero_nota}%"))

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    boletos = query.order_by(Boleto.data_vencimento).offset((page - 1) * per_page).limit(per_page).all()
    companies = db.query(Company).order_by(Company.name).all()
    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    today = date.today()

    return templates.TemplateResponse(
        "boletos/list.html",
        {
            "request": request,
            "boletos": boletos,
            "companies": companies,
            "fornecedores": fornecedores,
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
                "status": status or "",
                "company_id": company_id or "",
                "fornecedor_id": fornecedor_id or "",
                "numero_nota": numero_nota or "",
            },
        },
    )


@router.get("/boletos/new", response_class=HTMLResponse)
async def new_boleto_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "create", db):
        return RedirectResponse(url="/boletos", status_code=303)
    companies = db.query(Company).order_by(Company.name).all()
    fornecedores = db.query(Fornecedor).order_by(Fornecedor.name).all()
    notas = db.query(NotaFiscal).order_by(NotaFiscal.numero).all()
    return templates.TemplateResponse(
        "boletos/new.html", {"request": request, "companies": companies, "fornecedores": fornecedores, "notas": notas, "user": user}
    )


@router.post("/boletos/new")
async def create_boleto(
    request: Request,
    nota_fiscal_id: str = Form(""),
    company_id: int = Form(...),
    numero_nota: str = Form(...),
    descricao: str = Form(""),
    valor: float = Form(...),
    data_emissao: date = Form(...),
    data_vencimento: date = Form(...),
    anexo: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "create", db):
        return RedirectResponse(url="/boletos", status_code=303)

    anexo_path = None
    if anexo and anexo.filename:
        anexo_path = await upload_file(anexo, prefix="boletos")

    nf_id = int(nota_fiscal_id) if nota_fiscal_id else None

    boleto = Boleto(
        numero_nota=numero_nota,
        descricao=descricao,
        valor=valor,
        data_emissao=data_emissao,
        data_vencimento=data_vencimento,
        company_id=company_id,
        nota_fiscal_id=nf_id,
        anexo=anexo_path,
        status="atrasado" if data_vencimento < date.today() else "pendente",
    )
    db.add(boleto)
    db.commit()
    log_action(db, user.id, "create", "boleto", boleto.id, f"Boleto #{boleto.id} criado")
    return RedirectResponse(url=toast_url("/boletos", f"Boleto #{boleto.id} criado com sucesso"), status_code=303)


@router.get("/api/nota/{nota_id}/info")
async def get_nota_info(nota_id: int, db: Session = Depends(get_db)):
    nota = db.query(NotaFiscal).get(nota_id)
    if nota:
        return {
            "id": nota.id,
            "numero": nota.numero,
            "empresa_id": nota.empresa_id,
            "empresa_name": nota.empresa.name,
            "fornecedor_id": nota.fornecedor_id,
            "fornecedor_name": nota.fornecedor.name,
            "data_emissao": nota.data_emissao.isoformat(),
            "valor_total": nota.valor_total,
            "tipo_material": nota.tipo_material.name,
        }
    return {}


@router.get("/api/notas/search")
async def search_notas(q: str = Query(""), db: Session = Depends(get_db)):
    if not q or len(q) < 2:
        return []
    notas = db.query(NotaFiscal).filter(NotaFiscal.numero.ilike(f"%{q}%")).limit(10).all()
    return [
        {
            "id": n.id,
            "numero": n.numero,
            "fornecedor_name": n.fornecedor.name,
            "empresa_name": n.empresa.name,
            "empresa_id": n.empresa_id,
            "data_emissao": n.data_emissao.strftime("%d/%m/%Y"),
            "valor_total": n.valor_total,
        }
        for n in notas
    ]


@router.get("/boletos/{boleto_id}", response_class=HTMLResponse)
async def view_boleto(boleto_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)
    boleto = db.query(Boleto).get(boleto_id)
    if not boleto:
        return RedirectResponse(url="/boletos", status_code=303)
    return templates.TemplateResponse(
        "boletos/detail.html", {"request": request, "boleto": boleto, "user": user, "today": date.today()}
    )


@router.get("/boletos/{boleto_id}/edit", response_class=HTMLResponse)
async def edit_boleto_form(boleto_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "edit", db):
        return RedirectResponse(url="/boletos", status_code=303)
    boleto = db.query(Boleto).get(boleto_id)
    return templates.TemplateResponse(
        "boletos/form.html", {"request": request, "edit_boleto": boleto, "user": user}
    )


@router.post("/boletos/{boleto_id}/edit")
async def update_boleto(
    boleto_id: int,
    request: Request,
    descricao: str = Form(""),
    valor: float = Form(...),
    data_vencimento: date = Form(...),
    pago: bool = Form(False),
    anexo: UploadFile = File(None),
    comprovante: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "edit", db):
        return RedirectResponse(url="/boletos", status_code=303)
    boleto = db.query(Boleto).get(boleto_id)
    if boleto:
        boleto.descricao = descricao
        boleto.valor = valor
        boleto.data_vencimento = data_vencimento
        boleto.pago = pago
        if pago:
            boleto.status = "pago"
            if not boleto.data_pagamento:
                boleto.data_pagamento = date.today()
        else:
            boleto.status = "atrasado" if data_vencimento < date.today() else "pendente"

        if anexo and anexo.filename:
            boleto.anexo = await upload_file(anexo, prefix="boletos")

        if comprovante and comprovante.filename:
            comprovante_path = await upload_file(comprovante)

            payment = (
                db.query(BoletoPayment)
                .filter(BoletoPayment.boleto_id == boleto.id)
                .order_by(BoletoPayment.created_at.desc())
                .first()
            )
            if payment:
                payment.comprovante = comprovante_path
            else:
                payment = BoletoPayment(
                    boleto_id=boleto.id,
                    valor_pago=boleto.valor,
                    data_pagamento=date.today(),
                    comprovante=comprovante_path,
                )
                db.add(payment)

        db.commit()
        log_action(db, user.id, "update", "boleto", boleto.id, f"Boleto #{boleto.id} atualizado")
    return RedirectResponse(url=toast_url(f"/boletos/{boleto_id}", f"Boleto #{boleto_id} atualizado com sucesso"), status_code=303)


@router.post("/boletos/{boleto_id}/delete")
async def delete_boleto(boleto_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "delete", db):
        return RedirectResponse(url="/boletos", status_code=303)
    boleto = db.query(Boleto).get(boleto_id)
    nota_id = boleto.nota_fiscal_id if boleto else None
    if boleto:
        log_action(db, user.id, "delete", "boleto", boleto.id, f"Boleto #{boleto.id} excluído")
        db.delete(boleto)
        db.commit()
    if nota_id:
        return RedirectResponse(url=toast_url(f"/notas/{nota_id}", "Boleto excluído com sucesso"), status_code=303)
    return RedirectResponse(url=toast_url("/boletos", "Boleto excluído com sucesso"), status_code=303)


@router.get("/boletos/{boleto_id}/pay", response_class=HTMLResponse)
async def pay_boleto_form(boleto_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "edit", db):
        return RedirectResponse(url="/boletos", status_code=303)
    boleto = db.query(Boleto).get(boleto_id)
    if not boleto:
        return RedirectResponse(url="/boletos", status_code=303)
    return templates.TemplateResponse(
        "boletos/pay.html",
        {"request": request, "boleto": boleto, "user": user, "today": date.today()},
    )


@router.post("/boletos/{boleto_id}/pay")
async def pay_boleto(
    boleto_id: int,
    request: Request,
    valor_pago: float = Form(...),
    data_pagamento: date = Form(...),
    observacao: str = Form(""),
    comprovante: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "boletos", "edit", db):
        return RedirectResponse(url="/boletos", status_code=303)
    boleto = db.query(Boleto).get(boleto_id)
    if boleto:
        comprovante_path = None
        if comprovante and comprovante.filename:
            comprovante_path = await upload_file(comprovante)

        payment = BoletoPayment(
            boleto_id=boleto.id,
            valor_pago=valor_pago,
            data_pagamento=data_pagamento,
            observacao=observacao,
            comprovante=comprovante_path,
        )
        boleto.pago = True
        boleto.status = "pago"
        boleto.data_pagamento = data_pagamento
        db.add(payment)
        db.commit()
        log_action(db, user.id, "pay", "boleto", boleto.id, f"Boleto #{boleto.id} pago - R$ {valor_pago:.2f}")
    return RedirectResponse(url=toast_url(f"/boletos/{boleto_id}", f"Boleto #{boleto_id} pago com sucesso"), status_code=303)
