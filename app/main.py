# main.py

from fastapi import FastAPI, BackgroundTasks
from app.datos_categorias import descargar_datos_categorias
from app.datos_paises import descargar_datos_paises

# Crear instancia de la aplicación FastAPI con metadatos
app = FastAPI(
    title="API de Descarga de Reportes del CRT",
    description="Esta API permite automatizar la descarga de reportes mensuales del Consejo Regulador del Tequila.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    """
    Endpoint de verificación de estado.

    Retorna un diccionario simple para confirmar que el servidor está activo.
    """
    return {"status": "ok"}

@app.post("/descargar")
def iniciar_descarga(bg: BackgroundTasks, tipo: str = "categorias"):
    """
    Inicia la descarga automatizada de reportes del CRT en segundo plano.

    Parámetros:
    - tipo (str): Tipo de descarga a realizar. Puede ser:
        * 'categorias': descarga Producción Total, Consumo de Agave Total,
                        Exportaciones Totales por Categoría y por Forma.
        * 'paises': descarga Exportaciones por País.

    El proceso se ejecuta en segundo plano para no bloquear la respuesta HTTP.

    Retorna:
        Mensaje informativo sobre el estado de la solicitud.
    """
    if tipo == "categorias":
        bg.add_task(descargar_datos_categorias)
        return {"msg": "Descarga de categorías iniciada en segundo plano."}
    
    elif tipo == "paises":
        bg.add_task(descargar_datos_paises)
        return {"msg": "Descarga por país iniciada en segundo plano."}
    
    else:
        return {
            "error": "Tipo no válido. Usa 'categorias' o 'paises'."
        }
