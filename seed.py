from app.database import SessionLocal, engine, Base
from app.models import Role, User, TipoMaterial, Permission
from passlib.context import CryptContext

DEFAULT_TIPOS_MATERIAL = [
    "Frios",
    "Vestuários",
    "Eletrônicos",
    "Alimentos",
    "Serviços",
    "Outros",
]

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


def seed():
    Base.metadata.create_all(bind=engine)
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

        for resource, action in DEFAULT_PERMISSIONS:
            if not db.query(Permission).filter(Permission.resource == resource, Permission.action == action).first():
                db.add(Permission(resource=resource, action=action))
        db.commit()

        if not admin_role.permissions:
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
            print("Seed concluído: admin/admin123")
        else:
            print("Seed já executado anteriormente")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
