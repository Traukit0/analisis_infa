#########################################################################################
#                    CODIGO PARA ESTACIONES DE MUESTREO MO                              #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                 PROGRAMADO POR MANUEL E. CANO NESBET - 2024                           #
# ToDo:                                                                                 #
# - Manejo de errores y excepciones                                                     #
# - Mensajes de consola que se pasen a plugin para visualización                        #
#########################################################################################

from pyproj import Transformer
import zipfile
from os import remove
import pandas as pd
from .utils import nombrar_archivo

from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsField, QgsCoordinateTransformContext, QgsVectorFileWriter, QgsFields
)
from qgis.PyQt.QtCore import QVariant

def modulos(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    """
    Función para extraer los módulos (puntos y área) del archivo de datos
    Inputs:
    - Archivo Excel cargado con datos estandarizados
    - Directorio de salida donde se guardarán los archivos
    """  
    file_path = archivo_excel
    df = pd.read_excel(file_path, sheet_name='Modulos')

    # Snippet de código para salir de la función en el caso de que las hoja de modulos esté vacía
    if df.empty:
        mensaje = "\nNo hay datos de modulos en el archivo Excel. Si esto es un error revisar archivo"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    ######################################################
    ##### ACA EMPIEZA LA LOGICA DE CAPAS GEOGRAFICAS #####
    ######################################################

    # Crear una capa de puntos en QGIS con la misma estructura de atributos que la tabla Excel
    vlayer = QgsVectorLayer("Point?crs=epsg:32718", "Puntos", "memory")
    pr = vlayer.dataProvider()
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int, "", 254))
    fields.append(QgsField("Fecha", QVariant.Date, "", 254))
    fields.append(QgsField("Modulo", QVariant.Int, "", 254))
    fields.append(QgsField("Vertice", QVariant.Int, "", 254))
    fields.append(QgsField("X", QVariant.Int, "", 254))
    fields.append(QgsField("Y", QVariant.Int, "", 254))
    fields.append(QgsField("Huso", QVariant.Int, "",254))
    pr.addAttributes(fields)
    vlayer.updateFields()

    # Añadir puntos a la capa a través de un iterador
    for index, row in df.iterrows():
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row['X'], row['Y'])))
        feature.setAttributes([str(row['Centro']),
                            str(row['Fecha']),
                            str(row['Modulo']),
                            str(row['Vertice']),
                            str(row['X']),
                            str(row['Y']),
                            str(row['Huso'])])
        pr.addFeature(feature)
    vlayer.updateExtents()

    #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_shp.endswith('/') and not directorio_salida_shp.endswith('\\'):
        directorio_salida_shp += '/'

    # Guardar la capa de puntos en un archivo .shp
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    transform_context = QgsCoordinateTransformContext()

    nombre_archivo = nombrar_archivo(archivo_excel)

    QgsVectorFileWriter.writeAsVectorFormatV3(vlayer,
                                              f"{directorio_salida_shp}{nombre_archivo} Modulos Ptos.shp",
                                              transform_context,
                                              options)

    # Crear una capa de polígonos en QGIS
    pllayer = QgsVectorLayer("Polygon?crs=epsg:32718", "Polígonos", "memory")
    pr = pllayer.dataProvider()
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int, "", 254))
    fields.append(QgsField("Modulo", QVariant.Int, "", 254))
    fields.append(QgsField("Fecha", QVariant.Date, "", 254))
    pr.addAttributes(fields)
    pllayer.updateFields()

    # Crear polígonos a partir de los puntos agrupados por "Modulo"
    polygons = []
    for centro in df['Centro'].unique():
        centro_df = df[df['Centro'] == centro]
        for modulo in centro_df['Modulo'].unique():
            modulo_df = centro_df[centro_df['Modulo'] == modulo].sort_values(by='Vertice')
            polygon = QgsFeature()
            points = [QgsPointXY(row['X'], row['Y']) for idx, row in modulo_df.iterrows()]
            points.append(points[0])  # Cerrar el polígono
            polygon.setGeometry(QgsGeometry.fromPolygonXY([points]))
            polygon.setAttributes([str(centro), str(modulo), str(modulo_df.iloc[0]['Fecha'])])
            pr.addFeature(polygon)
            polygons.append({
                'centro': str(centro),
                'modulo': str(modulo),
                'fecha': str(modulo_df.iloc[0]['Fecha']),
                'points': points
            })
    pllayer.updateExtents()

    # Guardar la capa de polígonos en un archivo .shp
    options.driverName = "ESRI Shapefile"
    QgsVectorFileWriter.writeAsVectorFormatV3(pllayer,
                                              f"{directorio_salida_shp}{nombre_archivo} Modulos Area.shp",
                                              transform_context,
                                              options)

    ######################################################
    ##### ACA TERMINA LA LOGICA DE CAPAS GEOGRAFICAS #####
    ######################################################

    ##### ------------------------------------------ #####

    #############################################################
    ##### ACA EMPIEZA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################

    # Configurar la transformación de coordenadas con Transformer
    transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)

    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="1">
            <Folder id="3">
                <Style id="0">
                    <LineStyle id="1">
                        <color>ff00aaff</color>
                        <colorMode>normal</colorMode>
                        <width>2</width>
                        <gx:labelVisibility>True</gx:labelVisibility>
                    </LineStyle>
                    <PolyStyle id="2">
                        <color>4d00aaff</color>
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
        <tr><td>Fecha</td><td>{fecha}</td></tr>
        </table>
        ]]></description>
        <styleUrl>#0</styleUrl>
        <ExtendedData>
            <Data name="Centro">
                <value>{centro}</value>
                <displayName>Centro</displayName>
            </Data>
            <Data name="Fecha">
                <value>{fecha}</value>
                <displayName>Fecha</displayName>
            </Data>
        </ExtendedData>
        <MultiGeometry id="{multi_geometry_id}">
            <Polygon id="{polygon_id}">
                <outerBoundaryIs>
                    <LinearRing id="{linear_ring_id}">
                        <coordinates>{coordinates}</coordinates>
                    </LinearRing>
                </outerBoundaryIs>
            </Polygon>
        </MultiGeometry>
    </Placemark>
    '''

    placemarks = ''
    for i, poly in enumerate(polygons):
        coords = []
        for point in poly['points']:
            lon, lat = transformer.transform(point.x(), point.y())
            coords.append(f"{lon},{lat},0.0")
        coordinates = " ".join(coords)
        placemarks += placemark_template.format(
            placemark_id=i + 5,
            name=poly['modulo'],
            centro=poly['centro'],
            fecha=poly['fecha'],
            multi_geometry_id=i + 4,
            polygon_id=i + 6,
            linear_ring_id=i + 10,
            coordinates=coordinates
        )

    kml_content = kml_base.format(nombre=f"{nombre_archivo} Modulos Area", placemarks=placemarks)

    #############################################################
    ##### ACA TERMINA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################

        #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

    # Guardar el archivo KML
    nombre = f"{nombre_archivo} Modulos Area"
    with open(f"{directorio_salida_kmz}{nombre}.kml", 'w', encoding='utf-8') as file:
        file.write(kml_content)

    # Crear KMZ, que no es mas que un zip con extensión cambiada... 
    with zipfile.ZipFile(f"{directorio_salida_kmz}{nombre}.kmz", 'w') as kmz:
        kmz.write(f"{directorio_salida_kmz}{nombre}.kml")

    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    remove(f"{directorio_salida_kmz}{nombre}.kml")