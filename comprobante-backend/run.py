"""
run.py
Arranca el servidor FastAPI con Uvicorn.
Uso:
    python run.py
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("=" * 55)
    print("  Sistema de Detección de Fraude en Comprobantes")
    print("=" * 55)
    print(f"  Host  : {settings.APP_HOST}")
    print(f"  Puerto: {settings.APP_PORT}")
    print(f"  BD    : {settings.DB_NAME}@{settings.DB_HOST}:{settings.DB_PORT}")
    print(f"  Docs  : http://127.0.0.1:{settings.APP_PORT}/docs")
    print("=" * 55)

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
