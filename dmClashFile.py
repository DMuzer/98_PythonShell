
#  coding: utf-8 

#import dm_connect_pipe

import System
import math
import itertools
import collections
import random
import sys
import re

lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
	sys.path.append(lib_path)
from bs4 import BeautifulSoup as bs

from Autodesk.Revit.DB import *
from Autodesk.Revit import DB
import clr
from pathlib import Path



uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

pi2 = math.pi * 2

dut = 0.0032808398950131233

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
dsid = ElementId(bic.OST_GenericModel)
from contextlib import contextmanager

class WarningSwallower(IFailuresPreprocessor):
    def PreprocessFailures(self, failuresAccessor):
        from System.Collections.Generic import List
        #print("Обработка ошибки")
        try :
            fail_list = List[FailureMessageAccessor]()
            #print("обрабатываем дальше")
            fail_acc_list = list(failuresAccessor.GetFailureMessages().GetEnumerator())
            #print("Количество ошибок {}".format(len(fail_acc_list)))
            for failure in fail_acc_list:
                #print("Предупреждение {0}\n with id:".format(failure))
                failuresAccessor.DeleteWarning(failure)
            return FailureProcessingResult.Continue
        except Exception as ex :
            print("Ошибка во время ошибки\n{}".format(ex))
            return FailureProcessingResult.Continue

@contextmanager
def trans(doc, a="труба") :
    #print("новый тип транзакций  обработкой ошибки")

    tr = Transaction(doc)
    tr.Start(a)
    options = tr.GetFailureHandlingOptions()
    options.SetFailuresPreprocessor(WarningSwallower())
    tr.SetFailureHandlingOptions(options)
    try :	
        yield tr
    except Exception as ex:
        print("Ошибка транзакции\n{}".format(ex))
        
    finally :
        
        tr.Commit()

def create_ds(l, category = None) :

    olist = []
    if category is None :
        catid = dsid
    else :
        catid = dsid

    # print(type(l))

    if not hasattr(l, "__iter__") :
        olist = [l]
    else :
        olist = list(l)
    shapes = []

    while len(olist) > 0 :
        e = olist.pop()
        if isinstance(e, Face) :
            # print("face")
            olist.extend(e.GetEdgesAsCurveLoops())
        elif isinstance(e, XYZ) :
            shapes.append(Point.Create(e))
        elif hasattr(e, "__iter__") :
            olist.extend(list(e))
            '''
            elif type(e) == geoms.Polygon :
                olist.extend(get_CurveLoopsFromPolygon(e))
            '''
        elif isinstance(e, GeometryObject) :
            shapes.append(e)

    shapes_a = System.Array[GeometryObject](shapes)

    try :
        ds = DirectShape.CreateElement(doc, catid)
        ds.SetShape(shapes_a)
    except :
        with trans(doc) :
            ds = DirectShape.CreateElement(doc, catid)
            ds.SetShape(shapes_a)

    return ds

def set_color(e, r=0,g=0,b=0, a=0, view = None) :
    color = Color(r,g,b)
    if not view :
        view = uidoc.ActiveView
    ogs = OverrideGraphicSettings()
    ogs.SetProjectionLineColor(color)
    ogs.SetSurfaceTransparency(a)
    ogs.SetSurfaceForegroundPatternColor(color)
    ogs.SetSurfaceForegroundPatternId(ElementId(19))
    ogs.SetProjectionLineColor(color)
    ogs.SetCutLineColor(color)

    try :
        view.SetElementOverrides(e.Id, ogs)
    except Exception as ex:
        #print("Исключение при задании цвета set_color")
        #print(ex)
        try :
            tr = Transaction(doc)
            tr.Start("set color")
            view.SetElementOverrides(e.Id, ogs)
            
            tr.Commit()
            print("поправлено")
        except :
            pass

def get_sect_type() :
    def test(vt) :
        if not re.match(".*разрез.*", Element.Name.GetValue(vt), re.I) : return False
        if not re.match(".*рабочий.*", Element.Name.GetValue(vt), re.I) : return False
        if not re.match(".*увязка.*", Element.Name.GetValue(vt), re.I) : return False
        return True
    fc = FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
    res = [vt for vt in fc if test(vt)]
    print(res)
    if len(res) > 0 :
        return res[0]
    
    else :
        print("Не удалось найти шаблон разреза")
        res = [vt for vt in fc]
        return res[-1]
def en(e) :
	return Element.Name.GetValue(e)
	
