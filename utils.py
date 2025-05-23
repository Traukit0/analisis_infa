from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import pandas as pd
import zipfile
import os
from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsVectorFileWriter,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsCoordinateTransformContext,
    QgsWkbTypes,
)

def nombrar_archivo(archivo_excel):
    """
    Función para darle nombre a archivo. Toma como input el archivo excel
    y construye la mitad del nombre genérico para .shp y .kmz
    Se intenta llegar a una función general para todos los archivos.
    """
    # Leer el archivo Excel con context manager para asegurar cierre correcto
    archivo_a_analizar = None
    try:
        archivo_a_analizar = pd.ExcelFile(archivo_excel)
        hojas_libro = archivo_a_analizar.sheet_names
        df = None
        for hoja in hojas_libro:
            try:
                # Usar el ExcelFile directamente sin abrir nuevas conexiones
                df_temp = archivo_a_analizar.parse(hoja)
                if not df_temp.empty:
                    df = df_temp
                    break
            except ValueError:
                continue
        
        # Si no se encuentra ninguna hoja con datos, levantar excepción:
        if df is None:
            raise ValueError("""No se encontraron hojas con datos en el archivo Excel.
                             Es probable que el libro esté en blanco o las hojas no
                             contengan el nombre correcto""")

        # Convención de nombres de archivo y otros datos
        centro = str(df['Centro'].unique()[0])
        fecha_string = str(df['Fecha'].unique()[0])
        fecha_lista = fecha_string.split()
        anio = str(fecha_lista[0]).split("-")[0]
        mes = str(fecha_lista[0]).split("-")[1]
        # Para transformar el mes a la convención de nomenclatura de archivo
        meses = {'01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr', '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago', '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'}
        nombre_archivo = f"{centro} INFA {anio} {meses[mes]}"
        return nombre_archivo
    finally:
        # Cerrar explícitamente el archivo Excel
        if archivo_a_analizar is not None:
            archivo_a_analizar.close()

def obtener_segundos(seg_ini, seg_fin):
    """
    Función para obtener diferencia de segundos
    entre un tiempo inicial y un tiempo final
    """
    formato_tiempo = "%H:%M:%S"
    tiempo_inicial_dt = datetime.strptime(seg_ini, formato_tiempo)
    tiempo_final_dt = datetime.strptime(seg_fin, formato_tiempo)
    diferencia = tiempo_final_dt - tiempo_inicial_dt
    diferencia_segundos = diferencia.total_seconds()
    
    return diferencia_segundos

def obtener_distancia(punto_ini, punto_fin, crs):
    """
    Función para calcular la distancia en metros entre dos puntos.
    """
    # Verificar si el sistema de coordenadas es proyectado o geográfico
    if crs.isGeographic():
        # Coordenadas en grados
        lat1, lon1 = punto_ini.y(), punto_ini.x()
        lat2, lon2 = punto_fin.y(), punto_fin.x()

        # Radio de la Tierra en metros
        R = 6371000

        # Convertir grados a radianes
        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        # Diferencias de coordenadas
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Fórmula de Haversine
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distancia = R * c

        return distancia
    else:
        # Si el sistema de coordenadas es proyectado
        distancia = punto_ini.distance(punto_fin)
        return distancia

def km_h(metros, segundos):
    """
    Función para convertir datos de m/s a km/h
    """
    velocidad_ms = metros / segundos
    factor_conversion = 3.6 # No me voy a dar la paja de hacer otros cálculos
    velocidad_kmh = velocidad_ms * factor_conversion

    return velocidad_kmh

def obtener_nudos(velocidad_kmh):
    """
    Función para convertir km/h a nudos
    """
    # 1 kilómetro por hora es igual a aproximadamente 0.539957 nudos
    factor_conversion = 0.539957
    velocidad_nudos = velocidad_kmh * factor_conversion
    return velocidad_nudos

def obtener_velocidad_int(nudos):
    """
    Función que toma como input los nudos y devuelve un entero
    para clasificar la etiqueta
    Se debe tomar esta aproximación ya que la tabla da problemas 
    con los decimales
    """
    if nudos <= 2:
        return 2
    elif nudos <= 5:
        return 5
    elif nudos <= 10:
        return 10
    elif nudos <= 20:
        return 20
    elif nudos <= 30:
        return 30
    elif nudos <= 50:
        return 50
    else:
        return None

def estilo_segmento(velocidad):
    """
    Función para devolver un valor numérico,
    que se traduce en un estilo diferente en 
    función de la velocidad en nudos.
    """
    if velocidad == 2:
        estilo_url = 0
        return estilo_url
    elif velocidad == 5:
        estilo_url = 3
        return estilo_url
    elif velocidad == 10:
        estilo_url = 6
        return estilo_url
    elif velocidad == 20:
        estilo_url = 9
        return estilo_url
    elif velocidad == 30:
        estilo_url = 12
        return estilo_url
    elif velocidad == 50:
        estilo_url = 15
        return estilo_url
    
