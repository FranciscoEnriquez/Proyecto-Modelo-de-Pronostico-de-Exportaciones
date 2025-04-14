from fastapi import FastAPI, BackgroundTasks
from app.datos_categorias import descargar_datos_categorias
from app.datos_paises import descargar_datos_paises

app = FastAPI(
    title="API de Descarga de Reportes del CRT",
    description="Esta API permite automatizar la descarga de reportes mensuales del Consejo Regulador del Tequila.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/descargar")
def iniciar_descarga(bg: BackgroundTasks, tipo: str = "categorias"):
    """
    Inicia la descarga automatizada de reportes del CRT en segundo plano.
    
    Tipos válidos:
    - categorias: descarga Producción, Agave, Exportaciones por categoría/forma
    - paises: descarga Exportaciones por país
    """
    if tipo == "categorias":
        bg.add_task(descargar_datos_categorias)
        return {"msg": "Descarga de categorías iniciada en segundo plano."}
    elif tipo == "paises":
        bg.add_task(descargar_datos_paises)
        return {"msg": "Descarga por país iniciada en segundo plano."}
    else:
        return {"error": "Tipo no válido. Usa 'categorias' o 'paises'."}
