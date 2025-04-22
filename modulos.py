#########################################################################################
#                    CODIGO PARA ESTACIONES DE MUESTREO MO                              #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                 PROGRAMADO POR MANUEL E. CANO NESBET - 2024                           #
# ToDo:                                                                                 #
# - Manejo de errores y excepciones                                                     #
# - Mensajes de consola que se pasen a plugin para visualización                        #
#########################################################################################

from pathlib import Path
import zipfile
import pandas as pd
from pyproj import Transformer
from .utils import nombrar_archivo

from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsField, QgsCoordinateTransformContext, QgsVectorFileWriter, QgsFields, QgsProject,
)
from qgis.PyQt.QtCore import QVariant

def procesar_datos_desde_excel(archivo_excel):
    """Procesa los datos del archivo Excel y retorna un DataFrame"""
    try:
        df = pd.read_excel(archivo_excel, sheet_name='Modulos')
        if df.empty:
            return None, "\nNo hay datos de módulos en el archivo Excel"
        
        # Asegurar formato de fecha
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'])
        
        return df, None
    except Exception as e:
        return None, f"Error procesando archivo Excel: {str(e)}"

def crear_capa_puntos(df, epsg, nombre_capa):
    """Crea una capa de puntos en memoria con los datos del DataFrame"""
    vlayer = QgsVectorLayer(f"Point?crs=epsg:{epsg}", nombre_capa, "memory")
    pr = vlayer.dataProvider()
    
    # Definir campos
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int))
    fields.append(QgsField("Fecha", QVariant.Date))
    fields.append(QgsField("Modulo", QVariant.Int))
    fields.append(QgsField("Vertice", QVariant.Int))
    fields.append(QgsField("X", QVariant.Int))
    fields.append(QgsField("Y", QVariant.Int))
    fields.append(QgsField("Huso", QVariant.Int))
    
    pr.addAttributes(fields)
    vlayer.updateFields()
    
    # Añadir features
    features = []
    for _, row in df.iterrows():
        try:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(
                int(row['X']),
                int(row['Y'])
            )))
            
            attrs = [
                int(row['Centro']),
                str(pd.to_datetime(row['Fecha']).date()),
                int(row['Modulo']),
                int(row['Vertice']),
                int(row['X']),
                int(row['Y']),
                int(row['Huso'])
            ]
            feat.setAttributes(attrs)
            features.append(feat)
        except Exception as e:
            print(f"Error procesando punto: {str(e)}")
            continue
    
    if features:
        pr.addFeatures(features)
        vlayer.updateExtents()
    
    return vlayer

def crear_capa_poligonos(df, epsg, nombre_capa):
    """Crea una capa de polígonos en memoria"""
    pllayer = QgsVectorLayer(f"Polygon?crs=epsg:{epsg}", nombre_capa, "memory")
    pr = pllayer.dataProvider()
    
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int))
    fields.append(QgsField("Modulo", QVariant.Int))
    fields.append(QgsField("Fecha", QVariant.Date))
    
    pr.addAttributes(fields)
    pllayer.updateFields()
    
    polygons = []
    for centro in df['Centro'].unique():
        centro_df = df[df['Centro'] == centro]
        for modulo in centro_df['Modulo'].unique():
            try:
                modulo_df = centro_df[centro_df['Modulo'] == modulo].sort_values(by='Vertice')
                points = [QgsPointXY(int(row['X']), int(row['Y'])) 
                         for _, row in modulo_df.iterrows()]
                points.append(points[0])  # Cerrar el polígono
                
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPolygonXY([points]))
                feat.setAttributes([
                    int(centro),
                    int(modulo),
                    str(pd.to_datetime(modulo_df.iloc[0]['Fecha']).date())
                ])
                
                polygons.append({
                    'feature': feat,
                    'centro': str(centro),
                    'modulo': str(modulo),
                    'fecha': str(modulo_df.iloc[0]['Fecha'].strftime('%d/%m/%Y')),
                    'points': points
                })
            except Exception as e:
                print(f"Error procesando polígono: {str(e)}")
                continue
    
    if polygons:
        pr.addFeatures([p['feature'] for p in polygons])
        pllayer.updateExtents()
    
    return pllayer, polygons

