# Análisis INFA - Plugin para QGIS
![Chonque del Monte](/static/img/LOGO.png)

## Descripción general

El plugin "Análisis INFA" es una herramienta especializada para QGIS diseñada para procesar y analizar datos recolectados en terreno durante la ejecución de Informes Ambientales de la Acuicultura (INFA). Desarrollado específicamente para profesionales del sector acuícola y ambiental, este plugin transforma datos crudos de monitoreo en archivos geoespaciales analizables (.shp, .kmz), facilitando la evaluación de impacto ambiental en centros de cultivo acuícola.

## Características principales

- **Procesamiento de múltiples tipos de datos**: Manejo de estaciones de muestreo MO (materia orgánica), estaciones OX (oxígeno), transectas, módulos, tracks GPS, waypoints y datos batimétricos.
- **Transformación de coordenadas**: Conversión automática entre sistemas de coordenadas UTM y geográficas.
- **Generación de archivos Shapefile**: Creación de capas vectoriales con tablas de atributos estructuradas para análisis en QGIS.
- **Exportación a KMZ**: Generación de archivos compatibles con Google Earth para visualización 3D con simbología personalizada.
- **Interfaz integrada**: Totalmente integrado con la interfaz de QGIS, proporcionando una experiencia de usuario fluida.
- **Validación de datos**: Verificación automática de la integridad y consistencia de los datos de entrada.

## Requisitos del sistema

- QGIS 3.32 o superior
- Dependencias externas:
  - openpyxl (procesamiento de archivos Excel)
  - et-xmlfile (manejo de XML)
- Sistema operativo: Compatible con Windows, MacOS y Linux (cualquier SO que soporte QGIS 3.32+)
- Memoria RAM: Mínimo 4GB recomendado

## Instalación

1. Abrir QGIS
2. Ir a "Complementos" → "Administrar e instalar complementos..."
3. Seleccionar la pestaña "Instalar a partir de ZIP"
4. Navegar y seleccionar el archivo ZIP del plugin
5. Hacer clic en "Instalar complemento"
6. Una vez instalado, el ícono del plugin aparecerá en la barra de herramientas de QGIS

## Uso básico

1. **Iniciar el plugin**: Hacer clic en el ícono del plugin en la barra de herramientas de QGIS
2. **Configurar parámetros**:
   - Seleccionar los archivos de entrada (Excel con datos de estaciones, archivos GPX de tracks, etc.)
   - Definir directorios de salida para archivos shapefile (.shp) y Google Earth (.kmz)
   - Configurar el offset UTC si es necesario para los datos temporales
3. **Procesar datos**: Hacer clic en "Procesar" para iniciar la transformación de datos
4. **Visualizar resultados**: Los archivos generados se cargarán automáticamente en el proyecto QGIS actual

## Módulos disponibles

El plugin incluye varios módulos especializados:

| Módulo | Descripción |
|--------|-------------|
| Estaciones MO | Procesa datos de muestreo de materia orgánica en sedimentos |
| Estaciones OX | Analiza mediciones de oxígeno en la columna de agua |
| Transectas | Procesa líneas de muestreo utilizadas en evaluaciones ambientales |
| Módulos | Gestiona información sobre módulos de cultivo |
| Track GPX | Procesa rutas GPS grabadas durante los muestreos |
| Waypoints | Maneja puntos de interés marcados durante el trabajo de campo |
| Batimetría | Procesa datos de profundidad para generar modelos batimétricos |

## Flujo de trabajo recomendado

1. Recolección de datos en terreno (GPS, mediciones ambientales, muestras)
2. Organización de datos en las plantillas Excel predefinidas
3. Procesamiento con el plugin Análisis INFA
4. Análisis geoespacial de resultados en QGIS
5. Exportación a Google Earth para visualización tridimensional
6. Generación de informes y documentación técnica

## Solución de problemas comunes

- **Error al cargar archivos Excel**: Verifique que el formato de las hojas de cálculo corresponda con las plantillas requeridas.
- **Coordenadas incorrectas**: Asegúrese de que el huso UTM esté correctamente especificado en los datos de entrada.
- **Archivos KMZ no visibles**: Compruebe que los estilos e íconos estén correctamente referenciados en la carpeta del plugin.

