#########################################################################################
#                    CODIGO PARA ESTACIONES DE MUESTREO OX                              #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                 PROGRAMADO POR MANUEL E. CANO NESBET - 2024                           #
#########################################################################################

from pathlib import Path
import zipfile
import pandas as pd
from pyproj import Transformer
from datetime import datetime
from .utils import nombrar_archivo

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsCoordinateTransformContext,
    QgsVectorFileWriter,
    QgsFields,
    QgsProject,
)
from qgis.PyQt.QtCore import QVariant

def procesar_datos_desde_excel(archivo_excel):
    """Procesa los datos del archivo Excel y retorna un DataFrame"""
    try:
        df = pd.read_excel(archivo_excel, sheet_name='Estaciones_Ox')
        if df.empty:
            return None, "No hay estaciones de Ox en el archivo Excel."
        
        # Procesar formato de hora - método simplificado
        if 'Hora' in df.columns:
            # Convertir directamente el formato HH:MM que viene del Excel
            df['Hora'] = df['Hora'].apply(lambda x: x.strftime('%H:%M') if pd.notnull(x) else '')
        
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
    
    # Definir campos con tipos correctos
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int))
    fields.append(QgsField("Fecha", QVariant.Date))
    fields.append(QgsField("Hora", QVariant.String, len=5))  # HH:MM
    fields.append(QgsField("Estacion", QVariant.String, len=10))
    fields.append(QgsField("Tipo", QVariant.String, len=20))
    fields.append(QgsField("X", QVariant.Int))  # Coordenadas UTM sin decimales
    fields.append(QgsField("Y", QVariant.Int))  # Coordenadas UTM sin decimales
    fields.append(QgsField("Huso", QVariant.Int))
    
    pr.addAttributes(fields)
    vlayer.updateFields()
    
    # Añadir features
    features = []
    for _, row in df.iterrows():
        try:
            feat = QgsFeature()
            # Geometría
            x = int(row['X']) if pd.notnull(row['X']) else 0
            y = int(row['Y']) if pd.notnull(row['Y']) else 0
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            
            # Atributos con validación
            attrs = [
                int(row['Centro']) if pd.notnull(row['Centro']) else 0,
                str(pd.to_datetime(row['Fecha']).date()) if pd.notnull(row['Fecha']) else None,
                str(row['Hora'])[:5] if pd.notnull(row['Hora']) else '',
                str(row['Estacion']) if pd.notnull(row['Estacion']) else '',
                str(row['Tipo']) if pd.notnull(row['Tipo']) else '',
                x,
                y,
                int(row['Huso']) if pd.notnull(row['Huso']) else 0
            ]
            feat.setAttributes(attrs)
            features.append(feat)
        except Exception as e:
            print(f"Error al procesar fila: {e}")  # Debug info
            continue
    
    # Añadir features en bloque (más eficiente)
    if features:
        pr.addFeatures(features)
        vlayer.updateExtents()
    
    return vlayer

def generar_kmz(df, directorio_salida, nombre_archivo, plugin_dir):
    """Genera el archivo KMZ con la estructura correcta"""
    transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
    
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
                            <href>files/icono_ox.png</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ff0000ff</color>
                        <scale>0.7</scale>
                    </LabelStyle>
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
        <tr><td>Hora</td><td>{hora}</td></tr>
        <tr style="background-color:#DDDDFF;"><td>X</td><td>{x}</td></tr>
        <tr><td>Y</td><td>{y}</td></tr>
        <tr><td>Huso</td><td>{huso}</td></tr>
        </table>
        ]]></description>
        <styleUrl>#0</styleUrl>
        <Point id="{multi_geometry_id}">
            <coordinates>{coordinates}</coordinates>
        </Point>
    </Placemark>
    '''
    
    placemarks = []
    for idx, row in df.iterrows():
        try:
            lon, lat = transformer.transform(row['X'], row['Y'])
            
            placemark = placemark_template.format(
                placemark_id=f"placemark_{idx}",
                name=str(row['Estacion']),
                centro=row['Centro'],
                tipo=row['Tipo'],
                fecha=pd.to_datetime(row['Fecha']).strftime('%d/%m/%Y'),
                hora=row['Hora'],
                x=row['X'],
                y=row['Y'],
                huso=row['Huso'],
                multi_geometry_id=f"geom_{idx}",
                coordinates=f"{lon},{lat},0"
            )
            placemarks.append(placemark)
        except Exception as e:
            continue
    
    kml_content = kml_base.format(
        nombre=f"{nombre_archivo} Estaciones OX",
        placemarks="\n".join(placemarks)
    )
    
    # Crear archivo KMZ con estructura correcta
    kmz_path = Path(directorio_salida) / f"{nombre_archivo} Estaciones OX.kmz"
    try:
        with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
            kmz.writestr("doc.kml", kml_content)
            
            # Asegurar la estructura correcta del ícono
            icon_path = Path(plugin_dir) / 'files' / 'icono_ox.png'
            if icon_path.exists():
                kmz.writestr('files/', '')  # Crear directorio
                kmz.write(icon_path, 'files/icono_ox.png')
    except Exception as e:
        return None
    
    return kmz_path

def estaciones_ox(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    """Función principal para procesar estaciones OX"""
    # Procesamiento inicial
    df, error = procesar_datos_desde_excel(archivo_excel)
    if error:
        plugin_instance.mensajes_texto_plugin(error)
        return

    # Generación de Shapefile
    nombre_base = nombrar_archivo(archivo_excel)
    capa = crear_capa_puntos(df, 32718, f"{nombre_base} Estaciones OX")
    
    # Guardar SHP
    shp_path = Path(directorio_salida_shp) / f"{nombre_base} Estaciones OX Ptos.shp"
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.fileEncoding = 'UTF-8'
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

    # Cargar y estilizar capa
    capa_guardada = QgsVectorLayer(str(shp_path), f"{nombre_base} Estaciones OX Ptos", "ogr")
    if not capa_guardada.isValid():
        plugin_instance.mensajes_texto_plugin("Error cargando el SHP guardado")
        return

    # Aplicar estilo
    plugin_dir = Path(__file__).parent
    qml_path = plugin_dir / 'estilos_qml' / 'Estilo INFA Estaciones Ox.qml'
    if qml_path.exists():
        capa_guardada.loadNamedStyle(str(qml_path))
        capa_guardada.triggerRepaint()
    
    QgsProject.instance().addMapLayer(capa_guardada)

    # Generar KMZ
    kmz_path = generar_kmz(df, directorio_salida_kmz, nombre_base, plugin_dir)
    if not kmz_path:
        plugin_instance.mensajes_texto_plugin(f"Error generando archivo {nombre_base} Estaciones OX Ptos.kmz")

    plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_base} Estaciones OX Ptos.shp creado")
    plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_base} Estaciones OX Ptos.kmz creado")