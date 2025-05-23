#########################################################################################
#                CODIGO PARA EXTRACCIÓN DE DATOS DESDE ARCHIVO GPX                      #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#               PROGRAMADO POR MANUEL E. CANO NESBET - 05-06-2024                       #
# ToDo:                                                                                 #
# - Manejo de errores y excepciones                                                     #
# - Mensajes de consola que se pasen a plugin para visualización                        #
# - Manejo de aquellos puntos que no tengan UTC                                         #                                      #
#########################################################################################

import zipfile
import os
from pyproj import Transformer
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from PyQt5.QtCore import QVariant
from .utils import nombrar_archivo

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

def extraer_waypoints(gpx_path, archivo_excel, directorio_salida_shp, directorio_salida_kmz, valor_utc, plugin_instance):
    '''
    Función para extraer Waypoints desde un archivo GPX.
    Toma como parámetro el archivo de entrada en formato GPX
    y el mombre del archivo de salida, en formato .shp
    El nombre del archivo de salida se obtiene desde datos base de Excel
    Inputs:
    - Archivo GPX enviado por consultora
    - Archivo Excel cargado con datos estandarizados para el nombre del archivo final
    - Directorio de salida donde se guardarán los archivos
    '''
    uri = f"{gpx_path}?type=waypoint"
    capa_gpx = QgsVectorLayer(uri, "Waypoints", "gpx")
    if not capa_gpx.isValid():
        mensaje = f"\nwpt_gpx.extraer_waypoints: Error al cargar la capa {gpx_path} GPX."
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    crs_origen = capa_gpx.crs()
    crs_dest = QgsCoordinateReferenceSystem('EPSG:32718')
    transform = QgsCoordinateTransform(crs_origen, crs_dest, QgsProject.instance())

    campos_adicionales = [
        QgsField("fid", QVariant.Int),
        QgsField("Wpt", QVariant.String, len=20),
        QgsField("Wp_Com", QVariant.String, len=20),
        QgsField("Wp_Desc", QVariant.String, len=20),
        QgsField("Elev", QVariant.Double),
        QgsField("UTC", QVariant.String, len=50),
        QgsField("Ajuste", QVariant.Int),
        QgsField("Rollover", QVariant.Int),
        QgsField("Local", QVariant.String, len=50),
        QgsField("Dia", QVariant.String, len=50),
        QgsField("Hora", QVariant.String, len=50),
        QgsField("Name", QVariant.String, len=50),
        QgsField("Descrip", QVariant.String, len=50),
        QgsField("TimeStamp", QVariant.String, len=50),
        QgsField("Mostrar", QVariant.String, len=50),
        QgsField("Clase", QVariant.String, len=50)
    ]

    features = []
    fid = 1
    for feat in capa_gpx.getFeatures():
        geom = feat.geometry()
        geom.transform(transform)

        wpt = feat['name']
        elevation = feat['elevation']
        
        # Intentar obtener el tiempo desde el archivo GPX original
        with open(gpx_path, 'rb') as archivo_gpx:
            tree = ET.parse(archivo_gpx)        
        root = tree.getroot()
        
        # Buscar el waypoint correspondiente por nombre
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        wpt_xml = root.find(f".//gpx:wpt/[gpx:name='{wpt}']/gpx:time", namespaces=ns)
        
        if wpt_xml is not None:
            utc_time_str = wpt_xml.text
            # Convertir el formato ISO a datetime
            utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')
        else:
            mensaje = f"\nwpt_gpx.extraer_waypoints: No se encontró tiempo para el waypoint {wpt}"
            plugin_instance.mensajes_texto_plugin(mensaje)
            continue

        local_dt = utc_dt - timedelta(hours=valor_utc)
        local_time = local_dt.strftime('%Y/%m/%d %H:%M:%S')
        dia = local_dt.strftime('%Y/%m/%d')
        hora = local_dt.strftime('%H:%M:%S')
        hora_sec = local_dt.strftime('%H:%M')

        Wp_Com = None
        Wp_Desc = None
        ajuste = valor_utc
        rollover = 0
        name_hora = f"{wpt} ({hora_sec})"
        descrip = f"{local_time} (UTC-{valor_utc})"
        TimeStamp = local_dt.strftime('%d/%m/%Y %H:%M:%S')
        mostrar = "Si"

        # Bloque de lógica para discriminar puntos entre los escenarios posibles
        # Recordar que no todos los escenarios están cubiertos, siempre habrán algunos
        # Que escapen a esta lógica.
        def is_terreno_waypoint(wpt_name: str, elevation: float = None) -> bool:
            """
            Determina si un waypoint es de terreno basado en múltiples criterios
            
            Criterios para puntos de terreno:
            - Debe tener elevación (principal indicador)
            - El nombre debe ser numérico o seguir patrones específicos
            - No debe comenzar con prefijos típicos de puntos precargados
            """
            # Lista de prefijos comunes para puntos precargados
            prefijos_otros = ['A', 'B', 'C', 'P', 'EST', 'E', 'REF', 'R']
            
            # Si no hay elevación, probablemente no es punto de terreno
            if elevation is None:
                return False
                
            # Verificar si el nombre comienza con algún prefijo de puntos precargados
            for prefijo in prefijos_otros:
                if wpt_name.upper().startswith(prefijo):
                    # Si tiene un prefijo conocido y números, es un punto precargado
                    if any(char.isdigit() for char in wpt_name[len(prefijo):]):
                        return False
            
            # Verificar si es puramente numérico
            if wpt_name.isdigit():
                return True
                
            # Verificar patrones específicos de puntos de terreno
            # Por ejemplo: "123A", "456B" - números seguidos de una letra
            if len(wpt_name) > 1:
                base = wpt_name[:-1]
                suffix = wpt_name[-1]
                if base.isdigit() and suffix.isalpha():
                    return True
            
            # Por defecto, si tiene elevación pero no cumple los patrones anteriores,
            # se considera punto precargado
            return False

        # Reemplazar el bloque existente de discriminación de puntos con esta nueva lógica
        clase = 'Terreno' if is_terreno_waypoint(wpt, elevation) else 'Otro'

        new_feat = QgsFeature()
        new_feat.setGeometry(geom)
        new_feat.setAttributes([
            fid,
            wpt,
            Wp_Com,
            Wp_Desc,
            elevation,
            utc_time_str,
            ajuste, 
            rollover,
            local_time,
            dia,
            hora,
            name_hora,
            descrip,
            TimeStamp,
            mostrar,
            clase,
        ])
        features.append(new_feat)
        fid += 1

    fields = QgsFields()
    for field in campos_adicionales:
        fields.append(field)

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'ESRI Shapefile'
    options.fileEncoding = 'UTF-8'

    output_layer = QgsVectorLayer("Point?crs=EPSG:32718", "output_layer", "memory")
    output_layer_data_provider = output_layer.dataProvider()
    output_layer_data_provider.addAttributes(fields)
    output_layer.updateFields()
    output_layer_data_provider.addFeatures(features)

    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
        directorio_salida_shp += '/'

    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

    # Nombre del archivo
    wpt_ptos_shp = f"{directorio_salida_shp}{nombrar_archivo(archivo_excel)} Waypoints Ptos.shp"

    transform_context = QgsCoordinateTransformContext()
    QgsVectorFileWriter.writeAsVectorFormatV3(
        output_layer,
        wpt_ptos_shp,
        transform_context,
        options
    )
    plugin_instance.mensajes_texto_plugin(f"Archivo {nombrar_archivo(archivo_excel)} Waypoints Ptos.shp creado")
    # Lógica añadida para cargar capa .shp directamente a QGIS
    layer = QgsVectorLayer(wpt_ptos_shp, f"{nombrar_archivo(archivo_excel)} Waypoints Ptos.shp", "ogr")
    if not layer.isValid():
        mensaje = f"No pudo cargarse la capa '{nombrar_archivo(archivo_excel)} Waypoints Ptos.shp' en QGIS. Verificar el archivo generado"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return
    
    # Obtener el directorio base del plugin
    plugin_dir = os.path.dirname(__file__)

    # Construir la ruta completa al archivo .qml en la subcarpeta "estilos_qml"
    qml_style_path = os.path.join(plugin_dir, 'estilos_qml', 'Estilo Wpt Puntos.qml')

    if os.path.exists(qml_style_path):
        layer.loadNamedStyle(qml_style_path)
        layer.triggerRepaint()

    # Añadir la capa al proyecto actual en QGIS
    QgsProject.instance().addMapLayer(layer)

    # Concatenar la función para que se siga ejecutando el siguiente código,
    # Sin tener que intervenir en el código principal del plugin
    crear_kmz_terreno_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida_kmz, plugin_instance)
    crear_kmz_otro_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida_kmz, plugin_instance)