def descomprimir_kmz(archivo_kmz, directorio_salida):
    # Asegurarse de que el directorio de salida termina con una barra invertida
    if not directorio_salida.endswith('/') and not directorio_salida.endswith('\\'):
        directorio_salida += '/'

    # Verificar si el archivo es un archivo .kmz
    if not archivo_kmz.endswith('.kmz'):
        raise ValueError("El archivo proporcionado no es un archivo .kmz")
    # Abrir el archivo .kmz como un archivo zip

    with zipfile.ZipFile(archivo_kmz, 'r') as kmz:
        # Extraer todos los archivos en el directorio de salida
        kmz.extractall(directorio_salida)

        # Buscar el archivo .kml en el directorio extraído
        for archivo in os.listdir(directorio_salida):
            if archivo.endswith('.kml'):
                archivo_kml = os.path.normpath(os.path.join(directorio_salida, archivo))
                return archivo_kml

    # Si no se encuentra un archivo .kml
    raise FileNotFoundError("No se encontró ningún archivo .kml en el archivo .kmz")

def calcular_centroide(directorio_salida):
    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida.endswith('/') and not directorio_salida.endswith('\\'):
        directorio_salida += '/'
    poligono_entrada = f"{directorio_salida}CCAA.shp" # Acá se reconstruye el nombre del archivo
    # Cargar el archivo de entrada
    capa_ccaa = QgsVectorLayer(poligono_entrada, "capa_ccaa", "ogr")
    if not capa_ccaa.isValid():
        print("Error, el archivo de entrada para la capa concesión no es válido")
        return
    # Desde acá se crea una nueva capa para almacenar el centroide
    campos = QgsFields()
    campos.append(QgsField("id", QVariant.Int))

    nombre_centroide = f"{directorio_salida}centroide.shp"

    # Opciones para el objeto writer
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'ESRI Shapefile'
    options.fileEncoding = 'UTF-8'

    # Crear el escritor de archivos
    writer = QgsVectorFileWriter.create(
        nombre_centroide,
        campos,
        QgsWkbTypes.Point,
        capa_ccaa.crs(),
        QgsCoordinateTransformContext(),
        options
    )

    if writer.hasError() != QgsVectorFileWriter.NoError:
        print("Error, no se pudo crear el centroide")
        return

    for caracteristica in capa_ccaa.getFeatures():
        geom = caracteristica.geometry()
        centroide = geom.centroid()
        nueva_carac = QgsFeature()
        nueva_carac.setGeometry(centroide)
        nueva_carac.setAttributes([caracteristica.id()])
        writer.addFeature(nueva_carac)
    
    del writer
    print("Centroide creado OK!")
    return nombre_centroide

def obtener_dia_muestreo(archivo_excel):
    """
    Función para obtener el día cuando se ejecutó el muestreo
    La fecha sale en el acta de terreno: para diferentes días
    se emplean diferentes actas, así que siempre será un solo día.
    Args:
        - archivo_excel: archivo con datos desde el acta de muestreo
    return:
        - Día cuando se ejecutó el muestreo casteada int para calculos
    """
    # Leer el archivo Excel con context manager para asegurar cierre correcto
    archivo_a_analizar = None
    try:
        archivo_a_analizar = pd.ExcelFile(archivo_excel)
        hojas_libro = archivo_a_analizar.sheet_names
        df = None
        for hoja in hojas_libro:
            try:
                # Usar el ExcelFile directamente sin abrir nuevas conexiones
                df_temp = archivo_a_analizar.parse(hoja)
                if not df_temp.empty:
                    df = df_temp
                    break
            except ValueError:
                continue
        
        # Si no se encuentra ninguna hoja con datos, levantar excepción:
        if df is None:
            raise ValueError("""No se encontraron hojas con datos en el archivo Excel.
                             Es probable que el libro esté en blanco o las hojas no
                             contengan el nombre correcto""")
        
        # Para extraer el día del muestreo
        fecha_raw = df['Fecha'].unique()[0]
        fecha_string = str(fecha_raw)
        fecha_lista = fecha_string.split()
        
        try:
            fecha_parte = fecha_lista[0].split("-")
            dia = int(fecha_parte[2])
        except:
            dia_str = fecha_lista[0].split("-")[2]
            dia = int(dia_str.split("T")[0])
        
        return dia
    finally:
        # Cerrar explícitamente el archivo Excel
        if archivo_a_analizar is not None:
            archivo_a_analizar.close()