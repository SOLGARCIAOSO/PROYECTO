"""
app/services/ocr_service.py
CU2 — Preprocesamiento + extracción de texto con Tesseract OCR
"""
import re
import io
import numpy as np
from PIL import Image
import cv2

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_DISPONIBLE = True
except ImportError:
    TESSERACT_DISPONIBLE = False


# ─── Preprocesamiento ─────────────────────────────────────────────────────────

def preprocesar_imagen(imagen_bytes: bytes) -> np.ndarray:
    """
    Convierte bytes de imagen a array OpenCV preprocesado:
    1. Carga la imagen
    2. Convierte a escala de grises
    3. Aplica umbralización adaptativa (binarización)
    4. Corrige inclinación si es pronunciada
    5. Redimensiona si es muy pequeña
    """
    np_arr = np.frombuffer(imagen_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("No se pudo decodificar la imagen")

    # Redimensionar si es muy pequeña (mínimo 800px de ancho)
    h, w = img.shape[:2]
    if w < 800:
        escala = 800 / w
        img = cv2.resize(img, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

    # Escala de grises
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Reducción de ruido
    gris = cv2.medianBlur(gris, 3)

    # Umbralización adaptativa para manejar iluminación irregular
    binaria = cv2.adaptiveThreshold(
        gris, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    return binaria


# ─── Extracción OCR ───────────────────────────────────────────────────────────

def extraer_texto(imagen_bytes: bytes) -> dict:
    """
    Ejecuta OCR sobre la imagen y retorna:
    {
        "texto_completo": str,
        "confianza": float (0-100),
        "exito": bool
    }
    """
    if not TESSERACT_DISPONIBLE:
        return {
            "texto_completo": "",
            "confianza": 0.0,
            "exito": False,
            "error": "Tesseract no está instalado"
        }

    try:
        img_procesada = preprocesar_imagen(imagen_bytes)

        # Configuración de Tesseract: modo página 6 = bloque uniforme de texto
        config = "--oem 3 --psm 6 -l spa+eng"
        datos = pytesseract.image_to_data(
            img_procesada,
            config=config,
            output_type=pytesseract.Output.DICT
        )

        # Calcular confianza promedio (ignorar valores -1)
        confianzas = [c for c in datos["conf"] if c != -1]
        confianza_promedio = float(np.mean(confianzas)) if confianzas else 0.0

        # Reconstruir texto limpio
        texto = pytesseract.image_to_string(img_procesada, config=config)
        texto_limpio = " ".join(texto.split())

        return {
            "texto_completo": texto_limpio,
            "confianza": round(confianza_promedio, 2),
            "exito": True
        }

    except Exception as e:
        return {
            "texto_completo": "",
            "confianza": 0.0,
            "exito": False,
            "error": str(e)
        }


# ─── Detección de campos ──────────────────────────────────────────────────────

def extraer_campos(texto: str) -> dict:
    """
    Busca campos obligatorios de un comprobante colombiano mediante regex.
    Retorna dict con cada campo y si fue encontrado.
    """
    campos = {}

    # NIT: formato XXXXXXXXX-X o XXXXXXXXX
    patron_nit = re.search(r'\b(\d{6,10}-?\d?)\b', texto)
    campos["nit"] = patron_nit.group(1) if patron_nit else None

    # Fecha: múltiples formatos
    patron_fecha = re.search(
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{2}[/-]\d{2})\b', texto
    )
    campos["fecha"] = patron_fecha.group(1) if patron_fecha else None

    # Valor total: números con puntos/comas como miles, puede tener $ o COP
    patron_valor = re.search(
        r'(?:total|valor|monto)[:\s]*\$?\s*([\d.,]+)', texto, re.IGNORECASE
    )
    if not patron_valor:
        patron_valor = re.search(r'\$\s*([\d.,]+)', texto)
    campos["valor_total"] = patron_valor.group(1).strip() if patron_valor else None

    # Nombre del emisor (línea que antecede al NIT)
    patron_emisor = re.search(
        r'([A-ZÁÉÍÓÚ][A-Za-záéíóúñÑ\s&.,]{5,50})\s*(?:NIT|nit|S\.A|SAS|LTDA)', texto
    )
    campos["nombre_emisor"] = patron_emisor.group(1).strip() if patron_emisor else None

    # Código de transacción / referencia
    patron_codigo = re.search(
        r'(?:ref(?:erencia)?|código|transacci[oó]n|n[°º]\.?)[:\s#]*([A-Z0-9\-]{5,30})',
        texto, re.IGNORECASE
    )
    campos["codigo_transaccion"] = patron_codigo.group(1).strip() if patron_codigo else None

    # Valor en letras (opcional, para cruce)
    patron_letras = re.search(
        r'(?:son|valor en letras?)[:\s]+([A-Za-záéíóúñÑ\s]+(?:pesos?|mil|millones?))',
        texto, re.IGNORECASE
    )
    campos["valor_letras"] = patron_letras.group(1).strip() if patron_letras else None

    return campos