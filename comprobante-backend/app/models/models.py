"""
app/models/models.py
Tablas de la base de datos: análisis, indicadores y configuración
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text,
    DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Analisis(Base):
    """Tabla principal — un registro por comprobante analizado."""
    __tablename__ = "analisis"

    id               = Column(Integer, primary_key=True, index=True)
    nombre_archivo   = Column(String(255), nullable=False)
    fecha_analisis   = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Texto extraído por OCR
    texto_ocr        = Column(Text, nullable=True)
    confianza_ocr    = Column(Float, default=0.0)   # 0-100

    # Campos detectados
    campos_detectados = Column(JSON, nullable=True)  # dict con los campos

    # Resultado de clasificación
    veredicto        = Column(String(20), nullable=False)   # Verificado / Sospechoso / Fraudulento / No determinado
    indice_sospecha  = Column(Float, default=0.0)           # 0-100
    confianza_result = Column(Float, default=0.0)           # 0-100

    # Relación con indicadores activados
    indicadores      = relationship("Indicador", back_populates="analisis", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Analisis id={self.id} archivo={self.nombre_archivo} veredicto={self.veredicto}>"


class Indicador(Base):
    """Indicadores (anomalías) detectados en un análisis."""
    __tablename__ = "indicadores"

    id          = Column(Integer, primary_key=True, index=True)
    analisis_id = Column(Integer, ForeignKey("analisis.id"), nullable=False)
    tipo        = Column(String(100), nullable=False)   # ej: "campo_ausente", "entidad_desconocida"
    descripcion = Column(String(500), nullable=False)
    peso        = Column(Float, default=10.0)           # peso en el índice de sospecha
    es_critico  = Column(Boolean, default=False)

    analisis    = relationship("Analisis", back_populates="indicadores")


class Configuracion(Base):
    """
    Configuración ajustable por el administrador (CU8).
    Se guarda como clave-valor en JSON para máxima flexibilidad.
    """
    __tablename__ = "configuracion"

    id          = Column(Integer, primary_key=True, index=True)
    clave       = Column(String(100), unique=True, nullable=False)
    valor       = Column(JSON, nullable=False)
    descripcion = Column(String(300), nullable=True)
    actualizado = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Configuracion {self.clave}={self.valor}>"
