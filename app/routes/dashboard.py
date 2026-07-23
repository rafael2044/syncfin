from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.database import get_db
from app.models.boleto import Boleto
from app.models.user import User
from app.routes.auth import get_current_user, has_permission
from app.templates_config import templates

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "dashboard", "read", db):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=303)

    today = date.today()
    soon = today + timedelta(days=7)

    vencidos = (
        db.query(Boleto)
        .filter(Boleto.data_vencimento < today, Boleto.pago == False)
        .order_by(Boleto.data_vencimento)
        .all()
    )

    proximos_vencer = (
        db.query(Boleto)
        .filter(Boleto.data_vencimento >= today, Boleto.data_vencimento <= soon, Boleto.pago == False)
        .order_by(Boleto.data_vencimento)
        .all()
    )

    recentes = (
        db.query(Boleto)
        .order_by(Boleto.created_at.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "vencidos": vencidos,
            "proximos_vencer": proximos_vencer,
            "recentes": recentes,
            "today": today,
        },
    )
