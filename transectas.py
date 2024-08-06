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
import pandas as pd
import zipfile
from os import remove
from .utils import nombrar_archivo

from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsField, QgsCoordinateTransformContext, QgsVectorFileWriter, QgsFields
)
from qgis.PyQt.QtCore import QVariant

def transectas(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    """
    Función para extraer los transectas (puntos y líneas) del archivo de datos
    Requiere como input un archivo de datos Excel con estándar exacto de datos.
    Inputs:
    - Archivo Excel cargado con datos estandarizados
    - Directorio de salida donde se guardarán los archivos
    """ 
    # Leer el archivo Excel
    file_path = archivo_excel
    df = pd.read_excel(file_path, sheet_name='Transectas')

    # Snippet de código para salir de la función en el caso de que las hoja de transectas esté vacía
    if df.empty:
        mensaje = "\nNo hay transectas en el archivo Excel. Si esto es un error revisar archivo"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    ######################################################
    ##### ACA EMPIEZA LA LOGICA DE CAPAS GEOGRAFICAS #####
    ######################################################

    # Crear una capa de puntos en QGIS con la misma estructura de atributos que la tabla Excel
    vlayer = QgsVectorLayer("Point?crs=epsg:32718", "Puntos", "memory")
    pr = vlayer.dataProvider()
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int, "", 50))
    fields.append(QgsField("Fecha", QVariant.Date, "", 50))
    fields.append(QgsField("Hora", QVariant.Time, "", 50))
    fields.append(QgsField("Transecta", QVariant.Int, "", 50))
    fields.append(QgsField("Extremo", QVariant.String, "", 50))
    fields.append(QgsField("X", QVariant.Int, "", 50))
    fields.append(QgsField("Y", QVariant.Int, "", 50))
    fields.append(QgsField("Huso", QVariant.Int, "",50))
    pr.addAttributes(fields)
    vlayer.updateFields()

    # Añadir puntos a la capa a través de un iterador
    for index, row in df.iterrows():
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row['X'], row['Y'])))
        feature.setAttributes([
                            str(row['Centro']),
                            str(row['Fecha']),
                            str(row['Hora']),
                            str(row['Transecta']),
                            str(row['Extremo']),
                            str(row['X']),
                            str(row['Y']),
                            str(row['Huso'])
                            ])
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
                                              f"{directorio_salida_shp}{nombre_archivo} Transectas Ptos.shp",
                                              transform_context,
                                              options)

    # Crear una capa de líneas en QGIS
    llayer = QgsVectorLayer("LineString?crs=epsg:32718", "Líneas", "memory")
    pr = llayer.dataProvider()
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int, "", 254))
    fields.append(QgsField("Transecta", QVariant.Int, "", 254))
    fields.append(QgsField("Fecha", QVariant.Date, "", 254))
    pr.addAttributes(fields)
    llayer.updateFields()

    # Crear una línea para cada transecta conectando los extremos
    for centro in df['Centro'].unique():
        centro_df = df[df['Centro'] == centro]
        for transecta in centro_df['Transecta'].unique():
            transecta_df = centro_df[centro_df['Transecta'] == transecta].sort_values(by='Extremo')
            line = QgsFeature()
            line.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(row['X'], row['Y']) for idx, row in transecta_df.iterrows()]))
            line.setAttributes([str(centro), str(transecta), str(transecta_df.iloc[0]['Fecha'])])
            pr.addFeature(line)
    llayer.updateExtents()

    # Guardar la capa de líneas en un archivo .shp
    options.driverName = "ESRI Shapefile"
    QgsVectorFileWriter.writeAsVectorFormatV3(llayer,
                                              f"{directorio_salida_shp}{nombre_archivo} Transectas Linea.shp",
                                              transform_context,
                                              options)

    ######################################################
    ##### ACA TERMINA LA LOGICA DE CAPAS GEOGRAFICAS #####
    ######################################################

    ##### ------------------------------------------ #####

    #############################################################
    ##### ACA EMPIEZA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################

    # Crear el KML con los datos extraídos
    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="1">
            <Folder id="3">
                <Style id="0">
                    <LineStyle id="1">
                        <color>ff00aa55</color>
                        <colorMode>normal</colorMode>
                        <width>2</width>
                        <gx:labelVisibility>True</gx:labelVisibility>
                    </LineStyle>
                    <PolyStyle id="2">
                        <color>ff00aa55</color>
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
        <tr><td>Transecta</td><td>{transecta}</td></tr>
        <tr style="background-color:#DDDDFF;"><td>Fecha</td><td>{fecha}</td></tr>
        </table>
        ]]></description>
        <styleUrl>#0</styleUrl>
        <ExtendedData>
            <Data name="Centro">
                <value>{centro}</value>
                <displayName>Centro</displayName>
            </Data>
            <Data name="Transecta">
                <value>{transecta}</value>
                <displayName>Transecta</displayName>
            </Data>
            <Data name="Fecha">
                <value>{fecha}</value>
                <displayName>Fecha</displayName>
            </Data>
        </ExtendedData>
        <MultiGeometry id="{multi_geometry_id}">
            <LineString id="{line_string_id}">
                <coordinates>{coordinates}</coordinates>
            </LineString>
        </MultiGeometry>
    </Placemark>
    '''

    # Configurar la transformación de coordenadas con Transformer
    transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)

    placemarks = ''
    placemark_id = 1
    multi_geometry_id = 1
    line_string_id = 1

    for centro in df['Centro'].unique():
        centro_df = df[df['Centro'] == centro]
        for transecta in centro_df['Transecta'].unique():
            transecta_df = centro_df[centro_df['Transecta'] == transecta].sort_values(by='Extremo')
            coordinates = ' '.join([
                f"{transformer.transform(row['X'], row['Y'])[0]},{transformer.transform(row['X'], row['Y'])[1]},0.0"
                for idx, row in transecta_df.iterrows()
            ])
            placemarks += placemark_template.format(
                placemark_id=placemark_id,
                name=transecta,
                centro=centro,
                transecta=transecta,
                fecha=transecta_df.iloc[0]['Fecha'],
                multi_geometry_id=multi_geometry_id,
                line_string_id=line_string_id,
                coordinates=coordinates
            )
            placemark_id += 1
            multi_geometry_id += 1
            line_string_id += 1

    nombre_kml = f"{nombre_archivo} Transectas Linea"
    kml_content = kml_base.format(nombre=nombre_kml, placemarks=placemarks)

    #############################################################
    ##### ACA TERMINA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################

    #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

    # Guardar el contenido KML en un archivo
    with open(f"{directorio_salida_kmz}{nombre_kml}.kml", 'w') as file:
        file.write(kml_content)

    # Crear KMZ, que no es mas que un zip con extensión cambiada... 
    with zipfile.ZipFile(f"{directorio_salida_kmz}{nombre_kml}.kmz", 'w') as kmz:
        kmz.write(f"{directorio_salida_kmz}{nombre_kml}.kml")

    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    remove(f"{directorio_salida_kmz}{nombre_kml}.kml")