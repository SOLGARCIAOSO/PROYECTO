# Sistema de Detección de Fraude en Comprobantes

Backend Python (FastAPI) para análisis automatizado de comprobantes de pago colombianos.  
Detecta alteraciones combinando **OCR con Tesseract** y **comparación visual con OpenCV**.

---

## Requisitos previos

| Herramienta | Versión mínima | Instalación |
|-------------|---------------|-------------|
| Python      | 3.10+         | python.org |
| MySQL       | 8.0+          | mysql.com |
| Tesseract   | 5.x           | Ver abajo |

### Instalar Tesseract (Windows)
1. Descargar instalador: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar con los paquetes de idioma **Spanish** y **English**
3. Agregar al PATH: `C:\Program Files\Tesseract-OCR`
4. Verificar: `tesseract --version`

### Instalar Tesseract (Ubuntu/Debian)
```bash
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng
```

---

## Instalación del proyecto

```bash
# 1. Clonar / descomprimir el proyecto
cd comprobante-backend

# 2. Crear entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Configuración

```bash
# Copiar el archivo de ejemplo
cp .env.example .env
```

Editar `.env` con tus credenciales:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password_aqui
DB_NAME=comprobantes_db

UMBRAL_SOSPECHA=30
UMBRAL_FRAUDE=60
```

---

## Crear la base de datos

```bash
# Opción A: con el archivo SQL
mysql -u root -p < database/schema.sql

# Opción B: las tablas se crean automáticamente al arrancar el servidor
```

---

## Ejecutar el servidor

```bash
python run.py
```

El servidor arranca en: **http://localhost:8000**  
Documentación interactiva: **http://localhost:8000/docs**

---

## Pruebas por consola (sin servidor)

```bash
# Todas las pruebas con imágenes sintéticas
python tests/test_consola.py

# Con una imagen real
python tests/test_consola.py --imagen ruta/comprobante.jpg

# Solo un módulo
python tests/test_consola.py --solo ocr
python tests/test_consola.py --solo opencv
python tests/test_consola.py --solo validacion
python tests/test_consola.py --solo clasificacion
python tests/test_consola.py --solo exportacion
```

---

## Endpoints de la API

### Análisis de comprobantes

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/comprobante/analizar` | Analiza un comprobante (OCR + OpenCV) |
| `GET`  | `/comprobante/plantillas` | Lista plantillas de referencia disponibles |
| `POST` | `/comprobante/plantillas` | Sube una nueva plantilla de referencia |

**Ejemplo con curl:**
```bash
# Sin plantilla (análisis interno)
curl -X POST http://localhost:8000/comprobante/analizar \
  -F "archivo=@comprobante.jpg"

# Con plantilla de referencia
curl -X POST http://localhost:8000/comprobante/analizar \
  -F "archivo=@comprobante.jpg" \
  -F "plantilla=bancolombia.jpg"
```

### Historial (CU7)

| Método   | Ruta | Descripción |
|----------|------|-------------|
| `GET`    | `/historial/` | Listar análisis (paginado, filtro por veredicto) |
| `GET`    | `/historial/{id}` | Detalle completo de un análisis |
| `DELETE` | `/historial/{id}` | Eliminar un análisis |

### Configuración (CU8)

| Método   | Ruta | Descripción |
|----------|------|-------------|
| `GET`    | `/configuracion/` | Ver toda la configuración |
| `POST`   | `/configuracion/` | Crear o actualizar clave |
| `DELETE` | `/configuracion/{clave}` | Eliminar clave |

**Claves disponibles:**
- `umbral_sospecha` — índice mínimo para clasificar Sospechoso (default: 30)
- `umbral_fraude` — índice mínimo para clasificar Fraudulento (default: 60)
- `entidades_reconocidas` — lista JSON de bancos reconocidos
- `campos_obligatorios` — lista JSON de campos requeridos

### Exportación (CU9)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/exportar/?formato=csv` | Exportar historial en CSV |
| `GET`  | `/exportar/?formato=pdf` | Exportar historial en PDF |

**Ejemplo con rango de fechas:**
```bash
curl "http://localhost:8000/exportar/?formato=pdf&fecha_inicio=2026-01-01T00:00:00&fecha_fin=2026-12-31T23:59:59" \
  --output reporte.pdf
```

---

## Cómo funciona la detección con OpenCV

```
Imagen cargada
     │
     ▼
Preprocesar (gris + ecualización de histograma)
     │
     ├─── CON plantilla ──────────────────────────────────┐
     │    ORB keypoints → FLANN matching → Homografía     │
     │    Alinear imagen → Diferencia absoluta de píxels  │
     │    Umbralar + morfología → Contornos de zonas      │
     │    SSIM + similitud → Veredicto CV                 │
     │                                                    │
     └─── SIN plantilla ─────────────────────────────────┐│
          Laplacian (nitidez) + Canny (bordes)           ││
          Análisis de bloques (varianza local)           ││
          Heurística de indicios                         ││
                                                         ││
     ◄────────────────────────────────────────────────────┘│
     │                                                     │
     ▼                                                     │
Indicadores visuales (peso)                               │
     +                                                    │
Indicadores de texto (OCR + validación)                   │
     │                                                     │
     ▼                                                     │
Índice de sospecha (0-100)                                │
     │                                                     │
     ├── < umbral_sospecha → Verificado                   │
     ├── entre umbrales  → Sospechoso                     │
     └── >= umbral_fraude → Fraudulento                   │
```

---

## Estructura del proyecto

```
comprobante-backend/
├── app/
│   ├── api/routes/
│   │   ├── comprobante.py    # CU1-CU6: análisis principal
│   │   ├── historial.py      # CU7: consulta de casos
│   │   ├── configuracion.py  # CU8: panel de admin
│   │   └── exportacion.py    # CU9: PDF y CSV
│   ├── core/
│   │   ├── config.py         # Variables de entorno
│   │   └── database.py       # Conexión MySQL / SQLAlchemy
│   ├── models/models.py      # Tablas: analisis, indicadores, configuracion
│   ├── schemas/schemas.py    # Pydantic: validación I/O
│   └── services/
│       ├── ocr_service.py    # Tesseract OCR + preprocesamiento
│       ├── opencv_service.py # Comparación visual con OpenCV
│       ├── validacion_service.py  # Validación de campos colombianos
│       ├── analisis_service.py    # Patrones + clasificación
│       └── export_service.py      # Generación PDF/CSV
├── database/
│   └── schema.sql            # Script de creación de tablas MySQL
├── plantillas/               # Imágenes de referencia para comparación
├── tests/
│   └── test_consola.py       # Pruebas sin servidor
├── .env.example
├── requirements.txt
└── run.py                    # Arranque del servidor
```

---

## Flujo de uso con plantillas (recomendado)

1. Obtener un comprobante **original legítimo** de cada banco/pasarela
2. Subirlo como plantilla:
   ```bash
   curl -X POST http://localhost:8000/comprobante/plantillas \
     -F "archivo=@bancolombia_original.jpg" \
     -F "nombre=bancolombia"
   ```
3. Al analizar, indicar la plantilla correspondiente:
   ```bash
   curl -X POST http://localhost:8000/comprobante/analizar \
     -F "archivo=@comprobante_sospechoso.jpg" \
     -F "plantilla=bancolombia.jpg"
   ```

Sin plantilla, el sistema igual detecta anomalías mediante análisis interno de la imagen.
