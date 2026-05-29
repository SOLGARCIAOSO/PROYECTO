"""
app/services/analisis_service.py
CU4 — Análisis de patrones (OCR + OpenCV)
CU5 — Clasificación del comprobante
"""
import re

from app.services.validacion_service import es_emisor_reconocido

PESOS_TEXTO = {
    "campo_ausente_nit":          25.0,
    "campo_ausente_fecha":        20.0,
    "campo_ausente_valor":        20.0,
    "campo_ausente_emisor":       15.0,
    "campo_ausente_codigo":       15.0,
    "fecha_invalida":             20.0,
    "fecha_futura":               25.0,
    "valor_invalido":             20.0,
    "entidad_desconocida":        30.0,
    "discrepancia_valor_letras":  35.0,
    "confianza_ocr_baja":         10.0,
}

PESOS_VISUAL = {
    "alteracion_visual_alta":  50.0,
    "alteracion_visual_media": 25.0,
    "anomalia_interna":        20.0,
}


def analizar_patrones_texto(campos: dict, validaciones: dict, confianza_ocr: float) -> list[dict]:
    indicadores = []

    def agregar(tipo, desc, critico=False):
        indicadores.append({"tipo": tipo, "descripcion": desc,
                            "peso": PESOS_TEXTO.get(tipo, 10.0), "es_critico": critico})

    ausentes = {
        "nit":                ("campo_ausente_nit",    "NIT del emisor no detectado"),
        "fecha":              ("campo_ausente_fecha",   "Fecha de emisión no detectada"),
        "valor_total":        ("campo_ausente_valor",   "Valor total no detectado"),
        "nombre_emisor":      ("campo_ausente_emisor",  "Nombre del emisor no detectado"),
        "codigo_transaccion": ("campo_ausente_codigo",  "Código de transacción no detectado"),
    }
    for campo, (tipo, desc) in ausentes.items():
        if not campos.get(campo):
            agregar(tipo, desc)

    for campo_key in ("fecha", "valor_total", "nit"):
        v = validaciones.get(campo_key, {})
        if not v.get("valido") and campos.get(campo_key):
            msg = v.get("mensaje", "")
            if campo_key == "fecha":
                tipo = "fecha_futura" if "futura" in msg else "fecha_invalida"
                agregar(tipo, f"Fecha inválida: {msg}")
            elif campo_key == "valor_total":
                agregar("valor_invalido", f"Valor inválido: {msg}")

    nombre_emisor = campos.get("nombre_emisor")
    if nombre_emisor and not es_emisor_reconocido(nombre_emisor):
        agregar("entidad_desconocida",
                f"Emisor '{nombre_emisor}' no está en entidades reconocidas", critico=True)

    if campos.get("valor_total") and campos.get("valor_letras"):
        if not _valores_coinciden(campos["valor_total"], campos["valor_letras"]):
            agregar("discrepancia_valor_letras",
                    f"Discrepancia: '{campos['valor_total']}' vs '{campos['valor_letras']}'",
                    critico=True)

    if confianza_ocr < 40:
        agregar("confianza_ocr_baja",
                f"Calidad OCR baja ({confianza_ocr:.1f}%)")

    return indicadores


def analizar_patrones_visual(resultado_cv: dict) -> list[dict]:
    indicadores = []
    if not resultado_cv or not resultado_cv.get("exito"):
        return indicadores

    modo = resultado_cv.get("modo", "con_plantilla")

    if modo != "sin_plantilla":
        veredicto_cv = resultado_cv.get("veredicto_cv", "")
        similitud    = resultado_cv.get("similitud_pixel", 100)
        num_zonas    = resultado_cv.get("num_zonas", 0)
        ssim         = resultado_cv.get("ssim", 1.0)

        if veredicto_cv == "Alterado":
            indicadores.append({
                "tipo": "alteracion_visual_alta",
                "descripcion": (f"Imagen alterada vs plantilla: similitud {similitud:.1f}%, "
                                f"SSIM {ssim:.3f}, {num_zonas} zona(s) modificada(s)"),
                "peso": PESOS_VISUAL["alteracion_visual_alta"],
                "es_critico": True,
            })
        elif veredicto_cv == "Sospechoso":
            indicadores.append({
                "tipo": "alteracion_visual_media",
                "descripcion": (f"Diferencias moderadas vs plantilla: similitud {similitud:.1f}%, "
                                f"{num_zonas} zona(s) sospechosa(s)"),
                "peso": PESOS_VISUAL["alteracion_visual_media"],
                "es_critico": False,
            })
        if num_zonas > 5:
            indicadores.append({
                "tipo": "multiples_zonas_alteradas",
                "descripcion": f"{num_zonas} zonas alteradas detectadas por OpenCV",
                "peso": 15.0, "es_critico": True,
            })
    else:
        indicios = resultado_cv.get("indicios", [])
        peso     = resultado_cv.get("peso_anomalia", 0)
        if indicios:
            indicadores.append({
                "tipo": "anomalia_interna",
                "descripcion": " | ".join(indicios),
                "peso": peso,
                "es_critico": peso >= 30,
            })

    return indicadores


def clasificar(indicadores: list[dict], umbral_sospecha: int = 30, umbral_fraude: int = 60) -> dict:
    if not indicadores:
        return {"veredicto": "Verificado", "indice_sospecha": 0.0, "confianza": 98.0}

    indice = min(sum(i["peso"] for i in indicadores), 100.0)

    hay_critico = any(i.get("es_critico") for i in indicadores)
    if hay_critico and indice < umbral_sospecha:
        indice = float(umbral_sospecha)

    if indice >= umbral_fraude:
        veredicto = "Fraudulento"
        confianza = min(50 + indice * 0.5, 99.0)
    elif indice >= umbral_sospecha:
        veredicto = "Sospechoso"
        confianza = 40.0 + (indice - umbral_sospecha) * 0.5
    else:
        veredicto = "Verificado"
        confianza = max(99.0 - indice * 1.5, 50.0)

    return {
        "veredicto":       veredicto,
        "indice_sospecha": round(indice, 2),
        "confianza":       round(confianza, 2),
    }


def _valores_coinciden(valor_num: str, valor_letras: str) -> bool:
    TABLA = {"mil": 1_000, "miles": 1_000, "millon": 1_000_000,
             "millones": 1_000_000, "billon": 1_000_000_000}
    try:
        limpio_num = float(re.sub(r'[^\d.]', '', valor_num.replace(',', '.')))
    except (ValueError, AttributeError):
        return True
    letras_lower = valor_letras.lower()
    multiplicador = next((v for k, v in TABLA.items() if k in letras_lower), 1)
    m = re.search(r'\d+', letras_lower)
    if not m:
        return True
    try:
        valor_letras_num = float(m.group()) * multiplicador
    except ValueError:
        return True
    if limpio_num == 0:
        return True
    return abs(limpio_num - valor_letras_num) / limpio_num <= 0.05
