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

def extraer_track_points(gpx_path, archivo_excel, directorio_salida_shp, directorio_salida_kmz, valor_utc, plugin_instance):
    """
    Función para extraer PUNTOS DE TRACK desde un archivo GPX.
    Inputs:
    - Archivo GPX enviado por consultora
    - Archivo Excel cargado con datos estandarizados para el nombre del archivo final
    - Directorios de salida donde se guardarán los archivos
    - Valor UTC -3 o -4
    - Toma como input adicional el centroide generado desde el archivo de CCAA
    """
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
    campos_adicionales = [
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

    hay_puntos_track = False # bandera para asegurar que la capa no esté vacía

    # Crear la lista de características transformadas
    features = []
    id_punto = 0
    for feat in capa_gpx.getFeatures():
        hay_puntos_track = True
        geom = feat.geometry()
        geom.transform(transform)

        # Obtener el punto actual
        punto_actual = geom.asPoint()
        # Calcular la distancia entre ambos puntos, ahora se ocupa el cálculo del punto de referencia
        distancia_entre_puntos = obtener_distancia(punto_referencia, punto_actual, crs_dest)
        # Ahora filtrar todos los puntos que estén a mas de cierta cantidad de metros. Valor hardcodeado!!
        buffer = 1500 # Este valor es aleatorio, cambiar para agrandar o achicar el buffer que discrimina
        if distancia_entre_puntos < buffer and distancia_entre_puntos != 0: # Esto es importante, la distancia calculada debe ser MENOR al buffer circular!!

            # Asegurarse de que estamos accediendo a los puntos de track
            utc_time = feat.attribute('time')
            elev = feat.attribute('ele')
            # Condicional en el caso que existan puntos de track sin atributo tiempo
            # O para cuando los waypoints pre cargados se asocien a el archivo de track puntos
            if utc_time == None or utc_time == 'Null':
                continue

            # Convertir QDateTime a string
            utc_time_str = utc_time.toString('yyyy-MM-dd HH:mm:ss')  # Formato correcto del tiempo en el archivo GPX
            utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
            local_dt = utc_dt - timedelta(hours=valor_utc)  # Acá se debe modificar a futuro para elegir entre -3 o -4
            local_time = local_dt.strftime('%Y/%m/%d %H:%M:%S')
            dia = local_dt.strftime('%Y/%m/%d')
            hora = local_dt.strftime('%H:%M:%S')
            name = local_dt.strftime('%H:%M')
            
            # Construir otros atributos
            id_track = 0 # Por ahora valor placeholder, a futuro puede tener funcionalidad para mas de 1 track
            id_segm = 0 # Por ahora valor placeholder, a futuro puede tener funcionalidad para mas de 1 track
            ajuste = valor_utc
            descrip = f"{local_time} (UTC-{valor_utc})"
            rollover = 0 # Placeholder
            TimeStamp = local_dt.strftime('%d/%m/%Y %H:%M:%S')
            mostrar = "Si"
            Valido = "Si"

            # Este bloque es para mostra solamente aquellos puntos del GPX que estén tomados el mismo día del muestreo
            dia_punto_gpx = local_dt.day
            dia_muestreo = obtener_dia_muestreo(archivo_excel)
            if dia_punto_gpx == dia_muestreo:
                # Crear la nueva característica con los campos adicionales
                new_feat = QgsFeature()
                new_feat.setGeometry(geom)
                new_feat.setAttributes([
                    id_track,
                    id_segm,
                    id_punto,
                    elev,
                    utc_time_str,
                    ajuste, 
                    rollover, # A futuro implementar lógica para con o sin rollover
                    local_time,
                    dia,
                    hora,
                    name,
                    descrip,
                    TimeStamp, # Es lo mismo que local_time pero el orden de la fecha es al revés
                    mostrar,
                    Valido,
                ])
                features.append(new_feat)
                id_punto += 1

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


    ######################################################
    ##### ACA TERMINA LA LOGICA DE CAPAS GEOGRAFICAS #####
    ######################################################

    ##### ------------------------------------------ #####

    #############################################################
    ##### ACA EMPIEZA LA LOGICA DE CREAR KML CON SCHEMA XML #####
    #############################################################

    kml_base = '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="27">
            <Folder id="4">
                <Style id="0">
                    <IconStyle id="1">
                        <color>7effffff</color>
                        <colorMode>normal</colorMode>
                        <scale>0.2519685039370079</scale>
                        <heading>0</heading>
                        <Icon id="2">
                            <href>{icono}</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ffffffff</color>
                        <scale>0.7</scale>
                    </LabelStyle>
                    <LineStyle id="3">
                        <color>ffb4781f</color>
                        <colorMode>normal</colorMode>
                    </LineStyle>
                </Style>
                <name>{name}</name>
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
                <when>{timestamp}</when>
            </TimeStamp>
            <styleUrl>#0</styleUrl>
            <Point id="{multi_geometry_id}">
                <coordinates>{coordinates}</coordinates>
            </Point>
        </Placemark>
    '''
    # Leer la capa shapefile
    capa_shp = QgsVectorLayer(nombre_archivo_shp, "capa_shp", "ogr")
    if not capa_shp.isValid():
        mensaje = f"\npuntos_track_gpx.extraer_track_points: Error al cargar la capa {nombre_archivo_shp}"
        plugin_instance.mensajes_texto_plugin(mensaje)
        return

    transform = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)

    # Esto es para darle el camino correcto al ícono en el entorno del plugin
    plugin_dir = os.path.dirname(__file__)

    # Icono para los puntos de track
    icono_track_ptos = os.path.normpath(os.path.join(plugin_dir, 'files', 'icono_pto_track_utc.png'))

    placemarks = ''
    placemark_id = 1
    nombre_kmz = f"{nombrar_archivo(archivo_excel)} Track Ptos"
    for feat in capa_shp.getFeatures():
        geom = feat.geometry()
        coords = geom.asPoint()
        lon, lat = transform.transform(coords.x(), coords.y())
        coordinates = f"{lon},{lat},0"
        name = feat['Name']
        id_descrip = f"[ID {feat['ID_track']}-{feat['ID_Segm']}-{feat['ID_Punto']}]"
        fecha_separada = feat['Dia'].split('/')
        # No hay forma de evitar este punto para pasar los meses a español...
        descrip_separado = feat['Descrip'].split(' ')
        utc_segun_shp = descrip_separado[2]
        meses = {'01': 'ene', '02': 'feb', '03': 'mar', '04': 'abr', '05': 'may', '06': 'jun',
                 '07': 'jul', '08': 'ago', '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dic'}
        descrip = f"{fecha_separada[2]} {meses[fecha_separada[1]]}. {fecha_separada[0]} {feat['Hora']} {utc_segun_shp} {id_descrip}"
        timestamp = f"{fecha_separada[0]}-{fecha_separada[1]}-{fecha_separada[2]}T{feat['Hora']}Z"
        
        placemark = placemark_template.format(
            placemark_id=placemark_id,
            name=name,
            descrip=descrip,
            timestamp=timestamp,
            multi_geometry_id=placemark_id,
            coordinates=coordinates
        )
        placemarks += placemark
        placemark_id += 1

        kml_content = kml_base.format(
            name=nombre_kmz,
            placemarks=placemarks,
            icono=icono_track_ptos
        )

    # Esto es para asegurar que siempre se guarde bien el directorio de salida
    if not directorio_salida_kmz.endswith('/') and not directorio_salida_kmz.endswith('\\'):
        directorio_salida_kmz += '/'

    # Guardar el contenido KML en un archivo
    kml_filename = os.path.normpath(f"{directorio_salida_kmz}{nombre_kmz}.kml")
    with open(kml_filename, 'w') as file:
        try:
            file.write(kml_content)
        except UnboundLocalError:
            mensaje = f"""\nNo hay puntos de track para crear el KMZ. Esto puede deberse a:
            - El archivo .gpx tiene errores
            - No se obtuvieron puntos de track en terreno
            - La fecha de la inspección en terreno es diferente a la de toma de datos
            Revisar posibles errores y volver a correr el plugin"""
            plugin_instance.mensajes_texto_plugin(mensaje)
            return

    # Crear KMZ, que no es más que un zip con extensión cambiada
    kmz_filename = os.path.normpath(f"{directorio_salida_kmz}{nombre_kmz}.kmz")
    with zipfile.ZipFile(kmz_filename, 'w') as kmz:
        kmz.write(kml_filename, arcname=os.path.basename(kml_filename))
        kmz.write(icono_track_ptos, arcname=os.path.basename(icono_track_ptos))

    # Borrar archivo .kml ya que es innecesario, solo sirve el KMZ
    os.remove(kml_filename)

    return nombre_archivo_shp