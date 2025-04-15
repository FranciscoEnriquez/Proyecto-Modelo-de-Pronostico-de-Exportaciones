# scripts/consolidado_pais.py
"""
Este script procesa y consolida todos los archivos CSV contenidos en la carpeta
ExportacionesPais, dentro del proyecto Modelo_Pronosticos/data.

Por cada archivo:
- Lee el contenido omitiendo encabezados adicionales.
- Verifica que tenga el formato esperado de columnas.
- Limpia las columnas numéricas eliminando comas y valores vacíos.
- Extrae el año y mes desde el nombre del archivo.
- Renombra columnas técnicas a nombres descriptivos.
- Guarda el resultado consolidado en un solo archivo CSV.

Autor: Francisco Enríquez
"""

import os
import pandas as pd

# === Configuración de rutas ===

# Directorio base donde se encuentran los CSV por año
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ExportacionesPais")

# Ruta de salida para el archivo consolidado
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "consolidado_exportaciones_pais.csv")


def limpiar_exportaciones_pais(ruta_csv):
    """
    Limpia y transforma un archivo CSV de exportaciones por país.

    Parámetros:
        ruta_csv (str): Ruta al archivo CSV individual.

    Retorna:
        pd.DataFrame | None: DataFrame limpio o None si el archivo no es válido.
    """
    try:
        # Leer el CSV desde la fila 3 (skiprows=2) donde están los encabezados reales
        df = pd.read_csv(ruta_csv, skiprows=2, quotechar='"', encoding="utf-8")

        # Validar el formato esperado
        columnas_esperadas = ["NombrePais", "textbox11", "Categoria", "textbox14", "Clase", "textbox17"]
        if df.shape[1] != 6 or list(df.columns) != columnas_esperadas:
            print(f" ⚠ Formato inesperado: {ruta_csv} ({df.shape[1]} columnas)")
            return None

        # Limpieza de columnas numéricas (quitar comas y convertir a float)
        for col in ["textbox11", "textbox14", "textbox17"]:
            df[col] = df[col].astype(str).str.replace(",", "").str.strip()
            df[col] = df[col].replace('', '0').astype(float)

        # Extraer año y mes desde el nombre del archivo
        nombre_archivo = os.path.basename(ruta_csv)
        año, mes, *_ = nombre_archivo.split("-")
        df["AñoArchivo"] = int(año)
        df["Mes"] = int(mes)

        return df

    except Exception as e:
        print(f"  Error procesando {ruta_csv}: {e}")
        return None


# === Procesamiento de todos los archivos CSV ===

dataframes = []  # Lista para almacenar los DataFrames limpios
print("\n=== Procesando carpeta: ExportacionesPais ===")

# Iterar sobre cada año desde 1995 a 2025
for año in range(1995, 2026):
    carpeta_año = os.path.join(BASE_DIR, f"{año}-ExportacionesPais")
    if not os.path.exists(carpeta_año):
        print(f" Carpeta no encontrada: {carpeta_año}")
        continue

    # Procesar cada archivo CSV del año
    for archivo in os.listdir(carpeta_año):
        if archivo.endswith(".csv"):
            ruta_csv = os.path.join(carpeta_año, archivo)
            print(f" Leyendo: {ruta_csv}")
            df = limpiar_exportaciones_pais(ruta_csv)
            if df is not None:
                print(f"  Archivo válido: {archivo} ({len(df)} filas)")
                dataframes.append(df)
            else:
                print(f"  Saltado: {archivo}")

# === Consolidación y guardado ===

if dataframes:
    df_final = pd.concat(dataframes, ignore_index=True)

    # Renombrar columnas a nombres más claros
    df_final.rename(columns={
        "textbox11": "Total_Pais_Mes",
        "textbox14": "Total_Categoria_Mes",
        "textbox17": "Litros 40 % Alc. Vol"
    }, inplace=True)

    # Guardar el archivo consolidado en data/
    df_final.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n Consolidado guardado como '{OUTPUT_PATH}' ({len(df_final)} filas)")
else:
    print(" No se encontraron archivos válidos para combinar.")
