#########################################################################################
#                     CODIGO PARA CREAR SEGMENTOS DE TRACK                              #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                 PROGRAMADO POR MANUEL E. CANO NESBET - 2024                           #
#########################################################################################

import zipfile
import os
from pyproj import Transformer
from PyQt5.QtCore import QVariant
from typing import Optional, List, Dict, Tuple
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
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsPoint,
)

def get_field_definitions() -> List[QgsField]:
    """Retorna la lista de campos para la capa de segmentos."""
    return [
        QgsField("Local_min", QVariant.String, len=50),
        QgsField("Local_max", QVariant.String, len=50),
        QgsField("km_hr", QVariant.Double),
        QgsField("kt", QVariant.Double),
        QgsField("Velocidad", QVariant.Int, len=5),
        QgsField("Name", QVariant.String, len=20),
        QgsField("Descrip", QVariant.String, len=50),
        QgsField("Dia", QVariant.String, len=50),  # Campo añadido
        QgsField("Hora", QVariant.String, len=50)  # Campo añadido
    ]

def process_point_features(layer: QgsVectorLayer) -> List[QgsFeature]:
    """Procesa los puntos de la capa y los ordena por tiempo."""
    features = sorted(layer.getFeatures(), key=lambda f: f["Hora"])
    puntos = []
    for feature in features:
        geom = feature.geometry()
        point = geom.asPoint()
        puntos.append(QgsPoint(point.x(), point.y()))
    return puntos

def create_segment_feature(puntos: List[QgsPoint], i: int, features: List[QgsFeature], 
                         crs: QgsCoordinateReferenceSystem) -> Optional[Tuple[QgsFeature, Dict]]:
    """Crea una característica de segmento con sus atributos."""
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromPolyline([puntos[i], puntos[i + 1]]))
    
    distancia_entre_puntos = obtener_distancia(puntos[i], puntos[i + 1], crs)
    
    # Verificar si la distancia es cero para evitar división por cero
    if distancia_entre_puntos == 0:
        return None
    
    tiempo_entre_puntos = obtener_segundos(features[i]["Hora"], features[i+1]["Hora"])
    
    km_hr_valor = round(km_h(distancia_entre_puntos, tiempo_entre_puntos), 2)
    kt_valor = round(obtener_nudos(km_hr_valor), 2)
    distancia_valor = round(distancia_entre_puntos, 1)
    tiempo_valor = int(tiempo_entre_puntos)
    velocidad_valor = obtener_velocidad_int(kt_valor)
    name_valor = f"{round(kt_valor, 1)} kt"

    attrs = {
        "Local_min": f"{features[i]['Dia']} {features[i]['Hora']}",
        "Local_max": f"{features[i+1]['Dia']} {features[i+1]['Hora']}",
        "km_hr": km_hr_valor,
        "kt": kt_valor,
        "Velocidad": velocidad_valor,
        "Name": name_valor,
        "Descrip": f"{distancia_valor} mt - {tiempo_valor} seg",
        "Dia": features[i]["Dia"],
        "Hora": features[i]["Hora"]
    }
    
    f.setAttributes([
        attrs["Local_min"],
        attrs["Local_max"], 
        attrs["km_hr"],
        attrs["kt"],
        attrs["Velocidad"],
        attrs["Name"],
        attrs["Descrip"],
        attrs["Dia"],    # Campo añadido
        attrs["Hora"]    # Campo añadido
    ])
    return f, attrs