def generar_kmz(polygons, directorio_salida, nombre_archivo):
    """Genera el archivo KMZ con la estructura correcta"""
    transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
    
    placemarks = []
    for idx, poly in enumerate(polygons):
        try:
            coords = []
            for point in poly['points']:
                lon, lat = transformer.transform(point.x(), point.y())
                coords.append(f"{lon},{lat},0")
            
            placemark = crear_placemark(
                idx,
                poly['modulo'],
                poly['centro'],
                poly['fecha'],
                " ".join(coords)
            )
            placemarks.append(placemark)
        except Exception as e:
            print(f"Error generando placemark: {str(e)}")
            continue
    
    kml_content = get_kml_base().format(
        nombre=f"{nombre_archivo} Modulos Area",
        placemarks="\n".join(placemarks)
    )
    
    # Crear archivo KMZ
    kmz_path = Path(directorio_salida) / f"{nombre_archivo} Modulos Area.kmz"
    try:
        with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
            kmz.writestr("doc.kml", kml_content)
    except Exception as e:
        print(f"Error creando KMZ: {str(e)}")
        return None
    
    return kmz_path

def crear_placemark(idx, modulo, centro, fecha, coordinates):
    """Crea un Placemark individual"""
    return f'''
    <Placemark id="placemark_{idx}">
        <name>{modulo}</name>
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
        <MultiGeometry id="geom_{idx}">
            <Polygon id="poly_{idx}">
                <outerBoundaryIs>
                    <LinearRing id="ring_{idx}">
                        <coordinates>{coordinates}</coordinates>
                    </LinearRing>
                </outerBoundaryIs>
            </Polygon>
        </MultiGeometry>
    </Placemark>
    '''

def get_kml_base():
    """Retorna la plantilla base del KML"""
    return '''
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

def modulos(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    """Función principal para procesar módulos"""
    # Procesamiento inicial
    df, error = procesar_datos_desde_excel(archivo_excel)
    if error:
        plugin_instance.mensajes_texto_plugin(error)
        return

    nombre_base = nombrar_archivo(archivo_excel)
    
    # Generar capa de puntos
    capa_puntos = crear_capa_puntos(df, 32718, f"{nombre_base} Modulos Ptos")
    shp_path = Path(directorio_salida_shp) / f"{nombre_base} Modulos Ptos.shp"
    guardar_y_cargar_capa(capa_puntos, shp_path, "Estilo INFA Modulo Ptos.qml", plugin_instance)
    
    # Generar capa de polígonos
    capa_poligonos, polygons = crear_capa_poligonos(df, 32718, f"{nombre_base} Modulos Area")
    shp_path = Path(directorio_salida_shp) / f"{nombre_base} Modulos Area.shp"
    guardar_y_cargar_capa(capa_poligonos, shp_path, "Estilo INFA Modulo Area.qml", plugin_instance)
    
    # Generar KMZ
    try:
        generar_kmz(polygons, directorio_salida_kmz, nombre_base)
        plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_base} Modulos Area.shp creado")
        plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_base} Modulos Area.kmz creado")
    except:
        plugin_instance.mensajes_texto_plugin("Error generando archivo KMZ")

def guardar_y_cargar_capa(capa, shp_path, estilo_qml, plugin_instance):
    """Guarda y carga una capa en QGIS con su estilo"""
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    
    resultado = QgsVectorFileWriter.writeAsVectorFormatV3(
        capa,
        str(shp_path),
        QgsCoordinateTransformContext(),
        options
    )
    
    if resultado[0] != QgsVectorFileWriter.NoError:
        plugin_instance.mensajes_texto_plugin(f"Error guardando SHP: {resultado[1]}")
        return
    
    # Cargar capa
    layer = QgsVectorLayer(str(shp_path), shp_path.stem, "ogr")
    if not layer.isValid():
        plugin_instance.mensajes_texto_plugin(f"Error cargando capa {shp_path.name}")
        return
    
    # Aplicar estilo
    plugin_dir = Path(__file__).parent
    qml_path = plugin_dir / 'estilos_qml' / estilo_qml
    if qml_path.exists():
        layer.loadNamedStyle(str(qml_path))
        layer.triggerRepaint()
    
    QgsProject.instance().addMapLayer(layer)