"""
app/services/validacion_service.py
CU3 — Validación de campos obligatorios del comprobante
"""
import re
from datetime import datetime


# Entidades bancarias y pasarelas colombianas reconocidas
ENTIDADES_RECONOCIDAS = {
    "bancolombia", "banco de bogota", "davivienda", "bbva", "banco popular",
    "banco agrario", "banco av villas", "banco caja social", "banco gnb sudameris",
    "banco pichincha", "banco falabella", "banco finandina", "banco mundo mujer",
    "banco w", "citibank", "scotiabank colpatria", "itau", "nequi", "daviplata",
    "pse", "payu", "epayco", "mercado pago", "wompi", "bold", "adyen",
    "redeban", "credibanco", "tuya", "epm", "claro pay", "movistar",
    "codensa", "almacenes éxito", "efecty", "baloto", "movilred", "pago express",
}


def validar_nit(nit: str | None) -> tuple[bool, str]:
    """Valida formato NIT colombiano: XXXXXXXXX-X"""
    if not nit:
        return False, "NIT ausente"
    limpio = re.sub(r'[\s.]', '', nit)
    if re.fullmatch(r'\d{7,10}-?\d?', limpio):
        return True, "OK"
    return False, f"Formato de NIT inválido: '{nit}'"


def validar_fecha(fecha: str | None) -> tuple[bool, str]:
    """Valida que la fecha sea parseable y no futura."""
    if not fecha:
        return False, "Fecha ausente"
    formatos = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]
    for fmt in formatos:
        try:
            dt = datetime.strptime(fecha, fmt)
            if dt > datetime.utcnow():
                return False, "Fecha futura sospechosa"
            return True, "OK"
        except ValueError:
            continue
    return False, f"Fecha con formato no reconocido: '{fecha}'"


def validar_valor(valor: str | None) -> tuple[bool, str]:
    """Valida que el valor sea numérico y mayor a cero."""
    if not valor:
        return False, "Valor total ausente"
    # Quitar separadores de miles y símbolo $
    limpio = re.sub(r'[\s$.,]', '', valor)
    try:
        numero = float(limpio.replace(',', '.'))
        if numero <= 0:
            return False, "Valor total debe ser mayor a cero"
        return True, "OK"
    except ValueError:
        return False, f"Valor no numérico: '{valor}'"


def validar_emisor(nombre: str | None) -> tuple[bool, str]:
    """Valida presencia y reconocimiento del emisor."""
    if not nombre:
        return False, "Nombre del emisor ausente"
    nombre_lower = nombre.lower().strip()
    for entidad in ENTIDADES_RECONOCIDAS:
        if entidad in nombre_lower:
            return True, "OK"
    # Emisor presente pero no reconocido → válido con advertencia
    return True, f"Emisor '{nombre}' no está en la lista de referencia"


def validar_codigo(codigo: str | None) -> tuple[bool, str]:
    """Valida presencia del código de transacción."""
    if not codigo:
        return False, "Código de transacción ausente"
    if len(codigo) < 4:
        return False, "Código de transacción demasiado corto"
    return True, "OK"


def validar_campos(campos: dict) -> dict:
    """
    Ejecuta todas las validaciones.
    Retorna dict con resultado por campo y porcentaje total de validez.
    """
    validaciones = {}

    ok_nit,    msg_nit    = validar_nit(campos.get("nit"))
    ok_fecha,  msg_fecha  = validar_fecha(campos.get("fecha"))
    ok_valor,  msg_valor  = validar_valor(campos.get("valor_total"))
    ok_emisor, msg_emisor = validar_emisor(campos.get("nombre_emisor"))
    ok_codigo, msg_codigo = validar_codigo(campos.get("codigo_transaccion"))

    validaciones["nit"]               = {"valido": ok_nit,    "mensaje": msg_nit}
    validaciones["fecha"]             = {"valido": ok_fecha,  "mensaje": msg_fecha}
    validaciones["valor_total"]       = {"valido": ok_valor,  "mensaje": msg_valor}
    validaciones["nombre_emisor"]     = {"valido": ok_emisor, "mensaje": msg_emisor}
    validaciones["codigo_transaccion"] = {"valido": ok_codigo, "mensaje": msg_codigo}

    total = len(validaciones)
    validos = sum(1 for v in validaciones.values() if v["valido"])
    validaciones["_porcentaje_valido"] = round((validos / total) * 100, 1)

    return validaciones


def es_emisor_reconocido(nombre: str | None) -> bool:
    """Comprueba si el emisor está en la lista de referencia."""
    if not nombre:
        return False
    nombre_lower = nombre.lower()
    return any(e in nombre_lower for e in ENTIDADES_RECONOCIDAS)
