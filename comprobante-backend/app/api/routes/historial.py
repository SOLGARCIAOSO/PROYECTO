"""
app/api/routes/historial.py
CU7 — Consultar historial de casos
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Analisis
from app.schemas.schemas import AnalisisResumen, AnalisisOut

router = APIRouter(prefix="/historial", tags=["Historial"])


@router.get("/", response_model=list[AnalisisResumen], summary="Listar todos los análisis realizados")
def listar_historial(
    skip: int = Query(0, ge=0, description="Registros a omitir (paginación)"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros a retornar"),
    veredicto: Optional[str] = Query(None, description="Filtrar por: Verificado, Sospechoso, Fraudulento"),
    db: Session = Depends(get_db),
):
    """Retorna historial ordenado por fecha descendente."""
    query = db.query(Analisis).order_by(Analisis.fecha_analisis.desc())

    if veredicto:
        opciones_validas = {"Verificado", "Sospechoso", "Fraudulento", "No determinado"}
        if veredicto not in opciones_validas:
            raise HTTPException(status_code=400, detail=f"Veredicto inválido. Opciones: {opciones_validas}")
        query = query.filter(Analisis.veredicto == veredicto)

    registros = query.offset(skip).limit(limit).all()

    if not registros:
        return []   # CU7 curso alterno 3a: retorna lista vacía en lugar de 404

    return registros


@router.get("/{analisis_id}", response_model=AnalisisOut, summary="Ver detalle de un análisis")
def detalle_analisis(analisis_id: int, db: Session = Depends(get_db)):
    """Retorna el análisis completo con indicadores activados."""
    registro = db.query(Analisis).filter(Analisis.id == analisis_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail=f"No existe análisis con ID {analisis_id}")
    return registro


@router.delete("/{analisis_id}", summary="Eliminar un análisis del historial")
def eliminar_analisis(analisis_id: int, db: Session = Depends(get_db)):
    """Elimina un registro y sus indicadores asociados."""
    registro = db.query(Analisis).filter(Analisis.id == analisis_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail=f"No existe análisis con ID {analisis_id}")
    db.delete(registro)
    db.commit()
    return {"mensaje": f"Análisis {analisis_id} eliminado correctamente"}
