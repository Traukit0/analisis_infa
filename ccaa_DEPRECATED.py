import os
import re
import pandas as pd
import xml.etree.ElementTree as ET
from pyproj import Transformer
from os import remove
import zipfile
from shapely.geometry import Point, Polygon
from .utils import nombrar_archivo, descomprimir_kmz

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsFields,
    QgsCoordinateTransformContext,
    QgsVectorFileWriter,
    QgsProject,
)
from qgis.PyQt.QtCore import QVariant

def extraer_placemark_data_CCAA(kml_file_path, archivo_excel):

    nombre_codigo_centro = nombrar_archivo(archivo_excel)
    codigo_centro = nombre_codigo_centro.split(" ")[0]

    # Parse the KML file
    tree = ET.parse(kml_file_path)
    root = tree.getroot()
    
    # Define the namespace
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    # Find all placemarks
    placemarks = root.findall('.//kml:Placemark', ns)
    
    # Iterate through each placemark
    for placemark in placemarks:
        description = placemark.find('kml:description', ns)
        if description is not None and f'Código de Centro</td><td>{codigo_centro}' in description.text:
            # Parse the HTML content in the description
            # Extract table data from the description using regular expressions
            table_data = re.findall(r'<tr><td>(.*?)</td><td>(.*?)</td></tr>', description.text)

            # Map the extracted data to the desired fields
            data = {field_name: field_value for field_name, field_value in table_data}

            # Map the extracted data to the desired fields
            result = {
                "Cd_Centro": data.get("Código de Centro"),
                "Titular": data.get("Nombre de Titular"),
                "Grupo": data.get("Grupo Especie"),
                "Estado": data.get("Estado"),
            }
            
            # Extract coordinates and remove duplicates
            coordinates = []
            polygon = placemark.find('.//kml:coordinates', ns)
            if polygon is not None:
                coords_text = polygon.text.strip()
                coords_pairs = coords_text.split()
                unique_coords = set()
                for pair in coords_pairs:
                    lon, lat, _ = pair.split(',')
                    coord_tuple = (float(lon), float(lat))
                    if coord_tuple not in unique_coords:
                        unique_coords.add(coord_tuple)
                        coordinates.append(coord_tuple)
            
            return [result, coordinates]
    
    return None

