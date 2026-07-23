from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
from app.config import get_settings

settings = get_settings()

connect_args = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif settings.DATABASE_URL.startswith("postgresql"):
    if settings.DB_SSL_MODE:
        connect_args["sslmode"] = settings.DB_SSL_MODE
        if settings.DB_SSL_ROOT_CERT:
            connect_args["sslrootcert"] = str(Path(settings.DB_SSL_ROOT_CERT).resolve())
        if settings.DB_SSL_CERT:
            connect_args["sslcert"] = str(Path(settings.DB_SSL_CERT).resolve())
        if settings.DB_SSL_KEY:
            connect_args["sslkey"] = str(Path(settings.DB_SSL_KEY).resolve())
    elif settings.DB_SSL_ROOT_CERT and settings.DB_SSL_CERT and settings.DB_SSL_KEY:
        connect_args["sslmode"] = "verify-full"
        connect_args["sslrootcert"] = str(Path(settings.DB_SSL_ROOT_CERT).resolve())
        connect_args["sslcert"] = str(Path(settings.DB_SSL_CERT).resolve())
        connect_args["sslkey"] = str(Path(settings.DB_SSL_KEY).resolve())
    else:
        connect_args["sslmode"] = "require"

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)


if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
