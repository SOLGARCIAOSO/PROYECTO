"""
app/api/routes/configuracion.py
CU8 — Configurar reglas de validación (panel del administrador)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Configuracion
from app.schemas.schemas import ConfiguracionIn, ConfiguracionOut, MensajeOut

router = APIRouter(prefix="/configuracion", tags=["Configuración (Admin)"])


@router.get("/", response_model=list[ConfiguracionOut], summary="Ver toda la configuración actual")
def listar_configuracion(db: Session = Depends(get_db)):
    return db.query(Configuracion).all()


@router.get("/{clave}", response_model=ConfiguracionOut, summary="Ver valor de una clave")
def obtener_configuracion(clave: str, db: Session = Depends(get_db)):
    config = db.query(Configuracion).filter(Configuracion.clave == clave.lower()).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Clave '{clave}' no encontrada")
    return config


@router.post("/", response_model=ConfiguracionOut, summary="Crear o actualizar una clave")
def crear_configuracion(data: ConfiguracionIn, db: Session = Depends(get_db)):
    """Crea la clave si no existe; la actualiza si ya existe."""
    _validar_coherencia(data, db)

    existente = db.query(Configuracion).filter(Configuracion.clave == data.clave).first()
    if existente:
        existente.valor = data.valor
        if data.descripcion:
            existente.descripcion = data.descripcion
        db.commit()
        db.refresh(existente)
        return existente

    nueva = Configuracion(clave=data.clave, valor=data.valor, descripcion=data.descripcion)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.delete("/{clave}", response_model=MensajeOut, summary="Eliminar una clave de configuración")
def eliminar_configuracion(clave: str, db: Session = Depends(get_db)):
    config = db.query(Configuracion).filter(Configuracion.clave == clave.lower()).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Clave '{clave}' no encontrada")
    db.delete(config)
    db.commit()
    return {"mensaje": f"Clave '{clave}' eliminada correctamente"}


# ─── Validación de coherencia (CU8 curso alterno 3a) ─────────────────────────

def _validar_coherencia(data: ConfiguracionIn, db: Session):
    """
    Verifica que umbral_sospecha < umbral_fraude.
    Lanza 400 si la regla se viola.
    """
    clave = data.clave

    if clave == "umbral_sospecha":
        fraude_cfg = db.query(Configuracion).filter(Configuracion.clave == "umbral_fraude").first()
        if fraude_cfg:
            if not (int(data.valor) < int(fraude_cfg.valor)):
                raise HTTPException(
                    status_code=400,
                    detail=f"umbral_sospecha ({data.valor}) debe ser menor que umbral_fraude ({fraude_cfg.valor})"
                )

    if clave == "umbral_fraude":
        sospecha_cfg = db.query(Configuracion).filter(Configuracion.clave == "umbral_sospecha").first()
        if sospecha_cfg:
            if not (int(sospecha_cfg.valor) < int(data.valor)):
                raise HTTPException(
                    status_code=400,
                    detail=f"umbral_fraude ({data.valor}) debe ser mayor que umbral_sospecha ({sospecha_cfg.valor})"
                )
