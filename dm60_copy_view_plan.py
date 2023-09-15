#  coding: utf-8

#import dm_connect_pipe

import dm_nearest_geometry as dm1
import dm_connect_2 as dm
from Autodesk.Revit.DB import IFC as ifc
import NetTopologySuite.Geometries as nts_geom
import NetTopologySuite as nts
import System
import math

from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math
import sys
import clr
import System
from System.Collections.Generic import IList, List
from dm_connect_pipe import get_nearest_end_connector

clr.AddReferenceToFileAndPath(
    r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
clr.AddReferenceToFileAndPath(
    r"C:\Program Files\Autodesk\Revit 2021\RevitAPIIFC.dll")

lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path:
    sys.path.append(lib_path)


reload(dm)
reload(dm1)
check_print = True

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

pi2 = math.pi * 2

dut = 0.0032808398950131233


bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType

print("d60_copy_view_plan")

class dmCommandNewPlan(object) :
    def __init__(self, elevations, name_temp = "В_{:+0.3f} до {:+0.3f}", 
                        view_depth=0 * dut, 
                        cut_plane=1000*dut, 
                        top_level=3000 *dut) :
        self.elevations = elevations
        print("Уровни")
        print(self.elevations)
        self.uidoc = __revit__.ActiveUIDocument
        self.doc = self.uidoc.Document
        self.av = self.uidoc.ActiveView
        self.view_depth = view_depth
        self.cut_plane = cut_plane
        self.top_level = top_level
        self.name_temp = name_temp
        print(self.av.Name)

    def create_plans(self) :
        
        with dm.trans(self.doc) :
            for l in self.elevations :
                view_base_elevation = self.av.GenLevel.Elevation
                bottom_l = l - view_base_elevation 
                top_l = l + self.top_level - view_base_elevation
                cut_l = l+self.cut_plane - view_base_elevation

                new_view_id = ElementTransformUtils.CopyElement(self.doc, self.av.Id, XYZ.Zero)[0]
                new_view = self.doc.GetElement(new_view_id)
                new_name = self.name_temp.format(bottom_l/dut/1000, top_l/dut/1000)

                i_break =  0
                new_name_base = new_name
                while True :
                    if i_break > 100 : break
                    i_break += 1
                    try :
                        new_view.Name =  new_name
                        break
                    except :
                        print("ошибка имени пробуем другое имя")
                        new_name = "{}_копия {}".format(new_name_base, i_break)
                         

                view_range = new_view.GetViewRange()

                view_range.SetOffset(PlanViewPlane.TopClipPlane, top_l)
                view_range.SetOffset(PlanViewPlane.ViewDepthPlane, bottom_l)
                view_range.SetOffset(PlanViewPlane.BottomClipPlane, bottom_l)
                view_range.SetOffset(PlanViewPlane.CutPlane, cut_l)

                new_view.SetViewRange(view_range)

                print(new_name)


        pass






