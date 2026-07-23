from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.routes.auth import get_current_user, has_permission
from app.templates_config import templates

router = APIRouter()


@router.get("/audit", response_class=HTMLResponse)
async def audit_logs_page(
    request: Request,
    db: Session = Depends(get_db),
    entity: str = Query(None),
    action: str = Query(None),
    user_id: str = Query(None),
    page: int = Query(1),
    per_page: int = Query(50),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(current_user, "permissions", "read", db):
        return RedirectResponse(url="/dashboard", status_code=303)

    query = db.query(AuditLog)

    if entity:
        query = query.filter(AuditLog.entity == entity)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        uid = int(user_id)
        query = query.filter(AuditLog.user_id == uid)

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    users = db.query(User).order_by(User.username).all()

    return templates.TemplateResponse(
        "audit/list.html",
        {
            "request": request,
            "logs": logs,
            "users": users,
            "user": current_user,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
            "filters": {
                "entity": entity or "",
                "action": action or "",
                "user_id": user_id or "",
            },
        },
    )
