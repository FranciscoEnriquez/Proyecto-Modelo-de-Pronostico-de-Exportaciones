# -*- coding: utf-8 -*-

"""
datos_categorias.py

Este script utiliza Selenium para automatizar la descarga mensual de archivos CSV 
del Consejo Regulador del Tequila (CRT) para los siguientes módulos:
- Producción Total de Tequila
- Consumo de Agave Total
- Exportaciones Totales por Categoría
- Exportaciones Totales por Forma

Cada archivo se guarda en la carpeta /data/{nombre_categoria}/{año}-{nombre_categoria}.

Autor: Francisco Enríquez
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ruta al ejecutable de ChromeDriver
CHROME_DRIVER_PATH = "C:/Users/franc/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"

# Directorio base donde se almacenarán los archivos descargados
BASE_DOWNLOAD_DIR = r"C:\Users\franc\Downloads\Modelo_Pronosticos\data"

# Formato de exportación en el visor del CRT
FORMATO_EXPORTACION = "CSV (delimitado por comas)"
EXTENSION = ".csv"

# Mapeo de nombres de meses
meses = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
}

# URLs de los visores por categoría
PAGINAS = {
    "ProduccionTotalTequila": "https://old.crt.org.mx/EstadisticasCRTweb/Informes/ProduccionTotalTequila.aspx",
    "ConsumodeAgaveTotal": "https://old.crt.org.mx/EstadisticasCRTweb/Informes/ConsumodeAgaveTotal.aspx",
    "ExportacionesTotalCategoria": "https://old.crt.org.mx/EstadisticasCRTweb/Informes/ExportacionesTotalCategoria.aspx",
    "ExportacionesTotalForma": "https://old.crt.org.mx/EstadisticasCRTweb/Informes/ExportacionesTotalForma.aspx"
}


def esperar_y_renombrar(nombre_destino, archivos_antes, download_dir, extension=EXTENSION, timeout=1):
    """
    Espera a que se complete la descarga y renombra el archivo al formato deseado.

    :param nombre_destino: nombre con el que se debe guardar el archivo.
    :param archivos_antes: conjunto de archivos antes de iniciar la descarga.
    :param download_dir: directorio de descarga.
    :param extension: extensión del archivo esperado.
    :param timeout: tiempo máximo de espera en segundos.
    :return: True si la descarga fue exitosa y se renombró el archivo.
    """
    print("  Esperando descarga completa...")
    tiempo = 0.0
    archivo_nuevo = None

    while tiempo < timeout:
        archivos_despues = set(os.listdir(download_dir))
        diferencia = archivos_despues - archivos_antes
        finalizados = [f for f in diferencia if f.endswith(extension)]

        if finalizados:
            archivo_nuevo = os.path.join(download_dir, finalizados[0])
            print(f"  Archivo detectado: {archivo_nuevo}")
            break

        time.sleep(0.2)
        tiempo += 0.2

    if archivo_nuevo and os.path.exists(archivo_nuevo):
        nuevo_path = os.path.join(download_dir, nombre_destino + extension)
        try:
            if os.path.exists(nuevo_path):
                print(f"  Eliminando archivo existente: {nuevo_path}")
                os.remove(nuevo_path)
            os.rename(archivo_nuevo, nuevo_path)
            print(f"  Renombrado como: {nuevo_path}")
            return True
        except Exception as e:
            print(f"  Error al renombrar: {str(e)}")
            return False
    else:
        print("  No se encontró el archivo descargado.")
        return False


def esperar_renderizado(wait):
    """
    Espera a que el informe esté completamente cargado en el visor.
    """
    try:
        print(" Esperando que el informe se cargue completamente...")
        wait.until(EC.presence_of_element_located((By.ID, "VisibleReportContentReportViewer1_ctl09")))
        wait.until(EC.element_to_be_clickable((By.ID, "ReportViewer1_ctl05_ctl04_ctl00_ButtonLink")))
        print(" Informe listo.")
    except Exception as e:
        print(f" Error: el informe no terminó de cargar ({type(e).__name__})")


def descargar_datos_categorias():
    """
    Función principal que itera sobre cada página, año y mes
    para automatizar la descarga y renombrar los reportes.
    """
    for nombre_pagina, url in PAGINAS.items():
        print(f"\n######## INICIANDO: {nombre_pagina} ########")

        for anio in range(1995, 2025):
            print(f"\n==============================")
            print(f"Descargando archivos del año {anio} - {nombre_pagina}")
            print(f"==============================")

            folder_name = f"{anio}-{nombre_pagina}"
            download_dir = os.path.join(BASE_DOWNLOAD_DIR, nombre_pagina, folder_name)
            os.makedirs(download_dir, exist_ok=True)

            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "directory_upgrade": True,
                "profile.default_content_setting_values.automatic_downloads": 1
            }

            options = webdriver.ChromeOptions()
            options.add_experimental_option("prefs", prefs)
            options.add_argument("--start-maximized")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            service = Service(CHROME_DRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 120)

            driver.get(url)

            try:
                wait.until(EC.presence_of_element_located((By.ID, "ReportViewer1_ctl04_ctl03_ddDropDownButton")))
                driver.find_element(By.ID, "ReportViewer1_ctl04_ctl03_ddDropDownButton").click()
                time.sleep(1)

                year_option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//label[normalize-space(text())='{anio}']")))
                year_option.click()
                time.sleep(0.5)
            except Exception as e:
                print(f"  No disponible el año {anio}, continuando...")
                driver.quit()
                continue

            for mes_num, mes_nombre in meses.items():
                print(f"\n Procesando {anio}-{mes_nombre}...")

                try:
                    driver.find_element(By.ID, "ReportViewer1_ctl04_ctl05_ddDropDownButton").click()
                    time.sleep(1)

                    # Desmarcar checkboxes activos
                    for cb in driver.find_elements(By.XPATH, "//div[@id='ReportViewer1_ctl04_ctl05_divDropDown']//input[@type='checkbox']"):
                        if cb.is_selected():
                            cb.click()
                            time.sleep(0.2)

                    # Seleccionar mes
                    label_mes = wait.until(EC.element_to_be_clickable((By.XPATH, f"//label[normalize-space(text())='{mes_nombre}']")))
                    label_mes.click()
                    time.sleep(0.5)

                    # Clic en botón 'Ver Informe'
                    driver.find_element(By.ID, "ReportViewer1_ctl04_ctl00").click()
                    esperar_renderizado(wait)
                    time.sleep(1.5)

                    if "No se encontro" in driver.page_source:
                        print(f" {anio}-{mes_nombre} no contiene datos.")
                        continue

                    archivos_antes = set(os.listdir(download_dir))

                    try:
                        print(" Abriendo menú de exportación...")
                        driver.find_element(By.ID, "ReportViewer1_ctl05_ctl04_ctl00_ButtonLink").click()
                        time.sleep(0.5)

                        print(f" Buscando opción de exportación: {FORMATO_EXPORTACION}")
                        export_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[normalize-space(text())='{FORMATO_EXPORTACION}']")))
                        export_link.click()
                    except Exception as e:
                        print(f" No se encontró la opción de exportación para {anio}-{mes_nombre} ({type(e).__name__})")
                        continue

                    nombre_destino = f"{anio}-{mes_num}-{nombre_pagina}"
                    if esperar_y_renombrar(nombre_destino, archivos_antes, download_dir):
                        print(f"  Descarga completada para {anio}-{mes_num}")
                    else:
                        print(f"  Fallo en descarga de {anio}-{mes_num}")

                except Exception as e:
                    try:
                        driver.switch_to.alert.accept()
                        print(" Alerta aceptada")
                    except:
                        pass

                    try:
                        driver.switch_to.default_content()
                    except:
                        print(f" No se puede cambiar al contenido principal.")

                    print(f"  Error durante {anio}-{mes_nombre}: {str(e)}")
                    continue

            driver.quit()

    print("\n Proceso de descarga finalizado.")
