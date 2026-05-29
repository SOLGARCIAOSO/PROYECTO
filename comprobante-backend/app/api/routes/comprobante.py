"""
app/api/routes/comprobante.py
CU1  — Cargar imagen
CU2  — OCR (Tesseract)
CU3  — Validar campos
CU4  — Analizar patrones (texto + OpenCV)
CU5  — Clasificar
CU6  — Mostrar resultado
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import threading

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Analisis, Indicador
from app.schemas.schemas import AnalisisOut
from app.services.ocr_service import extraer_texto, extraer_campos
from app.services.validacion_service import validar_campos
from app.services.analisis_service import (
    analizar_patrones_texto,
    analizar_patrones_visual,
    clasificar,
)
from app.services.opencv_service import (
    comparar_con_plantilla,
    comparar_sin_plantilla,
    guardar_plantilla,
    listar_plantillas,
)
from app.services.alerta_service import enviar_alerta

router = APIRouter(prefix="/comprobante", tags=["Análisis de comprobantes"])


# ══════════════════════════════════════════════════════════════════════════════
# POST /comprobante/analizar
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/analizar",
    response_model=AnalisisOut,
    summary="CU1-CU6: Analiza un comprobante (OCR + OpenCV)",
)
async def analizar_comprobante(
    archivo: UploadFile = File(..., description="Imagen JPG o PNG del comprobante"),
    plantilla: Optional[str] = Form(
        None,
        description="Nombre de la plantilla de referencia (ej: bancolombia.jpg). "
                    "Si se omite, se usa análisis interno sin plantilla."
    ),
    db: Session = Depends(get_db),
):
    # ── CU1: Validar formato ──────────────────────────────────────────────────
    if archivo.content_type not in settings.FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido: '{archivo.content_type}'. Use JPG o PNG."
        )

    contenido = await archivo.read()
    tamano_mb = len(contenido) / (1024 * 1024)
    if tamano_mb > settings.TAMANO_MAX_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo demasiado grande ({tamano_mb:.1f} MB). Máximo {settings.TAMANO_MAX_MB} MB."
        )

    # ── CU2: OCR ──────────────────────────────────────────────────────────────
    resultado_ocr = extraer_texto(contenido)
    texto_ocr     = resultado_ocr.get("texto_completo", "")
    confianza_ocr = resultado_ocr.get("confianza", 0.0)
    campos        = extraer_campos(texto_ocr)

    # ── CU3: Validar campos ───────────────────────────────────────────────────
    validaciones = validar_campos(campos)

    # ── CU4a: Análisis de texto ───────────────────────────────────────────────
    indicadores_texto = analizar_patrones_texto(campos, validaciones, confianza_ocr)

    # ── CU4b: Análisis visual con OpenCV ──────────────────────────────────────
    if plantilla:
        resultado_cv = comparar_con_plantilla(contenido, plantilla)
    else:
        resultado_cv = comparar_sin_plantilla(contenido)

    indicadores_visual = analizar_patrones_visual(resultado_cv)

    todos_indicadores = indicadores_texto + indicadores_visual

    # ── CU5: Clasificación ────────────────────────────────────────────────────
    resultado = clasificar(
        todos_indicadores,
        umbral_sospecha=settings.UMBRAL_SOSPECHA,
        umbral_fraude=settings.UMBRAL_FRAUDE,
    )

    if not resultado_ocr.get("exito") and not texto_ocr:
        resultado["veredicto"] = "No determinado"
        resultado["confianza"] = 0.0

    campos["_opencv"] = {
        k: v for k, v in resultado_cv.items()
        if k not in ("exito", "error") and not isinstance(v, list)
    }
    if resultado_cv.get("zonas_alteradas"):
        campos["_opencv"]["zonas_alteradas"] = resultado_cv["zonas_alteradas"]

    # ── CU6: Persistir ────────────────────────────────────────────────────────
    nuevo = Analisis(
        nombre_archivo    = archivo.filename,
        texto_ocr         = texto_ocr,
        confianza_ocr     = confianza_ocr,
        campos_detectados = campos,
        veredicto         = resultado["veredicto"],
        indice_sospecha   = resultado["indice_sospecha"],
        confianza_result  = resultado["confianza"],
    )
    db.add(nuevo)
    db.flush()

    for ind in todos_indicadores:
        db.add(Indicador(
            analisis_id = nuevo.id,
            tipo        = ind["tipo"],
            descripcion = ind["descripcion"],
            peso        = ind["peso"],
            es_critico  = ind["es_critico"],
        ))

    db.commit()
    db.refresh(nuevo)

    # ── Alerta por correo (en hilo separado para no bloquear la respuesta) ────
    if resultado["veredicto"] in ("Sospechoso", "Fraudulento"):
        threading.Thread(
            target=enviar_alerta,
            args=(
                nuevo.id,
                resultado["veredicto"],
                resultado["indice_sospecha"],
                resultado["confianza"],
                campos,
                todos_indicadores,
            ),
            daemon=True
        ).start()

    return nuevo


# ══════════════════════════════════════════════════════════════════════════════
# Gestión de plantillas
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/plantillas", tags=["Plantillas"], summary="Listar plantillas disponibles")
def listar():
    return {"plantillas": listar_plantillas()}


@router.post("/plantillas", tags=["Plantillas"], summary="Subir plantilla de referencia")
async def subir_plantilla(
    archivo: UploadFile = File(..., description="Imagen JPG/PNG de plantilla original"),
    nombre: Optional[str] = Form(None, description="Nombre para guardar (sin extensión)")
):
    if archivo.content_type not in settings.FORMATOS_PERMITIDOS:
        raise HTTPException(status_code=400, detail="Solo se aceptan JPG y PNG como plantillas")

    contenido = await archivo.read()
    nombre_final = nombre or archivo.filename
    ruta = guardar_plantilla(nombre_final, contenido)
    return {"mensaje": "Plantilla guardada", "ruta": ruta, "nombre": nombre_final}
