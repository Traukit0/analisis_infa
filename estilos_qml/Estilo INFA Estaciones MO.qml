<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" maxScale="0" readOnly="0" version="3.4.13-Madeira" styleCategories="AllStyleCategories" simplifyLocal="1" minScale="1e+08" simplifyMaxScale="1" simplifyDrawingHints="0" simplifyDrawingTol="1" labelsEnabled="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 symbollevels="0" type="singleSymbol" enableorderby="0" forceraster="0">
    <symbols>
      <symbol alpha="1" force_rhr="0" type="marker" clip_to_extent="1" name="0">
        <layer pass="0" class="SimpleMarker" locked="0" enabled="1">
          <prop v="0" k="angle"/>
          <prop v="51,160,44,255" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,255,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.4" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style previewBkgrdColor="#ffffff" fieldName="'Est ' ||  &quot;Estacion&quot;  || ' '  ||  &quot;Tipo&quot;   ||  '\n'  ||  '[' || left(&quot;Hora_Ini&quot;,5) || '-' ||  left(&quot;Hora_Ter&quot;,5)  || ']'&#xd;&#xa;" multilineHeight="1" fontItalic="0" textOpacity="1" isExpression="1" fontCapitals="0" namedStyle="Normal" fontWeight="50" fontStrikeout="0" fontWordSpacing="0" textColor="31,120,180,255" blendMode="0" fontLetterSpacing="0" fontSizeUnit="Point" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontSize="8" fontUnderline="0" useSubstitutions="0" fontFamily="Arial">
        <text-buffer bufferSizeUnits="MM" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferColor="255,255,255,255" bufferOpacity="1" bufferNoFill="1" bufferBlendMode="0" bufferSize="1" bufferJoinStyle="128" bufferDraw="1"/>
        <background shapeDraw="0" shapeRadiiY="0" shapeRotation="0" shapeBorderWidthUnit="MM" shapeOffsetUnit="MM" shapeSizeX="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeSVGFile="" shapeSizeY="0" shapeType="0" shapeRadiiUnit="MM" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBlendMode="0" shapeSizeUnit="MM" shapeRadiiX="0" shapeJoinStyle="64" shapeFillColor="255,255,255,255" shapeOffsetX="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetY="0" shapeBorderColor="128,128,128,255" shapeRotationType="0" shapeBorderWidth="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeOpacity="1"/>
        <shadow shadowOffsetUnit="MM" shadowOffsetAngle="135" shadowOffsetDist="1" shadowBlendMode="6" shadowOffsetGlobal="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOpacity="0.7" shadowDraw="0" shadowScale="100" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowUnder="0" shadowRadiusUnit="MM" shadowRadiusAlphaOnly="0" shadowRadius="1.5" shadowColor="0,0,0,255"/>
        <substitutions/>
      </text-style>
      <text-format placeDirectionSymbol="0" multilineAlign="3" rightDirectionSymbol=">" formatNumbers="0" leftDirectionSymbol="&lt;" reverseDirectionSymbol="0" autoWrapLength="0" addDirectionSymbol="0" plussign="0" wrapChar="" useMaxLineLengthForAutoWrap="1" decimals="3"/>
      <placement offsetUnits="MM" distUnits="MM" rotationAngle="0" repeatDistance="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" fitInPolygonOnly="0" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" xOffset="0" repeatDistanceUnits="MM" maxCurvedCharAngleOut="-25" offsetType="0" quadOffset="4" centroidInside="0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" preserveRotation="1" dist="2" placement="6" maxCurvedCharAngleIn="25" priority="5" yOffset="0" centroidWhole="0" placementFlags="10" distMapUnitScale="3x:0,0,0,0,0,0"/>
      <rendering maxNumLabels="2000" zIndex="0" upsidedownLabels="0" mergeLines="0" displayAll="0" limitNumLabels="0" scaleMin="0" fontMinPixelSize="3" labelPerPart="0" drawLabels="1" minFeatureSize="0" obstacleFactor="2" fontLimitPixelSize="0" obstacleType="0" obstacle="1" scaleVisibility="0" scaleMax="0" fontMaxPixelSize="10000"/>
      <dd_properties>
        <Option type="Map">
          <Option type="QString" value="" name="name"/>
          <Option name="properties"/>
          <Option type="QString" value="collection" name="type"/>
        </Option>
      </dd_properties>
    </settings>
  </labeling>
  <customproperties>
    <property key="dualview/previewExpressions" value="Estacion"/>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer attributeLegend="1" diagramType="Histogram">
    <DiagramCategory labelPlacementMethod="XHeight" enabled="0" rotationOffset="270" penColor="#000000" minScaleDenominator="0" sizeType="MM" diagramOrientation="Up" lineSizeScale="3x:0,0,0,0,0,0" sizeScale="3x:0,0,0,0,0,0" scaleDependency="Area" barWidth="5" minimumSize="0" width="15" penWidth="0" lineSizeType="MM" penAlpha="255" height="15" scaleBasedVisibility="0" opacity="1" backgroundColor="#ffffff" backgroundAlpha="255" maxScaleDenominator="1e+08">
      <fontProperties style="" description="MS Shell Dlg 2,8.25,-1,5,50,0,0,0,0,0"/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings linePlacementFlags="18" placement="0" dist="0" showAll="1" priority="0" zIndex="0" obstacle="0">
    <properties>
      <Option type="Map">
        <Option type="QString" value="" name="name"/>
        <Option name="properties"/>
        <Option type="QString" value="collection" name="type"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="Centro">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Fecha">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Hora_Ini">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Hora_Ter">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Estacion">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Tipo">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Huso">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias index="0" name="" field="Centro"/>
    <alias index="1" name="" field="Fecha"/>
    <alias index="2" name="" field="Hora_Ini"/>
    <alias index="3" name="" field="Hora_Ter"/>
    <alias index="4" name="" field="Estacion"/>
    <alias index="5" name="" field="Tipo"/>
    <alias index="6" name="" field="Huso"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default expression="" applyOnUpdate="0" field="Centro"/>
    <default expression="" applyOnUpdate="0" field="Fecha"/>
    <default expression="" applyOnUpdate="0" field="Hora_Ini"/>
    <default expression="" applyOnUpdate="0" field="Hora_Ter"/>
    <default expression="" applyOnUpdate="0" field="Estacion"/>
    <default expression="" applyOnUpdate="0" field="Tipo"/>
    <default expression="" applyOnUpdate="0" field="Huso"/>
  </defaults>
  <constraints>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="Centro"/>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="Fecha"/>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="Hora_Ini"/>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="Hora_Ter"/>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="Estacion"/>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="Tipo"/>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="Huso"/>
  </constraints>
  <constraintExpressions>
    <constraint exp="" field="Centro" desc=""/>
    <constraint exp="" field="Fecha" desc=""/>
    <constraint exp="" field="Hora_Ini" desc=""/>
    <constraint exp="" field="Hora_Ter" desc=""/>
    <constraint exp="" field="Estacion" desc=""/>
    <constraint exp="" field="Tipo" desc=""/>
    <constraint exp="" field="Huso" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig sortOrder="0" sortExpression="&quot;Estacion&quot;" actionWidgetStyle="dropDown">
    <columns>
      <column width="-1" type="field" hidden="0" name="Estacion"/>
      <column width="-1" type="actions" hidden="1"/>
      <column width="-1" type="field" hidden="0" name="Centro"/>
      <column width="-1" type="field" hidden="0" name="Tipo"/>
      <column width="-1" type="field" hidden="0" name="Fecha"/>
      <column width="-1" type="field" hidden="0" name="Hora_Ini"/>
      <column width="-1" type="field" hidden="0" name="Hora_Ter"/>
      <column width="-1" type="field" hidden="0" name="Huso"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- codificación: utf-8 -*-
