#########################################################################################
#                CODIGO PARA EXTRACCIÓN DE DATOS DESDE ARCHIVO GPX                      #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#               PROGRAMADO POR MANUEL E. CANO NESBET - 05-06-2024                       #
# ToDo:                                                                                 #
# - Manejo de aquellos puntos que no tengan UTC                                         #
#########################################################################################

import zipfile
import os
from pyproj import Transformer
from datetime import datetime, timedelta
from PyQt5.QtCore import QVariant
from .utils import (nombrar_archivo,
                    calcular_centroide,
                    obtener_distancia,
                    obtener_dia_muestreo,)
from typing import Optional, List, Dict, Tuple

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
    QgsPoint,
    QgsPointXY,
)

# Constantes
BUFFER_DISTANCE = 1500  # metros
UTM_CRS = 'EPSG:32718'
WGS84_CRS = 'EPSG:4326'
MESES = {
    '01': 'ene', '02': 'feb', '03': 'mar', '04': 'abr', 
    '05': 'may', '06': 'jun', '07': 'jul', '08': 'ago', 
    '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dic'
}

def get_field_definitions() -> List[QgsField]:
    """Retorna la lista de campos para la capa de puntos."""
    return [
        QgsField("ID_track", QVariant.String, len=10),
        QgsField("ID_Segm", QVariant.String, len=10),
        QgsField("ID_Punto", QVariant.Int),
        QgsField("Elev", QVariant.Double, len=10),
        QgsField("UTC", QVariant.String, len=50),
        QgsField("Ajuste", QVariant.Int),
        QgsField("Rollover", QVariant.Int),
        QgsField("Local", QVariant.String, len=50),
        QgsField("Dia", QVariant.String, len=20),
        QgsField("Hora", QVariant.String, len=20),
        QgsField("Name", QVariant.String, len=50),
        QgsField("Descrip", QVariant.String, len=254),
        QgsField("TimeStamp", QVariant.String, len=50),
        QgsField("Mostrar", QVariant.String, len=10),
        QgsField("Valido", QVariant.String, len=10)
    ]

def process_feature(feat: QgsFeature, transform: QgsCoordinateTransform, 
                   punto_referencia: QgsPointXY, valor_utc: int, 
                   dia_muestreo: int, id_punto: int, 
                   plugin_instance: any) -> Optional[Tuple[QgsFeature, int]]:
    """
    Procesa una característica individual y retorna una nueva característica procesada.
    Retorna None si la característica debe ser descartada.
    """
    try:
        geom = feat.geometry()
        geom.transform(transform)
        
        # Validar punto dentro del buffer
        punto_actual = geom.asPoint()
        if not is_point_valid(punto_actual, punto_referencia):
            return None
            
        # Procesar tiempo
        utc_time = feat.attribute('time')
        if not utc_time or utc_time == 'Null':
            return None
            
        # Crear atributos
        attrs = create_feature_attributes(utc_time, valor_utc, id_punto, feat)
        
        if attrs['dia_local'].day != dia_muestreo:
            return None
            
        new_feat = QgsFeature()
        new_feat.setGeometry(geom)
        new_feat.setAttributes(list(attrs.values()))
        
        return new_feat, id_punto + 1
        
    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"Error procesando feature: {str(e)}")
        return None

def is_point_valid(punto_actual: QgsPointXY, punto_referencia: QgsPointXY) -> bool:
    """Valida si un punto está dentro del buffer permitido."""
    distancia = obtener_distancia(punto_referencia, punto_actual, QgsCoordinateReferenceSystem(UTM_CRS))
    return 0 < distancia < BUFFER_DISTANCE

def create_feature_attributes(utc_time: str, valor_utc: int, id_punto: int, feat: QgsFeature) -> Dict:
    """Crea los atributos para una nueva característica."""
    utc_time_str = utc_time.toString('yyyy-MM-dd HH:mm:ss')
    utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
    local_dt = utc_dt - timedelta(hours=valor_utc)
    
    return {
        'id_track': 0,
        'id_segm': 0,
        'id_punto': id_punto,
        'elev': feat.attribute('ele'),
        'utc_time_str': utc_time_str,
        'ajuste': valor_utc,
        'rollover': 0,
        'local_time': local_dt.strftime('%Y/%m/%d %H:%M:%S'),
        'dia': local_dt.strftime('%Y/%m/%d'),
        'hora': local_dt.strftime('%H:%M:%S'),
        'name': local_dt.strftime('%H:%M'),
        'descrip': f"{local_dt.strftime('%Y/%m/%d %H:%M:%S')} (UTC-{valor_utc})",
        'TimeStamp': local_dt.strftime('%d/%m/%Y %H:%M:%S'),
        'mostrar': "Si",
        'Valido': "Si",
        'dia_local': local_dt
    }