def get_level(p) :
	fc = FilteredElementCollector(doc).OfClass(Level).ToElements()
	res = max([l for l in fc if p.Z >= l.Elevation], key = lambda x : x.Elevation)
	return res
def get_level_above(p) :
	fc = FilteredElementCollector(doc).OfClass(Level).ToElements()
	res = min([l for l in fc if p.Z < l.Elevation], key = lambda x : x.Elevation)
	return res


def createPipeSection(pipe) :

	vt = get_sect_type()
	
	print(en(vt))
	
	lc = pipe.Location.Curve
	p1 = lc.GetEndPoint(0)
	p2 = lc.GetEndPoint(1)
	_dv = lc.Direction
	dv = XYZ(_dv.X, _dv.Y, 0).Normalize()
	
	rdirection = 0
	rtr = Transform.CreateRotation(XYZ.BasisZ, -math.pi/2)
	
	if not rdirection :
		dv = -dv
			
	dvn = rtr.OfVector(dv)
		
		
	
	
	w = (p2-p1).GetLength() * 1.3 + 5000 * dut
	
	
	p = (p1 + p2) * 0.5
	
	l = get_level(p)
	la = get_level_above(p)
	
	bottom = l.Elevation - 1000 * dut
	top = la.Elevation + 1000 * dut
	h = top - bottom
	
	pntMin = XYZ(-w/2, -h/2, -1)
	pntMax = XYZ(w/2, h/2, 1)
	
	origin = XYZ(p.X, p.Y, (top + bottom)/2)
	
	view_transform = Transform.Identity
	view_transform.BasisZ = dvn.Normalize()
	view_transform.BasisX = dv.Normalize()
	view_transform.BasisY = XYZ.BasisZ
	view_transform.Origin = origin
	
	bb = BoundingBoxXYZ()
	bb.Min = pntMin
	bb.Max = pntMax
	bb.Enabled = True
	print(1)
	bb.Transform = view_transform
	print(2)
	
	tr = Transaction(doc)
	tr.Start("create view")
	
	new_view = ViewSection.CreateSection(doc, vt.Id, bb)
	name = "Разрез по трубе id{}".format(pipe.Id)
	name1 = name 
	nn = 0 
	while True :
		try :
			new_view.Name = name1
			break
		except :
			nn += 1
			name1 = "{} {}".format(name, nn)
			if nn > 500 : break
	
	tr.Commit()
	return new_view



