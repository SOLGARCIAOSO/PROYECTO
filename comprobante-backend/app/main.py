"""
app/main.py
Punto de entrada de la aplicación FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base

# Importar modelos para que SQLAlchemy los registre antes de crear tablas
from app.models import models  # noqa: F401

from app.api.routes import comprobante, historial, configuracion, exportacion

# ── Crear tablas automáticamente al arrancar ──────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Aplicación ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sistema de Detección de Fraude en Comprobantes",
    description=(
        "API REST para análisis automatizado de comprobantes de pago colombianos. "
        "Detecta alteraciones mediante OCR (Tesseract), validación de campos y análisis de patrones."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (permite peticiones desde el frontend local) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(comprobante.router)
app.include_router(historial.router)
app.include_router(configuracion.router)
app.include_router(exportacion.router)


# ── Raíz ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Estado"])
def raiz():
    return {
        "estado": "activo",
        "app": "Detección de Fraude en Comprobantes v1.0",
        "docs": "/docs",
        "umbrales": {
            "sospecha": settings.UMBRAL_SOSPECHA,
            "fraude":   settings.UMBRAL_FRAUDE,
        }
    }


@app.get("/salud", tags=["Estado"])
def salud():
    return {"estado": "OK"}
