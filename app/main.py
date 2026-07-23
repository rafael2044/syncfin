from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from pathlib import Path

from app.database import SessionLocal
from app.models import Role, User, TipoMaterial, Permission
from app.routes import auth, dashboard, users, companies, fornecedores, notas, tipos_material, boletos, reports, permissions, audit
from app.routes.auth import get_user_permissions_list
from passlib.context import CryptContext

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SyncFin - Sistema de Gestão Financeira")


class PermissionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.permissions = []
        token = request.cookies.get("access_token")
        if token:
            try:
                from jose import jwt
                from app.config import get_settings
                settings = get_settings()
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                username = payload.get("sub")
                if username:
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.username == username).first()
                        if user and user.is_active:
                            request.state.permissions = get_user_permissions_list(user, db)
                    finally:
                        db.close()
            except Exception:
                pass
        response = await call_next(request)
        return response


app.add_middleware(PermissionsMiddleware)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(companies.router)
app.include_router(fornecedores.router)
app.include_router(notas.router)
app.include_router(tipos_material.router)
app.include_router(boletos.router)
app.include_router(reports.router)
app.include_router(permissions.router)
app.include_router(audit.router)

DEFAULT_TIPOS_MATERIAL = [
    "Frios",
    "Vestuários",
    "Eletrônicos",
    "Alimentos",
    "Serviços",
    "Outros",
]


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrador do sistema")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(name="user", description="Usuário padrão")
            db.add(user_role)
            db.commit()

        for tipo_name in DEFAULT_TIPOS_MATERIAL:
            if not db.query(TipoMaterial).filter(TipoMaterial.name == tipo_name).first():
                db.add(TipoMaterial(name=tipo_name))
        db.commit()

        DEFAULT_PERMISSIONS = [
            ("dashboard", "read"),
            ("fornecedores", "read"), ("fornecedores", "create"), ("fornecedores", "edit"), ("fornecedores", "delete"),
            ("companies", "read"), ("companies", "create"), ("companies", "edit"), ("companies", "delete"),
            ("categories", "read"), ("categories", "create"), ("categories", "edit"), ("categories", "delete"),
            ("boletos", "read"), ("boletos", "create"), ("boletos", "edit"), ("boletos", "delete"),
            ("users", "read"), ("users", "create"), ("users", "edit"), ("users", "delete"),
            ("reports", "read"),
            ("permissions", "read"), ("permissions", "edit"),
        ]
        for resource, action in DEFAULT_PERMISSIONS:
            if not db.query(Permission).filter(Permission.resource == resource, Permission.action == action).first():
                db.add(Permission(resource=resource, action=action))
        db.commit()

        if admin_role.permissions:
            pass
        else:
            all_perms = db.query(Permission).all()
            admin_role.permissions = list(all_perms)
            db.commit()

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@syncfin.com",
                full_name="Administrador",
                hashed_password=pwd_context.hash("admin123"),
                role_id=admin_role.id,
            )
            db.add(admin_user)
            db.commit()

        from datetime import date
        from app.models.boleto import Boleto
        today = date.today()
        overdue_boletos = db.query(Boleto).filter(
            Boleto.pago == False,
            Boleto.status != "atrasado",
            Boleto.data_vencimento < today
        ).all()
        for b in overdue_boletos:
            b.status = "atrasado"
        if overdue_boletos:
            db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")