class dmClash(object) :
    def __init__(self, clash, doc=None, pref = "") :
        self.doc = doc
        self.clash = clash
        self.pref = pref 
        
    def _get_name(self) :
        return self.clash["name"]
        
    name = property(_get_name)
    
    def _get_pos(self) :
        return self.clash.pos3f
    pos = property(_get_pos)
    
    def _get_pos_xyz(self) :
        pos = self.pos
        x, y, z = float(pos['x']) * 1000 * dut, float(pos['y']) * 1000* dut, float(pos['z'])*1000 * dut
        return XYZ(x,y,z)
        
    pos_xyz = property(_get_pos_xyz)

    def _get_pos_transformed(self) :
        tt = self.doc.ActiveProjectLocation.GetTotalTransform()
        return tt.OfPoint(self.pos_xyz)
    
    pos_transformed = property(_get_pos_transformed)
    
    def _get_id1(self) :
        for oa in self.clash.find_all('clashobject')[0].find_all("objectattribute") :
            if oa.find("name").get_text() == "ID объекта" :
                return int(oa.find("value").get_text())

    def _get_id2(self) :
        for oa in self.clash.find_all('clashobject')[1].find_all("objectattribute") :
            if oa.find("name").get_text() == "ID объекта" :
                return int(oa.find("value").get_text())
    
    def _get_object1(self) :
        return 
    
    def _getElementType1(self) :
        for oa in self.clash.find_all('clashobject')[0].find_all("smarttags") :
            #print(oa.find("name").get_text())
            if oa.find("name").get_text() == "Элемент Имя" :
                    return oa.find("value").get_text()
    ElementType1 = property(_getElementType1)

  
    def _getElementType2(self) :
        for oa in self.clash.find_all('clashobject')[1].find_all("smarttags") :
            #print(oa.find("name").get_text())
            if oa.find("name").get_text() == "Элемент Имя" :
                    return oa.find("value").get_text()
	         
    
    ElementType2 = property(_getElementType2)

    def _getElementTypeName1(self) :
        for oa in self.clash.find_all('clashobject')[0].find_all("smarttag") :
            if oa.find("name").get_text() == "Элемент Тип" :
                typeN = oa.find("value").get_text()
                if typeN.StartsWith("Трубы:") :
                    return "Трубы"
                else :
                    return typeN
    ElementTypeName1 = property(_getElementTypeName1)

    def _getElementTypeName2(self) :
        for oa in self.clash.find_all('clashobject')[1].find_all("smarttag") :
            if oa.find("name").get_text() == "Элемент Тип" :
                typeN = oa.find("value").get_text()
                if typeN.StartsWith("Трубы:") :
                    return "Трубы"
                else :
                    return typeN
    ElementTypeName2 = property(_getElementTypeName2)

    def findDs(self) :
        fc = FilteredElementCollector(doc).OfClass(DirectShape).ToElements()
        guid = self.clash['guid']
        for ds in fc :
            if ds.LookupParameter("Марка").AsString() == guid :
                return ds
            
    def updateStatus(self) :
        ds = self.findDs()
        if not ds : return 
        p8 = ds.LookupParameter("О_Примечание")
        if p8 :
            v = p8.AsString()
            if v and len(p8.AsString()) > 0 : 
                print("{} оставляем существующий статус".format(self.name))
                return 
            tr = None
            if not doc.IsModifiable :
                tr = Transaction(doc, "Обновление статуса коллизии")
                tr.Start()
            p8.Set(self.clash['status'])
            print("{} обновлена".format(self.name))
            if tr : tr.Commit()

    def updatePosition(self) :
        ds = self.findDs()
        if not ds : return 
        p8 = ds.LookupParameter("DM_Пересечение_координаты")
        if p8 :
            tr = None
            if not doc.IsModifiable :
                tr = Transaction(doc, "Обновление координаты коллизии")
                tr.Start()
            pos = self.pos_transformed
            posStr = "{},{},{}".format(pos.X, pos.Y, pos.Z)
            p8.Set(posStr)
            print("{} обновлена".format(self.name))
            if tr : tr.Commit()


    def create_point(self, dist = 100 * dut) :
        from System.Collections.Generic import List
        solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)        

        pnt = self.pos_transformed
        p1 = pnt - XYZ(dist, dist, dist)
        p2 = p1 + XYZ(2*dist,0,0)
        p3 = p2 + XYZ(0, 2*dist, 0)
        p4 = p3 + XYZ(-2*dist,0,0)

        lines = CurveLoop.Create(List[Curve]([
            Line.CreateBound(p1, p2),
            Line.CreateBound(p2, p3),
            Line.CreateBound(p3, p4),
            Line.CreateBound(p4, p1)
        ]))

        box = GeometryCreationUtilities.CreateExtrusionGeometry(List[CurveLoop]([lines]),
                                                              XYZ.BasisZ,
                                                              2 * dist,
                                                              solid_opt)
        
        ds = create_ds(box)

        with trans(doc, "set collision point parameters") as tr :

            p1 = ds.LookupParameter("Марка")
            if p1 :
                p1.Set(self.clash["guid"])
            p2 = ds.LookupParameter("Наименование")
            if p2 :
                p2.Set(self.name)
            p3 = ds.LookupParameter("Комментарии")
            if p3 :
                p3.Set(self.pref)
            p4 = ds.LookupParameter("DM_Пересечение_id1")
            if p4 :
                p4.Set(self._get_id1())
            p5 = ds.LookupParameter("DM_Пересечение_id2")
            if p5 :
                p5.Set(self._get_id2())

            p6 = ds.LookupParameter("DM_Пересечение_Тип_объекта_1")
            if p6 :
                p6.Set(self.ElementTypeName1)
            p7 = ds.LookupParameter("DM_Пересечение_Тип_объекта_2")
            if p7 :
                p7.Set(self.ElementTypeName2)
            p8 = ds.LookupParameter("О_Примечание")
            if p8 :
                p8.Set(self.clash['status'])
            p9 = ds.LookupParameter("DM_Пересечение_Уровень")
            if p9 :
                p9.Set(self._getLevel().Name)

            print(pnt)


    def create_view3d(self, dist = 1500*dut, viewtype_name = None) :
        view_types = FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
        view_types_3D = {Element.Name.GetValue(vt) : vt for vt in view_types if vt.ViewFamily == ViewFamily.ThreeDimensional}
        
        view_type = None
        if viewtype_name :
            try :
                view_type = view_types_3D[viewtype_name]
            except :
                pass 
        if not view_type :
            view_type = view_types_3D.values()[-1]
            viewtype_name = Element.Name.GetValue(view_type)
       
        p1 = self.pos_transformed

        with trans(self.doc) :
            new_view = View3D.CreateIsometric(doc, view_type.Id)
            num = 1
            while True :
                try :
                    new_view.Name = "Р_В_{}_{}_{}".format(self.pref, self.name,num)
                    break
                except :
                    num += 1
                    if num > 1000 : break

            try :
                nparam = new_view.LookupParameter("Вид_Примечание")
                nparam.Set("{}_{}".format(self.pref,self.name))
            except :
                pass 
                    
            sbox = new_view.GetSectionBox()

            sbox.Min = p1 - XYZ(dist,dist,dist)
            sbox.Max = p1 + XYZ(dist,dist,dist)
            new_view.SetSectionBox(sbox)

            vp = p1 - 20 * XYZ.BasisX

            fd = XYZ.BasisX
            ud = XYZ.BasisZ


           
            vo = ViewOrientation3D(p1 - 20* XYZ(1,-1,-0.5).Normalize(), ud, fd)

            new_view.SetOrientation(vo)

        return new_view

    def create_view3d_copy(self, dist = 1500*dut, view=None) :
        
        p1 = self.pos_transformed

        fc = FilteredElementCollector(doc).OfClass(View3D).ToElements()

        def vname_test(x) :
            if not re.match(".*шаблон.*", x.Name, re.I) : return False
            if not re.match(".*3D.*",x.Name, re.I) : return False
            if not re.match(".*коллизии.*",x.Name, re.I) : return False
            return True
        
        v3ds = [p for p in fc if vname_test(p)]
        if len(v3ds) == 0 : 
            print("Не нашел шаблона")
            return 
        v3 = v3ds[0]

        with trans(self.doc) :
            #new_view = View3D.CreateIsometric(doc, view_type.Id)
            new_view_id = ElementTransformUtils.CopyElement(self.doc, v3.Id, XYZ.Zero)[0]
            new_view = self.doc.GetElement(new_view_id)
            num = 1
            while True :
                try :
                    new_view.Name = "Р_В_{}_{}_{}".format(self.pref, self.name,num)
                    break
                except :
                    num += 1
                    if num > 1000 : break

            try :
                nparam = new_view.LookupParameter("Вид_Примечание")
                nparam.Set("{}_{}".format(self.pref,self.name))

                p4 = new_view.LookupParameter("DM_Пересечение_id1")
                if p4 :
                    p4.Set(self._get_id1())
                p5 = new_view.LookupParameter("DM_Пересечение_id2")
                if p5 :
                    p5.Set(self._get_id2())

                p6 = new_view.LookupParameter("DM_Пересечение_Тип_объекта_1")
                if p6 :
                    p6.Set(self.ElementTypeName1)
                p7 = new_view.LookupParameter("DM_Пересечение_Тип_объекта_2")
                if p7 :
                    p7.Set(self.ElementTypeName2)

                p8 = new_view.LookupParameter("Вид_Подзаголовок")
                if p8 :
                    p8.Set(self.clash['status'])

            except Exception as ex: 
                print(ex)
                pass 
                    
            sbox = new_view.GetSectionBox()

            sbox.Min = p1 - XYZ(dist,dist,dist)
            sbox.Max = p1 + XYZ(dist,dist,dist)
            new_view.SetSectionBox(sbox)

            vp = p1 - 20 * XYZ.BasisX

            fd = XYZ.BasisX
            ud = XYZ.BasisZ


           
            #vo = ViewOrientation3D(p1 - 20* XYZ(1,-1,-0.5).Normalize(), ud, fd)

            #new_view.SetOrientation(vo)

        return new_view
    
    def create_planview(self) :
        p1 = self.pos_transformed

        fc = FilteredElementCollector(self.doc).OfClass(Level).ToElements()

        bl = min([l for  l in fc if p1.Z - l.Elevation >= 0], key = lambda x : p1.Z - l.Elevation)
        view_types = FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()


        view_types_plans = [vt for vt in view_types if vt.ViewFamily == ViewFamily.FloorPlan]
        floor_plan_type  = view_types_plans[-1]

        bmin = XYZ(p1.X - 50, p1.Y - 50, -10)
        bmax = XYZ(p1.X + 50, p1.Y + 50, +10)
        bb = BoundingBoxXYZ()
        bb.Min = bmin
        bb.Max = bmax

        with Transaction(doc,'Create Floor Plan') as t:
            t.Start()

            view = ViewPlan.Create(doc, floor_plan_type.Id, bl.Id)
            num = 1
            while True :
                try :
                    view.Name = "Р_П_{}_{}_{}".format(self.pref, self.name,num)
                    break
                except :
                    num += 1
                    if num > 1000 : break
            view.CropBoxActive = True
            view.CropBoxVisible = True 
            view.CropBox = bb
            try :
                nparam = view.LookupParameter("Вид_Примечание")
                nparam.Set("{}_{}".format(self.pref,self.name))

                p4 = view.LookupParameter("DM_Пересечение_id1")
                if p4 :
                    p4.Set(self._get_id1())
                p5 = view.LookupParameter("DM_Пересечение_id2")
                if p5 :
                    p5.Set(self._get_id2())

                p6 = view.LookupParameter("DM_Пересечение_Тип_объекта_1")
                if p6 :
                    p6.Set(self.ElementTypeName1)
                p7 = view.LookupParameter("DM_Пересечение_Тип_объекта_2")
                if p7 :
                    p7.Set(self.ElementTypeName2)
                p8 = view.LookupParameter("Вид_Подзаголовок")
                if p8 :
                    p8.Set(self.clash['status'])
            except :
                pass 

            t.Commit()

        return view 
    def _getLevel(self) :
        p1 = self.pos_transformed  
        fc = FilteredElementCollector(self.doc).OfClass(Level).ToElements()
        bl = min([l for  l in fc if p1.Z - l.Elevation >= 0], key = lambda x : p1.Z - x.Elevation)
        return bl
    
    def create_planview_copy(self) :
        """
        ***************************************************************
        * Создание плана для отработки коллизи из копии
        * план для копии должен иметь имя которое содержит План шаблон коллизии
        * и соответственно должен быть план с соответствующим уровнем
        ***************************************************************
        """
        p1 = self.pos_transformed
        self.p1 = p1

        fc = FilteredElementCollector(self.doc).OfClass(Level).ToElements()

        bl = min([l for  l in fc if p1.Z - l.Elevation >= 0], key = lambda x : p1.Z - x.Elevation)
        view_types = FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
        print(f"найденный уровень : {bl.Name}")
        self.bl = bl


        view_types_plans = [vt for vt in view_types if vt.ViewFamily == ViewFamily.FloorPlan]
        # floor_plan_type  = view_types_plans[-1]

        fc = FilteredElementCollector(doc).OfClass(ViewPlan).ToElements()

        def pname_test(x) :
            if not re.match(".*шаблон.*", x.Name, re.I) : return False
            if not re.match(".*план.*",x.Name, re.I) : return False
            if not re.match(".*коллизии.*",x.Name, re.I) : return False
            return True
        plans = [p for p in fc if pname_test(p)]
        plans = [p for p in plans if p.GenLevel.Elevation < p1.Z]
        self.plans = plans
        if len(plans) == 0 : return 
        pplan = max(plans, key = lambda x : x.GenLevel.Elevation)
        bl = pplan.GenLevel
        self.bl = pplan.GenLevel
        self.pplan = pplan

        bmin = XYZ(p1.X - 20, p1.Y - 20, -10)
        bmax = XYZ(p1.X + 20, p1.Y + 20, +10)
        bb = BoundingBoxXYZ()
        bb.Min = bmin
        bb.Max = bmax
        
        topElevation = round((p1.Z -  pplan.GenLevel.Elevation + 500 * dut) / 100 / dut) * 100 * dut
        cutElevation = min(topElevation-100*dut, 1200 * dut)
        self.topElevation = topElevation
        with Transaction(doc,'Create Floor Plan') as t:
            t.Start()

            #view = ViewPlan.Create(doc, floor_plan_type.Id, bl.Id)
            viewid = ElementTransformUtils.CopyElement(self.doc, pplan.Id, XYZ.Zero)[0]
            view = self.doc.GetElement(viewid)

            num = 1
            while True :
                try :
                    view.Name = "Р_П_{}_{}_{}".format(self.pref, self.name,num)
                    break
                except :
                    num += 1
                    if num > 1000 : break
            view.CropBoxActive = True
            view.CropBoxVisible = True 
            view.CropBox = bb
            print("Устанавливаем плоскости")


            planViewRange = view.GetViewRange()
            self.planViewRange = planViewRange
            #print(f"Нижнее смещение = {planViewRange.GetOffset(PlnaViewPlane.BottomPlane)}\nСмещение секущей плоскости {} ")
            planViewRange.SetOffset(PlanViewPlane.CutPlane, cutElevation)
            planViewRange.SetOffset(PlanViewPlane.TopClipPlane, topElevation)
            view.SetViewRange(planViewRange)
            try :
                nparam = view.LookupParameter("Вид_Примечание")
                nparam.Set("{}_{}".format(self.pref,self.name))
                p4 = view.LookupParameter("DM_Пересечение_id1")
                if p4 :
                    p4.Set(self._get_id1())
                p5 = view.LookupParameter("DM_Пересечение_id2")
                if p5 :
                    p5.Set(self._get_id2())

                p6 = view.LookupParameter("DM_Пересечение_Тип_объекта_1")
                if p6 :
                    p6.Set(self.ElementTypeName1)
                p7 = view.LookupParameter("DM_Пересечение_Тип_объекта_2")
                if p7 :
                    p7.Set(self.ElementTypeName2)
                p8 = view.LookupParameter("Вид_Подзаголовок")
                if p8 :
                    p8.Set(self.clash['status'])

            except :
                pass          
            t.Commit()
        return view
    
    def createPipeSection(self) :
        elementId =self.getThisDocClashElement()
        element = self.doc.GetElement(elementId)
        if type(element) != Plumbing.Pipe :
            return
        newSection = createPipeSection(element)

        tr = Transaction(self.doc, "rename section")
        tr.Start()
        num = 1
        while True :
            try :
                newSection.Name = "Р_П_{}_{}_{}".format(self.pref, self.name,num)
                break
            except :
                num += 1
                if num > 1000 : break

        try :
            nparam = newSection.LookupParameter("Вид_Примечание")
            nparam.Set("{}_{}".format(self.pref,self.name))
            nparam = newSection.LookupParameter("Вид_Сортировка")
            nparam.Set("Увязка")

            p4 = newSection.LookupParameter("DM_Пересечение_id1")
            if p4 :
                p4.Set(self._get_id1())
            else :
                print("DM_Пересечение_id1 ошибка установки параметра")
            p5 = newSection.LookupParameter("DM_Пересечение_id2")
            if p5 :
                p5.Set(self._get_id2())

            p6 = newSection.LookupParameter("DM_Пересечение_Тип_объекта_1")
            if p6 :
                p6.Set(self.ElementTypeName1)
            p7 = newSection.LookupParameter("DM_Пересечение_Тип_объекта_2")
            if p7 :
                p7.Set(self.ElementTypeName2)
            p8 = newSection.LookupParameter("Вид_Подзаголовок")
            if p8 :
                p8.Set(self.clash['status'])


        except Exception as ex:
            print("ошибка при создании разреза")
            print(ex)
            pass 
        tr.Commit()

        return newSection
    
    def getThisDocClashElement(self) :
        def match(s, docName) :
            for smartTag in s.find_all("smarttag") :
                if smartTag.find("name").string == "Элемент Файл источника" :
                    if docName.startswith(Path(smartTag.value.string).stem) :
                        return True
        def objectIdTag(element) :
            for smartTag in element.find_all("smarttag") :
                if smartTag.find("name").string == "ID объекта Значение" :
                    return smartTag.value.string

        return ElementId(self._get_id1())
        docName = Path(self.doc.PathName).name
        for element in self.clash.find_all("clashobject") :
            if match(element, docName) :
                return ElementId(int(objectIdTag(element)))		
        return
    clashElementId = property(getThisDocClashElement)


class dmClashFile(object) :
    def __init__(self, fn, pref = "", doc = None) :
        self.pref = pref 
        if doc :
            self.doc = doc
        else :
            self.doc = uidoc.Document
        self.fn = fn
        with open(self.fn, encoding = 'utf') as f:
            #self.s = bs(f.read().decode("utf-8"), from_encoding="utf-8")
            self.s = bs(f.read())
            
    
    def _get_clashes(self) :
        return [dmClash(cr, self.doc, pref = self.pref) for cr in self.s.find_all("clashresult")]
    clashes = property(_get_clashes)
    def _get_num_clashes(self) :
        return len(self.s.find_all("clashresult"))
    num_clashes = property(_get_num_clashes)

    def __repr__(self) :
        s = "Файл обработки {}\n префикс {}\nколичество коллизий {}".format(self.fn, 
                                                                            self.pref, 
                                                                            self.num_clashes)
        return s

    