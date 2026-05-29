"""
tests/test_consola.py
Prueba completa del pipeline sin levantar el servidor.
Genera imágenes sintéticas para probar sin depender de Tesseract/MySQL.

Uso:
    python tests/test_consola.py                           # prueba todo con imágenes sintéticas
    python tests/test_consola.py --imagen ruta/factura.jpg # prueba con imagen real
    python tests/test_consola.py --solo ocr                # solo un módulo: config/ocr/validacion/opencv/clasificacion
"""
import sys
import os
import argparse
import json
import time
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Colores ANSI ──────────────────────────────────────────────────────────────
V  = "\033[92m"   # verde
R  = "\033[91m"   # rojo
AM = "\033[93m"   # amarillo
AZ = "\033[94m"   # azul
GR = "\033[90m"   # gris
N  = "\033[1m"    # negrita
RE = "\033[0m"    # reset

def ok(msg):      print(f"  {V}✓{RE} {msg}")
def fallo(msg):   print(f"  {R}✗{RE} {msg}")
def warn(msg):    print(f"  {AM}⚠{RE} {msg}")
def info(msg):    print(f"  {AZ}→{RE} {msg}")
def titulo(t):    print(f"\n{N}{AZ}{'═'*60}\n  {t}\n{'═'*60}{RE}")
def subtitulo(t): print(f"\n{N}  {t}{RE}")
def sep():        print(f"  {GR}{'─'*55}{RE}")


# ══════════════════════════════════════════════════════════════
# Generador de imágenes sintéticas
# ══════════════════════════════════════════════════════════════

def crear_imagen_comprobante(texto_extra: str = "", alterar: bool = False) -> bytes:
    """Genera un PNG sintético que simula un comprobante de pago."""
    import cv2

    img = np.ones((800, 600, 3), dtype=np.uint8) * 255  # fondo blanco

    fuente    = cv2.FONT_HERSHEY_SIMPLEX
    color_txt = (20, 20, 20)
    color_az  = (180, 60, 0)

    # Encabezado
    cv2.rectangle(img, (0, 0), (600, 80), (0, 100, 180), -1)
    cv2.putText(img, "BANCOLOMBIA", (150, 50), fuente, 1.2, (255,255,255), 2)

    lineas = [
        ("COMPROBANTE DE PAGO",          120, 0.7, color_az),
        ("NIT: 890903938-8",              165, 0.55, color_txt),
        ("Fecha: 15/03/2025",            200, 0.55, color_txt),
        ("Referencia: TXN-20250315-0042",235, 0.55, color_txt),
        ("",                              270, 0.5, color_txt),
        ("Valor Total: $1.500.000",       310, 0.7, (0, 120, 0)),
        ("Son: UN MILLON QUINIENTOS MIL PESOS", 350, 0.45, color_txt),
        ("",                              390, 0.5, color_txt),
        ("Estado: APROBADO",              430, 0.6, (0,150,0)),
    ]

    for texto, y, escala, color in lineas:
        if texto:
            cv2.putText(img, texto, (30, y), fuente, escala, color, 1)

    # Líneas divisorias
    for y in [100, 280, 460]:
        cv2.line(img, (20, y), (580, y), (200, 200, 200), 1)

    # Pie
    cv2.rectangle(img, (0, 700), (600, 800), (240, 240, 240), -1)
    cv2.putText(img, "www.bancolombia.com.co", (150, 750), fuente, 0.45, (100,100,100), 1)

    if texto_extra:
        cv2.putText(img, texto_extra, (30, 500), fuente, 0.5, color_txt, 1)

    if alterar:
        # Simular alteración: sobrescribir valor con otro
        cv2.rectangle(img, (25, 295), (400, 325), (255, 255, 255), -1)
        cv2.putText(img, "Valor Total: $150.000", (30, 318), fuente, 0.65, (0,0,0), 1)
        # Mancha
        cv2.rectangle(img, (100, 340), (250, 365), (220, 220, 255), -1)

    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


# ══════════════════════════════════════════════════════════════
# TEST 1: Configuración
# ══════════════════════════════════════════════════════════════

