#########################################################################################
#                CODIGO PARA CREACIÓN DE KMZ A PARTIR DE BATIMETRÍA                      #
#                 GENERACIÓN DE ARCHIVO KMZ CON DATOS RESPECTIVOS                        #
#                PROGRAMADO POR MANUEL E. CANO NESBET - 05-06-2024                      #
#########################################################################################

from pathlib import Path
import zipfile
import os
import shutil
import re
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
    QgsMapSettings
)

def cargar_capa_batimetria(batimetria_shp, plugin_instance):
    """Carga y estiliza la capa de batimetría"""
    # Cargar capa original
    original_layer = QgsVectorLayer(batimetria_shp, "Batimetria", "ogr")
    if not original_layer.isValid():
        plugin_instance.mensajes_texto_plugin("No pudo cargarse la capa 'Batimetria' en QGIS")
        return None

    # Configurar proyecto y CRS
    project = QgsProject.instance()
    target_crs = QgsCoordinateReferenceSystem("EPSG:32718")
    project.setCrs(target_crs)
    
    # Si la capa original no está en EPSG:32718, configurar transformación
    if original_layer.crs().authid() != "EPSG:32718":
        # Crear transformación de coordenadas
        transform = QgsCoordinateTransform(
            original_layer.crs(),
            target_crs,
            project
        )
        # Aplicar transformación al proyecto
        project.transformContext().addCoordinateOperation(
            original_layer.crs(),
            target_crs, 
            transform.coordinateOperation()
        )
        
    # Aplicar estilo QML
    plugin_dir = Path(__file__).parent
    qml_path = plugin_dir / 'estilos_qml' / 'Estilo Batimetria.qml'
    
    if qml_path.exists():
        original_layer.loadNamedStyle(str(qml_path))
        original_layer.triggerRepaint()
    
    # Agregar capa al proyecto
    project.addMapLayer(original_layer)
    
    return original_layer

def generar_line_strings(coords, transform):
    """Genera los LineStrings para un conjunto de coordenadas"""
    line_string_template = '''
    <LineString id="{line_string_id}">
        <coordinates>{coordinates}</coordinates>
    </LineString>
    '''
    
    line_strings = []
    for idx, line in enumerate(coords, 1):
        coordinates = []
        for point in line:
            # Crear QgsPointXY para la transformación
            punto = QgsPointXY(point.x(), point.y())
            # Transformar el punto
            punto_transformado = transform.transform(punto)
            # Formatear como lon,lat,0 para KML
            coordinates.append(f"{punto_transformado.x()},{punto_transformado.y()},0")
        
        line_strings.append(
            line_string_template.format(
                line_string_id=idx,
                coordinates=' '.join(coordinates)
            )
        )
    
    return ''.join(line_strings)

def detect_schema(layer):
    """Detecta qué esquema de campos tiene la capa"""
    fields = [field.name() for field in layer.fields()]
    
    if all(field in fields for field in ['Fuente', 'Z', 'Centro']):
        return {
            'centro': 'Centro',
            'z': 'Z',
            'fuente': 'Fuente'
        }
    elif all(field in fields for field in ['cd_centro', 'z', 'fuente']):
        return {
            'centro': 'cd_centro',
            'z': 'z',
            'fuente': 'fuente'
        }
    return None

def crear_placemark(feat, coords, transformer, placemark_id, schema):
    """Crea un Placemark individual"""
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
        <MultiGeometry id="geom_{placemark_id}">
            {line_strings}
        </MultiGeometry>
    </Placemark>
    '''
    
    return placemark_template.format(
        placemark_id=placemark_id,
        name=feat[schema['z']],
        centro=feat[schema['centro']],
        fuente=feat[schema['fuente']],
        line_strings=generar_line_strings(coords, transformer)
    )

def batimetria_kmz(batimetria_shp, directorio_salida_kmz, plugin_instance):
    """Procesa archivo de batimetría y genera KMZ"""
    # Verificar y cargar capa
    capa = QgsVectorLayer(batimetria_shp, "capa_shp", "ogr")
    if not capa.isValid():
        plugin_instance.mensajes_texto_plugin(f"Error al cargar la capa {batimetria_shp}")
        return

    # Cargar capa en QGIS con el CRS correcto
    layer = cargar_capa_batimetria(batimetria_shp, plugin_instance)
    if not layer:
        return

    # Detectar esquema de campos
    schema = detect_schema(layer)
    if not schema:
        plugin_instance.mensajes_texto_plugin("Error: Formato de campos no reconocido en el archivo de batimetría")
        return

    # Configurar transformación de coordenadas para KMZ (32718 -> 4326)
    source_crs = QgsCoordinateReferenceSystem("EPSG:32718")
    dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())

    # Agrupar entidades por valor de 'Fuente'
    grupos_por_fuente = {}
    for feat in layer.getFeatures():
        valor_fuente = feat[schema['fuente']]
        clave = str(valor_fuente) if valor_fuente is not None else "SIN_FUENTE"
        grupos_por_fuente.setdefault(clave, []).append(feat)

    # Asegurar directorio de salida
    directorio_salida = Path(directorio_salida_kmz)
    try:
        directorio_salida.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Exportar un KMZ por cada grupo de 'Fuente'
    for fuente_valor, features in grupos_por_fuente.items():
        placemarks = []
        for idx, feat in enumerate(features, 1):
            coords = feat.geometry().asMultiPolyline()
            placemark = crear_placemark(feat, coords, transform, idx, schema)
            placemarks.append(placemark)

        kml_content = get_kml_base().format(
            nombre=f"Batimetria {fuente_valor}",
            placemarks='\n'.join(placemarks)
        )

        # Determinar nombre de archivo con año si está presente
        match = re.search(r'(19|20)\d{2}', str(fuente_valor))
        if match:
            anio = match.group(0)
            nombre_archivo = f"Batimetria_{anio}.kmz"
        else:
            seguro = ''.join(c if c.isalnum() else '_' for c in str(fuente_valor)).strip('_')
            nombre_archivo = f"Batimetria_{seguro}.kmz"

        kmz_path = directorio_salida / nombre_archivo

        try:
            with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
                kmz.writestr("doc.kml", kml_content)
            plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_archivo} creado")
        except Exception as e:
            plugin_instance.mensajes_texto_plugin(f"Error creando KMZ '{nombre_archivo}': {str(e)}")

def get_kml_base():
    """Retorna la plantilla base del KML"""
    return '''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document id="1">
            <Folder id="3">
                <Style id="0">
                    <LineStyle id="1">
                        <color>7fffff00</color>
                        <colorMode>normal</colorMode>
                        <width>0.52</width>
                        <gx:labelVisibility>True</gx:labelVisibility>
                    </LineStyle>
                    <PolyStyle id="2">
                        <color>7fffff00</color>
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