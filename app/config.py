from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = "syncfin-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DB_SSL_MODE: str = ""
    DB_SSL_ROOT_CERT: str = ""
    DB_SSL_CERT: str = ""
    DB_SSL_KEY: str = ""

    STORAGE_TYPE: str = "local"
    SQUARE_CLOUD_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