"""
Los formularios de QGIS pueden tener una función de Python que
es llamada cuando se abre el formulario.

Use esta función para añadir lógica extra a sus formularios.

Introduzca el nombre de la función en el campo
"Python Init function".
Sigue un ejemplo:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field editable="1" name="Centro"/>
    <field editable="1" name="Estacion"/>
    <field editable="1" name="Fecha"/>
    <field editable="1" name="Hora"/>
    <field editable="1" name="Hora_Ini"/>
    <field editable="1" name="Hora_Ter"/>
    <field editable="1" name="Horario"/>
    <field editable="1" name="Huso"/>
    <field editable="1" name="Tipo"/>
    <field editable="1" name="X"/>
    <field editable="1" name="Y"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="Centro"/>
    <field labelOnTop="0" name="Estacion"/>
    <field labelOnTop="0" name="Fecha"/>
    <field labelOnTop="0" name="Hora"/>
    <field labelOnTop="0" name="Hora_Ini"/>
    <field labelOnTop="0" name="Hora_Ter"/>
    <field labelOnTop="0" name="Horario"/>
    <field labelOnTop="0" name="Huso"/>
    <field labelOnTop="0" name="Tipo"/>
    <field labelOnTop="0" name="X"/>
    <field labelOnTop="0" name="Y"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>Estacion</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>
