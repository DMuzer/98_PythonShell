#  coding: utf-8 

#import dm_connect_pipe

import System
import math

from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math, sys
import clr
import System
from System.Collections.Generic import IList, List
from dm_connect_pipe import get_nearest_end_connector

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
check_print=True

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

pi2 = math.pi * 2

dut = 0.0032808398950131233


bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType

print("d57_work_section_create")

class dm_WorkSectionCreation() :
    def __init__(self, pipe =None, uidoc = None, doc  = None, ViewTypeId = None) :
        self.pipe = pipe
        if uidoc :
            self.uidoc = uidoc
        else :
            self.uidoc = uidoc
        if doc :
            self.doc = doc
        else :
            self.doc = None  

        
        if type(ViewTypeId) == int :
            self.ViewTypeId = ElementId(ViewTypeId)
        else :
            self.ViewTypeId = ViewTypeId

        self.ViewType = self.doc.GetElement(self.ViewTypeId)
        

    def Pipe_pickup(self) :
        pipe_ref = self.uidoc.Selection.PickObject(OT.Element)
        self.pipe = self.doc.GetElement(pipe_ref)
        return self.pipe 

    
    def Create(self) :
        try :
            lc = self.pipe.Location.Curve
            p1 = lc.GetEndPoint(0)
            p2 = lc.GetEndPoint(1)
            d = lc.Direction
            d = XYZ(d.X, d.Y, 0).Normalize()
            
            self.level = self.pipe.ReferenceLevel

            self.elevation = self.level.Elevation

            bottom = self.elevation - 1000 * dut
            top = max(p1.Z, p2.Z) + 1000 * dut 

            w = (p2 - p1).GetLength() * 1.3 + 5000 * dut
            h = top - bottom

            rot_trans = Transform.CreateRotation(XYZ.BasisZ, -math.pi / 2)
            dn = rot_trans.OfVector(d)

            pntMin = XYZ(-w / 2, -h / 2, -1)
            pntMax = XYZ(w  / 2 ,  h / 2, 1)

            origin = XYZ((p2.X+p1.X)*0.5, (p2.Y+p1.Y)*0.5, (top+bottom) * 0.5)

            viewTransform = Transform.Identity
            viewTransform.BasisZ = dn.Normalize()
            viewTransform.BasisX = d
            viewTransform.BasisY = XYZ.BasisZ
            viewTransform.Origin = origin

            
            bb = BoundingBoxXYZ()
            bb.Min = pntMin
            bb.Max = pntMax 
            bb.Enabled = True 
            
            bb.Transform = viewTransform
            
            
            with dm.trans(doc) :
                new_view = ViewSection.CreateSection(self.doc, self.ViewType.Id, bb)

            self.uidoc.ActiveView = new_view
        except Exception as ex:
            print("ошибка")
            print(ex.args)


    def CreateNormalSection(self, new_name = None) :
        """
        ***************************************************************
        * СОЗДАНИЕ РАЗРЕЗА ПЕРПЕНДИКУЛЯРНОГО ТРУБЕ
        * 
        * 
        ***************************************************************
        """
        lc = self.pipe.Location.Curve
        p1 = lc.GetEndPoint(0)
        p2 = lc.GetEndPoint(1)
        d = lc.Direction

        pnt = self.uidoc.Selection.PickPoint()
        pnt_proj = lc.Project(pnt).XYZPoint


        self.level = self.pipe.ReferenceLevel
        self.elevation = self.level.Elevation

        bottom = self.elevation - 1000 * dut
        top = max(p1.Z, p2.Z) + 1000 * dut 

        w = 5000 * dut
        h = top - bottom

        rot_trans = Transform.CreateRotation(XYZ.BasisZ, math.pi / 2)
        dn = rot_trans.OfVector(d)

        pntMin = XYZ(-w / 2, -h / 2, -1)
        pntMax = XYZ(w  / 2 ,  h / 2, 1)

        origin = XYZ(pnt_proj.X, pnt_proj.Y, (top+bottom) * 0.5)

        viewTransform = Transform.Identity
        viewTransform.BasisZ = d
        viewTransform.BasisX = dn 
        viewTransform.BasisY = XYZ.BasisZ
        viewTransform.Origin = origin

        bb = BoundingBoxXYZ()
        bb.Min = pntMin
        bb.Max = pntMax 
        bb.Enabled = True 
        bb.Transform = viewTransform

        with dm.trans(doc) :
            new_view = ViewSection.CreateSection(self.doc, self.ViewType.Id, bb)
            if new_name :
                new_view.Name = new_name

        self.uidoc.ActiveView = new_view

        
        

