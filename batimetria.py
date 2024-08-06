#########################################################################################
#                CODIGO PARA CREACIÓN DE KM A PARTIR DE BATIMETRÍA                      #
#                 GENERACIÓN DE ARCHIVO KMZ CON DATOS RESPECTIVOS                       #
#                PROGRAMADO POR MANUEL E. CANO NESBET - 05-06-2024                      #
# ToDo:                                                                                 #
#########################################################################################

import os
from pyproj import Transformer
import zipfile

from qgis.core import QgsVectorLayer

def batimetria_kmz(batimetria_shp, directorio_salida_kmz, plugin_instance):
    """
    Función que transforma .shp batimetria en KMZ
    Toma como parámetro la batimetria
    - Archivo de batimetría shp extraído desde servicio de mapa Sernapesca
    - Directorio de salida donde se guardarán los archivos
    """
    # Crear contenido KML y KMZ
    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="1">
            <Folder id="3">
                <Style id="0">
                    <LineStyle id="1">
                        <color>cab3b3b3</color>
                        <colorMode>normal</colorMode>
                        <width>0.52</width>
                        <gx:labelVisibility>True</gx:labelVisibility>
                    </LineStyle>
                    <PolyStyle id="2">
                        <color>cab3b3b3</color>
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
        <description><![CDATA[
        <table>
        <tr style="background-color:#DDDDFF;"><td>Centro</td><td>{centro}</td></tr>
        <tr><td>Fuente</td><td>{fuente}</td></tr>
        </table>
        ]]></description>
        <styleUrl>#0</styleUrl>
        <ExtendedData>
            <Data name="Centro">
                <value>{centro}</value>
                <displayName>Centro</displayName>
            </Data>
            <Data name="Fuente">
                <value>{fuente}</value>
                <displayName>Fuente</displayName>
            </Data>
        </ExtendedData>
        <MultiGeometry id="{multi_geometry_id}">
            {line_strings}
        </MultiGeometry>
    </Placemark>
    '''

    line_string_template = '''
    <LineString id="{line_string_id}">
        <coordinates>{coordinates}</coordinates>
    </LineString>
    '''

    # Leer el .shp que se entrega listo a diferencia de los otros procesos
    capa_shp = QgsVectorLayer(batimetria_shp, "capa_shp", "ogr")
    if not capa_shp.isValid():
        mensaje = f"\nbatimetria.batimetria_kmz: Error al cargar la capa {batimetria_shp} SHP."
        plugin_instance.mensajes_texto_plugin(mensaje)
        return    

    # Configurar la transformación de coordenadas con Transformer
    transformer = Transformer.from_crs("epsg:4326", "epsg:4326", always_xy=True)

    placemarks = ''
    placemark_id = 1
    multi_geometry_id = 1
    line_string_id = 1

    for feat in capa_shp.getFeatures():
        geom = feat.geometry()
        coords = geom.asMultiPolyline()

        # Crear múltiples LineString para cada Placemark
        line_strings = ''
        for line in coords:
            coordinates = ''
            for point in line:
                lon, lat = transformer.transform(point.x(), point.y())
                coordinates += f"{lon},{lat},0 "

            line_string = line_string_template.format(
                line_string_id=line_string_id,
                coordinates=coordinates.strip(),
            )
            line_strings += line_string
            line_string_id += 1

        name = feat['z'] # El nombre de cada car. es la profundidad
        fuente = feat['fuente']
        centro = feat['cd_centro']

        placemark = placemark_template.format(
            placemark_id=placemark_id,
            name=name,
            fuente=fuente,
            centro=centro,
            multi_geometry_id=multi_geometry_id,
            line_strings=line_strings,
        )
        placemarks += placemark
        placemark_id += 1
        multi_geometry_id += 1

    # Nombre archivo KMZ
    nombre_kmz = "batimetria" 

    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

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
        kmz.write(kml_filename, arcname=kml_filename)
        
    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    os.remove(kml_filename)
    # Pasar al box de texto un mensaje que indique que se creó el archivo.
    mensaje_ok = f"\nArchivo {nombre_kmz}.kmz creado"
    plugin_instance.mensajes_texto_plugin(mensaje_ok)