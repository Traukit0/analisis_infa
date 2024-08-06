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
from datetime import datetime, timedelta
from PyQt5.QtCore import QVariant
from .utils import nombrar_archivo

# Asegurar que las rutas de QGIS y Python estén configuradas
# En desarrollo se deben declarar antes por problema de qgis.core

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
        utc_time = feat['time']
        utc_time_str = utc_time.toString('yyyy/MM/dd HH:mm:ss.zzz')
        utc_dt = datetime.strptime(utc_time_str, '%Y/%m/%d %H:%M:%S.%f')
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
        try:
            clase = "Terreno" if elevation is not None else "Otro"
        except:
            mensaje = """\nSe encontró un error en la disriminación de puntos por altura
                  revisar archivo .shp ya que ambos tipos de puntos tienen datos de altitud"""
            plugin_instance.mensajes_texto_plugin(mensaje)
            quit()

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
    # Concatenar la función para que se siga ejecutando el siguiente código,
    # Sin tener que intervenir en el código principal del plugin
    crear_kmz_terreno_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida_kmz, plugin_instance)
    crear_kmz_otro_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida_kmz, plugin_instance)

def crear_kmz_terreno_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida, plugin_instance):
    '''
    Crea un archivo KMZ a partir de un archivo SHP
    El archivo KMZ creado corresponde a waypoints
    obtenidos en terreno, con dato de altura. Tiene asociado un timestamp
    Inputs: 
    - wpt_ptos_shp = Archivo desde el cual se obtendrán os datos para generar KMZ
    - archivo_excel = Archivo para obtener datos de fecha y nombre
    - directorio_salida = Donde se guarda finalmente el archivo
    '''
    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="27">
            <Folder id="4">
                <Style id="0">
                    <IconStyle id="1">
                        <scale>0.453543</scale>
                        <heading>0</heading>
                        <Icon id="2">
                            <href>{icono}</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ffffaa00</color>
                        <scale>0.7</scale>
                    </LabelStyle>
                    <LineStyle id="3">
                        <color>ffb4781f</color>
                        <colorMode>normal</colorMode>
                    </LineStyle>
                </Style>
                <name>{nombre}</name>
                {placemarks}
            </Folder>
        </Document>
    </kml>
    '''
    placemark_template = '''
        <Placemark id="{placemark_id}">
            <name>{name}</name>
            <description>{descrip}</description>
            <TimeStamp id="{placemark_id}">
                <when>{UTC}</when>
            </TimeStamp>
            <styleUrl>#0</styleUrl>
            <Point id="{multi_geometry_id}">
                <coordinates>{coordinates}</coordinates>
            </Point>
        </Placemark>
    '''

    # Leer la capa shapefile
    capa_shp = QgsVectorLayer(wpt_ptos_shp, "capa_shp", "ogr")
    if not capa_shp.isValid():
        mensaje = f"\nwpt_gpx.crear_kmz_terreno_desde_shp: Error al cargar la capa {wpt_ptos_shp} SHP."
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    transform = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)

    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida.endswith('/') and not directorio_salida.endswith('\\'):
        directorio_salida += '/'

    # Esto es para darle el camino correcto al ícono en el entorno del plugin
    plugin_dir = os.path.dirname(__file__)

    # Icono para los puntos de track
    icono_path = os.path.normpath(os.path.join(plugin_dir, 'files', 'icono_wpt_terreno.png'))
    nombre_kmz = f"{nombrar_archivo(archivo_excel)} Waypoints Ptos Terreno"
    placemarks = ''
    placemark_id = 1
    hay_puntos_terreno = False
    for feat in capa_shp.getFeatures():
        if feat['Clase'] == 'Terreno': # Comprobar que sean wpt de terreno
            hay_puntos_terreno = True
            geom = feat.geometry()
            coords = geom.asPoint()
            lon, lat = transform.transform(coords.x(), coords.y())
            coordinates = f"{lon},{lat},0"
            name = feat['Name']
            descrip = feat['Descrip']
            fecha_separada = feat['Dia'].split('/')
            UTC = f"{fecha_separada[0]}-{fecha_separada[1]}-{fecha_separada[2]}T{feat['Hora']}Z"
            
            placemark = placemark_template.format(
                placemark_id=placemark_id,
                name=name,
                descrip=descrip,
                UTC=UTC,
                multi_geometry_id=placemark_id,
                coordinates=coordinates
            )
            placemarks += placemark
            placemark_id += 1

        kml_content = kml_base.format(
            nombre=nombre_kmz,
            placemarks=placemarks,
            icono=icono_path
        )

    # Snippet para verificar que de no existir ptos. como "otro" no genere el kmz
    if not hay_puntos_terreno:
        hay_puntos_terreno_msg_error = "\nNo se encontraron waypoints con 'Clase' = 'Terreno'. No se genera archivo KMZ"
        plugin_instance.mensajes_texto_plugin(hay_puntos_terreno_msg_error)
        return

    # Guardar el contenido KML en un archivo
    kml_filename = f"{directorio_salida}{nombre_kmz}.kml"
    with open(kml_filename, 'w') as file:
        file.write(kml_content)

    # Crear KMZ, que no es más que un zip con extensión cambiada
    kmz_filename = f"{directorio_salida}{nombre_kmz}.kmz"
    with zipfile.ZipFile(kmz_filename, 'w') as kmz:
        kmz.write(kml_filename, arcname=kml_filename)
        kmz.write(icono_path, arcname=icono_path)

    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    os.remove(kml_filename)

def crear_kmz_otro_desde_shp(wpt_ptos_shp, archivo_excel, directorio_salida, plugin_instance):
    '''
    Crea un archivo KMZ a partir de un archivo SHP
    El archivo KMZ creado corresponde a waypoints
    cargados previamente en el GPS, sin dato de altura.
    - wpt_ptos_shp = Archivo desde el cual se obtendrán os datos para generar KMZ
    - archivo_excel = Archivo para obtener datos de fecha y nombre
    - directorio_salida = Donde se guarda finalmente el archivo
    '''
    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="27">
            <Folder id="4">
                <Style id="0">
                    <IconStyle id="1">
                        <scale>0.453543</scale>
                        <heading>0</heading>
                        <Icon id="2">
                            <href>{icono}</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ff00aaff</color>
                        <scale>0.7</scale>
                    </LabelStyle>
                    <LineStyle id="3">
                        <color>ffb4781f</color>
                        <colorMode>normal</colorMode>
                    </LineStyle>
                </Style>
                <name>{nombre}</name>
                {placemarks}
            </Folder>
        </Document>
    </kml>
    '''
    placemark_template = '''
        <Placemark id="{placemark_id}">
            <name>{name}</name>
            <description>{descrip}</description>
            <styleUrl>#0</styleUrl>
            <Point id="{multi_geometry_id}">
                <coordinates>{coordinates}</coordinates>
            </Point>
        </Placemark>
    '''

    # Leer la capa shapefile
    capa_shp = QgsVectorLayer(wpt_ptos_shp, "capa_shp", "ogr")
    if not capa_shp.isValid():
        mensaje = f"wpt_gpx.crear_kmz_otro_desde_shp: Error al cargar la capa {wpt_ptos_shp} SHP."
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    transform = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)


    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida.endswith('/') and not directorio_salida.endswith('\\'):
        directorio_salida += '/'

    # Esto es para darle el camino correcto al ícono en el entorno del plugin
    plugin_dir = os.path.dirname(__file__)

    # Icono para los puntos de track
    icono_path = os.path.normpath(os.path.join(plugin_dir, 'files', 'icono_wpt_otro.png'))
    nombre_kmz = f"{nombrar_archivo(archivo_excel)} Waypoints Ptos Otros"

    placemarks = ''
    placemark_id = 1
    hay_puntos_otro = False
    for feat in capa_shp.getFeatures():
        if feat['Clase'] == 'Otro': # Comprobar que sean wpt de terreno
            hay_puntos_otro = True
            geom = feat.geometry()
            coords = geom.asPoint()
            lon, lat = transform.transform(coords.x(), coords.y())
            coordinates = f"{lon},{lat},0"
            name = feat['Wpt']
            descrip = feat['Descrip']
            
            placemark = placemark_template.format(
                placemark_id=placemark_id,
                name=name,
                descrip=descrip,
                multi_geometry_id=placemark_id,
                coordinates=coordinates
            )
            placemarks += placemark
            placemark_id += 1

        kml_content = kml_base.format(
            nombre=nombre_kmz,
            placemarks=placemarks,
            icono=icono_path
        )

    # Snippet para verificar que de no existir ptos. como "otro" no genere el kmz
    if not hay_puntos_otro:
        hay_puntos_otro_msg_error = "\nNo se encontraron waypoints con 'Clase' = 'Otro'. No se genera archivo KMZ"
        plugin_instance.mensajes_texto_plugin(hay_puntos_otro_msg_error)
        return

    # Guardar el contenido KML en un archivo
    kml_filename = f"{directorio_salida}{nombre_kmz}.kml"
    with open(kml_filename, 'w') as file:
        file.write(kml_content)

    # Crear KMZ, que no es más que un zip con extensión cambiada
    kmz_filename = f"{directorio_salida}{nombre_kmz}.kmz"
    with zipfile.ZipFile(kmz_filename, 'w') as kmz:
        kmz.write(kml_filename, arcname=kml_filename)
        kmz.write(icono_path, arcname=icono_path)

    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    os.remove(f"{kml_filename}")