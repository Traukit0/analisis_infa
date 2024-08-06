#########################################################################################
#                CODIGO PARA EXTRACCIÓN DE DATOS DESDE ARCHIVO GPX                      #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                   PROGRAMADO POR MANUEL E. CANO NESBET - 2024                         #
# ToDo:                                                                                 #
# - Manejo de errores y excepciones                                                     #
# - Mensajes de consola que se pasen a plugin para visualización                        #
#########################################################################################

from .utils import nombrar_archivo
from PyQt5.QtCore import QVariant

# Imports varios
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
)

def extraer_track(gpx_path, archivo_excel, directorio_salida_shp, plugin_instance):
    """
    Función para extraer línea track desde un archivo GPX.
    Inputs:
    - Archivo GPX enviado por consultora
    - Archivo Excel cargado con datos estandarizados para el nombre del archivo final
    - Directorio de salida donde se guardarán los archivos
    '"""
    # Cargar la capa GPX, acá estaba el queso de porque no funcionaba... no ocupar 'uri'
    capa_gpx = QgsVectorLayer(f"{gpx_path}|layername=tracks", "Tracks", "ogr")
    if not capa_gpx.isValid():
        mensaje = f"\ntrack_gpx.extraer_track: Error al cargar la capa {gpx_path} GPX."
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    # Definir sistemas de referencia de coordenadas
    crs_origen = capa_gpx.crs()
    crs_dest = QgsCoordinateReferenceSystem('EPSG:32718')

    # Crear el transformador de coordenadas
    transform = QgsCoordinateTransform(crs_origen, crs_dest, QgsProject.instance())

    # Definir los campos adicionales
    campos_adicionales = [
        QgsField("Track", QVariant.String, len=254),
    ]

    hay_track = False # Bandera para asegurar que hay track en archivo

    # Crear la lista de características transformadas
    features = []
    for feat in capa_gpx.getFeatures():
        hay_track = True
        geom = feat.geometry()
        geom.transform(transform)
        track = feat['name']
        # Crear la nueva característica con los campos adicionales
        new_feat = QgsFeature()
        new_feat.setGeometry(geom)
        new_feat.setAttributes([
            track
        ])
        features.append(new_feat)
    
    # Snippet para verificar que de no existir Track no se siga ejecutando el código
    if not hay_track:
        mensaje = "\nNo se encontró Track. No se genera archivo KMZ para esta capa"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    # Crear la capa de salida SHP
    fields = QgsFields()
    for field in campos_adicionales:
        fields.append(field)

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'ESRI Shapefile'
    options.fileEncoding = 'UTF-8'

    # Crear una nueva capa con los campos adicionales correctamente definidos
    output_layer = QgsVectorLayer("linestring?crs=EPSG:32718", "output_layer", "memory")
    output_layer_data_provider = output_layer.dataProvider()
    output_layer_data_provider.addAttributes(fields)
    output_layer.updateFields()
    output_layer_data_provider.addFeatures(features)

    # Nombre de archivo
    nombre_archivo = nombrar_archivo(archivo_excel)

    #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
        directorio_salida_shp += '/'

    # Escribir la capa de salida a un archivo SHP
    transform_context = QgsCoordinateTransformContext()
    QgsVectorFileWriter.writeAsVectorFormatV3(
        output_layer,
        f"{directorio_salida_shp}{nombre_archivo} Track Linea.shp",
        transform_context,
        options
    )
