# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AnalisisInfa
                                 A QGIS plugin
 Plugin para el análisis remoto de INFAs realizadas en terreno
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-07-11
        copyright            : (C) 2024 by Manuel Eduardo Cano Nesbet
        email                : mcano@sernapesca.cl
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AnalisisInfa class from file AnalisisInfa.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .analisis_infa import AnalisisInfa
    return AnalisisInfa(iface)
