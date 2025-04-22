#########################################################################################
#                    CODIGO PARA ESTACIONES DE MUESTREO MO                              #
#       GENERACIÓN DE ARCHIVO .SHP SON SU RESPECTIVA TABLA DE ATRIBUTOS                 #
#  GENERACIÓN ADICIONAL DE ARCHIVO KMZ LLEVADO A ESTÁNDAR REQUERIDO PARA GOOGLE EARTH   #
#                 PROGRAMADO POR MANUEL E. CANO NESBET - 2024 (MEJORADO)                #
#########################################################################################

from pyproj import Transformer
import pandas as pd
import zipfile
from pathlib import Path
from datetime import datetime
import os

from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsField, QgsCoordinateTransformContext, QgsVectorFileWriter, 
    QgsFields, QgsProject, QgsCoordinateReferenceSystem, QgsWkbTypes
)
from qgis.PyQt.QtCore import QVariant, QDate, QTime

from .utils import nombrar_archivo

def procesar_datos_desde_excel(archivo_excel):
    """Carga y valida los datos del Excel"""
    try:
        # Cargar manteniendo como texto las horas
        df = pd.read_excel(
            archivo_excel, 
            sheet_name='Estaciones_MO',
            dtype={'Hora_Ini': str, 'Hora_Ter': str}
        )
        
        if df.empty:
            return None, "No hay estaciones de MO en el archivo Excel."
            
        # Convertir fechas
        df['Fecha'] = pd.to_datetime(df['Fecha']).dt.date
        
        # Procesar horas con posible presencia de segundos
        for col in ['Hora_Ini', 'Hora_Ter']:
            # Eliminar segundos si existen
            df[col] = pd.to_datetime(
                df[col].str.split(':').str[:2].str.join(':'),  # Tomar solo HH:MM
                format='%H:%M', 
                errors='coerce'
            ).dt.time
            
            # Verificar nulos
            if df[col].isnull().any():
                return None, f"Formato de hora inválido en columna {col}"
                
        return df, None
        
    except Exception as e:
        return None, f"Error procesando Excel: {str(e)}"

