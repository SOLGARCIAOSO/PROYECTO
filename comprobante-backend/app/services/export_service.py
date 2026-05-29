"""
app/services/export_service.py
CU9 — Exportación de reportes en PDF y CSV
"""
import csv
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet


# ─── CSV ──────────────────────────────────────────────────────────────────────

def generar_csv(registros: list) -> bytes:
    """
    Genera un CSV con el historial de análisis.
    Retorna bytes listos para enviar como respuesta.
    """
    output = io.StringIO()
    escritor = csv.writer(output)

    # Encabezado
    escritor.writerow([
        "ID", "Archivo", "Fecha análisis",
        "Veredicto", "Índice sospecha (%)", "Confianza (%)",
        "Confianza OCR (%)", "Indicadores"
    ])

    for r in registros:
        indicadores_desc = " | ".join(
            i.descripcion for i in (r.indicadores or [])
        )
        escritor.writerow([
            r.id,
            r.nombre_archivo,
            r.fecha_analisis.strftime("%Y-%m-%d %H:%M:%S"),
            r.veredicto,
            f"{r.indice_sospecha:.1f}",
            f"{r.confianza_result:.1f}",
            f"{r.confianza_ocr:.1f}",
            indicadores_desc,
        ])

    return output.getvalue().encode("utf-8-sig")   # BOM para Excel en español


# ─── PDF ──────────────────────────────────────────────────────────────────────

def generar_pdf(registros: list, fecha_inicio=None, fecha_fin=None) -> bytes:
    """
    Genera un PDF con reporte consolidado de análisis.
    Retorna bytes listos para enviar como respuesta.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=inch, bottomMargin=inch
    )
    estilos = getSampleStyleSheet()
    elementos = []

    # — Título ——————————————————————————————————————————————————
    titulo = Paragraph(
        "<b>Reporte de Análisis de Comprobantes</b>",
        estilos["Title"]
    )
    elementos.append(titulo)
    elementos.append(Spacer(1, 0.2 * inch))

    # — Período ——————————————————————————————————————————————————
    periodo = "Todo el historial"
    if fecha_inicio or fecha_fin:
        fi = fecha_inicio.strftime("%Y-%m-%d") if fecha_inicio else "—"
        ff = fecha_fin.strftime("%Y-%m-%d") if fecha_fin else "—"
        periodo = f"Del {fi} al {ff}"
    elementos.append(Paragraph(f"Período: {periodo}", estilos["Normal"]))
    elementos.append(Paragraph(
        f"Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        estilos["Normal"]
    ))
    elementos.append(Spacer(1, 0.3 * inch))

    # — Métricas generales ———————————————————————————————————————
    total = len(registros)
    verificados  = sum(1 for r in registros if r.veredicto == "Verificado")
    sospechosos  = sum(1 for r in registros if r.veredicto == "Sospechoso")
    fraudulentos = sum(1 for r in registros if r.veredicto == "Fraudulento")
    no_det       = sum(1 for r in registros if r.veredicto == "No determinado")

    elementos.append(Paragraph("<b>Métricas generales</b>", estilos["Heading2"]))
    metricas = [
        ["Total analizados", str(total)],
        ["Verificados",      f"{verificados} ({_pct(verificados, total)}%)"],
        ["Sospechosos",      f"{sospechosos} ({_pct(sospechosos, total)}%)"],
        ["Fraudulentos",     f"{fraudulentos} ({_pct(fraudulentos, total)}%)"],
        ["No determinados",  f"{no_det} ({_pct(no_det, total)}%)"],
    ]
    t_metricas = Table(metricas, colWidths=[2.5 * inch, 2 * inch])
    t_metricas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(t_metricas)
    elementos.append(Spacer(1, 0.3 * inch))

    # — Tabla detalle ————————————————————————————————————————————
    if registros:
        elementos.append(Paragraph("<b>Detalle de análisis</b>", estilos["Heading2"]))

        encabezado = ["ID", "Archivo", "Fecha", "Veredicto", "Sospecha%", "Confianza%"]
        filas = [encabezado]
        for r in registros:
            filas.append([
                str(r.id),
                r.nombre_archivo[:30],
                r.fecha_analisis.strftime("%Y-%m-%d"),
                r.veredicto,
                f"{r.indice_sospecha:.1f}",
                f"{r.confianza_result:.1f}",
            ])

        t_detalle = Table(filas, colWidths=[0.4*inch, 2.2*inch, 1*inch, 1.1*inch, 0.8*inch, 0.9*inch])
        t_detalle.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E75B6")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EBF3FA")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (4, 0), (5, -1), "CENTER"),
        ]))
        # Color veredicto
        COLORES_VEREDICTO = {
            "Verificado":     colors.HexColor("#1a7a1a"),
            "Sospechoso":     colors.HexColor("#cc8800"),
            "Fraudulento":    colors.HexColor("#cc0000"),
            "No determinado": colors.grey,
        }
        for i, r in enumerate(registros, start=1):
            color = COLORES_VEREDICTO.get(r.veredicto, colors.black)
            t_detalle.setStyle(TableStyle([
                ("TEXTCOLOR", (3, i), (3, i), color),
                ("FONTNAME",  (3, i), (3, i), "Helvetica-Bold"),
            ]))
        elementos.append(t_detalle)

    doc.build(elementos)
    return buffer.getvalue()


def _pct(parte: int, total: int) -> str:
    if total == 0:
        return "0.0"
    return f"{parte / total * 100:.1f}"
