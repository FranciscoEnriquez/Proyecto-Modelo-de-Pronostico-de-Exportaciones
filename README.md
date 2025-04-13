# API de Exportaciones de Tequila

Esta API está construida con **FastAPI** y automatiza la descarga mensual de reportes públicos desde el portal del **Consejo Regulador del Tequila (CRT)**.

## 📌 Funcionalidad

Permite automatizar la recolección de datos de exportaciones:
- Por forma (100% agave, mixto, etc.)
- Por país

Las descargas se realizan mediante `Selenium`, y los archivos CSV se organizan automáticamente en subcarpetas por año y tipo.

## 🚀 Endpoints disponibles

| Método | Ruta               | Descripción                                        |
|--------|--------------------|----------------------------------------------------|
| GET    | `/health`          | Verifica si la API está activa                     |
| POST   | `/ingest?tipo=total` | Inicia la descarga por forma (ExportacionesTotal...) |
| POST   | `/ingest?tipo=pais`  | Inicia la descarga por país (ExportacionesPorPais)  |

## 🛠️ Cómo desplegar en Render

Render detectará automáticamente `main.py` dentro de la carpeta `app/` y usará `requirements.txt` para instalar las dependencias.

**Start Command (Render):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 10000