def extraer_track_points(gpx_path: str, archivo_excel: str, 
                        directorio_salida_shp: str, 
                        directorio_salida_kmz: str,
                        valor_utc: int, 
                        plugin_instance: any) -> Optional[str]:
    """
    Extrae puntos de track desde archivo GPX y genera archivos SHP y KMZ.
    
    Args:
        gpx_path: Ruta al archivo GPX
        archivo_excel: Ruta al archivo Excel con datos estandarizados
        directorio_salida_shp: Directorio para guardar archivo SHP
        directorio_salida_kmz: Directorio para guardar archivo KMZ
        valor_utc: Ajuste horario UTC (-3 o -4)
        plugin_instance: Instancia del plugin para mensajes
        
    Returns:
        str: Ruta del archivo SHP generado o None si hay error
    """
    try:
        # Normalizar rutas de archivo
        gpx_path = os.path.normpath(gpx_path)
        archivo_excel = os.path.normpath(archivo_excel)
        directorio_salida_shp = os.path.normpath(directorio_salida_shp)

        # Esto es para asegurar que siempre se guarde bien el directorio de salida
        if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
            directorio_salida_shp += '/'

        centroide_shp = calcular_centroide(directorio_salida_shp) # Debe ser así porque me aweoné con el otro código

        # Ahora se carga la capa de centroide para trabajar sobre ella
        capa_centroide = QgsVectorLayer(centroide_shp, "centroide","ogr")
        if not capa_centroide.isValid():
            mensaje = "\nError al cargar la capa del centroide"
            plugin_instance.mensajes_texto_plugin(mensaje)
            return
        # Obtener el punto de referencia, es la primera caracaterística de la capa pero uno nunca sabe,
        # Quizás hayan dos polígonos en una misma concesión
        carac_referencia = next(capa_centroide.getFeatures())
        punto_referencia = carac_referencia.geometry().asPoint()

        # Transformar el punto de referencia a UTM (EPSG:32718)
        # esto es necesario para calcular las distancias
        crs_origen_ref = capa_centroide.crs()
        crs_dest_ref = QgsCoordinateReferenceSystem('EPSG:32718')
        transform_ref = QgsCoordinateTransform(crs_origen_ref, crs_dest_ref, QgsProject.instance())
        geom_referencia = carac_referencia.geometry()
        geom_referencia.transform(transform_ref)
        punto_referencia = geom_referencia.asPoint()

        # Cargar la capa GPX, acá estaba el queso de porque no funcionaba... no ocupar 'uri'
        capa_gpx = QgsVectorLayer(f"{gpx_path}|layername=track_points", "Track Points", "ogr")
        if not capa_gpx.isValid():
            mensaje = f"\npuntos_track_gpx.extraer_track_points: Error al cargar la capa {gpx_path} GPX."
            plugin_instance.mensajes_texto_plugin(mensaje)
            return

        # Definir sistemas de referencia de coordenadas
        crs_origen = capa_gpx.crs()
        crs_dest = QgsCoordinateReferenceSystem('EPSG:32718')

        # Crear el transformador de coordenadas
        transform = QgsCoordinateTransform(crs_origen, crs_dest, QgsProject.instance())

        # Definir los campos adicionales
        campos_adicionales = get_field_definitions()

        hay_puntos_track = False # bandera para asegurar que la capa no esté vacía

        # Crear la lista de características transformadas
        features = []
        id_punto = 0
        dia_muestreo = obtener_dia_muestreo(archivo_excel)
        for feat in capa_gpx.getFeatures():
            hay_puntos_track = True
            result = process_feature(feat, transform, punto_referencia, valor_utc, dia_muestreo, id_punto, plugin_instance)
            if result:
                new_feat, id_punto = result
                features.append(new_feat)

        if not hay_puntos_track:
            mensaje = "\nNo se encontraron puntos de track en el archivo GPX. No se genera SHP ni KMZ"
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
        output_layer = QgsVectorLayer("Point?crs=EPSG:32718", "output_layer", "memory")
        output_layer_data_provider = output_layer.dataProvider()
        output_layer_data_provider.addAttributes(fields)
        output_layer.updateFields()
        output_layer_data_provider.addFeatures(features)

        # Escribir la capa de salida a un archivo SHP
        transform_context = QgsCoordinateTransformContext()

        # para nombrar archivo y que no sea necesario incluirlo como input
        nombre_archivo = nombrar_archivo(archivo_excel)

        # Esto es para asegurar que siempre se guarde bien el directorio de salida
        if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
            directorio_salida_shp += '/'

        # Normalizar nuevamente la ruta final del archivo
        nombre_archivo_shp = os.path.normpath(f"{directorio_salida_shp}{nombre_archivo} Track Ptos.shp")

        QgsVectorFileWriter.writeAsVectorFormatV3(
            output_layer,
            nombre_archivo_shp,
            transform_context,
            options
        )

        plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_archivo} Track Ptos.shp creado")

        # Lógica añadida para cargar capa .shp directamente a QGIS
        layer = QgsVectorLayer(nombre_archivo_shp, f"{nombre_archivo} Track Ptos.shp", "ogr")
        if not layer.isValid():
            mensaje = f"No pudo cargarse la capa '{nombre_archivo} Track Ptos.shp' en QGIS. Verificar el archivo generado"
            plugin_instance.mensajes_texto_plugin(mensaje)
            return
        
        # Obtener el directorio base del plugin
        plugin_dir = os.path.dirname(__file__)

        # Construir la ruta completa al archivo .qml en la subcarpeta "estilos_qml"
        qml_style_path = os.path.join(plugin_dir, 'estilos_qml', 'Estilo Track Puntos.qml')

        if os.path.exists(qml_style_path):
            layer.loadNamedStyle(qml_style_path)
            layer.triggerRepaint()

        # Añadir la capa al proyecto actual en QGIS
        QgsProject.instance().addMapLayer(layer)

        ######################################################
        ##### ACA TERMINA LA LOGICA DE CAPAS GEOGRAFICAS #####
        ######################################################

        ##### ------------------------------------------ #####

        #############################################################
        ##### ACA EMPIEZA LA LOGICA DE CREAR KML CON SCHEMA XML #####
        #############################################################

        # Definir la estructura base del KML con los estilos necesarios
        kml_base = '''<?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
            <Document>
                <name>Track Puntos</name>
                <Folder>
                    <name>Track Puntos</name>
                    <Style id="0">
                        <IconStyle>
                            <color>7effffff</color>
                            <scale>0.2519685039370079</scale>
                            <Icon>
                                <href>files/icono_pto_track_utc.png</href>
                            </Icon>
                        </IconStyle>
                        <LabelStyle>
                            <scale>0.7</scale>
                        </LabelStyle>
                    </Style>
                    {placemarks}
                </Folder>
            </Document>
        </kml>
        '''

        # Plantilla para cada punto
        placemark_template = '''
                    <Placemark>
                        <name>{name}</name>
                        <description>{description}</description>
                        <TimeStamp><when>{timestamp}</when></TimeStamp>
                        <styleUrl>#0</styleUrl>
                        <Point>
                            <coordinates>{coordinates}</coordinates>
                        </Point>
                    </Placemark>
        '''

        # Leer la capa shapefile para generar el KMZ
        capa_shp = QgsVectorLayer(nombre_archivo_shp, "capa_shp", "ogr")
        if not capa_shp.isValid():
            mensaje = f"\nError al cargar la capa {nombre_archivo_shp} para generar KMZ"
            plugin_instance.mensajes_texto_plugin(mensaje)
            return nombre_archivo_shp

        # Configurar transformación para el KMZ (a coordenadas geográficas)
        transform_to_wgs84 = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem('EPSG:32718'),
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance()
        )

        # Generar los placemarks
        placemarks = ''
        for feature in capa_shp.getFeatures():
            # Obtener y transformar geometría
            geom = feature.geometry()
            geom.transform(transform_to_wgs84)
            point = geom.asPoint()
            
            # Formatear datos para el KMZ
            fecha_separada = feature['Dia'].split('/')
            timestamp = f"{fecha_separada[0]}-{fecha_separada[1]}-{fecha_separada[2]}T{feature['Hora']}Z"
            
            # Crear descripción formateada
            id_descrip = f"[ID {feature['ID_track']}-{feature['ID_Segm']}-{feature['ID_Punto']}]"
            description = f"{fecha_separada[2]} {MESES[fecha_separada[1]]}. {fecha_separada[0]} {feature['Hora']} {feature['Descrip']} {id_descrip}"

            placemark = placemark_template.format(
                name=feature['Name'],
                description=description,
                timestamp=timestamp,
                coordinates=f"{point.x()},{point.y()},0"
            )
            placemarks += placemark

        # Generar el contenido final del KML
        kml_content = kml_base.format(placemarks=placemarks)

        # Asegurar que el directorio de salida termine con separador
        if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
            directorio_salida_kmz += '/'

        # Obtener la ruta al ícono
        plugin_dir = os.path.dirname(__file__)
        icono_track_ptos = os.path.join(plugin_dir, 'files', 'icono_pto_track_utc.png')

        # Crear archivos temporales y KMZ final
        nombre_base = nombrar_archivo(archivo_excel) # para construir la primera mitad del nombre
        print(nombre_base)
        nombre_kmz = f"{nombre_base} Track Ptos" # Acá se termina de construir el nombre completo
        print(nombre_kmz)
        kml_temp = os.path.normpath(f"{directorio_salida_kmz}{nombre_kmz}.kml")
        kmz_final = os.path.normpath(f"{directorio_salida_kmz}{nombre_kmz}.kmz")

        # Escribir KML temporal
        with open(kml_temp, 'w', encoding='utf-8') as f:
            f.write(kml_content)

        # Crear archivo KMZ
        with zipfile.ZipFile(kmz_final, 'w') as kmz:
            kmz.write(kml_temp, arcname=f"{nombre_kmz}.kml")
            kmz.write(icono_track_ptos, arcname="files/icono_pto_track_utc.png")

        # Eliminar KML temporal
        os.remove(kml_temp)
        plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_kmz}.kmz creado")
        return nombre_archivo_shp
        
    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"Error en extraer_track_points: {str(e)}")
        return None