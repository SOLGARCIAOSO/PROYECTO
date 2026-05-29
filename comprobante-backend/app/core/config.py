"""
app/core/config.py
Configuración central leída desde .env
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Base de datos
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "comprobantes_db")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # App
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Umbrales de clasificación (0-100)
    UMBRAL_SOSPECHA: int = int(os.getenv("UMBRAL_SOSPECHA", 30))
    UMBRAL_FRAUDE: int = int(os.getenv("UMBRAL_FRAUDE", 60))

    # Tesseract
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")

    # Formatos permitidos
    FORMATOS_PERMITIDOS: set = {"image/jpeg", "image/png"}
    TAMANO_MAX_MB: int = 10


settings = Settings()
