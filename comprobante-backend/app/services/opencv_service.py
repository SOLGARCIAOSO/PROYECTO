"""
app/services/opencv_service.py
Comparación visual de comprobantes usando OpenCV.

Flujo:
  1. Preprocesar imagen cargada
  2. Alinear (warp) contra la plantilla usando ORB + homografía
  3. Comparar píxel a píxel con diferencia absoluta
  4. Detectar regiones alteradas con contornos
  5. Calcular índice de similitud y retornar evidencia
"""

import cv2
import numpy as np
from pathlib import Path

# Carpeta donde se guardan las plantillas de referencia
PLANTILLAS_DIR = Path(__file__).parent.parent.parent / "plantillas"
PLANTILLAS_DIR.mkdir(exist_ok=True)


# ─── Utilidades de imagen ─────────────────────────────────────────────────────

def bytes_a_bgr(imagen_bytes: bytes) -> np.ndarray:
    """Convierte bytes a imagen BGR de OpenCV."""
    arr = np.frombuffer(imagen_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen")
    return img


def preprocesar(img: np.ndarray, ancho_objetivo: int = 1000) -> np.ndarray:
    """
    Redimensiona, convierte a gris y aplica umbralización adaptativa.
    Estandariza el tamaño para que todas las imágenes sean comparables.
    """
    # Redimensionar manteniendo proporción
    h, w = img.shape[:2]
    escala = ancho_objetivo / w
    img_r = cv2.resize(img, (ancho_objetivo, int(h * escala)), interpolation=cv2.INTER_AREA)

    gris = cv2.cvtColor(img_r, cv2.COLOR_BGR2GRAY)

    # Ecualización de histograma para normalizar iluminación
    gris = cv2.equalizeHist(gris)

    return gris


# ─── Alineación por homografía ────────────────────────────────────────────────

def alinear_imagen(img_query: np.ndarray, img_plantilla: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    Usa ORB para detectar keypoints y FLANN para emparejar.
    Calcula homografía y transforma img_query al espacio de img_plantilla.
    Retorna (imagen_alineada, exito).
    """
    orb = cv2.ORB_create(nfeatures=1000)

    kp1, des1 = orb.detectAndCompute(img_query,     None)
    kp2, des2 = orb.detectAndCompute(img_plantilla, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        # Sin suficientes keypoints → devolver imagen sin alinear
        h, w = img_plantilla.shape[:2]
        img_resized = cv2.resize(img_query, (w, h))
        return img_resized, False

    # Matcher por fuerza bruta con distancia Hamming (adecuado para ORB)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)

    # Filtro de Lowe: solo matches buenos
    buenos = []
    for m_n in matches:
        if len(m_n) == 2:
            m, n = m_n
            if m.distance < 0.75 * n.distance:
                buenos.append(m)

    if len(buenos) < 10:
        h, w = img_plantilla.shape[:2]
        img_resized = cv2.resize(img_query, (w, h))
        return img_resized, False

    # Extraer puntos correspondientes
    pts_query     = np.float32([kp1[m.queryIdx].pt for m in buenos]).reshape(-1, 1, 2)
    pts_plantilla = np.float32([kp2[m.trainIdx].pt for m in buenos]).reshape(-1, 1, 2)

    # Homografía con RANSAC para robustez ante outliers
    H, mascara = cv2.findHomography(pts_query, pts_plantilla, cv2.RANSAC, 5.0)

    if H is None:
        h, w = img_plantilla.shape[:2]
        img_resized = cv2.resize(img_query, (w, h))
        return img_resized, False

    h, w = img_plantilla.shape[:2]
    img_alineada = cv2.warpPerspective(img_query, H, (w, h))
    return img_alineada, True


# ─── Detección de diferencias ─────────────────────────────────────────────────

def detectar_diferencias(img_a: np.ndarray, img_b: np.ndarray) -> dict:
    """
    Compara dos imágenes en escala de grises del mismo tamaño.
    Retorna:
      - similitud      : float 0-100 (100 = idénticas)
      - zonas_alteradas: lista de bounding boxes {x, y, w, h}
      - mascara_diff   : imagen binaria con zonas diferentes (para visualización)
      - num_zonas      : cantidad de regiones alteradas
    """
    # Asegurar mismo tamaño
    h, w = img_b.shape[:2]
    img_a = cv2.resize(img_a, (w, h))

    # Diferencia absoluta
    diff = cv2.absdiff(img_a, img_b)

    # Umbralizar diferencia (pixels con cambio > 30 de intensidad)
    _, mascara = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

    # Morfología: cerrar huecos pequeños para unir zonas cercanas
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)
    mascara = cv2.dilate(mascara, kernel, iterations=2)

    # Calcular similitud: porcentaje de píxeles idénticos
    total_pixeles = h * w
    pixeles_diff  = cv2.countNonZero(mascara)
    similitud = round((1 - pixeles_diff / total_pixeles) * 100, 2)

    # Encontrar contornos de zonas alteradas
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    zonas = []
    area_minima = 200   # ignorar ruido pequeño
    for c in contornos:
        area = cv2.contourArea(c)
        if area >= area_minima:
            x, y, bw, bh = cv2.boundingRect(c)
            zonas.append({
                "x": int(x), "y": int(y),
                "w": int(bw), "h": int(bh),
                "area": int(area)
            })

    return {
        "similitud":       similitud,
        "zonas_alteradas": zonas,
        "num_zonas":       len(zonas),
        "pixeles_diff":    int(pixeles_diff),
        "total_pixeles":   int(total_pixeles),
    }


# ─── SSIM simplificado (sin scikit-image) ─────────────────────────────────────

def ssim_simple(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """
    Calcula SSIM (Structural Similarity Index) manualmente con OpenCV.
    Retorna valor entre -1 y 1 (1 = idénticas).
    """
    h, w = img_b.shape[:2]
    img_a = cv2.resize(img_a, (w, h)).astype(np.float64)
    img_b = img_b.astype(np.float64)

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    mu1 = cv2.GaussianBlur(img_a, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(img_b, (11, 11), 1.5)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(img_a ** 2, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img_b ** 2, (11, 11), 1.5) - mu2_sq
    sigma12   = cv2.GaussianBlur(img_a * img_b, (11, 11), 1.5) - mu1_mu2

    num = (2 * mu1_mu2 + C1) * (2 * sigma12 + C2)
    den = (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)

    mapa_ssim = num / den
    return float(np.mean(mapa_ssim))


# ─── Pipeline principal ───────────────────────────────────────────────────────

def comparar_con_plantilla(imagen_bytes: bytes, nombre_plantilla: str) -> dict:
    """
    Compara la imagen cargada contra una plantilla guardada en /plantillas/.

    Retorna:
    {
        "exito"          : bool,
        "plantilla_usada": str,
        "alineacion_ok"  : bool,
        "similitud_pixel": float,   # 0-100
        "ssim"           : float,   # -1 a 1
        "zonas_alteradas": list,
        "num_zonas"      : int,
        "veredicto_cv"   : str,     # "Sin alteraciones" / "Sospechoso" / "Alterado"
        "peso_anomalia"  : float,   # contribución al índice de sospecha
        "error"          : str | None
    }
    """
    ruta_plantilla = PLANTILLAS_DIR / nombre_plantilla
    if not ruta_plantilla.exists():
        return {
            "exito": False,
            "error": f"Plantilla '{nombre_plantilla}' no encontrada en /plantillas/",
            "plantilla_usada": nombre_plantilla,
        }

    try:
        # Cargar imágenes
        img_query     = bytes_a_bgr(imagen_bytes)
        img_plantilla = cv2.imread(str(ruta_plantilla))

        if img_plantilla is None:
            return {"exito": False, "error": "No se pudo leer la plantilla"}

        # Preprocesar ambas
        gris_query     = preprocesar(img_query)
        gris_plantilla = preprocesar(img_plantilla)

        # Alinear
        gris_alineada, alineacion_ok = alinear_imagen(gris_query, gris_plantilla)

        # Comparar diferencias
        resultado_diff = detectar_diferencias(gris_alineada, gris_plantilla)
        similitud      = resultado_diff["similitud"]

        # SSIM
        ssim_val = ssim_simple(gris_alineada, gris_plantilla)

        # Veredicto visual
        # Combina similitud de píxeles y número de zonas alteradas
        num_zonas = resultado_diff["num_zonas"]
        if similitud >= 92 and num_zonas == 0:
            veredicto_cv  = "Sin alteraciones"
            peso_anomalia = 0.0
        elif similitud >= 80 or num_zonas <= 2:
            veredicto_cv  = "Sospechoso"
            peso_anomalia = 25.0
        else:
            veredicto_cv  = "Alterado"
            peso_anomalia = 50.0

        # Penalizar más si hay muchas zonas o SSIM muy bajo
        if num_zonas > 5:
            peso_anomalia = min(peso_anomalia + 10, 100)
        if ssim_val < 0.5:
            peso_anomalia = min(peso_anomalia + 15, 100)

        return {
            "exito":           True,
            "plantilla_usada": nombre_plantilla,
            "alineacion_ok":   alineacion_ok,
            "similitud_pixel": similitud,
            "ssim":            round(ssim_val, 4),
            "zonas_alteradas": resultado_diff["zonas_alteradas"],
            "num_zonas":       num_zonas,
            "veredicto_cv":    veredicto_cv,
            "peso_anomalia":   peso_anomalia,
            "error":           None,
        }

    except Exception as e:
        return {
            "exito": False,
            "error": str(e),
            "plantilla_usada": nombre_plantilla,
        }


def comparar_sin_plantilla(imagen_bytes: bytes) -> dict:
    """
    Análisis visual cuando NO hay plantilla disponible.
    Detecta anomalías internas: bordes irregulares, ruido localizado,
    inconsistencias de iluminación que indican edición digital.
    """
    try:
        img = bytes_a_bgr(imagen_bytes)
        gris = preprocesar(img)

        # ── Detección de bordes con Canny ────────────────────────────────────
        bordes = cv2.Canny(gris, 50, 150)
        densidad_bordes = cv2.countNonZero(bordes) / (gris.shape[0] * gris.shape[1])

        # ── Detección de ruido con Laplacian ─────────────────────────────────
        varianza_laplacian = cv2.Laplacian(gris, cv2.CV_64F).var()

        # ── Análisis de bloques: inconsistencia local de ruido ────────────────
        h, w = gris.shape
        tamano_bloque = 50
        varianzas_bloques = []
        for y in range(0, h - tamano_bloque, tamano_bloque):
            for x in range(0, w - tamano_bloque, tamano_bloque):
                bloque = gris[y:y+tamano_bloque, x:x+tamano_bloque]
                varianzas_bloques.append(float(np.var(bloque)))

        if varianzas_bloques:
            var_media    = np.mean(varianzas_bloques)
            var_std      = np.std(varianzas_bloques)
            # Bloques con varianza muy diferente a la media → zona editada
            outliers = [v for v in varianzas_bloques if abs(v - var_media) > 2.5 * var_std]
            pct_outliers = len(outliers) / len(varianzas_bloques) * 100
        else:
            pct_outliers = 0.0

        # ── Clasificación heurística ──────────────────────────────────────────
        indicios = []
        peso = 0.0

        if pct_outliers > 15:
            indicios.append(f"Inconsistencia de ruido en {pct_outliers:.1f}% de bloques (posible edición)")
            peso += 20

        if varianza_laplacian < 50:
            indicios.append("Imagen muy borrosa o de baja calidad (dificulta análisis)")
            peso += 10
        elif varianza_laplacian > 3000:
            indicios.append("Bordes excesivamente marcados (posible recompresión o edición)")
            peso += 15

        if densidad_bordes > 0.25:
            indicios.append("Alta densidad de bordes (posible superposición de texto o sellos)")
            peso += 10

        return {
            "exito":               True,
            "modo":                "sin_plantilla",
            "varianza_laplacian":  round(float(varianza_laplacian), 2),
            "densidad_bordes":     round(densidad_bordes * 100, 2),
            "pct_bloques_anomalos":round(pct_outliers, 2),
            "indicios":            indicios,
            "peso_anomalia":       min(peso, 50.0),   # techo 50 sin plantilla
            "error":               None,
        }

    except Exception as e:
        return {"exito": False, "error": str(e), "modo": "sin_plantilla"}


# ─── Gestión de plantillas ────────────────────────────────────────────────────

def listar_plantillas() -> list[str]:
    """Retorna los nombres de archivos en /plantillas/."""
    extensiones = {".jpg", ".jpeg", ".png"}
    return [
        f.name for f in PLANTILLAS_DIR.iterdir()
        if f.suffix.lower() in extensiones
    ]


def guardar_plantilla(nombre: str, imagen_bytes: bytes) -> str:
    """Guarda una imagen como plantilla de referencia."""
    # Asegurar extensión
    if not any(nombre.endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
        nombre += ".jpg"
    ruta = PLANTILLAS_DIR / nombre
    ruta.write_bytes(imagen_bytes)
    return str(ruta)
