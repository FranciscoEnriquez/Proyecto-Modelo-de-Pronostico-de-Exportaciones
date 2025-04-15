# -*- coding: utf-8 -*-

"""
datos_paises.py

Este script automatiza mediante Selenium la descarga de reportes mensuales 
de exportaciones por país desde el sitio del CRT.

Para cada mes y año desde 1997 hasta 2024:
- Selecciona todas las categorías, clases y países.
- Establece el rango de fechas para el mes correspondiente.
- Descarga el reporte en formato CSV.
- Renombra y guarda el archivo en la carpeta /data/{año}-ExportacionesPais/.

Autor: Francisco Enríquez
"""

import os
import time
import calendar
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuraciones globales
CHROME_DRIVER_PATH = "C:/Users/franc/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"
BASE_DOWNLOAD_DIR = r"C:\Users\franc\Downloads\Modelo_Pronosticos\data"
FORMATO_EXPORTACION = "CSV (delimitado por comas)"
EXTENSION = ".csv"


def esperar_y_renombrar(nombre_destino, archivos_antes, download_dir, extension=EXTENSION, timeout=20):
    """
    Espera a que el archivo sea descargado y lo renombra con un nombre específico.

    :param nombre_destino: Nombre deseado para el archivo (sin extensión)
    :param archivos_antes: Lista de archivos existentes antes de la descarga
    :param download_dir: Directorio de descarga
    :param extension: Extensión esperada
    :param timeout: Tiempo máximo de espera en segundos
    :return: True si se completó y renombró, False si no
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

        time.sleep(0.5)
        tiempo += 0.5

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
    Espera a que el informe esté completamente renderizado.
    """
    wait.until(EC.presence_of_element_located((By.ID, "VisibleReportContentReportViewer1_ctl09")))
    wait.until(EC.element_to_be_clickable((By.ID, "ReportViewer1_ctl05_ctl04_ctl00_ButtonLink")))


def procesar_mes(driver, wait, anio, mes, download_dir):
    """
    Descarga y guarda el informe del CRT para un año y mes específico.

    :param driver: Objeto WebDriver
    :param wait: Objeto WebDriverWait
    :param anio: Año (int)
    :param mes: Mes (int)
    :param download_dir: Carpeta de descarga
    """
    mes_str = f"{mes:02d}"
    nombre_destino = f"{anio}-{mes_str}-ExportacionesPais"

    print(f"\n==============================")
    print(f"Descargando informe de {nombre_destino}")
    print(f"==============================")

    try:
        # Navegar al visor de exportaciones por país
        driver.get("https://old.crt.org.mx/EstadisticasCRTweb/Informes/ExportacionesPorPais.aspx")
        wait.until(EC.presence_of_element_located((By.ID, "ReportViewer1_ctl04_ctl07_ddDropDownButton")))

        # Establecer fechas (formato: dd/mm/yyyy)
        fecha_inicial = f"01/{mes_str}/{anio}"
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        fecha_final = f"{ultimo_dia:02d}/{mes_str}/{anio}"
        print("  Estableciendo fechas:", fecha_inicial, "->", fecha_final)

        fecha_ini_input = wait.until(EC.presence_of_element_located((By.ID, "ReportViewer1_ctl04_ctl03_txtValue")))
        fecha_fin_input = wait.until(EC.presence_of_element_located((By.ID, "ReportViewer1_ctl04_ctl05_txtValue")))

        fecha_ini_input.clear()
        fecha_ini_input.send_keys(fecha_inicial)
        fecha_fin_input.clear()
        fecha_fin_input.send_keys(fecha_final)

        # Seleccionar todas las categorías
        print("  Seleccionando todas las categorías...")
        driver.find_element(By.ID, "ReportViewer1_ctl04_ctl07_ddDropDownButton").click()
        time.sleep(1)
        for cb in driver.find_elements(By.XPATH, "//div[@id='ReportViewer1_ctl04_ctl07_divDropDown']//input[@type='checkbox']"):
            if not cb.is_selected():
                cb.click()
                time.sleep(0.1)

        # Seleccionar todas las clases
        print("  Seleccionando todas las clases...")
        driver.find_element(By.ID, "ReportViewer1_ctl04_ctl09_ddDropDownButton").click()
        time.sleep(1)
        for cb in driver.find_elements(By.XPATH, "//div[@id='ReportViewer1_ctl04_ctl09_divDropDown']//input[@type='checkbox']"):
            if not cb.is_selected():
                cb.click()
                time.sleep(0.1)

        # Seleccionar todos los países
        print("  Seleccionando todos los países...")
        driver.find_element(By.ID, "ReportViewer1_ctl04_ctl11_ddDropDownButton").click()
        time.sleep(1)
        for cb in driver.find_elements(By.XPATH, "//div[@id='ReportViewer1_ctl04_ctl11_divDropDown']//input[@type='checkbox']"):
            if not cb.is_selected():
                cb.click()
                time.sleep(0.1)

        # Ejecutar informe
        print("  Ejecutando informe...")
        driver.find_element(By.ID, "ReportViewer1_ctl04_ctl00").click()
        time.sleep(6)
        esperar_renderizado(wait)

        archivos_antes = set(os.listdir(download_dir))
        driver.find_element(By.ID, "ReportViewer1_ctl05_ctl04_ctl00_ButtonLink").click()
        time.sleep(0.2)

        wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[normalize-space(text())='{FORMATO_EXPORTACION}']"))).click()

        if esperar_y_renombrar(nombre_destino, archivos_antes, download_dir):
            print(f" ✅ Descarga completada para {nombre_destino}")
        else:
            print(f" ❌ Fallo en descarga de {nombre_destino}")

    except Exception as e:
        try:
            driver.switch_to.alert.accept()
            print("  Alerta aceptada")
        except:
            pass
        print(f" ⚠ Error durante {nombre_destino}: {str(e)}")


def descargar_datos_paises():
    """
    Ejecuta la descarga de todos los informes mensuales de exportación por país desde 1997 hasta 2024.
    """
    for anio in range(1997, 2025):
        folder_name = f"{anio}-ExportacionesPais"
        download_dir = os.path.join(BASE_DOWNLOAD_DIR, folder_name)
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

        service = Service(CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 180)

        for mes in range(1, 13):
            procesar_mes(driver, wait, anio, mes, download_dir)

        driver.quit()

    print("\n✅ Proceso de descarga por país finalizado.")