def ccaa_a_shp_kmz(kmz_file_path, archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    kml_file_path=descomprimir_kmz(kmz_file_path, directorio_salida_kmz)
    resultados_placemark=extraer_placemark_data_CCAA(kml_file_path, archivo_excel)
    datos_placemark = resultados_placemark[0]  # Diccionario
    coordenadas = resultados_placemark[1]  # Lista de tuplas

    # Crear un dataframe con las coordenadas
    df = pd.DataFrame(coordenadas, columns=['Longitud', 'Latitud'])
    # Convertir las coordenadas a puntos y luego a un polígono
    points = [Point(xy) for xy in zip(df['Longitud'], df['Latitud'])]
    polygon = Polygon([(p.x, p.y) for p in points])

    # para agregar mas de un atributo
    campos_adicionales = [
        QgsField("Cd_Centro", QVariant.String, len=254),
        QgsField("Titular", QVariant.String, len=254),
        QgsField("Grupo", QVariant.String, len=254),
        QgsField("Estado", QVariant.String, len=254),
        ]

    # Crear una nueva capa de shapefile con atributos
    fields = QgsFields()
    for field in campos_adicionales:
        fields.append(field)
    
    layer = QgsVectorLayer("Polygon?crs=epsg:4326", "Polygons", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()

    # Crear una nueva característica y establecer su geometría y atributos
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt(polygon.wkt))
    feature.setAttributes([
        datos_placemark["Cd_Centro"],
        datos_placemark["Titular"],
        datos_placemark["Grupo"].title(),
        datos_placemark["Estado"].title(),
    ])

    provider.addFeature(feature)
    layer.updateExtents()

    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
        directorio_salida_shp += '/'

    # Guardar la capa en un archivo shapefile
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    transform_context = QgsCoordinateTransformContext()
    nombre_archivo = f"{directorio_salida_shp}CCAA.shp"
    QgsVectorFileWriter.writeAsVectorFormatV3(
        layer,
        nombre_archivo,
        transform_context,
        options)

    # Lógica añadida para cargar capa .shp directamente a QGIS
    layer = QgsVectorLayer(nombre_archivo, "CCAA", "ogr")
    if not layer.isValid():
        mensaje = f"No pudo cargarse la capa 'CCAA' en QGIS. Verificar el archivo generado"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return
    
    # Obtener el directorio base del plugin
    plugin_dir = os.path.dirname(__file__)

    # Construir la ruta completa al archivo .qml en la subcarpeta "estilos_qml"
    qml_style_path = os.path.join(plugin_dir, 'estilos_qml', 'Estilo Kmz CCAA Subpesca.qml')

    if os.path.exists(qml_style_path):
        layer.loadNamedStyle(qml_style_path)
        layer.triggerRepaint()

    # Añadir la capa al proyecto actual en QGIS
    QgsProject.instance().addMapLayer(layer)

    # Crear contenido KML y KMZ
    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document>
            <name>{nombre}</name>
            <StyleMap id="m_ylw-pushpin">
                <Pair>
                    <key>normal</key>
                    <styleUrl>#s_ylw-pushpin</styleUrl>
                </Pair>
                <Pair>
                    <key>highlight</key>
                    <styleUrl>#s_ylw-pushpin_hl</styleUrl>
                </Pair>
            </StyleMap>
            <Style id="s_ylw-pushpin">
                <IconStyle>
                    <scale>1.1</scale>
                    <Icon>
                        <href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
                    </Icon>
                    <hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
                </IconStyle>
                <LineStyle>
                    <width>2</width>
                </LineStyle>
                <PolyStyle>
                    <color>4dffffff</color>
                </PolyStyle>
            </Style>
            <Style id="s_ylw-pushpin_hl">
                <IconStyle>
                    <scale>1.3</scale>
                    <Icon>
                        <href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
                    </Icon>
                    <hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
                </IconStyle>
                <LineStyle>
                    <width>2</width>
                </LineStyle>
                <PolyStyle>
                    <color>4dffffff</color>
                </PolyStyle>
            </Style>
            <Folder id="0">
                <name>CCAA</name>
                {placemarks}
            </Folder>
        </Document>
    </kml>
    '''

    placemark_template = '''
            <Placemark id="{placemark_id}">
                <name>{cod_centro}</name>
                <styleUrl>#m_ylw-pushpin</styleUrl>
                <MultiGeometry id="{multi_geometry_id}">
                    <Polygon id="{polygon_id}">
                        <outerBoundaryIs>
                            <LinearRing id="7">
                                <coordinates>
                                {coordinates}
                                </coordinates>
                            </LinearRing>
                        </outerBoundaryIs>
                    </Polygon>
                </MultiGeometry>
            </Placemark>
    '''
    # Leer el shapefile asociado a los tracks, se obtiene desde la primera parte de la lógica
    capa_shp = QgsVectorLayer(nombre_archivo, "capa_shp", "ogr")
    if not capa_shp.isValid():
        mensaje = f"\nccaa.ccaa_a_shp_kmz: Error al cargar la capa {nombre_archivo}"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    # Configurar la transformación de coordenadas con Transformer
    transformer = Transformer.from_crs("epsg:4326", "epsg:4326", always_xy=True)

    placemarks = ''
    placemark_id = 0
    multi_geometry_id = 0
    polygon_id = 0
    
    for feat in capa_shp.getFeatures():
        geom = feat.geometry()
        coords = geom.asMultiPolygon()

        # Crear una cadena de coordenadas para KML
        coordinates = ''
        for polygon in coords:
            for ring in polygon:
                for point in ring:
                    lon, lat = transformer.transform(point.x(), point.y())
                    coordinates += f"{lon},{lat},0 "

        cod_centro = feat['Cd_Centro']

        placemark = placemark_template.format(
            cod_centro=cod_centro,
            placemark_id=placemark_id,
            multi_geometry_id=multi_geometry_id,
            polygon_id=polygon_id,
            coordinates=coordinates.strip()
        )
        placemarks += placemark
        placemark_id += 1
        multi_geometry_id += 1
        polygon_id += 1

    # Nombre archivo KMZ
    nombre_kmz = "CCAA.kmz"

    kml_content = kml_base.format(
        nombre=nombre_kmz,
        placemarks=placemarks,
    )

    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

    # Guardar el contenido KML en un archivo
    kml_filename = f"{directorio_salida_kmz}CCAA.kml"
    with open(kml_filename, 'w') as file:
        file.write(kml_content)   

    # Crear KMZ, que no es más que un zip con extensión cambiada
    kmz_filename = f"{directorio_salida_kmz}{nombre_kmz}"
    with zipfile.ZipFile(kmz_filename, 'w') as kmz:
        kmz.write(kml_filename, arcname=kml_filename)
        
    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    os.remove(kml_filename)
    # Borrar el archivo doc.kml que se genera al abrir la capa de concesiones
    try:
        os.remove(f'{directorio_salida_kmz}doc.kml')
        print("Archivo base doc.kml removido desde el directorio")
    except:
        print("No se ha encontrado el archivo doc.kml")
    return nombre_archivo