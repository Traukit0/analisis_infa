#########################################################################################
#                CODIGO PARA EXTRACCIÓN DE DATOS DESDE ARCHIVO GPX                      #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                   PROGRAMADO POR MANUEL E. CANO NESBET - 2024                         #
#########################################################################################

from pathlib import Path
from typing import Optional

from .utils import nombrar_archivo
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
)

# Constantes
TRACK_FIELD_NAME = "Track"
TRACK_FIELD_LENGTH = 254
TARGET_CRS = 'EPSG:32718'
ENCODING = 'UTF-8'
LAYER_TYPE = "linestring"

def extraer_track(gpx_path: str, archivo_excel: str, directorio_salida_shp: str, plugin_instance) -> Optional[str]:
    """
    Extrae línea track desde un archivo GPX y genera archivo shapefile.

    Args:
        gpx_path (str): Ruta al archivo GPX de entrada
        archivo_excel (str): Ruta al archivo Excel con datos estandarizados
        directorio_salida_shp (str): Directorio donde se guardará el shapefile
        plugin_instance: Instancia del plugin para manejo de mensajes

    Returns:
        Optional[str]: Ruta del archivo shapefile generado o None si hay error

    Raises:
        ValueError: Si los parámetros de entrada son inválidos
    """
    try:
        # Validar parámetros de entrada
        if not all([gpx_path, archivo_excel, directorio_salida_shp]):
            raise ValueError("Todos los parámetros son requeridos")

        # Validar que los archivos y directorios existan
        if not Path(gpx_path).exists():
            raise FileNotFoundError(f"Archivo GPX no encontrado: {gpx_path}")
        if not Path(directorio_salida_shp).exists():
            raise NotADirectoryError(f"Directorio de salida no existe: {directorio_salida_shp}")

        # Cargar la capa GPX
        capa_gpx = QgsVectorLayer(f"{gpx_path}|layername=tracks", "Tracks", "ogr")
        if not capa_gpx.isValid():
            raise ValueError(f"Error al cargar la capa GPX: {gpx_path}")

        # Configurar transformación de coordenadas
        crs_origen = capa_gpx.crs()
        crs_dest = QgsCoordinateReferenceSystem(TARGET_CRS)
        transform = QgsCoordinateTransform(crs_origen, crs_dest, QgsProject.instance())

        # Definir campos
        campos = QgsFields()
        campos.append(QgsField(TRACK_FIELD_NAME, QVariant.String, len=TRACK_FIELD_LENGTH))

        # Procesar features
        features = []
        for feat in capa_gpx.getFeatures():
            geom = feat.geometry()
            geom.transform(transform)
            new_feat = QgsFeature()
            new_feat.setGeometry(geom)
            new_feat.setAttributes([feat['name']])
            features.append(new_feat)

        if not features:
            plugin_instance.mensajes_texto_plugin("\nNo se encontró Track. No se genera archivo.")
            return None

        # Crear capa de salida
        output_layer = QgsVectorLayer(
            f"{LAYER_TYPE}?crs={TARGET_CRS}", "output_layer", "memory"
        )
        provider = output_layer.dataProvider()
        provider.addAttributes(campos)
        output_layer.updateFields()
        provider.addFeatures(features)

        # Preparar ruta de salida
        directorio_salida_shp = Path(directorio_salida_shp)
        nombre_archivo = nombrar_archivo(archivo_excel)
        ruta_salida = directorio_salida_shp / f"{nombre_archivo} Track Linea.shp"

        # Configurar opciones de escritura
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'ESRI Shapefile'
        options.fileEncoding = ENCODING

        # Escribir archivo
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            output_layer,
            str(ruta_salida),
            QgsCoordinateTransformContext(),
            options
        )

        if result[0] != QgsVectorFileWriter.NoError:
            raise IOError(f"Error al escribir shapefile: {result[1]}")

        return str(ruta_salida)

    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"\nError en extraer_track: {str(e)}")
        return None
