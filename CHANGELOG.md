# Changelog

Todos los cambios notables en el plugin Análisis INFA se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere al [Versionado Semántico](https://semver.org/lang/es/).

## [No publicado] - 2025-01-23

### 🚀 Nuevas Características
- **Batimetría**: Exportación de múltiples archivos KMZ por valor de `Fuente`. Cada grupo se exporta con nombre `Batimetria_YYYY.kmz` cuando el año está presente en el texto de `Fuente`; en caso contrario, se usa una versión saneada del valor.

### 🔧 Correcciones
- **Solucionado**: Error de división por cero en procesamiento de segmentos de track cuando existen puntos duplicados
- **Solucionado**: Puntos GPS duplicados causaban archivos shapefile con información redundante
- **Implementado**: Filtrado automático de puntos duplicados con distancia cero en segmentos
- **Implementado**: Filtrado automático de puntos con coordenadas idénticas en puntos de track
- **Mejorado**: Sistema de información sobre elementos omitidos por duplicación
- **Resultado**: El plugin ya no falla al procesar tracks con puntos GPS duplicados y genera archivos más limpios

### 🛠️ Mejoras Técnicas
- **UI**: El selector de “Archivo Batimetría (.shp)” ahora restringe la búsqueda a archivos con extensión `.shp` únicamente.
- **Modificado**: Función `create_segment_feature()` en `segmentos_track.py` ahora retorna `None` para segmentos con distancia cero
- **Implementado**: Sistema de filtrado de coordenadas duplicadas en `puntos_track_gpx.py` usando set para búsquedas eficientes
- **Agregado**: Contador de segmentos omitidos por duplicación en procesamiento de segmentos
- **Agregado**: Contador de puntos omitidos por coordenadas idénticas en procesamiento de puntos
- **Implementado**: Mensajes informativos sobre elementos duplicados eliminados en ambos módulos
- **Optimizado**: Verificación de duplicados con precisión de 6 decimales para evitar falsos positivos por precisión flotante

## [1.2] - 2025-01-23

### 🔧 Correcciones Críticas
- **Solucionado**: Archivos de track (puntos y segmentos) se generaban vacíos
- **Causa identificada**: Desalineamiento entre campos definidos (15) y valores asignados (16) en tabla de atributos
- **Corrección**: Reestructurada función `create_feature_attributes()` para alineamiento exacto de campos

### 🛠️ Mejoras en Gestión de Archivos
- **Implementado**: Context manager para archivos Excel en `utils.py`
- **Solucionado**: ResourceWarnings por archivos Excel no cerrados correctamente
- **Aplicado a**: Funciones `nombrar_archivo()` y `obtener_dia_muestreo()`
- **Resultado**: Eliminación completa de memory leaks relacionados con archivos Excel

### 🎯 Validaciones Robustas
- **Mejorado**: Sistema de validación de features en procesamiento de tracks
- **Agregado**: Verificación de existencia y contenido de archivos dependientes
- **Implementado**: Validación de que efectivamente se generaron features válidas (no solo que existían en el GPX original)
- **Beneficio**: Prevención de archivos SHP aparentemente exitosos pero vacíos

### 🔍 Gestión de Dependencias
- **Corregido**: `segmentos_track.py` ahora verifica existencia del archivo de puntos antes de procesarlo
- **Agregado**: Validación de que el archivo de puntos contiene datos antes de generar segmentos
- **Implementado**: Mensajes informativos sobre el estado de archivos dependientes

### 📊 Optimizaciones de Rendimiento
- **Eliminado**: Parsing múltiple de archivos Excel (se usaba `pd.read_excel()` en lugar de `ExcelFile.parse()`)
- **Optimizado**: Reutilización de conexiones a archivos Excel
- **Resultado**: Reducción significativa del tiempo de procesamiento para archivos grandes

### 🐛 Corrección de Errores de Filtrado
- **Identificado**: Problema con filtrado por día de muestreo causaba rechazo de todos los puntos
- **Mejorado**: Manejo más robusto de formatos de fecha en archivos Excel
- **Agregado**: Validación de consistencia entre fecha del Excel y timestamps del GPX

### ⚡ Mejoras en Experiencia de Usuario
- **Eliminado**: Mensajes de debugging excesivos que saturaban la consola
- **Conservado**: Mensajes informativos esenciales sobre el progreso del procesamiento
- **Mejorado**: Claridad en mensajes de error cuando no se encuentran datos válidos

### 🔄 Refactoring de Código
- **Simplificado**: Función `process_feature()` para mejor legibilidad y mantenimiento
- **Eliminado**: Funciones obsoletas (`is_point_valid()`, versión anterior de `create_feature_attributes()`)
- **Mejorado**: Documentación inline y estructura de funciones
- **Eliminado**: Llamados a print e ET.tree en wpt_gpx.py que se utilizaba para debugging, ya no era necesario

### 📈 Impacto de las Mejoras
- **Antes**: 468 features procesadas → 0 features válidas (archivos vacíos)
- **Después**: 468 features procesadas → 432 features válidas (archivos funcionales)
- **Resultado**: Plugin completamente funcional para procesamiento de tracks GPS
- **Beneficio**: Generación exitosa de todos los productos geoespaciales requeridos

## [1.1] - 2024-12-15

### 🚀 Nuevas Características
- **Agregado**: Soporte para procesamiento de waypoints GPX
- **Implementado**: Clasificación automática de waypoints por tipo
- **Mejorado**: Interfaz de usuario para selección de archivos múltiples

### 🔧 Correcciones
- **Solucionado**: Error en transformación de coordenadas para datos batimétricos
- **Corregido**: Problema de codificación de caracteres especiales en nombres de archivos

### 🛠️ Mejoras
- **Optimizado**: Procesamiento de archivos Excel de gran tamaño
- **Mejorado**: Validación de datos de entrada

## [1.0] - 2024-11-30

### 🚀 Lanzamiento Inicial
- **Implementado**: Procesamiento completo de estaciones MO (materia orgánica)
- **Implementado**: Procesamiento completo de estaciones OX (oxígeno)
- **Implementado**: Manejo de transectas de muestreo
- **Implementado**: Procesamiento de módulos de cultivo
- **Implementado**: Conversión de tracks GPS a formatos SHP y KMZ
- **Implementado**: Procesamiento de datos batimétricos
- **Agregado**: Interfaz gráfica integrada con QGIS
- **Agregado**: Sistema de estilos QML personalizados
- **Agregado**: Validación automática de datos de entrada
- **Implementado**: Transformación automática de coordenadas UTM a geográficas
- **Agregado**: Exportación compatible con Google Earth (KMZ)

### 🎨 Características de Diseño
- **Implementado**: Iconografía personalizada para diferentes tipos de datos
- **Agregado**: Estilos de visualización específicos para cada módulo
- **Implementado**: Simbología diferenciada por velocidad en tracks
- **Agregado**: Paleta de colores coherente en todos los módulos

### 🔧 Arquitectura Técnica
- **Implementado**: Arquitectura modular para fácil mantenimiento
- **Agregado**: Sistema de logging y manejo de errores
- **Implementado**: Validación robusta de formatos de archivo
- **Agregado**: Compatibilidad multiplataforma (Windows, macOS, Linux)

---

Para más información sobre versiones específicas, consulte los commits en el [repositorio de GitHub](https://github.com/Traukit0/analisis_infa). 