def ensure_directory_path(path):
    """Asegura que el directorio termine con un separador"""
    if not path.endswith('/') and not path.endswith('\\'):
        path += '/'
    return path

def create_kmz_file(kml_content, kmz_path, icon_path, icon_name):
    """Crea un archivo KMZ con el contenido KML y el ícono"""
    try:
        with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
            # Primero escribir el documento KML principal
            kmz.writestr('doc.kml', kml_content)
            
            # Crear el directorio files y agregar el ícono
            kmz.writestr('files/', '')
            kmz.write(icon_path, f'files/{icon_name}')
        return True
    except Exception as e:
        return False

def get_icon_path(plugin_dir, icon_name):
    """Obtiene la ruta completa del ícono"""
    return os.path.normpath(os.path.join(plugin_dir, 'files', icon_name))

def crear_kmz_terreno_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida, plugin_instance):
    '''
    Crea un archivo KMZ para waypoints obtenidos en terreno
    '''
    kml_base = '''<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document>
            <name>{nombre}</name>
            <Folder>
                <name>{nombre}</name>
                <Style id="waypoint_terreno">
                    <IconStyle>
                        <scale>0.453543</scale>
                        <Icon>
                            <href>files/icono_wpt_terreno.png</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ffffaa00</color>
                        <scale>0.7</scale>
                    </LabelStyle>
                </Style>
                {placemarks}
            </Folder>
        </Document>
    </kml>'''

    placemark_template = '''
        <Placemark id="{placemark_id}">
            <name>{name}</name>
            <description>{descrip}</description>
            <TimeStamp><when>{UTC}</when></TimeStamp>
            <styleUrl>#waypoint_terreno</styleUrl>
            <Point><coordinates>{coordinates}</coordinates></Point>
        </Placemark>'''

    try:
        # Leer la capa shapefile
        capa_shp = QgsVectorLayer(wpt_ptos_shp, "capa_shp", "ogr")
        if not capa_shp.isValid():
            raise ValueError(f"Error al cargar la capa {wpt_ptos_shp}")

        transform = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
        directorio_salida = ensure_directory_path(directorio_salida)
        plugin_dir = os.path.dirname(__file__)
        
        placemarks = []
        hay_puntos_terreno = False

        for feat in capa_shp.getFeatures():
            if feat['Clase'] == 'Terreno':
                hay_puntos_terreno = True
                coords = feat.geometry().asPoint()
                lon, lat = transform.transform(coords.x(), coords.y())
                fecha = feat['Dia'].split('/')
                placemark = placemark_template.format(
                    placemark_id=feat.id(),
                    name=feat['Name'],
                    descrip=feat['Descrip'],
                    UTC=f"{fecha[0]}-{fecha[1]}-{fecha[2]}T{feat['Hora']}Z",
                    coordinates=f"{lon},{lat},0"
                )
                placemarks.append(placemark)

        if not hay_puntos_terreno:
            plugin_instance.mensajes_texto_plugin("\nNo se encontraron waypoints de terreno")
            return

        nombre_temp = nombrar_archivo(archivo_excel)
        nombre_kmz_terreno = f"{nombre_temp} Waypoints Ptos Terreno.kmz"

        kml_content = kml_base.format(
            nombre=f"{nombre_temp} Wpt Ptos Terreno",
            placemarks='\n'.join(placemarks)
        )

        icon_path = get_icon_path(plugin_dir, 'icono_wpt_terreno.png')
        kmz_path = f"{directorio_salida}{nombre_kmz_terreno}"
        
        if create_kmz_file(kml_content, kmz_path, icon_path, 'icono_wpt_terreno.png'):
            plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_kmz_terreno} creado")
        else:
            plugin_instance.mensajes_texto_plugin("\nError al crear archivo KMZ de waypoints terreno")

    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"\nError en crear_kmz_terreno_desde_shp: {str(e)}")

