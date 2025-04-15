# scripts/consolidado_categorias.py
"""
Este script procesa y consolida los archivos CSV de cada categoría (Agave, Producción,
Exportaciones por Categoría y por Forma) desde la carpeta /data.

Para cada archivo:
- Lee el contenido ignorando líneas vacías y encabezados falsos.
- Verifica si contiene el encabezado esperado ['SubCategoria', 'Year', 'Valor'].
- Limpia y convierte la columna 'Valor' a tipo float.
- Agrega columnas de Año y Mes extraídas del nombre del archivo.
- Guarda un CSV consolidado por cada carpeta en la raíz de /data.

Autor: Francisco Enríquez
"""

import os
import pandas as pd

# === Configuración de rutas ===

# Directorio base donde están las subcarpetas con los CSV por año
BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Nombres de carpetas a procesar dentro de /data
CARPETAS = [
    "ConsumodeAgaveTotal",
    "ProduccionTotalTequila",
    "ExportacionesTotalCategoria",
    "ExportacionesTotalForma"
]


def limpiar_csv(ruta_csv):
    """
    Limpia y transforma un archivo CSV con columnas SubCategoria, Year y Valor.

    Parámetros:
        ruta_csv (str): Ruta al archivo CSV individual.

    Retorna:
        pd.DataFrame | None: DataFrame limpio o None si el archivo no es válido.
    """
    try:
        # Leer el archivo ignorando comentarios y líneas vacías
        with open(ruta_csv, encoding="utf-8") as f:
            lineas = [l.strip() for l in f if l.strip() and not l.startswith("#")]

        for i, linea in enumerate(lineas):
            columnas = linea.split(",")
            if columnas == ["SubCategoria", "Year", "Valor"]:
                # Extraer los datos válidos desde esa línea en adelante
                datos = [l.split(",") for l in lineas[i + 1:] if len(l.split(",")) == 3]
                if not datos:
                    print(f" Archivo sin datos válidos: {ruta_csv}")
                    return None

                df = pd.DataFrame(datos, columns=columnas)

                # Limpieza de columna Valor
                df["Valor"] = df["Valor"].str.replace(",", "")
                df = df[df["Valor"].str.strip() != ""]  # eliminar vacíos
                df["Valor"] = df["Valor"].astype(float)

                # Extraer Año y Mes del nombre del archivo
                nombre_archivo = os.path.basename(ruta_csv)
                año, mes, *_ = nombre_archivo.split("-")
                df["AñoArchivo"] = int(año)
                df["Mes"] = int(mes)

                return df

        print(f" Encabezado no encontrado en: {ruta_csv}")
        return None

    except Exception as e:
        print(f" Error leyendo {ruta_csv}: {e}")
        return None


# === Procesamiento por carpeta ===

for carpeta in CARPETAS:
    print(f"\n=== Procesando carpeta: {carpeta} ===")
    BASE_DIR = os.path.join(BASE_PATH, carpeta)
    dataframes = []

    # Iterar sobre años posibles
    for año in range(1995, 2026):
        carpeta_año = os.path.join(BASE_DIR, f"{año}-{carpeta}")
        if not os.path.exists(carpeta_año):
            print(f" Carpeta no encontrada: {carpeta_año}")
            continue

        # Procesar todos los archivos .csv del año
        for archivo in os.listdir(carpeta_año):
            if archivo.endswith(".csv"):
                ruta_csv = os.path.join(carpeta_año, archivo)
                print(f" Leyendo: {ruta_csv}")
                df = limpiar_csv(ruta_csv)
                if df is not None:
                    print(f"  Archivo válido: {archivo} ({len(df)} filas)")
                    dataframes.append(df)
                else:
                    print(f"  Saltado: {archivo}")

    # Consolidar y guardar CSV por carpeta
    if dataframes:
        df_final = pd.concat(dataframes, ignore_index=True)
        output_file = os.path.join(BASE_PATH, f"consolidado_{carpeta.lower()}.csv")
        df_final.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n Consolidado guardado como '{output_file}' ({len(df_final)} filas)")
    else:
        print(" No se encontraron archivos válidos para combinar.")
