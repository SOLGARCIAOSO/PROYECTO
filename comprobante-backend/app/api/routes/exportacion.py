"""
app/api/routes/exportacion.py
CU9 — Exportar reporte de análisis (PDF o CSV)
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.models import Analisis
from app.services.export_service import generar_csv, generar_pdf

router = APIRouter(prefix="/exportar", tags=["Exportación (Admin)"])


@router.get("/", summary="CU9: Exportar reporte de análisis")
def exportar_reporte(
    formato: str = Query("csv", description="Formato de exportación: 'csv' o 'pdf'"),
    fecha_inicio: Optional[datetime] = Query(None, description="Desde (ISO 8601, ej: 2026-01-01T00:00:00)"),
    fecha_fin: Optional[datetime]    = Query(None, description="Hasta (ISO 8601, ej: 2026-12-31T23:59:59)"),
    db: Session = Depends(get_db),
):
    """
    Genera y descarga un reporte con los análisis del rango de fechas indicado.
    Si no se especifica rango, exporta todo el historial.
    """
    if formato not in ("csv", "pdf"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use 'csv' o 'pdf'.")

    query = db.query(Analisis).order_by(Analisis.fecha_analisis.desc())

    if fecha_inicio:
        query = query.filter(Analisis.fecha_analisis >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Analisis.fecha_analisis <= fecha_fin)

    registros = query.all()

    # CU9 curso alterno 3a: sin registros en el rango
    if not registros:
        raise HTTPException(
            status_code=404,
            detail="No hay registros en el rango de fechas seleccionado."
        )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if formato == "csv":
        contenido = generar_csv(registros)
        return Response(
            content=contenido,
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f"attachment; filename=reporte_{timestamp}.csv"}
        )

    # PDF
    contenido = generar_pdf(registros, fecha_inicio, fecha_fin)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_{timestamp}.pdf"}
    )
