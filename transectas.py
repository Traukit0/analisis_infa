from typing import Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from pyproj import Transformer
import pandas as pd
import zipfile
import os
from os import remove
from .utils import nombrar_archivo

from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsField, QgsCoordinateTransformContext, QgsVectorFileWriter, 
    QgsFields, QgsProject,
)
from qgis.PyQt.QtCore import QVariant

# Constants
EPSG_SOURCE = "epsg:32718"
EPSG_TARGET = "epsg:4326"
FIELD_DEFINITIONS = [
    ("Centro", QVariant.Int, "", 50),
    ("Fecha", QVariant.Date, "", 50),
    ("Hora", QVariant.Time, "", 50),
    ("Transecta", QVariant.Int, "", 50),
    ("Extremo", QVariant.String, "", 50),
    ("X", QVariant.Int, "", 50),
    ("Y", QVariant.Int, "", 50),
    ("Huso", QVariant.Int, "", 50),
]

@dataclass
class LayerConfig:
    """Configuration for layer creation"""
    name: str
    geometry_type: str
    style_file: str
    
def create_vector_layer(config: LayerConfig, fields: list) -> Tuple[QgsVectorLayer, Any]:
    """Create a new vector layer with specified configuration"""
    vlayer = QgsVectorLayer(f"{config.geometry_type}?crs={EPSG_SOURCE}", config.name, "memory")
    provider = vlayer.dataProvider()
    
    fields_collection = QgsFields()
    for name, type_, _, size in fields:
        fields_collection.append(QgsField(name, type_, "", size))
    
    provider.addAttributes(fields_collection)
    vlayer.updateFields()
    
    return vlayer, provider

def save_layer(layer: QgsVectorLayer, output_path: str, layer_name: str, style_path: str) -> None:
    """Save layer to file and add to QGIS project"""
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    transform_context = QgsCoordinateTransformContext()
    
    QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, output_path, transform_context, options
    )
    
    result_layer = QgsVectorLayer(output_path, layer_name, "ogr")
    if not result_layer.isValid():
        raise ValueError(f"Could not load layer {layer_name}")
        
    if os.path.exists(style_path):
        result_layer.loadNamedStyle(style_path)
        result_layer.triggerRepaint()
        
    QgsProject.instance().addMapLayer(result_layer)

