"""
app/services/alerta_service.py
Envío de alertas por correo cuando se detecta fraude o sospecha
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Configuración
CORREO_ORIGEN = "paylents@gmail.com"
CORREO_DESTINO = "david652225@gmail.com"
APP_PASSWORD = "rkvwmnppgvgyeqmj"


def enviar_alerta(analisis_id: int, veredicto: str, indice_sospecha: float,
                  confianza: float, campos: dict, indicadores: list):
    """
    Envía un correo de alerta cuando el veredicto es Sospechoso o Fraudulento.
    """
    if veredicto not in ("Sospechoso", "Fraudulento"):
        return False

    try:
        # Construir cuerpo del correo
        color = "#ffb300" if veredicto == "Sospechoso" else "#ff3d5a"
        emoji = "⚠️" if veredicto == "Sospechoso" else "🚨"
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Campos detectados
        campos_html = ""
        nombres = {
            "nit": "NIT",
            "fecha": "Fecha",
            "valor_total": "Valor total",
            "nombre_emisor": "Emisor",
            "codigo_transaccion": "Código transacción"
        }
        for k, nombre in nombres.items():
            val = campos.get(k) or "No detectado"
            color_campo = "#e8eaf0" if campos.get(k) else "#ff3d5a"
            campos_html += f"""
            <tr>
                <td style="padding:6px 12px;font-family:monospace;font-size:12px;color:#7a7f8e;">{nombre}</td>
                <td style="padding:6px 12px;font-size:13px;color:{color_campo};">{val}</td>
            </tr>"""

        # Indicadores
        indicadores_html = ""
        for ind in indicadores:
            badge_color = "#ff3d5a" if ind.get("es_critico") else "#ffb300"
            badge_text = "CRÍTICO" if ind.get("es_critico") else f"peso {ind.get('peso', 0)}"
            indicadores_html += f"""
            <tr>
                <td style="padding:6px 12px;">
                    <span style="background:rgba(255,61,90,0.15);color:{badge_color};
                                 font-family:monospace;font-size:11px;padding:2px 6px;
                                 border-radius:4px;">{badge_text}</span>
                </td>
                <td style="padding:6px 12px;font-size:13px;color:#7a7f8e;">
                    {ind.get('descripcion', '')}
                </td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background:#0a0c0f;font-family:'DM Sans',Arial,sans-serif;">
        <div style="max-width:600px;margin:0 auto;padding:24px;">

            <!-- Header -->
            <div style="text-align:center;margin-bottom:24px;">
                <h1 style="font-family:monospace;color:#00e5a0;font-size:20px;letter-spacing:4px;margin:0;">
                    PAY<span style="color:#7a7f8e;">LENS</span>
                </h1>
                <p style="color:#7a7f8e;font-size:12px;font-family:monospace;margin:4px 0 0;">
                    Sistema de Detección de Fraude
                </p>
            </div>

            <!-- Banner veredicto -->
            <div style="background:rgba(255,61,90,0.08);border:1px solid {color};
                        border-radius:12px;padding:20px 24px;margin-bottom:20px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:32px;">{emoji}</span>
                    <div>
                        <h2 style="color:{color};font-family:monospace;font-size:22px;
                                   margin:0 0 4px;letter-spacing:2px;">
                            {veredicto.upper()}
                        </h2>
                        <p style="color:#7a7f8e;margin:0;font-size:13px;">
                            Análisis #{analisis_id} · {fecha}
                        </p>
                    </div>
                </div>
            </div>

            <!-- Métricas -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
                <div style="background:#111318;border:1px solid #2a2d36;border-radius:8px;
                            padding:16px;text-align:center;">
                    <div style="font-family:monospace;font-size:28px;color:{color};font-weight:700;">
                        {indice_sospecha:.1f}%
                    </div>
                    <div style="font-size:12px;color:#7a7f8e;">Índice de sospecha</div>
                </div>
                <div style="background:#111318;border:1px solid #2a2d36;border-radius:8px;
                            padding:16px;text-align:center;">
                    <div style="font-family:monospace;font-size:28px;color:#00e5a0;font-weight:700;">
                        {confianza:.1f}%
                    </div>
                    <div style="font-size:12px;color:#7a7f8e;">Confianza del sistema</div>
                </div>
            </div>

            <!-- Campos detectados -->
            <div style="background:#111318;border:1px solid #2a2d36;border-radius:8px;
                        padding:16px;margin-bottom:16px;">
                <h3 style="font-family:monospace;font-size:11px;color:#7a7f8e;
                           text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;">
                    ● Campos detectados (OCR)
                </h3>
                <table style="width:100%;border-collapse:collapse;">
                    {campos_html}
                </table>
            </div>

            <!-- Indicadores -->
            <div style="background:#111318;border:1px solid #2a2d36;border-radius:8px;
                        padding:16px;margin-bottom:16px;">
                <h3 style="font-family:monospace;font-size:11px;color:#7a7f8e;
                           text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;">
                    ● Indicadores activados
                </h3>
                <table style="width:100%;border-collapse:collapse;">
                    {indicadores_html if indicadores_html else
                     '<tr><td style="color:#7a7f8e;font-size:13px;padding:6px 12px;">Sin indicadores</td></tr>'}
                </table>
            </div>

            <!-- Recomendación -->
            <div style="background:rgba(0,102,255,0.08);border:1px solid rgba(0,102,255,0.3);
                        border-radius:8px;padding:16px;margin-bottom:24px;">
                <p style="color:#e8eaf0;font-size:13px;margin:0;line-height:1.6;">
                    <strong style="color:#0066ff;">Recomendación:</strong>
                    Revisar el comprobante manualmente y verificar el NIT del emisor en
                    <a href="https://muisca.dian.gov.co" style="color:#00e5a0;">muisca.dian.gov.co</a>.
                    No procesar el pago hasta confirmar la autenticidad del documento.
                </p>
            </div>

            <!-- Footer -->
            <p style="text-align:center;color:#7a7f8e;font-size:11px;font-family:monospace;">
                PayLens · Alerta automática del sistema · {fecha}
            </p>

        </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{emoji} PayLens — Alerta: Comprobante {veredicto} #{analisis_id}"
        msg["From"] = f"PayLens Alertas <{CORREO_ORIGEN}>"
        msg["To"] = CORREO_DESTINO
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(CORREO_ORIGEN, APP_PASSWORD)
            smtp.sendmail(CORREO_ORIGEN, CORREO_DESTINO, msg.as_string())

        return True

    except Exception as e:
        print(f"Error enviando alerta: {e}")
        return False
