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

print("d58_pipe_bypass")

av = uidoc.ActiveView
vud = av.ViewDirection

if not av.SketchPlane :
    pl1 = Plane.CreateByNormalAndOrigin(av.ViewDirection, av.Origin,)
    with dm.trans(doc) :
        sk_pl = SketchPlane.Create(doc, pl1)
        av.SketchPlane = sk_pl

pipe_ref = uidoc.Selection.PickObject(OT.Element)
pipe = doc.GetElement(pipe_ref)

p1_ = uidoc.Selection.PickPoint()
p2_ = uidoc.Selection.PickPoint()
p3_ = uidoc.Selection.PickPoint()

plc = pipe.Location.Curve
pdir = plc.Direction

p1 = plc.Project(p1_).XYZPoint
p2 = plc.Project(p2_).XYZPoint
p3 = plc.Project(p3_).XYZPoint

v3 = p3_- p3
v3ud = vud.DotProduct(v3) * vud
v3pd = pdir.DotProduct(v3) * pdir

v3n = v3 - v3ud - v3pd

ptr_1 = p1 
ptr_2 = p1 + v3n
ptr_3 = p2 + v3n
ptr_4 = p2

rl1 = Line.CreateBound(ptr_1, ptr_2)
rl2 = Line.CreateBound(ptr_2, ptr_3)
rl3 = Line.CreateBound(ptr_3, ptr_4)


points_ = [p1, p2, p3, ptr_1, ptr_2, ptr_3,ptr_4]
points =[]

for _p in points_ :
    _p1 = Point.Create(_p)
    points.append(_p1)

shapes = points + [
    rl1,
    rl2,
    rl3,
]

shapes_a = System.Array[GeometryObject](shapes)
with dm.trans(doc) :
    # ds = DirectShape.CreateElement(doc, ElementId(bic.OST_GenericModel))
    # ds = ds.SetShape(shapes_a)

    pipe2_id = Plumbing.PlumbingUtils.BreakCurve(doc, pipe.Id, p1)
    pipe2 = doc.GetElement(pipe2_id)

    if pipe.Location.Curve.Distance(p2) < pipe2.Location.Curve.Distance(p2) :
        pipe, pipe2 = pipe2, pipe

    pipe3_id = Plumbing.PlumbingUtils.BreakCurve(doc, pipe2.Id, p2)
    pipe3 = doc.GetElement(pipe3_id)

    if pipe2.Location.Curve.Distance(p1) > pipe3.Location.Curve.Distance(p1) :
        pipe2, pipe3 = pipe3, pipe2

    pipe_c1_id = ElementTransformUtils.CopyElement(doc, pipe2.Id, XYZ.Zero)[0]
    pipe_c2_id = ElementTransformUtils.CopyElement(doc, pipe2.Id, XYZ.Zero)[0]
    pipe_c3_id = ElementTransformUtils.CopyElement(doc, pipe2.Id, XYZ.Zero)[0]

    pipe_c1 = doc.GetElement(pipe_c1_id)
    pipe_c2 = doc.GetElement(pipe_c2_id)
    pipe_c3 = doc.GetElement(pipe_c3_id)

    pipe_c1.Location.Curve = rl1 
    pipe_c2.Location.Curve = rl2
    pipe_c3.Location.Curve = rl3

    c_11, c_12 = get_nearest_end_connector(pipe, ptr_1), get_nearest_end_connector(pipe_c1, ptr_1)
    c_21, c_22 = get_nearest_end_connector(pipe_c1, ptr_2), get_nearest_end_connector(pipe_c2, ptr_2)
    c_31, c_32 = get_nearest_end_connector(pipe_c2, ptr_3), get_nearest_end_connector(pipe_c3, ptr_3)
    c_41, c_42 = get_nearest_end_connector(pipe_c3, ptr_4), get_nearest_end_connector(pipe3, ptr_4)

    doc.Create.NewElbowFitting(c_11, c_12)
    doc.Create.NewElbowFitting(c_42, c_41)
    doc.Create.NewElbowFitting(c_21, c_22)
    elb3 = doc.Create.NewElbowFitting(c_32, c_31)

    c_51 = get_nearest_end_connector(elb3, ptr_3)

    #c_51.DisconnectFrom(c_31)
    #c_51.ConnectTo(c_31)

    



    doc.Delete(pipe2.Id)