def create_kml_content(df: pd.DataFrame, transformer: Transformer) -> str:
    """Generate KML content from dataframe, creating lines between I and T points"""
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
        <name>Transecta {transecta}</name>
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
        <LineString id="{line_string_id}">
            <coordinates>{coordinates}</coordinates>
        </LineString>
    </Placemark>
    '''
    
    placemarks = ''
    placemark_id = 1
    line_string_id = 1
    
    # Procesar por transecta para crear las líneas
    for transecta in df['Transecta'].unique():
        # Obtener los puntos de esta transecta
        transecta_df = df[df['Transecta'] == transecta].sort_values(by='Extremo')
        
        if len(transecta_df) == 2 and {'I', 'T'}.issubset(set(transecta_df['Extremo'])):
            # Transformar coordenadas de ambos puntos
            coordinates = []
            for _, row in transecta_df.iterrows():
                lon, lat = transformer.transform(row['X'], row['Y'])
                coordinates.append(f"{lon},{lat},0")
            
            # Unir las coordenadas en un string
            coordinates_str = ' '.join(coordinates)
            
            placemarks += placemark_template.format(
                placemark_id=placemark_id,
                transecta=transecta,
                centro=transecta_df.iloc[0]['Centro'],
                fecha=transecta_df.iloc[0]['Fecha'],
                line_string_id=line_string_id,
                coordinates=coordinates_str
            )
            placemark_id += 1
            line_string_id += 1
            
    return kml_base.format(nombre="Transectas Linea", placemarks=placemarks)

def transectas(archivo_excel: str, directorio_salida_shp: str, directorio_salida_kmz: str, plugin_instance: Any) -> None:
    """
    Process transect data from Excel file and create corresponding GIS layers.
    
    Args:
        archivo_excel: Path to Excel file containing transect data
        directorio_salida_shp: Output directory for shapefile
        directorio_salida_kmz: Output directory for KMZ file
        plugin_instance: Plugin instance for messaging
    """
    try:
        df = pd.read_excel(archivo_excel, sheet_name='Transectas')
        if df.empty:
            plugin_instance.mensajes_texto_plugin("\nNo hay transectas en el archivo Excel.")
            return
            
        # Ensure output directories end with separator
        directorio_salida_shp = Path(directorio_salida_shp).as_posix() + '/'
        directorio_salida_kmz = Path(directorio_salida_kmz).as_posix() + '/'
        
        plugin_dir = Path(__file__).parent
        nombre_archivo = nombrar_archivo(archivo_excel)
        
        # Create and save point layer
        point_config = LayerConfig(
            name="Puntos",
            geometry_type="Point",
            style_file=str(plugin_dir / 'estilos_qml' / 'Estilo INFA Transecta Ptos.qml')
        )
        
        point_layer, point_provider = create_vector_layer(point_config, FIELD_DEFINITIONS)
        
        # Add points
        features = []
        for _, row in df.iterrows():
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(int(row['X']), int(row['Y']))))
            feature.setAttributes([str(row[field[0]]) for field in FIELD_DEFINITIONS])
            features.append(feature)
            
        point_provider.addFeatures(features)
        point_layer.updateExtents()
        
        # Save point layer
        point_output = f"{directorio_salida_shp}{nombre_archivo} Transectas Ptos.shp"
        save_layer(point_layer, point_output, f"{nombre_archivo} Transectas Ptos.shp", point_config.style_file)
        
        # Create and process line layer
        line_config = LayerConfig(
            name="Líneas",
            geometry_type="LineString",
            style_file=str(plugin_dir / 'estilos_qml' / 'Estilo INFA Transecta Linea.qml')
        )
        
        llayer = QgsVectorLayer(f"{line_config.geometry_type}?crs={EPSG_SOURCE}", line_config.name, "memory")
        pr = llayer.dataProvider()
        
        # Definir campos para las líneas
        line_fields = [
            ("Centro", QVariant.Int, "", 254),
            ("Transecta", QVariant.Int, "", 254),
            ("Fecha", QVariant.Date, "", 254)
        ]
        
        fields = QgsFields()
        for name, type_, _, size in line_fields:
            fields.append(QgsField(name, type_, "", size))
        pr.addAttributes(fields)
        llayer.updateFields()

        # Crear líneas para cada transecta
        features = []
        # Agrupar solo por número de transecta
        for transecta in df['Transecta'].unique():
            # Obtener todos los puntos de esta transecta
            transecta_df = df[df['Transecta'] == transecta].sort_values(by='Extremo')
            
            if len(transecta_df) != 2:
                plugin_instance.mensajes_texto_plugin(
                    f"\nAdvertencia: La transecta {transecta} no tiene exactamente 2 puntos"
                )
                continue
            
            # Verificar que tenemos punto inicial (I) y terminal (T)
            if not {'I', 'T'}.issubset(set(transecta_df['Extremo'])):
                plugin_instance.mensajes_texto_plugin(
                    f"\nAdvertencia: La transecta {transecta} no tiene punto inicial y terminal"
                )
                continue
            
            # Crear la línea con los dos puntos
            points = [QgsPointXY(int(row['X']), int(row['Y'])) 
                     for _, row in transecta_df.iterrows()]
            
            if len(points) == 2:
                line = QgsFeature()
                line_geom = QgsGeometry.fromPolylineXY(points)
                
                # Verificar que la geometría es válida
                if not line_geom.isGeosValid():
                    plugin_instance.mensajes_texto_plugin(
                        f"\nError: Geometría inválida en transecta {transecta}"
                    )
                    continue
                
                line.setGeometry(line_geom)
                # Convertir fecha a string para evitar problemas de formato
                line.setAttributes([
                    int(transecta_df.iloc[0]['Centro']),
                    int(transecta),
                    str(transecta_df.iloc[0]['Fecha'])
                ])
                features.append(line)
        
        # Añadir todas las líneas de una vez
        if features:
            pr.addFeatures(features)
            llayer.updateExtents()
        else:
            plugin_instance.mensajes_texto_plugin("\nAdvertencia: No se pudieron crear líneas")
            return

        # Guardar la capa de líneas
        shp_lineas_file_path = f"{directorio_salida_shp}{nombre_archivo} Transectas Linea.shp"
        save_layer(llayer, shp_lineas_file_path, f"{nombre_archivo} Transectas Linea.shp", line_config.style_file)

        # Create KML/KMZ con verificación adicional
        transformer = Transformer.from_crs(EPSG_SOURCE, EPSG_TARGET, always_xy=True)
        kml_content = create_kml_content(df, transformer)
        
        kmz_path = Path(directorio_salida_kmz) / "Transectas Linea"
        with open(f"{kmz_path}.kml", 'w') as file:
            file.write(kml_content)
            
        with zipfile.ZipFile(f"{kmz_path}.kmz", 'w') as kmz:
            kmz.write(f"{kmz_path}.kml")
            
        remove(f"{kmz_path}.kml")
        
    except Exception as e:
        plugin_instance.mensajes_texto_plugin(f"\nError procesando transectas: {str(e)}")