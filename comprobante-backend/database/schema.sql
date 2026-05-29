-- ============================================================
-- schema.sql
-- Crea la base de datos y las tablas del sistema
-- Ejecutar en MySQL con:
--   mysql -u root -p < database/schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS comprobantes_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE comprobantes_db;

-- ── Tabla principal de análisis ───────────────────────────────
CREATE TABLE IF NOT EXISTS analisis (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    nombre_archivo    VARCHAR(255)   NOT NULL,
    fecha_analisis    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    texto_ocr         LONGTEXT,
    confianza_ocr     FLOAT          NOT NULL DEFAULT 0.0,
    campos_detectados JSON,
    veredicto         VARCHAR(20)    NOT NULL,
    indice_sospecha   FLOAT          NOT NULL DEFAULT 0.0,
    confianza_result  FLOAT          NOT NULL DEFAULT 0.0,
    INDEX idx_fecha     (fecha_analisis),
    INDEX idx_veredicto (veredicto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Indicadores / anomalías por análisis ─────────────────────
CREATE TABLE IF NOT EXISTS indicadores (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    analisis_id INT          NOT NULL,
    tipo        VARCHAR(100) NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    peso        FLOAT        NOT NULL DEFAULT 10.0,
    es_critico  TINYINT(1)   NOT NULL DEFAULT 0,
    FOREIGN KEY (analisis_id) REFERENCES analisis(id) ON DELETE CASCADE,
    INDEX idx_analisis (analisis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Configuración ajustable por administrador ─────────────────
CREATE TABLE IF NOT EXISTS configuracion (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    clave       VARCHAR(100) NOT NULL UNIQUE,
    valor       JSON         NOT NULL,
    descripcion VARCHAR(300),
    actualizado DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Valores por defecto de configuración ─────────────────────
INSERT INTO configuracion (clave, valor, descripcion) VALUES
('umbral_sospecha', '30',
 'Índice mínimo de sospecha (0-100) para clasificar como Sospechoso'),
('umbral_fraude', '60',
 'Índice mínimo de sospecha (0-100) para clasificar como Fraudulento'),
('entidades_reconocidas',
 '["bancolombia","banco de bogota","davivienda","bbva","banco popular","nequi","daviplata","pse","payu","epayco","mercado pago","wompi","bold"]',
 'Lista de entidades bancarias y pasarelas de pago reconocidas'),
('campos_obligatorios',
 '["nit","fecha","valor_total","nombre_emisor","codigo_transaccion"]',
 'Campos que debe tener un comprobante válido'),
('tamano_max_mb', '10',
 'Tamaño máximo permitido para la imagen del comprobante en MB')
ON DUPLICATE KEY UPDATE valor = VALUES(valor);

SELECT 'Base de datos creada correctamente.' AS resultado;