## Desarrollo futuro

- Concentración de todos los exports en un solo archivo KMZ comprensivo
- Incorporación de mapas base en las exportaciones KMZ
- Soporte para transformación directa de archivos .gdb a .gpx
- Mejoras en la validación de datos y manejo de errores
- Implementación de generación automática de informes PDF

## Changelog

### Versión 1.2 - 23 de enero de 2025

#### 🔧 Correcciones Críticas
- **Solucionado**: Archivos de track (puntos y segmentos) se generaban vacíos
- **Causa identificada**: Desalineamiento entre campos definidos (15) y valores asignados (16) en tabla de atributos
- **Corrección**: Reestructurada función `create_feature_attributes()` para alineamiento exacto de campos

#### 🛠️ Mejoras en Gestión de Archivos
- **Implementado**: Context manager para archivos Excel en `utils.py`
- **Solucionado**: ResourceWarnings por archivos Excel no cerrados correctamente
- **Aplicado a**: Funciones `nombrar_archivo()` y `obtener_dia_muestreo()`
- **Resultado**: Eliminación completa de memory leaks relacionados con archivos Excel

#### 🎯 Validaciones Robustas
- **Mejorado**: Sistema de validación de features en procesamiento de tracks
- **Agregado**: Verificación de existencia y contenido de archivos dependientes
- **Implementado**: Validación de que efectivamente se generaron features válidas (no solo que existían en el GPX original)
- **Beneficio**: Prevención de archivos SHP aparentemente exitosos pero vacíos

#### 🔍 Gestión de Dependencias
- **Corregido**: `segmentos_track.py` ahora verifica existencia del archivo de puntos antes de procesarlo
- **Agregado**: Validación de que el archivo de puntos contiene datos antes de generar segmentos
- **Implementado**: Mensajes informativos sobre el estado de archivos dependientes

#### 📊 Optimizaciones de Rendimiento
- **Eliminado**: Parsing múltiple de archivos Excel (se usaba `pd.read_excel()` en lugar de `ExcelFile.parse()`)
- **Optimizado**: Reutilización de conexiones a archivos Excel
- **Resultado**: Reducción significativa del tiempo de procesamiento para archivos grandes

#### 🐛 Corrección de Errores de Filtrado
- **Identificado**: Problema con filtrado por día de muestreo causaba rechazo de todos los puntos
- **Mejorado**: Manejo más robusto de formatos de fecha en archivos Excel
- **Agregado**: Validación de consistencia entre fecha del Excel y timestamps del GPX

#### ⚡ Mejoras en Experiencia de Usuario
- **Eliminado**: Mensajes de debugging excesivos que saturaban la consola
- **Conservado**: Mensajes informativos esenciales sobre el progreso del procesamiento
- **Mejorado**: Claridad en mensajes de error cuando no se encuentran datos válidos

#### 🔄 Refactoring de Código
- **Simplificado**: Función `process_feature()` para mejor legibilidad y mantenimiento
- **Eliminado**: Funciones obsoletas (`is_point_valid()`, versión anterior de `create_feature_attributes()`)
- **Mejorado**: Documentación inline y estructura de funciones
- **Eliminado**: llamados a print e ET.tree en wpt_gpx.py que se utilizaba para debugging, ya no era necesario.

#### 📈 Impacto de las Mejoras
- **Antes**: 468 features procesadas → 0 features válidas (archivos vacíos)
- **Después**: 468 features procesadas → 432 features válidas (archivos funcionales)
- **Resultado**: Plugin completamente funcional para procesamiento de tracks GPS
- **Beneficio**: Generación exitosa de todos los productos geoespaciales requeridos

## Información legal y técnica

- **Autor**: Manuel Eduardo Cano Nesbet
- **Licencia**: GNU General Public License v2
- **Versión actual**: 1.2
- **Contacto**: mcano@sernapesca.cl
- **Repositorio**: [https://github.com/Traukit0/analisis_infa](https://github.com/Traukit0/analisis_infa)

---

*Este plugin está diseñado específicamente para uso profesional en el análisis ambiental de la acuicultura en Chile. Los resultados deben ser interpretados por personal calificado en el contexto de la normativa ambiental vigente.*