#  coding: utf-8 
"""
***************************************************************
*** СОЗДАНИЕ ВЕТКИ СПРИНКЛЕРОВ БЕЗ ОГРАНИЧЕНИЯ Н
*** 
***************************************************************
* Убрано ограничение на то чтобы спринклер проецировался на 
* трубу, при необходимости добавляется дополнительный участок трубы
* чтобы подойти к точке подключения
***************************************************************
"""
dut = 0.0032808398950131233

view_name = 'DM_ОТМЕТКИ'
margin_rel = False
margin = 200 * dut



from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math, sys
import clr
import System
from System.Collections.Generic import IList, List

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
clr.AddReferenceToFileAndPath(r"C:\Program Files\Autodesk\Revit 2021\RevitAPIIFC.dll")
import NetTopologySuite as nts
import NetTopologySuite.Geometries as nts_geom
from Autodesk.Revit.DB import IFC as ifc

lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
	sys.path.append(lib_path)
	
import dm_connect_2 as dm
import dm_nearest_geometry as dm1

reload(dm)	
reload(dm1)


pi2 = math.pi * 2

dut = 0.0032808398950131233


	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

print('Работаем')

view = uidoc.ActiveView

vis_filter = VisibleInViewFilter(doc, view.Id)
categories = System.Array[bic]([
    bic.OST_PipeCurves,
    bic.OST_PipeFitting, 
    bic.OST_Sprinklers, 
    bic.OST_PipeAccessory,
    bic.OST_MechanicalEquipment,
    bic.OST_GenericModel,
])
multicat_filter = ElementMulticategoryFilter(categories)

els = FilteredElementCollector(doc).WherePasses(
    vis_filter).WherePasses(
        multicat_filter).WhereElementIsNotElementType().ToElementIds()
print(len(els))




with dm.trans(doc) :
    doc.Delete(els)



