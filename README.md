# CHONQUE DEL MONTE
![Chonque del Monte](/static/img/LOGO.png)

# QGIS Plugin para análisis de datos de INFAS obtenidos en terreno, utilizando PyQT5 y qgis.core

Este repositorio contiene un plugin para uso en QGIS 3.36 o superior, que toma datos obtenidos en terreno y crea archivos .shp (shapefile) y .kmz (para Google Earth), a fin de efectuar análisis sobre estos últimos. El framework base es PyQT5 y corre a través de la API de QGIS a través de qgis.core

## Descripción general
Este plugin está diseñado para tomar como inputs diferentes archivos resultantes de muestreo en terreno por parte de una consultora externa para dar cumplimiento a la ejecución de INFA (Informe Ambiental de la Acuicultura) en centros de cultivo, para luego efectuar análisis sobre los archivos que entrega el plugin. El uso del mismo está irrestrictamente unido a cualquier versión de QGIS superior a la 3.36, ya que funciona al interior de éste. 

### Características principales

- **QGIS** Software de información geográfica (SIG) que es la base de procesamiento sobre la cual trabaja el plugin.
- **PyQT5** Framework sobre el cual se ejecutan los geoprocesos.
- **qgis.core** API interna de QGIS para trabajar con geometrías vectoriales

### Pre requisitos

- QGIS 3.36 o superior

## Instalación

Se debe instalar como archivo comprimido dentro de QGIS en: complementos -> administrar o instalar complementos -> Instalar a partir de zip.

## Uso

Se deben cargar todos los archivos necesarios para le ejecución del plugin, una vez procesados los datos los archivos resultantes estarán en las carpetas indicadas como parámetros.

## A tener en consideración

Versión 1.0, puede contener muchos errores debido a lo amplio y diverso de los análisis efectuados, además de error humano en la toma de los datos originales.

## ToDo:

- Añadir manual de uso
- Mejorar lógica de algunos procesos
- Mejorar explicaciones de instalación