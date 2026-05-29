"""
app/schemas/schemas.py
Modelos Pydantic: validación de entrada y serialización de salida
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator


# ─── Indicador ────────────────────────────────────────────────────────────────

class IndicadorOut(BaseModel):
    id: int
    tipo: str
    descripcion: str
    peso: float
    es_critico: bool

    model_config = {"from_attributes": True}


# ─── Análisis ─────────────────────────────────────────────────────────────────

class AnalisisOut(BaseModel):
    id: int
    nombre_archivo: str
    fecha_analisis: datetime
    texto_ocr: Optional[str]
    confianza_ocr: float
    campos_detectados: Optional[dict]
    veredicto: str
    indice_sospecha: float
    confianza_result: float
    indicadores: List[IndicadorOut] = []

    model_config = {"from_attributes": True}


class AnalisisResumen(BaseModel):
    """Para el listado del historial (sin texto OCR completo)."""
    id: int
    nombre_archivo: str
    fecha_analisis: datetime
    veredicto: str
    indice_sospecha: float
    confianza_result: float

    model_config = {"from_attributes": True}


# ─── Configuración ────────────────────────────────────────────────────────────

class ConfiguracionIn(BaseModel):
    clave: str
    valor: Any
    descripcion: Optional[str] = None

    @field_validator("clave")
    @classmethod
    def clave_no_vacia(cls, v):
        if not v.strip():
            raise ValueError("La clave no puede estar vacía")
        return v.strip().lower()


class ConfiguracionOut(BaseModel):
    id: int
    clave: str
    valor: Any
    descripcion: Optional[str]
    actualizado: datetime

    model_config = {"from_attributes": True}


# ─── Exportación ──────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    formato: str = "csv"                       # "csv" o "pdf"

    @field_validator("formato")
    @classmethod
    def formato_valido(cls, v):
        if v not in ("csv", "pdf"):
            raise ValueError("El formato debe ser 'csv' o 'pdf'")
        return v


# ─── Respuesta genérica ───────────────────────────────────────────────────────

class MensajeOut(BaseModel):
    mensaje: str
    detalle: Optional[Any] = None
