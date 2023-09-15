#  coding: utf-8 


from Autodesk.Revit import *
from Autodesk.Revit.DB import *
import Autodesk.Revit.Exceptions
import System 
import clr

import math, sys
import clr

import re

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

	
import dm_connect_2 as dm
import dm_nearest_geometry as dm1

reload(dm)	
reload(dm1)

print("dm61_split_systems.py")

import re

"""
***************************************************************
* Загружаем список систем и смотрим, в каких системах 
* сколько спринклеров
* 
***************************************************************
"""

def count_sprinklers(s) :
    spr_val = int(bic.OST_Sprinklers)
    spr_count = 0 
    for e in s.Elements :
        if e.Category.Id.IntegerValue == spr_val :
            spr_count += 1
        else :
            print(e.Name)
    return spr_count


def get_large_pipes(s, min_d = 150 * dut) :
    res = []
    for e in s.PipingNetwork :
        if type(e) != Plumbing.Pipe :
            continue
        if e.Diameter < min_d : continue
        res.append(e)
    return res

def get_end_pipe()

        

    

fc = FilteredElementCollector(doc).OfCategory(bic.OST_PipingSystem).WhereElementIsNotElementType().ToElements()

for s in fc :
    print(s.Name)

    if s.Name == "В21с-1 3" :
        print(100*"-")
        sprinklers_num = count_sprinklers(s)
        
        break

from collections import Counter

big_pipes = get_large_pipes(s)
print(len(big_pipes))

print(sprinklers_num)
