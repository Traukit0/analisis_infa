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
import os
from os import remove
import pandas as pd
from .utils import nombrar_archivo


from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsField, QgsCoordinateTransformContext, QgsVectorFileWriter, QgsFields
)
from qgis.PyQt.QtCore import QVariant

def estaciones_ox(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    """
    Función para extraer las estaciones de MO del archivo de datos
    Requiere como input un archivo de datos Excel con estándar exacto de datos.
    """
    file_path = archivo_excel
    df = pd.read_excel(file_path, sheet_name='Estaciones_Ox')

    # Snippet de código para salir de la función en el caso de que las hoja de transectas esté vacía
    if df.empty:
        mensaje = "\nNo hay estaciones de Ox en el archivo Excel. Si esto es un error revisar archivo"
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
    fields.append(QgsField("Hora", QVariant.Time, "", 254))
    fields.append(QgsField("Estacion", QVariant.String, "", 254))
    fields.append(QgsField("Tipo", QVariant.String, "", 254))
    fields.append(QgsField("X", QVariant.Int, "", 254))
    fields.append(QgsField("Y", QVariant.Int, "", 254))
    fields.append(QgsField("Huso", QVariant.Int, "",254))
    pr.addAttributes(fields)
    vlayer.updateFields()

    # Añadir puntos a la capa
    for index, row in df.iterrows():
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row['X'], row['Y'])))
        feature.setAttributes([str(row['Centro']),
                            str(row['Fecha']),
                            str(row['Hora']),
                            str(row['Estacion']),
                            str(row['Tipo']),
                            str(row['X']),
                            str(row['Y']),
                            str(row['Huso'])]),
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
                                              f"{directorio_salida_shp}{nombre_archivo} Estaciones Ox Ptos.shp",
                                              transform_context,
                                              options)

    ######################################################
    ##### ACA TERMINA LA LOGICA DE CAPAS GEOGRAFICAS #####
    ######################################################

    ##### ------------------------------------------ #####

    #############################################################
    ##### ACA EMPIEZA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################

    ################# NOTA IMPORTANTE #################
    ## SE DECIDIÓ PARA LOS ARCHIVOS EXTRAÍDOS DESDE  ##
    ## EXCEL IMPLEMENTAR LÓGICA SOLAMENTE BASADA EN  ##
    ## DICHO ARCHIVO, A FIN DE SIMPLIFICAR PROCESO.  ##
    ## NO SE UTILIZÓ COMO BASE PARA EL KMZ EL        ##
    ## ARCHIVO .SHP                                  ##
    ################# NOTA IMPORTANTE #################
    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="27">
            <Folder id="4">
                <Style id="0">
                    <IconStyle id="1">
                        <color>ffffffff</color>
                        <colorMode>normal</colorMode>
                        <scale>0.755906</scale>
                        <heading>0</heading>
                        <Icon id="2">
                            <href>{icono}</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ff0000ff</color>
                        <scale>0.7</scale>
                    </LabelStyle>
                    <LineStyle id="3">
                        <color>ff2a1edb</color>
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
        <description><![CDATA[
        <table>
        <tr style="background-color:#DDDDFF;"><td>Centro</td><td>{centro}</td></tr>
        <tr><td>Tipo</td><td>{tipo}</td></tr>
        <tr style="background-color:#DDDDFF;"><td>Fecha</td><td>{fecha}</td></tr>
        <tr><td>Hora_Ini</td><td>{Hora}</td></tr>
        <tr style="background-color:#DDDDFF;"><td>X</td><td>{X}</td></tr>
        <tr><td>Y</td><td>{Y}</td></tr>
        </table>
        ]]></description>
        <styleUrl>#0</styleUrl>
        <ExtendedData>
            <Data name="Centro">
                <value>{centro}</value>
                <displayName>Centro</displayName>
            </Data>
            <Data name="Tipo">
                <value>{tipo}</value>
                <displayName>Tipo</displayName>
            </Data>
            <Data name="Fecha">
                <value>{fecha}</value>
                <displayName>Fecha</displayName>
            </Data>
            <Data name="Hora">
                <value>{Hora}</value>
                <displayName>Hora</displayName>
            </Data>
            <Data name="X">
                <value>{X}</value>
                <displayName>X</displayName>
            </Data>
            <Data name="Y">
                <value>{Y}</value>
                <displayName>Y</displayName>
            </Data>
        </ExtendedData>
        <Point id="{multi_geometry_id}">
            <coordinates>{coordinates}</coordinates>
        </Point>
    </Placemark>
    '''
    file_path = archivo_excel
    df = pd.read_excel(file_path, sheet_name='Estaciones_Ox')

    # Configurar la transformación de coordenadas con Transformer
    transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)

    placemarks = ''
    placemark_id = 1
    multi_geometry_id = 1

    ## Main loop para ir escribiendo los datos
    for centro in df['Centro'].unique():
        centro_df = df[df['Centro'] == centro]
        for estacion in centro_df['Estacion'].unique():
            estacion_df = centro_df[centro_df['Estacion'] == estacion]
            coordinates = ' '.join([
                f"{transformer.transform(row['X'], row['Y'])[0]},{transformer.transform(row['X'], row['Y'])[1]},0.0"
                for idx, row in estacion_df.iterrows()
            ])
            placemarks += placemark_template.format(
                placemark_id=placemark_id,
                centro=centro,
                tipo=estacion_df.iloc[0]['Tipo'],
                name=estacion_df.iloc[0]['Estacion'],
                Hora=estacion_df.iloc[0]['Hora'],
                X=estacion_df.iloc[0]['X'],
                Y=estacion_df.iloc[0]['Y'],
                fecha=estacion_df.iloc[0]['Fecha'],
                multi_geometry_id=multi_geometry_id,
                coordinates=coordinates,
            )
            placemark_id += 1
            multi_geometry_id += 1

    #Esto es para darle el camino correcto al ícono en el entorno del plugin
    plugin_dir = os.path.dirname(__file__)

    path_icono = os.path.join(plugin_dir, 'files', 'icono_ox.png') # Refactorizado para plugin
    nombre = nombrar_archivo(archivo_excel)
    nombre_archivo = f"{nombre} Estaciones Ox Ptos"
    kml_content = kml_base.format(nombre=nombre_archivo, placemarks=placemarks, icono=path_icono)

    #############################################################
    ##### ACA TERMINA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################

    #Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

    # Guardar el contenido KML en un archivo
    with open(f"{directorio_salida_kmz}{nombre_archivo}.kml", 'w') as file:
        file.write(kml_content)

    # Crear KMZ, que no es mas que un zip con extensión cambiada... 
    with zipfile.ZipFile(f"{directorio_salida_kmz}{nombre_archivo}.kmz", 'w') as kmz:
        kmz.write(f"{directorio_salida_kmz}{nombre_archivo}.kml")
        kmz.write(path_icono, arcname=path_icono)

    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    remove(f"{directorio_salida_kmz}{nombre_archivo}.kml")
