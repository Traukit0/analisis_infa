#########################################################################################
#            CODIGO PARA CREACIÓN DE KMZ A PARTIR DE CAPA SHP CONCESIONES               #
#                 GENERACIÓN DE ARCHIVO KMZ CON DATOS RESPECTIVOS                       #
#          DATOS DE CAPA CONCESIONES EXTRAÍDA DESDE VISOR MAPAS SUBPESCA                #
#                       https://mapas.subpesca.cl/ideviewer                             #
#   SE DEBE ACTUALIZAR CAPA CON CADA ACTUALIZACION DEL PLUGIN - FECHA ARCHIVO 22-08-24  #
#                PROGRAMADO POR MANUEL E. CANO NESBET - 05-06-2024                      #
#########################################################################################

from pathlib import Path
import zipfile
from pyproj import Transformer
from .utils import nombrar_archivo

from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
)
from qgis.PyQt.QtCore import QVariant

def cargar_capa_ccaa(ccaa_shp, plugin_instance):
    """Carga y estiliza la capa de concesión"""
    layer = QgsVectorLayer(ccaa_shp, "CCAA", "ogr")
    if not layer.isValid():
        plugin_instance.mensajes_texto_plugin("No pudo cargarse la capa 'CCAA' en QGIS")
        return None

    # Aplicar estilo QML
    plugin_dir = Path(__file__).parent
    qml_path = plugin_dir / 'estilos_qml' / 'Estilo CCAA Subpesca.qml'
    
    if qml_path.exists():
        layer.loadNamedStyle(str(qml_path))
        layer.triggerRepaint()
    
    QgsProject.instance().addMapLayer(layer)
    return layer

def crear_capa_ccaa(feature_original, plugin_instance):
    """Crea una nueva capa con los atributos seleccionados"""
    fields = QgsFields()
    campos_ccaa = [
        QgsField("Cd_Centro", QVariant.String, len=254),
        QgsField("Titular", QVariant.String, len=254),
        QgsField("Grupo", QVariant.String, len=254),
        QgsField("Estado", QVariant.String, len=254),
    ]
    
    for field in campos_ccaa:
        fields.append(field)
    
    nuevo_layer = QgsVectorLayer("Polygon?crs=epsg:32718", "Polygons", "memory")
    provider = nuevo_layer.dataProvider()
    provider.addAttributes(fields)
    nuevo_layer.updateFields()
    
    # Crear feature
    feature = QgsFeature()
    feature.setGeometry(feature_original.geometry())
    feature.setAttributes([
        feature_original["N_CODIGOCE"],
        feature_original["TITULAR"],
        feature_original["T_GRUPOESP"].title(),
        feature_original["T_ESTADOTR"].title(),
    ])
    
    provider.addFeature(feature)
    nuevo_layer.updateExtents()
    
    return nuevo_layer

def extraer_ccaa_shp(archivo_excel, directorio_salida_shp, plugin_instance):
    """Extrae la geometría de la concesión desde archivo de concesiones Subpesca"""
    plugin_dir = Path(__file__).parent
    ccaa_path = plugin_dir / 'ccaa_shp' / 'Concesiones_de_Acuicultura.shp'
    
    capa_concesiones = QgsVectorLayer(str(ccaa_path), "CCAA", "ogr")
    if not capa_concesiones.isValid():
        plugin_instance.mensajes_texto_plugin("No pudo cargarse la capa 'CCAA' para extracción")
        return None
    
    nombre_codigo_centro = nombrar_archivo(archivo_excel)
    codigo_centro = nombre_codigo_centro.split(" ")[0]
    
    for feat in capa_concesiones.getFeatures():
        if feat["N_CODIGOCE"] == int(codigo_centro):
            nuevo_layer = crear_capa_ccaa(feat, plugin_instance)
            
            # Guardar shapefile
            directorio_salida = Path(directorio_salida_shp)
            shp_path = directorio_salida / "CCAA.shp"
            
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            
            resultado = QgsVectorFileWriter.writeAsVectorFormatV3(
                nuevo_layer,
                str(shp_path),
                QgsCoordinateTransformContext(),
                options
            )
            
            if resultado[0] != QgsVectorFileWriter.NoError:
                plugin_instance.mensajes_texto_plugin(f"Error guardando SHP: {resultado[1]}")
                return None
            
            # Cargar capa en QGIS
            return cargar_capa_ccaa(str(shp_path), plugin_instance)
    
    plugin_instance.mensajes_texto_plugin(f"No se encontró concesión con código {codigo_centro}")
    return None

def generar_kmz(capa_shp, directorio_salida, plugin_instance):
    """Genera el archivo KMZ con la estructura correcta"""
    transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
    
    placemarks = []
    for idx, feat in enumerate(capa_shp.getFeatures()):
        geom = feat.geometry()
        coords = geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]
        
        coordinates = []
        for polygon in coords:
            for ring in polygon:
                coord_str = ' '.join(
                    f"{lon},{lat},0"
                    for lon, lat in (transformer.transform(point.x(), point.y()) for point in ring)
                )
                coordinates.append(coord_str)
        
        placemark = crear_placemark(
            feat['Cd_Centro'],
            coordinates[0],
            idx
        )
        placemarks.append(placemark)
    
    # Crear archivo KMZ
    kmz_path = Path(directorio_salida) / "CCAA.kmz"
    try:
        with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
            kmz.writestr("doc.kml", get_kml_content(placemarks))
        plugin_instance.mensajes_texto_plugin("\nArchivo CCAA.kmz creado")
        return kmz_path
    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"Error creando KMZ: {str(e)}")
        return None

def crear_placemark(codigo_centro, coordinates, idx):
    """Crea un Placemark individual"""
    return f'''
    <Placemark id="placemark_{idx}">
        <name>{codigo_centro}</name>
        <styleUrl>#m_ylw-pushpin</styleUrl>
        <MultiGeometry id="geom_{idx}">
            <Polygon id="poly_{idx}">
                <outerBoundaryIs>
                    <LinearRing>
                        <coordinates>
                        {coordinates}
                        </coordinates>
                    </LinearRing>
                </outerBoundaryIs>
            </Polygon>
        </MultiGeometry>
    </Placemark>
    '''

def get_kml_content(placemarks):
    """Retorna el contenido KML completo"""
    return f'''
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
        <Document>
            <name>CCAA</name>
            {get_styles()}
            <Folder id="0">
                <name>CCAA</name>
                {''.join(placemarks)}
            </Folder>
        </Document>
    </kml>
    '''

def get_styles():
    """Retorna los estilos KML"""
    return '''
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
    '''

def ccaa_a_kmz(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    """Función principal para procesar CCAA"""
    # Extraer y cargar shapefile
    capa_ccaa = extraer_ccaa_shp(archivo_excel, directorio_salida_shp, plugin_instance)
    if not capa_ccaa:
        return
    
    # Generar KMZ
    kmz_path = generar_kmz(capa_ccaa, directorio_salida_kmz, plugin_instance)
    if not kmz_path:
        plugin_instance.mensajes_texto_plugin("Error al generar archivo KMZ de CCAA")
        return
    
    plugin_instance.mensajes_texto_plugin("Procesamiento de CCAA completado exitosamente")