#########################################################################################
#                     CODIGO PARA CREAR SEGMENTOS DE TRACK                              #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                 PROGRAMADO POR MANUEL E. CANO NESBET - 2024                           #
# ToDo:                                                                                 #
# - Manejo de errores y excepciones                                                     #
# - Mensajes de consola que se pasen a plugin para visualización                        #
#########################################################################################

import zipfile
import os
from pyproj import Transformer
from PyQt5.QtCore import QVariant
from .utils import (
    nombrar_archivo,
    obtener_distancia,
    obtener_segundos,
    obtener_nudos,
    km_h,
    obtener_velocidad_int,
    estilo_segmento,
    )

from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsVectorFileWriter,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsCoordinateTransformContext,
    QgsGeometry,
    QgsPoint,
)

def crear_segmentos_track(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    """
    Función para obtener segmentos de track a partir de archivo .shp
    de geometría de puntos. 
    Inputs:
    - Archivo Excel cargado con datos estandarizados para el nombre del archivo
    - Directorio de salida donde se guardarán los archivos
    """
    # Sección para encontrar archivo de puntos de track.
    # Se implementa de este modo para no intervenir el archivo principal del plugin
    # Se elimina como input y se maneja de forma interna

    #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
        directorio_salida_shp += '/'

    nombre_capa_shp = os.path.normpath(f"{directorio_salida_shp}{nombrar_archivo(archivo_excel)} Track Ptos.shp")

    # Cargar la capa de puntos
    layer = QgsVectorLayer(nombre_capa_shp, "puntos", "ogr")
    if not layer.isValid():
        mensaje = f"\nsegmentos_track.crear_segmentos_track: Error al cargar la capa: {nombre_capa_shp}"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    # Crear una nueva capa de líneas
    fields = QgsFields()
    fields.append(QgsField("Local_min", QVariant.String, len=50))
    fields.append(QgsField("Local_max", QVariant.String, len=50))
    fields.append(QgsField("km_hr", QVariant.Double))
    fields.append(QgsField("kt", QVariant.Double))
    fields.append(QgsField("Velocidad", QVariant.Int, len=5))
    fields.append(QgsField("Name", QVariant.String, len=20))
    fields.append(QgsField("Descrip", QVariant.String, len=50))
    fields.append(QgsField("Dia", QVariant.String, len=50))
    fields.append(QgsField("Hora", QVariant.String, len=50))

    crs = layer.crs()
    transform_context = QgsProject.instance().transformContext()

    # Crear una capa temporal para los segmentos de línea
    output_layer = QgsVectorLayer("LineString?crs={}".format(crs.authid()), "segmentos", "memory")
    output_layer_data_provider = output_layer.dataProvider()
    output_layer_data_provider.addAttributes(fields)
    output_layer.updateFields()

    # Leer los puntos y crear segmentos de línea
    features = sorted(layer.getFeatures(), key=lambda f: f["Hora"])  # Ordenar por tiempo

    puntos = []
    for feature in features:
        geom = feature.geometry()
        point = geom.asPoint()
        puntos.append(QgsPoint(point.x(), point.y()))

    for i in range(len(puntos) - 1):
        f = QgsFeature(output_layer.fields())
        f.setGeometry(QgsGeometry.fromPolyline([puntos[i], puntos[i + 1]]))

        distancia_entre_puntos = obtener_distancia(puntos[i], puntos[i + 1], crs)
        tiempo_entre_puntos = obtener_segundos(features[i]["Hora"], features[i+1]["Hora"])
        # Redondear los valores a 2 decimales
        km_hr_valor = round(km_h(distancia_entre_puntos, tiempo_entre_puntos), 2)
        kt_valor = round(obtener_nudos(km_hr_valor), 2)
        distancia_valor = round(distancia_entre_puntos, 1)
        tiempo_valor = int(tiempo_entre_puntos)
        velocidad_valor = obtener_velocidad_int(kt_valor)
        name_valor = f"{round(kt_valor, 1)} kt"

        # Copiar atributos desde el punto inicial
        f.setAttribute("Local_min", f"{features[i]['Dia']} {features[i]['Hora']}")
        f.setAttribute("Local_max", f"{features[i+1]['Dia']} {features[i+1]['Hora']}")
        f.setAttribute("km_hr", km_hr_valor)
        f.setAttribute("kt", kt_valor)
        f.setAttribute("Velocidad", velocidad_valor)
        f.setAttribute("Name", name_valor)
        f.setAttribute("Descrip", f"{distancia_valor} mt - {tiempo_valor} seg")
        f.setAttribute("Dia", features[i]["Dia"])
        f.setAttribute("Hora", features[i]["Hora"])

        output_layer_data_provider.addFeature(f)

    #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
        directorio_salida_shp += '/'

    # Darle nombre al archivo
    nombre_archivo = f'{nombrar_archivo(archivo_excel)} Track Segmentos.shp'
    nombre_track_segmentos_shp = f'{directorio_salida_shp}{nombre_archivo}'

    # Guardar la capa de segmentos en un archivo .shp usando writeAsVectorFormatV3
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    QgsVectorFileWriter.writeAsVectorFormatV3(
        output_layer,
        nombre_track_segmentos_shp,
        QgsCoordinateTransformContext(),
        options)


    ######################################################
    ##### ACA TERMINA LA LOGICA DE CAPAS GEOGRAFICAS #####
    ######################################################

    ##### ------------------------------------------ #####

    #############################################################
    ##### ACA EMPIEZA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################
        
    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="1">
            <Folder id="18">
            <Style id="0">
                <LineStyle id="1">
                    <color>ff2ca033</color>
                    <colorMode>normal</colorMode>
                    <width>1.32</width>
                    <gx:labelVisibility>True</gx:labelVisibility>
                </LineStyle>
                <PolyStyle id="2">
                    <color>ff2ca033</color>
                    <colorMode>normal</colorMode>
                    <fill>1</fill>
                    <outline>1</outline>
                </PolyStyle>
            </Style>
            <Style id="3">
                <LineStyle id="4">
                    <color>ffb8d6de</color>
                    <colorMode>normal</colorMode>
                    <width>1.32</width>
                    <gx:labelVisibility>True</gx:labelVisibility>
                </LineStyle>
                <PolyStyle id="5">
                    <color>ffb8d6de</color>
                    <colorMode>normal</colorMode>
                    <fill>1</fill>
                    <outline>1</outline>
                </PolyStyle>
            </Style>
            <Style id="6">
                <LineStyle id="7">
                    <color>ffb1bef2</color>
                    <colorMode>normal</colorMode>
                    <width>1.32</width>
                    <gx:labelVisibility>True</gx:labelVisibility>
                </LineStyle>
                <PolyStyle id="8">
                    <color>ffb1bef2</color>
                    <colorMode>normal</colorMode>
                    <fill>1</fill>
                    <outline>1</outline>
                </PolyStyle>
            </Style>
            <Style id="9">
                <LineStyle id="10">
                    <color>ff8895e3</color>
                    <colorMode>normal</colorMode>
                    <width>1.32</width>
                    <gx:labelVisibility>True</gx:labelVisibility>
                </LineStyle>
                <PolyStyle id="11">
                    <color>ff8895e3</color>
                    <colorMode>normal</colorMode>
                    <fill>1</fill>
                    <outline>1</outline>
                </PolyStyle>
            </Style>
            <Style id="12">
                <LineStyle id="13">
                    <color>ff5f6bd5</color>
                    <colorMode>normal</colorMode>
                    <width>1.32</width>
                    <gx:labelVisibility>True</gx:labelVisibility>
                </LineStyle>
                <PolyStyle id="14">
                    <color>ff5f6bd5</color>
                    <colorMode>normal</colorMode>
                    <fill>1</fill>
                    <outline>1</outline>
                </PolyStyle>
            </Style>
            <Style id="15">
                <LineStyle id="16">
                    <color>ff3642c6</color>
                    <colorMode>normal</colorMode>
                    <width>1.32</width>
                    <gx:labelVisibility>True</gx:labelVisibility>
                </LineStyle>
                <PolyStyle id="17">
                    <color>ff3642c6</color>
                    <colorMode>normal</colorMode>
                    <fill>1</fill>
                    <outline>1</outline>
                </PolyStyle>
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
                <TimeStamp id="{timestamp_id}">
                    <when>{when}</when>
                </TimeStamp>
                <styleUrl>{estilo_id}</styleUrl>
                <MultiGeometry id="{multi_geometry_id}">
                    <LineString id="{line_string_id}">
                        <coordinates>
                        {coordinates}
                        </coordinates>
                    </LineString>
                </MultiGeometry>
            </Placemark>
    '''
    # Leer el shapefile asociado a los tracks, se obtiene desde la primera parte de la lógica
    capa_shp = QgsVectorLayer(nombre_track_segmentos_shp, "capa_shp", "ogr")
    if not capa_shp.isValid():
        mensaje = f"\nsegmentos_track.crear_segmentos_track: Error al cargar la capa {nombre_track_segmentos_shp} SHP."
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    # Configurar la transformación de coordenadas con Transformer
    transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)

    placemarks = ''
    placemark_id = 20
    multi_geometry_id = 19
    line_string_id = 21
    timestamp_id = 23

    for feat in capa_shp.getFeatures():
        geom = feat.geometry()
        coords = geom.asMultiPolyline()

        # Crear una cadena de coordenadas para KML
        coordinates = ''
        for line in coords:
            for point in line:
                lon, lat = transformer.transform(point.x(), point.y())
                coordinates += f"{lon},{lat},0 "

        name = feat['Name'] # El nombre de cada car. es los nudos... creo
        fecha_separada = feat['Dia'].split('/')
        # No hay forma de evitar este punto para pasar los meses a español...
        when = f"{fecha_separada[0]}-{fecha_separada[1]}-{fecha_separada[2]}T{feat['Hora']}"
        descrip = feat['Descrip']
        estilo_id = f"#{estilo_segmento(int(feat['Velocidad']))}"

        placemark = placemark_template.format(
            placemark_id=placemark_id,
            name=name,
            descrip=descrip,
            timestamp_id=timestamp_id,
            when=when,
            estilo_id=estilo_id,
            multi_geometry_id=multi_geometry_id,
            line_string_id=line_string_id,
            coordinates=coordinates.strip(),            
        )
        placemarks += placemark
        placemark_id += 5
        multi_geometry_id += 5
        line_string_id += 5
        timestamp_id += 5

    #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

    # Nombre archivo KMZ
    nombre_kmz = f"{nombrar_archivo(archivo_excel)} Track Segmentos" 

    kml_content = kml_base.format(
        nombre=nombre_kmz,
        placemarks=placemarks,
    )
    
    # Guardar el contenido KML en un archivo
    kml_filename = f"{directorio_salida_kmz}{nombre_kmz}.kml"
    with open(kml_filename, 'w') as file:
        file.write(kml_content)   

    # Crear KMZ, que no es más que un zip con extensión cambiada
    kmz_filename = f"{directorio_salida_kmz}{nombre_kmz}.kmz"
    with zipfile.ZipFile(kmz_filename, 'w') as kmz:
        kmz.write(kml_filename, arcname=os.path.basename(kml_filename))
        
    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    os.remove(kml_filename)