def crear_capa_puntos(df, epsg, nombre_capa):
    """Crea una capa de puntos en memoria con los datos del DataFrame"""
    vlayer = QgsVectorLayer(f"Point?crs=epsg:{epsg}", nombre_capa, "memory")
    pr = vlayer.dataProvider()
    
    # Definir campos con tipos correctos
    fields = QgsFields()
    fields.append(QgsField("Centro", QVariant.Int))
    fields.append(QgsField("Fecha", QVariant.Date))
    fields.append(QgsField("Hora_Ini", QVariant.String, len=5))  # HH:MM
    fields.append(QgsField("Hora_Ter", QVariant.String, len=5))  # HH:MM
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
                str(row['Hora_Ini'])[:5] if pd.notnull(row['Hora_Ini']) else '',
                str(row['Hora_Ter'])[:5] if pd.notnull(row['Hora_Ter']) else '',
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
    placemarks = []
    
    # Nueva plantilla KML actualizada según el formato requerido
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
                            <href>files/icono_mo.png</href>
                        </Icon>
                    </IconStyle>
                    <LabelStyle>
                        <color>ff00aa55</color>
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
        <tr><td>Hora_Ini</td><td>{hora_ini}</td></tr>
        <tr style="background-color:#DDDDFF;"><td>Hora_Ter</td><td>{hora_ter}</td></tr>
        <tr><td>X</td><td>{x}</td></tr>
        <tr style="background-color:#DDDDFF;"><td>Y</td><td>{y}</td></tr>
        <tr><td>Huso</td><td>{Huso}</td></tr>
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
            <Data name="Hora_Ini">
                <value>{hora_ini}</value>
                <displayName>Hora_Ini</displayName>
            </Data>
            <Data name="Hora_Ter">
                <value>{hora_ter}</value>
                <displayName>Hora_Ter</displayName>
            </Data>
            <Data name="X">
                <value>{x}</value>
                <displayName>X</displayName>
            </Data>
            <Data name="Y">
                <value>{y}</value>
                <displayName>Y</displayName>
            </Data>
            <Data name="Huso">
                <value>{Huso}</value>
                <displayName>Huso</displayName>
            </Data>
        </ExtendedData>
        <Point id="{multi_geometry_id}">
            <coordinates>{coordinates}</coordinates>
        </Point>
    </Placemark>
    '''
    
    # Generación de placemarks
    for idx, row in df.iterrows():
        try:
            lon, lat = transformer.transform(row['X'], row['Y'])
            
            placemark = placemark_template.format(
                placemark_id=f"placemark_{idx}",
                name=f"{row['Estacion']}",
                centro=row['Centro'],
                tipo=row['Tipo'],
                fecha=row['Fecha'].strftime('%d/%m/%Y'),
                hora_ini=row['Hora_Ini'].strftime('%H:%M'),  # Solo hora:minutos
                hora_ter=row['Hora_Ter'].strftime('%H:%M'),  # Solo hora:minutos
                x=row['X'],
                y=row['Y'],
                Huso=row['Huso'],
                multi_geometry_id=f"geom_{idx}",
                coordinates=f"{lon},{lat},0"
            )
            placemarks.append(placemark)
            
        except Exception as e:
            continue
    
    # Generar KML completo
    kml_content = kml_base.format(
        nombre=f"{nombre_archivo} Estaciones MO",
        placemarks="\n".join(placemarks)
    )
    
    # Crear archivo KMZ
    kmz_path = Path(directorio_salida) / f"{nombre_archivo} Estaciones MO.kmz"
    
    try:
        with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
            # 1. Primero escribir el KML
            kmz.writestr(f"doc.kml", kml_content)  # Usar nombre estándar doc.kml
            
            # 2. Manejar el ícono con más robustez
            icon_paths = [
                Path(plugin_dir) / 'files' / 'icono_mo.png',
                Path(__file__).parent / 'files' / 'icono_mo.png',
                Path(os.path.dirname(os.path.abspath(__file__))) / 'files' / 'icono_mo.png'
            ]
            
            icon_found = False
            for icon_path in icon_paths:
                if icon_path.exists():
                    # Crear primero el directorio files en el ZIP
                    kmz.writestr('files/', '')  # Crear directorio explícitamente
                    # Añadir el ícono manteniendo la estructura
                    kmz.write(icon_path, 'files/icono_mo.png')
                    icon_found = True
                    break
            
            if not icon_found:
                raise FileNotFoundError(f"No se encontró el archivo de ícono en ninguna ubicación conocida")
                
    except Exception as e:
        error_msg = f"Error creando archivo KMZ: {str(e)}"
        print(error_msg)
        return None

    return kmz_path

def estaciones_mo(archivo_excel, directorio_salida_shp, directorio_salida_kmz, plugin_instance):
    # Procesamiento inicial
    df, error = procesar_datos_desde_excel(archivo_excel)
    if error:
        plugin_instance.mensajes_texto_plugin(error)
        return

    # Generación de Shapefile
    nombre_base = nombrar_archivo(archivo_excel)
    capa = crear_capa_puntos(df, 32718, f"{nombre_base} Estaciones MO")
    
    # Guardar SHP
    shp_path = Path(directorio_salida_shp) / f"{nombre_base} Estaciones MO Ptos.shp"
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.fileEncoding = 'UTF-8'
    options.driverName = "ESRI Shapefile"
    
    # Guardar usando la capa temporal
    resultado = QgsVectorFileWriter.writeAsVectorFormatV3(
        capa,
        str(shp_path),
        QgsCoordinateTransformContext(),
        options
    )
    
    if resultado[0] != QgsVectorFileWriter.NoError:
        plugin_instance.mensajes_texto_plugin(f"Error guardando SHP: {resultado[1]}")
        return

    # Cargar la capa desde el archivo guardado
    capa_guardada = QgsVectorLayer(str(shp_path), f"{nombre_base} Estaciones MO Ptos", "ogr")
    
    if not capa_guardada.isValid():
        plugin_instance.mensajes_texto_plugin("Error cargando el SHP guardado")
        return

    # Aplicar estilo
    plugin_dir = Path(__file__).parent
    estilo_path = plugin_dir / 'estilos_qml' / 'Estilo INFA Estaciones MO.qml'
    
    if estilo_path.exists():
        capa_guardada.loadNamedStyle(str(estilo_path))
        capa_guardada.triggerRepaint()

    # Añadir al proyecto la capa guardada en disco
    QgsProject.instance().addMapLayer(capa_guardada)

    # Generación KMZ
    generar_kmz(
        df,
        directorio_salida_kmz,
        nombre_base,
        str(plugin_dir)
    )

    plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_base} Estaciones MO Ptos.shp creado")
    plugin_instance.mensajes_texto_plugin(f"Archivo {nombre_base} Estaciones MO Ptos.kmz creado")