def crear_segmentos_track(archivo_excel: str, directorio_salida_shp: str, 
                         directorio_salida_kmz: str, plugin_instance: any) -> Optional[str]:
    """
    Función para obtener segmentos de track a partir de archivo .shp de geometría de puntos.
    
    Args:
        archivo_excel: Archivo Excel con datos estandarizados para el nombre del archivo
        directorio_salida_shp: Directorio de salida para archivos
        directorio_salida_kmz: Directorio de salida para archivos KMZ
        plugin_instance: Instancia del plugin para mensajes
        
    Returns:
        None: Retorna None solo en caso de error
    """
    try:
        # Normalizar rutas y directorios
        directorio_salida_shp = os.path.normpath(directorio_salida_shp)
        if not directorio_salida_shp.endswith(os.sep):
            directorio_salida_shp += os.sep

        nombre_capa_shp = os.path.normpath(f"{directorio_salida_shp}{nombrar_archivo(archivo_excel)} Track Ptos.shp")
        
        # Verificar si el archivo existe antes de intentar cargarlo
        if not os.path.exists(nombre_capa_shp):
            mensaje = f"\nsegmentos_track.crear_segmentos_track: Archivo de puntos no encontrado: {nombre_capa_shp}"
            plugin_instance.mensajes_texto_plugin(mensaje)
            return None
        
        # Cargar capa de puntos
        layer = QgsVectorLayer(nombre_capa_shp, "puntos", "ogr")
        if not layer.isValid():
            mensaje = f"\nsegmentos_track.crear_segmentos_track: Error al cargar la capa: {nombre_capa_shp}"
            plugin_instance.mensajes_texto_plugin(mensaje)
            return None

        # Verificar que la capa tenga features
        feature_count = layer.featureCount()
        if feature_count == 0:
            mensaje = f"\nsegmentos_track.crear_segmentos_track: La capa de puntos está vacía: {nombre_capa_shp}"
            plugin_instance.mensajes_texto_plugin(mensaje)
            return None
            
        plugin_instance.mensajes_texto_plugin(f"Capa de puntos cargada exitosamente con {feature_count} features")

        # Preparar capa de salida
        fields = QgsFields()
        for field in get_field_definitions():
            fields.append(field)

        # Crear capa temporal
        output_layer = QgsVectorLayer("LineString?crs={}".format(layer.crs().authid()), 
                                    "segmentos", "memory")
        output_layer_data_provider = output_layer.dataProvider()
        output_layer_data_provider.addAttributes(fields)
        output_layer.updateFields()

        # Procesar puntos
        puntos = process_point_features(layer)
        
        # Crear segmentos
        segmentos_omitidos = 0
        for i in range(len(puntos) - 1):
            resultado = create_segment_feature(puntos, i, 
                                             sorted(layer.getFeatures(), key=lambda f: f["Hora"]), 
                                             layer.crs())
            if resultado is None:
                segmentos_omitidos += 1
                continue
            feature, _ = resultado
            output_layer_data_provider.addFeature(feature)
        
        # Informar sobre segmentos omitidos si los hay
        if segmentos_omitidos > 0:
            plugin_instance.mensajes_texto_plugin(f"Se omitieron {segmentos_omitidos} segmentos con distancia cero (puntos duplicados)")

        # Guardar archivo SHP
        nombre_archivo = f'{nombrar_archivo(archivo_excel)} Track Segmentos.shp'
        nombre_track_segmentos_shp = f'{directorio_salida_shp}{nombre_archivo}'

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        QgsVectorFileWriter.writeAsVectorFormatV3(
            output_layer,
            nombre_track_segmentos_shp,
            QgsCoordinateTransformContext(),
            options)

        plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_archivo} creado")

        # Cargar capa en QGIS
        layer = QgsVectorLayer(nombre_track_segmentos_shp, nombre_archivo, "ogr")
        if not layer.isValid():
            mensaje = f"No pudo cargarse la capa '{nombre_archivo}' en QGIS. Verificar el archivo generado"
            plugin_instance.mensajes_texto_plugin(mensaje)
            return None

        # Aplicar estilo
        plugin_dir = os.path.dirname(__file__)
        qml_style_path = os.path.join(plugin_dir, 'estilos_qml', 'Estilo Track Segmentos.qml')
        if os.path.exists(qml_style_path):
            layer.loadNamedStyle(qml_style_path)
            layer.triggerRepaint()

        QgsProject.instance().addMapLayer(layer)

        # Generar KMZ
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
            return None

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
        nombre_temp = nombrar_archivo(archivo_excel)
        nombre_kmz = f"{nombre_temp} Track Segmentos" 

        kml_content = kml_base.format(
            nombre=nombre_kmz,
            placemarks=placemarks,
        )
        
        # Guardar el contenido KML en un archivo
        kml_filename = f"{directorio_salida_kmz}doc.kml"
        with open(kml_filename, 'w') as file:
            file.write(kml_content)   

        # Crear KMZ, que no es más que un zip con extensión cambiada
        kmz_filename = f"{directorio_salida_kmz}{nombre_kmz}.kmz"
        with zipfile.ZipFile(kmz_filename, 'w') as kmz:
            kmz.write(kml_filename, arcname=os.path.basename(kml_filename))
            
        # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
        os.remove(kml_filename)
        plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_kmz}.kmz creado")
        # No return needed here - successful execution

    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"Error en crear_segmentos_track: {str(e)}")
        return None  # Return None only on error