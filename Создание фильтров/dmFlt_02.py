#  coding: utf-8 

from Autodesk.Revit import *
from Autodesk.Revit.DB import *
import Autodesk.Revit.Exceptions
import System 
import clr

import math, sys
import clr

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
import NetTopologySuite as nts
import NetTopologySuite.Geometries as nts_geom


lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
	sys.path.append(lib_path)
	

lib_path = r"D:\18_проектирование\98_PythonShell\Создание фильтров"
if not lib_path in sys.path :
	sys.path.append(lib_path)
	



pi2 = math.pi * 2

dut = 0.0032808398950131233

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType


uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

print("dmFlt_02.py")

fc = FilteredElementCollector(doc)
# fc.OfCategory(bic.OST_PipingSystem)
fc.OfClass(Plumbing.PipingSystemType)
pss = fc.ToElements()

pipe_param = FilteredElementCollector(doc).OfClass(Plumbing.Pipe).FirstElement()
print(80*"-")
param_id = pipe_param.LookupParameter("ИмяСистемы").Id
print(param_id)
print(80*"*")

filt_categories = System.Collections.Generic.List[ElementId]([
                        ElementId(bic.OST_PipeCurves), 
                         ElementId(bic.OST_PipeFitting), 
                         ElementId(bic.OST_PipeAccessory), 
                          ElementId(bic.OST_MechanicalEquipment), 
                        ElementId(bic.OST_Sprinklers)                    
                        ])

av = uidoc.ActiveView
tr = Transaction(doc)
tr.Start("1")

for ps in pss :
    if not str(ps.SystemClassification).startswith("FireProtect") :
        # print(ps)
        # print(ps.Abbreviation)
        # print(ps.SystemClassification)
        continue
    if ps.Abbreviation == "" : continue
    print(ps.Abbreviation)

    filter_name_pos = "АПТ {}".format(ps.Abbreviation)
    filter_name_neg = "АПТ {} НЕ".format(ps.Abbreviation)
    print(filter_name_pos)
    print(filter_name_neg)

    print(1)

    prf_pos = ParameterFilterRuleFactory.CreateContainsRule(param_id, ps.Abbreviation, True)

    filt_rule_pos = ElementParameterFilter(prf_pos)

    

    filt_rule_neg = ElementParameterFilter(
                            ParameterFilterRuleFactory.CreateNotContainsRule(param_id, ps.Abbreviation, True))
    
    print(2)
    
    param_filter_pos = ParameterFilterElement.Create(doc, 
                    filter_name_pos, 
                    filt_categories, 
                    filt_rule_pos
                     )
    
tr.Commit()