def crear_kmz_otro_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida, plugin_instance):
    '''
    Crea un archivo KMZ para waypoints precargados
    '''
    kml_base = '''<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document>
            <name>{nombre}</name>
            <Folder>
                <name>{nombre}</name>
                <Style id="waypoint_otro">
                    <IconStyle>
                        <scale>0.453543</scale>
                        <Icon>
                            <href>files/icono_wpt_otro.png</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ff00aaff</color>
                        <scale>0.7</scale>
                    </LabelStyle>
                </Style>
                {placemarks}
            </Folder>
        </Document>
    </kml>'''

    placemark_template = '''
        <Placemark id="{placemark_id}">
            <name>{name}</name>
            <description>{descrip}</description>
            <styleUrl>#waypoint_otro</styleUrl>
            <Point><coordinates>{coordinates}</coordinates></Point>
        </Placemark>'''

    try:
        capa_shp = QgsVectorLayer(wpt_ptos_shp, "capa_shp", "ogr")
        if not capa_shp.isValid():
            raise ValueError(f"Error al cargar la capa {wpt_ptos_shp}")

        transform = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
        directorio_salida = ensure_directory_path(directorio_salida)
        plugin_dir = os.path.dirname(__file__)
        
        placemarks = []
        hay_puntos_otro = False

        for feat in capa_shp.getFeatures():
            if feat['Clase'] == 'Otro':
                hay_puntos_otro = True
                coords = feat.geometry().asPoint()
                lon, lat = transform.transform(coords.x(), coords.y())
                placemark = placemark_template.format(
                    placemark_id=feat.id(),
                    name=feat['Wpt'],
                    descrip=feat['Descrip'],
                    coordinates=f"{lon},{lat},0"
                )
                placemarks.append(placemark)

        if not hay_puntos_otro:
            plugin_instance.mensajes_texto_plugin("\nNo se encontraron waypoints otros")
            return

        nombre_temp = nombrar_archivo(archivo_excel)
        nombre_kmz_otros = f"{nombre_temp} Waypoints Ptos Otros.kmz"

        kml_content = kml_base.format(
            nombre=f"{nombre_temp} Wpt Ptos Otros",
            placemarks='\n'.join(placemarks)
        )

        icon_path = get_icon_path(plugin_dir, 'icono_wpt_otro.png')
        kmz_path = f"{directorio_salida}{nombre_kmz_otros}"
        
        if create_kmz_file(kml_content, kmz_path, icon_path, 'icono_wpt_otro.png'):
            plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_kmz_otros} creado")
        else:
            plugin_instance.mensajes_texto_plugin("\nError al crear archivo KMZ de waypoints otros")

    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"\nError en crear_kmz_otro_desde_shp: {str(e)}")