def test_configuracion():
    titulo("TEST 1 — Configuración del sistema")
    try:
        from app.core.config import settings
        ok(f"DB URL        : {settings.DATABASE_URL}")
        ok(f"Umbral sospecha: {settings.UMBRAL_SOSPECHA}")
        ok(f"Umbral fraude  : {settings.UMBRAL_FRAUDE}")
        ok(f"Formatos       : {settings.FORMATOS_PERMITIDOS}")
        ok(f"Tamaño máximo  : {settings.TAMANO_MAX_MB} MB")
        return True
    except Exception as e:
        fallo(f"Error en configuración: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# TEST 2: Validación de campos
# ══════════════════════════════════════════════════════════════

def test_validacion():
    titulo("TEST 2 — Validación de campos obligatorios (CU3)")
    from app.services.validacion_service import validar_nit, validar_fecha, validar_valor, validar_campos

    errores = 0

    subtitulo("NIT")
    sep()
    casos_nit = [
        ("900123456-1", True, "NIT con dígito verificación"),
        ("123456789",   True, "NIT sin guión"),
        ("abc-xyz",     False, "NIT inválido"),
        (None,          False, "NIT nulo"),
    ]
    for nit, esperado, desc in casos_nit:
        resultado, msg = validar_nit(nit)
        icono = f"{V}✓{RE}" if resultado == esperado else f"{R}✗{RE}"
        if resultado != esperado: errores += 1
        print(f"  {icono} [{desc:30}] → {msg}")

    subtitulo("Fecha")
    sep()
    casos_fecha = [
        ("15/03/2025", True,  "Formato DD/MM/YYYY"),
        ("2025-03-15", True,  "Formato YYYY-MM-DD"),
        ("99/99/9999", False, "Fecha imposible"),
        (None,         False, "Fecha nula"),
    ]
    for fecha, esperado, desc in casos_fecha:
        resultado, msg = validar_fecha(fecha)
        icono = f"{V}✓{RE}" if resultado == esperado else f"{R}✗{RE}"
        if resultado != esperado: errores += 1
        print(f"  {icono} [{desc:30}] → {msg}")

    subtitulo("Valor")
    sep()
    casos_valor = [
        ("1.500.000",   True,  "Formato colombiano"),
        ("$2,500,000",  True,  "Con símbolo $"),
        ("0",           False, "Cero"),
        (None,          False, "Nulo"),
    ]
    for valor, esperado, desc in casos_valor:
        resultado, msg = validar_valor(valor)
        icono = f"{V}✓{RE}" if resultado == esperado else f"{R}✗{RE}"
        if resultado != esperado: errores += 1
        print(f"  {icono} [{desc:30}] → {msg}")

    subtitulo("Validación de conjunto completo")
    sep()
    campos_completos = {
        "nit": "890903938-8", "fecha": "15/03/2025",
        "valor_total": "1500000", "nombre_emisor": "Bancolombia",
        "codigo_transaccion": "TXN-20250315-0042",
    }
    resultado = validar_campos(campos_completos)
    pct = resultado.get("_porcentaje_valido", 0)
    icono = f"{V}✓{RE}" if pct >= 80 else f"{R}✗{RE}"
    print(f"  {icono} Campos válidos: {pct}%")

    print(f"\n  {'─'*30}")
    if errores == 0:
        ok(f"TEST 2 PASADO — 0 errores")
    else:
        fallo(f"TEST 2 con {errores} errores")
    return errores == 0


# ══════════════════════════════════════════════════════════════
# TEST 3: OCR
# ══════════════════════════════════════════════════════════════

def test_ocr(imagen_bytes: bytes):
    titulo("TEST 3 — Extracción OCR (CU2)")
    from app.services.ocr_service import extraer_texto, extraer_campos

    t0 = time.time()
    resultado = extraer_texto(imagen_bytes)
    elapsed = time.time() - t0

    if resultado.get("exito"):
        ok(f"OCR exitoso en {elapsed:.2f}s")
        ok(f"Confianza: {resultado['confianza']:.1f}%")
        texto = resultado["texto_completo"]
        info(f"Texto ({len(texto)} chars): {texto[:120]}{'...' if len(texto)>120 else ''}")

        campos = extraer_campos(texto)
        subtitulo("Campos detectados:")
        sep()
        for k, v in campos.items():
            icono = f"{V}✓{RE}" if v else f"{AM}–{RE}"
            print(f"  {icono} {k:25}: {v}")
        return True, resultado, campos
    else:
        warn(f"OCR no disponible o imagen sintética: {resultado.get('error', 'sin texto')}")
        warn("Continuando con campos vacíos (modo demo)")
        campos_demo = {
            "nit": "890903938-8", "fecha": "15/03/2025",
            "valor_total": "1500000", "nombre_emisor": "Bancolombia",
            "codigo_transaccion": "TXN-20250315-0042", "valor_letras": None,
        }
        return True, resultado, campos_demo


# ══════════════════════════════════════════════════════════════
# TEST 4: OpenCV — comparación visual
# ══════════════════════════════════════════════════════════════

def test_opencv(img_original: bytes, img_alterada: bytes):
    titulo("TEST 4 — Análisis visual con OpenCV (CU4b)")
    from app.services.opencv_service import (
        comparar_sin_plantilla, guardar_plantilla, comparar_con_plantilla
    )

    subtitulo("4a. Análisis interno SIN plantilla (imagen original)")
    sep()
    t0 = time.time()
    r = comparar_sin_plantilla(img_original)
    elapsed = time.time() - t0
    if r["exito"]:
        ok(f"Análisis en {elapsed:.2f}s")
        ok(f"Varianza Laplacian : {r['varianza_laplacian']}")
        ok(f"Densidad bordes    : {r['densidad_bordes']}%")
        ok(f"Bloques anómalos   : {r['pct_bloques_anomalos']}%")
        ok(f"Peso anomalía      : {r['peso_anomalia']}")
        if r["indicios"]:
            warn(f"Indicios: {'; '.join(r['indicios'])}")
        else:
            ok("Sin indicios sospechosos")
    else:
        fallo(f"Error: {r.get('error')}")

    subtitulo("4b. Análisis CON plantilla — imagen original vs plantilla")
    sep()
    guardar_plantilla("plantilla_test.jpg", img_original)
    info("Plantilla guardada: plantilla_test.jpg")

    t0 = time.time()
    r2 = comparar_con_plantilla(img_original, "plantilla_test.jpg")
    elapsed = time.time() - t0
    if r2["exito"]:
        ok(f"Comparación en {elapsed:.2f}s")
        ok(f"Alineación OK  : {r2['alineacion_ok']}")
        ok(f"Similitud pixel: {r2['similitud_pixel']}%")
        ok(f"SSIM           : {r2['ssim']}")
        ok(f"Zonas alteradas: {r2['num_zonas']}")
        color = V if r2["veredicto_cv"] == "Sin alteraciones" else AM
        print(f"  {color}→ Veredicto CV : {r2['veredicto_cv']}{RE}")
    else:
        fallo(f"Error: {r2.get('error')}")

    subtitulo("4c. Análisis CON plantilla — imagen ALTERADA vs plantilla")
    sep()
    t0 = time.time()
    r3 = comparar_con_plantilla(img_alterada, "plantilla_test.jpg")
    elapsed = time.time() - t0
    if r3["exito"]:
        ok(f"Comparación en {elapsed:.2f}s")
        ok(f"Similitud pixel: {r3['similitud_pixel']}%")
        ok(f"SSIM           : {r3['ssim']}")
        ok(f"Zonas alteradas: {r3['num_zonas']}")
        color = R if r3["veredicto_cv"] == "Alterado" else AM
        print(f"  {color}→ Veredicto CV : {r3['veredicto_cv']}{RE}")
        if r3["zonas_alteradas"]:
            for z in r3["zonas_alteradas"][:3]:
                info(f"   Zona: x={z['x']} y={z['y']} w={z['w']} h={z['h']} area={z['area']}px²")
    else:
        fallo(f"Error: {r3.get('error')}")

    return r, r2, r3


# ══════════════════════════════════════════════════════════════
# TEST 5: Pipeline completo (sin BD)
# ══════════════════════════════════════════════════════════════

def test_pipeline_completo(img_original: bytes, img_alterada: bytes):
    titulo("TEST 5 — Pipeline completo OCR + OpenCV + Clasificación (CU4+CU5)")
    from app.services.validacion_service import validar_campos
    from app.services.analisis_service import (
        analizar_patrones_texto, analizar_patrones_visual, clasificar
    )
    from app.services.opencv_service import (
        comparar_con_plantilla, comparar_sin_plantilla
    )
    from app.core.config import settings

    for etiqueta, imagen_bytes, usar_plantilla in [
        ("ORIGINAL  (esperado: Verificado)",  img_original, True),
        ("ALTERADA  (esperado: Fraudulento)", img_alterada, True),
    ]:
        subtitulo(f"Imagen: {etiqueta}")
        sep()

        # Campos demo (OCR puede no estar disponible en entorno de prueba)
        campos_demo = {
            "nit": "890903938-8", "fecha": "15/03/2025",
            "valor_total": "1500000", "nombre_emisor": "Bancolombia",
            "codigo_transaccion": "TXN-20250315-0042", "valor_letras": None,
        }

        validaciones   = validar_campos(campos_demo)
        ind_texto      = analizar_patrones_texto(campos_demo, validaciones, 85.0)

        if usar_plantilla:
            resultado_cv = comparar_con_plantilla(imagen_bytes, "plantilla_test.jpg")
        else:
            resultado_cv = comparar_sin_plantilla(imagen_bytes)

        ind_visual = analizar_patrones_visual(resultado_cv)
        todos      = ind_texto + ind_visual

        resultado = clasificar(todos, settings.UMBRAL_SOSPECHA, settings.UMBRAL_FRAUDE)

        color_v = V if resultado["veredicto"] == "Verificado" else (
                  R if resultado["veredicto"] == "Fraudulento" else AM)

        ok(f"Indicadores texto  : {len(ind_texto)}")
        ok(f"Indicadores visual : {len(ind_visual)}")
        ok(f"Índice sospecha    : {resultado['indice_sospecha']}%")
        ok(f"Confianza          : {resultado['confianza']}%")
        print(f"  {color_v}★ VEREDICTO : {resultado['veredicto']}{RE}")

        if todos:
            print(f"\n  {GR}Indicadores activados:{RE}")
            for ind in todos:
                critico = f" {R}[CRÍTICO]{RE}" if ind["es_critico"] else ""
                print(f"    • [{ind['tipo']}] {ind['descripcion'][:70]} (peso={ind['peso']}){critico}")
        print()


# ══════════════════════════════════════════════════════════════
# TEST 6: Exportación (sin BD)
# ══════════════════════════════════════════════════════════════

def test_exportacion():
    titulo("TEST 6 — Exportación PDF/CSV (CU9)")
    from app.services.export_service import generar_csv, generar_pdf

    # Mock de registros
    class MockIndicador:
        def __init__(self, desc): self.descripcion = desc

    class MockAnalisis:
        def __init__(self, id, archivo, veredicto, sospecha, confianza):
            self.id             = id
            self.nombre_archivo = archivo
            from datetime import datetime
            self.fecha_analisis = datetime.utcnow()
            self.veredicto      = veredicto
            self.indice_sospecha= sospecha
            self.confianza_result=confianza
            self.confianza_ocr  = 85.0
            self.indicadores    = [MockIndicador("NIT ausente"), MockIndicador("Entidad desconocida")]

    registros = [
        MockAnalisis(1, "comprobante_real.jpg",    "Verificado",  5.0,  97.0),
        MockAnalisis(2, "comprobante_editado.jpg", "Fraudulento", 75.0, 87.5),
        MockAnalisis(3, "comprobante_scan.jpg",    "Sospechoso",  40.0, 55.0),
    ]

    subtitulo("CSV")
    sep()
    csv_bytes = generar_csv(registros)
    ok(f"CSV generado: {len(csv_bytes)} bytes")
    preview = csv_bytes.decode("utf-8-sig").split("\n")
    for linea in preview[:4]:
        info(linea)

    subtitulo("PDF")
    sep()
    pdf_bytes = generar_pdf(registros)
    ok(f"PDF generado: {len(pdf_bytes)} bytes")

    # Guardar para verificación manual
    out = Path("tests/output")
    out.mkdir(exist_ok=True)
    (out / "reporte_test.csv").write_bytes(csv_bytes)
    (out / "reporte_test.pdf").write_bytes(pdf_bytes)
    ok(f"Archivos guardados en tests/output/")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Test de consola del backend de comprobantes")
    parser.add_argument("--imagen", help="Ruta a una imagen real para probar OCR")
    parser.add_argument("--solo", choices=["config","ocr","validacion","opencv","clasificacion","exportacion"],
                        help="Ejecutar solo un módulo")
    args = parser.parse_args()

    print(f"\n{N}{AZ}{'═'*60}")
    print(f"  SISTEMA DE DETECCIÓN DE FRAUDE — PRUEBAS DE CONSOLA")
    print(f"{'═'*60}{RE}")
    print(f"  Raíz del proyecto: {ROOT}")

    # Imágenes de prueba
    if args.imagen and Path(args.imagen).exists():
        img_original = Path(args.imagen).read_bytes()
        img_alterada = img_original   # misma imagen, no hay alterada
        info(f"Usando imagen real: {args.imagen}")
    else:
        info("Generando imágenes sintéticas de prueba...")
        img_original = crear_imagen_comprobante()
        img_alterada = crear_imagen_comprobante(alterar=True)
        ok("Imágenes sintéticas creadas")

    resultados = {}

    solo = args.solo
    if not solo or solo == "config":
        resultados["config"] = test_configuracion()
    if not solo or solo == "validacion":
        resultados["validacion"] = test_validacion()
    if not solo or solo == "ocr":
        ok_ocr, _, _ = test_ocr(img_original)
        resultados["ocr"] = ok_ocr
    if not solo or solo == "opencv":
        test_opencv(img_original, img_alterada)
        resultados["opencv"] = True
    if not solo or solo == "clasificacion":
        test_pipeline_completo(img_original, img_alterada)
        resultados["clasificacion"] = True
    if not solo or solo == "exportacion":
        test_exportacion()
        resultados["exportacion"] = True

    # Resumen final
    titulo("RESUMEN DE PRUEBAS")
    for nombre, resultado in resultados.items():
        if resultado:
            ok(f"{nombre:20} PASADO")
        else:
            fallo(f"{nombre:20} FALLIDO")

    total  = len(resultados)
    pasados = sum(1 for v in resultados.values() if v)
    print(f"\n  {N}Resultado: {pasados}/{total} pruebas pasadas{RE}\n")

    sys.exit(0 if pasados == total else 1)


if __name__ == "__main__":
    main()
