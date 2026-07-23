from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.database import Base
from app.config import get_settings
from app.models import Role, User, Company, Fornecedor, FornecedorCNPJ, TipoMaterial, NotaFiscal, Boleto, BoletoPayment, Permission  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_connect_args():
    connect_args = {}
    if settings.DATABASE_URL.startswith("postgresql"):
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
    return connect_args


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=get_connect_args(),
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
