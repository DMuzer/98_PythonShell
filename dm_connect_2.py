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

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
import NetTopologySuite as nts
from NetTopologySuite.Geometries import *
import NetTopologySuite.Geometries as geoms

from dm_connect_pipe import *

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

pi2 = math.pi * 2

dut = 0.0032808398950131233

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
dsid = ElementId(bic.OST_GenericModel)

def get_contour_length(cls) :
    """
    ***************************************************************
    * Возвращает общую длину контура
    * вход cl - список CurveLoops
    * 
    ***************************************************************
    """
    res = 0
    for cl in cls :
        res += cl.GetExactLength()
    return res 
        


def set_workset(e, ws, trans_ = None) :
    """
    ***************************************************************
    * Устанавливаем рабочий набор для элемента
    * Входные данные 
    * e - элемент
    * ws - рабочий набор в виде элемента ревит.
    * trans_ - транзакция. если пустой, то функция создаст транзакцию и выполнит ее
    *           если не пустой, то она выполнится в контексте действующей транзакции.
    ***************************************************************
    """
    try : 
        p = e.Parameter[BuiltInParameter.ELEM_PARTITION_PARAM]
        if p :
            if not trans_ :
                with trans(e.Document) :
                    p.Set(ws.Id.IntegerValue)
            else :
                p.Set(ws.Id.IntegerValue)
    except Exception as ex :
        print("Ошибка set_workset")
        print(ex)
        raise

def get_sprinkler_types() :
    ec = FilteredElementCollector(doc).OfCategory(bic.OST_Sprinklers).WhereElementIsElementType().ToElements()
    return {en(e_) : e_.Id for e_ in ec}

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
        elif type(e) == geoms.Polygon :
            olist.extend(get_CurveLoopsFromPolygon(e))
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



def get_parametes_values(el) :
    pass


def draw_model_loop(cl) :
    """
    Отрисовка curve_loop в модели
    """
    doc = __revit__.ActiveUIDocument.Document
    pl = cl.GetPlane()


    with trans(doc) :
        sk_pl = SketchPlane.Create(doc, pl)
        for c in cl :
            doc.Create.NewModelCurve(c, sk_pl)




from System.Collections.Generic import IList, List

def get_covering_zones(pg, mp, prot_radius, raw_data = False) :

    """
    Вычисление зон орошения для спринклеров.
    Вызывается внешняя python программа
    входные данные:
    pg - shapely Polygon или NetTopologySuite.Geometries.
    """

    fn = r"D:\18_проектирование\get_covering_zones.py"

    args = ['python', fn]

    import subprocess



    proc = subprocess.Popen(args, stdout = subprocess.PIPE, stdin = subprocess.PIPE, stderr = subprocess.PIPE)

    try :
        data2 = "{}\n {} \n {}\n".format(pg.AsText(), mp.AsText(), prot_radius).encode()
        print("Это данные на входе: \n {} \n\n".format(data2))
        out, errs = proc.communicate(data2)
        res = out.decode(errors='ignore')
        # print("Ошибка : \n{errs.decode(errors='ignore')}")

    except Exception as ex :
        print("Завершение с ошибкой\n{}".format(ex))

    print(res)
    pgs = []
    wkt = nts.IO.WKTReader()
    for s in res.split("\n") :
        try :
            plg = wkt.Read(s)
            
            pgs.append(plg)
        except Exception as ex:
            print("Ошибка при преобразовании\n{}\n".format(ex))
            pass

    if raw_data :
        return res 
    else :
        return pgs 


def CorrectCurveLoop(cloop) :
  
    new_loop = CurveLoop()

    # create_ds(cloop)

    cl = list(cloop)

    p1 = cl[0].GetEndPoint(0)
    p1_ = p1
    points =  [p1]
    
    for l in cl :
        if isinstance(l, Line) :
            p2 = l.GetEndPoint(1)
            points.append(p2)
        elif isinstance(l, Arc) :
            pnts = list(l.Tessellate())
            for p3 in pnts[:] :
                points.append(p3)

    p1 = points[0]
    points1 = []
    for p2 in points[1:] :
        if p1.DistanceTo(p2) > 0.01 :
            points1.append(p1)
            p1 = p2 


    p1 = points1[0]
    p2 = points1[-1]


    if not p1.IsAlmostEqualTo(p2) :
        if p1_.DistanceTo(p2) < 0.01 :
            points1.pop()

        points1.append(p1)

    for p1, p2 in zip(points1[:-1], points1[1:]) :
        l1 = Line.CreateBound(p1, p2)
        new_loop.Append(l1)

    # create_ds(points1)

    return new_loop

def CorrectCurveLoops(curve_loops) :
    loops = list(curve_loops)
    res_ = []
    

    for cl in loops :
        cl_ = CorrectCurveLoop(cl)
        res_.append(cl_)
    
    res = System.Array[CurveLoop](res_)
    return res


            

def AnalyzeCurveLoops(cloops) :
    from collections import Counter
    print("Анализ CurveLoops")

    print("Тип объекта : {}".format(cloops))
    print("Количество кривых в массиве: {}".format(len(cloops)))

    print("Анализ замкнутых цепей")

    for n, cl in enumerate(cloops) :
        print(80*"*")
        print("Цепь {}\n".format(n))
        print("Количество элементов в цепи {}".format(cl.NumberOfCurves()))
        types = Counter()
        for l in cl :
            types[type(l)] += 1
        print(types)

        

        lenghts = [l.Length for l in cl]

        print("Минимальная длина {}".format(min(lenghts)/dut))

        cll = list(cl)
        l0 = cll[0]
        ll = cll[-1]

        p1 = l0.GetEndPoint(0)
        pn = ll.GetEndPoint(1)
        print("Первая точка {} {} {}".format(p1.X, p1.Y, p1.Z))
        print("Последня точка {} {} {}".format(pn.X, pn.Y, pn.Z))

        if p1.DistanceTo(pn) < 0.0000001 :
            print("Цепь замкнута")

        
        for l1, l2 in zip(cll[:-1], cll[1:]) :
            p1 = l1.GetEndPoint(1)
            p2 = l2.GetEndPoint(0)

            d = p1.DistanceTo(p2)
            if d > 0.00001 :
                print("Точки последовательных линий не совпадают расстояние : {}".format(d/dut))
            
            
        

        print(80*"*")

def get_sprinkler_covering_area(pg, 
                            p, 
                            prot_radius, 
                            show = False) :
    """
    ***************************************************************
    * ВЫЧИСЛЕНИЕ ЗОНЫ ПОКРЫТИЯ СПРИНКЛЕРА С УЧЕТОМ ПРЕГРАД
    * на вход подается фигура границ помещения на выходе -
    * фигура - зоны покрытия спринклера при этом вычисляются мервые зоны
    ***************************************************************
    """

    pg = pg.Buffer(-100*dut).Buffer(200*dut).Buffer(-100*dut)

    try :
        try :
            try :
                spr_zone = p.Buffer(prot_radius)
                zone_border = spr_zone.ExteriorRing

                try :
                
                    barriers = pg.Intersection(spr_zone)
                except Exception as ex:

                    print("ошибка при вычислениии пересечения\n{}\n{}".format(ex, ex.clsException))
                    raise
                barriers_boundary = barriers.Boundary
            except :
                print('первый блок')
                raise
            
            
            pnts = zone_border.Coordinates
            
            
            lines = []
            try :
                int_pnt = geoms.MultiPoint(System.Array[geoms.Point]([]))
            except :
                print("Ошибка при формировании int_pnt")
                raise
            int_pnt1 = []
        except Exception as ex:
            print("Ошибка при формировании точек до цикла \n{}".format(ex))
            raise
        
        for p1 in pnts :
            try :
                l1 = geoms.LineString(System.Array[geoms.Coordinate]([p.Coordinate, p1]))
                lines.append(l1)
                
                int1 = barriers_boundary.Intersection(l1)

                n_pnt = geoms.Point(nts.Operation.Distance.DistanceOp(int1, p).NearestPoints()[0])
                
                #n_pnt = shapely.ops.nearest_points(int1, p)[0]
                
                int_pnt = int_pnt.Union(n_pnt)
                int_pnt1.append(n_pnt)
            except :
                print('ошибка в цикле')
                raise

        try :
            lr_coords = System.Array[geoms.Coordinate]([p_.Coordinate for p_ in int_pnt1])
            lr = geoms.LinearRing(lr_coords)    
            res = geoms.Polygon(lr)
        except Exception as ex :
            print("Ошибка при формировании полигона".format(ex))
            raise

    except Exception as ex :
        print("возникла ошибка при вычислении зон покрытия\n{}".format(ex))
    
    return res

def draw_polygon_boundaries(pgs, view = None) :
    try : 
        if not view :
            view = last_app.sprinkler_view

        print(view.Name)
        
        doc = view.Document

        if pgs.NumGeometries < 2 :
            pgs = geoms.Polygon(System.Array[Polygon]([pgs]))

        with trans(doc) :
            for ls in pgs.Boundary :
                coords = ls.Coordinates
                i1 = 0
                i2 = 1
                while i2 < len(coords) :
                    c1 = coords[i1]
                    c2 = coords[i2]
                    try :
                        p1 = XYZ(c1.X, c1.Y,0)
                        p2 = XYZ(c2.X, c2.Y,0)
                        l1 = Line.CreateBound(p1, p2)
                
                        
                        doc.Create.NewDetailCurve(view, l1)


                        i1 = i2
                    except Exception as ex:
                        print("Ошибка при рисовании линии")
                        # print(ex)
                        # print(ex.clsException)
                        
                        pass
                    i2 += 1
            

    except :
        print("Ошибка draw_polygon_boundaries")
        raise
  



def draw_polygon(pgs, view=None, fregion_type=None) :
    print("Попытка вывода полигона")
    if not view :
        view = last_app.sprinkler_view
    if not fregion_type :
        fregion_type = last_app.sprinkler_plan_area_type

    

    # if pgs.NumGeometries < 2 :
    if isinstance(pgs, geoms.Polygon) :
        pgs = geoms.MultiPolygon(System.Array[geoms.Polygon]([pgs]))
    
    lrs = []
    for pg in pgs :
        if pg.Area < 0.00001 : continue
        lrs.append(get_CurveLoopFromLinearRing(pg.ExteriorRing))
        for lr in pg.InteriorRings :
            lrs.append(get_CurveLoopFromLinearRing(lr))

    curv_loops = System.Array[CurveLoop](lrs)
    doc = view.Document

    try : 
        with trans(doc) :
            res = FilledRegion.Create(doc, fregion_type.Id, view.Id, curv_loops)

        return res
    except :
        return 


def draw_points(points, view, rad=1, lstype=None) :
    doc = view.Document

    with trans(doc) :
        for p in points :
            arc = Arc.Create(p, rad, 0, pi2, XYZ.BasisX, XYZ.BasisY)
            nl = doc.Create.NewDetailCurve(view, arc)
            if lstype :
                nl.LineStyle = lstype

def draw_region_from_curve_loops(cl, view=None, fregion_type=None) :
    
    if not view :
        view = last_app.sprinkler_view
    if not fregion_type :
        fregion_type = last_app.sprinkler_plan_area_type

    doc = view.Document
    with trans(doc) :
        res = FilledRegion.Create(doc, fregion_type.Id, view.Id, cl)
        return res


def clean_curve_loops(cls, buf1 = -500 * dut, buf2 = 300 * dut, num_segments = 5) :
    def clean_linear_ring(lr) :
        dists = [5, 10, 20, 30, 40, 50, 75, 100, 150, 200, 300,400,500,600,1000]
        pg = geoms.Polygon(lr)
        res = []
        for d in dists :
            try :
                pg1 = pg.Buffer(d).Buffer(-2*d).Buffer(d)
                
                if type(pg) == geom.Polygon :
                    pgs = [pg]
                elif type(pg) == geom.MultiPolygon :
                    pgs = list(pg.Geometries)

                for g in pgs :
                    if type(g) == geoms.Polygon :
                        try :
                            if g.Area > 0.01 :
                                cl = get_CurveLoopFromLinearRing(g.ExternalRing)
                                res.append(cl)
                            break

                        except :
                            pass
                break
                
            except :
                pass
            if len(res) == 0 :
                print('Не удалось откорректировать контур')
        return res 
    def process_curve_loop(cl, buf1=-5*dut, buf2=5*dut) :
        lr = get_LinearRingFromCurveLoop(cl)
        pg = geoms.Polygon(lr)
        pg = pg.Buffer(buf1).Buffer(-buf1+buf2).Buffer(-buf2)

        curve_loops = []
        lin_rings = []
        if pg.GeometryType == "MultiPolygon" :
            for g in pg.Geometries :
                lin_rings.append(g.ExteriorRing)
        else :
            lin_rings.append(pg.ExteriorRing)

        to_process = []
        for lr in lin_rings :
            try :
                cl = get_CurveLoopFromLinearRing(lr)
                curve_loops.append(cl)
            except :
                print("Ошибка при формировании одного из контуров в clean_curve_loops_")
                to_process.append(lr)

        while len(to_process) > 0 :
            lr = to_process.pop()
            cleaned = clean_linear_ring(lr)
            curve_loops.extend(cleaned)    
        return curve_loops

    
    curve_loops = []
    for cl in cls :
        cl_p = process_curve_loop(cl,buf1, buf2)
        curve_loops.extend(cl_p)
    return System.Array[CurveLoop](curve_loops)

def clean_curve_loops_(cls, buf1 = -50 * dut, buf2 = 50 * dut, num_segments = None) :
    """
    Подчистка объектов CurveLoop для исключения мелких деталей
    """
    import random 
    pgs = []

    for cl in cls :
        lr = get_LinearRingFromCurveLoop(cl)
        pg = geoms.Polygon(lr).Buffer(buf1).Buffer(-buf1+buf2).Buffer(-buf2)

        if pg.GeometryType == "MultiPolygon" :
            for g in pg.Geometries :
                pgs.append(g.ExteriorRing)
        else :
            pgs.append(pg.ExteriorRing)

    try :
        cls_ = []
        for lr in pgs :
            try : 
                cl = get_CurveLoopFromLinearRing(lr)
                cls_.append(cl)

            except Exception as ex:
                print("Пропуск контура")


   
    except Exception as ex :
        print('Ошибка в функции clean_curve_loops')
        print('при добавлении')
        print('\n{}\n{}'.format(ex, ex.clsException))
        raise

    return System.Array[CurveLoop](cls_)


    


def draw_region_from_polygon(pg, view=None, fregion_type=None) :

    if not view :
        view = last_app.sprinkler_view
    if not fregion_type :
        fregion_type = last_app.sprinkler_plan_area_type

    doc = view.Document


    curve_loops = []

    for lr in pg.Boundary :
        try :
            cl = get_CurveLoopFromLinearRing(lr)
            curve_loops.append(cl)
        except Exception as ex:
            print("Ошибка draw_region_from_polygon\nПри формировании одного из контуров\n{}\n{}".format(ex, ex.clsException))
    cl = System.Array[CurveLoop](curve_loops)

    res = None
    with trans(doc) :
        res = FilledRegion.Create(doc, fregion_type.Id, view.Id, cl)

    return res

def get_PolygonFromCurveLoops(curve_loops) :
    # from collections import deque
    pgs = []

    for cl in curve_loops :
        # print(50*'-')
        
        lr = get_LinearRingFromCurveLoop(cl)

        pg = geoms.Polygon(lr)

        fixer = nts.Geometries.Utilities.GeometryFixer(pg)
        fixer.Fix(pg)
        pg = fixer.GetResult()

        pgs.append(pg)
        continue

        print(lr.GeometryType)
        fixer = nts.Geometries.Utilities.GeometryFixer(lr)
        fixer.Fix(lr)
        lr = fixer.GetResult()
        print(lr.GeometryType)

        if lr.GeometryType != "LinearRing" :
            print(50*'-')
            print(len(list(lr.Coordinates)))
            print(lr.Length)
            print(50*'-')
            create_ds(lr)

    
        pgs.append(geoms.Polygon(lr))

    pgs = sorted(pgs, key = lambda x : x.Area, reverse=False)
    polygons = []

    while len(pgs) > 0 :
        found = False 
        lr = pgs.pop()
        for p in polygons :
            if p.Contains(lr) :
                found = True
                polygons.remove(p)
                p = p.Difference(lr) 
                # print("------ Проверка на тип полигона---------")
                # print(type(p))
                # print(isinstance(p, geoms.Polygon))
                # print(isinstance(p, geoms.MultiPolygon))

                if isinstance(p, geoms.Polygon) :
                    # print('Полигон')
                    polygons.append(p)
                elif isinstance(p, geoms.MultiPolygon) :
                    # print("Мультиполигон")
                    polygons.extend(list(p.Geometries))

                # print('---------------------------')
        if not found :
            if isinstance(lr, geoms.Polygon) :
                # print('Полигон')
                polygons.append(lr)
            elif isinstance(lr, geoms.MultiPolygon) :
                # print("Мультиполигон")
                polygons.extend(list(lr.Geometries))
            # polygons.append(lr)
                
    try :
        pg = geoms.MultiPolygon(System.Array[geoms.Polygon](polygons))
    except :
        print('Ошибка при формировании MultiPoligon в функции get_PolygonFromCurveLoops')
        for p in polygons :
            print(type(p))
        raise
    return pg

def get_CurveLoopsFromPolygon(pg) :

    if type(pg) != geoms.MultiPolygon :
        pg1 = geoms.MultiPolygon(System.Array[geoms.Polygon]([pg]))
    else :
        pg1 = pg
    curve_loops = []
    for pg in pg1.Geometries : 
        boundary = pg.Boundary
        if type(boundary) != geoms.MultiLineString :
            boundary = geoms.MultiLineString(System.Array[LineString]([boundary]))
        for lr in boundary :
            try :
                cl = get_CurveLoopFromLinearRing(lr)
                curve_loops.append(cl)
            except Exception as ex:
                print("ошибка get_CurveLoopsFromPolygon")
                print(ex)
                
                pass
    return curve_loops

def get_CurvesFromCurveLoops(curve_loops) :
    
    curves = []
    min_len = 5 * dut
    for cl in curve_loops :
        for c in cl :
            
            if c.Length > min_len :
                curves.append(c)
    return curves

def get_CurvesFromPolygon(pg) :
    curve_loops = get_CurveLoopsFromPolygon(pg)
    curves = get_CurvesFromCurveLoops(curve_loops)
    return curves





def get_sprinkler_pos(pg, max_step, prot_radius, rot_angle = 0, allowed_buffer = -500*dut) :
    """
    Вычисляет позиции спринклеров для размещения внутри контура для расчета применяется библиотека NetTopologySuite
    вход:
        pg - Polygon - полигон - помещение, зона, на которой размещаются спринклера

        max_step - максимальное расстояние между спринклерами в регулярной расстановке
        prot_radius - радиус орошения спринклера для вычиления защищенных зон
        rot_angle -  угол на который следует повернуть зону, чтобы размещать спринклеры по осям X и Y. потом спринклеры также будут повернуты обратно (для упрощения расчетов и алгоритма)
    
    """
    check_print = False
    if check_print :
        print('**************************')
        print('0 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')

    try :
        rotation_angle = math.radians(rot_angle)
        rot_center = pg.Centroid
        pg1 = pg.Buffer(-50*dut)
        pg2 = pg1.Buffer(100*dut)
        pg = pg2.Buffer(-50*dut)

    except Exception as ex :
        print('Ошибка в функции get_sprinkler_pos()')
        print('\n{}\n{}'.format(ex, ex.clsException))
    print('get_sprinkler_pos : 1')

    if check_print :
        print('**************************')
        print('0.2 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')
        print(rot_center)

    gfc = nts.Geometries.Utilities.GeometryFixer(pg)
    gfc.KeepCollapsed = False
    pg = gfc.GetResult()

    
    tr_rot = nts.Geometries.Utilities.AffineTransformation().Rotate(rotation_angle, rot_center.X, rot_center.Y)

    if check_print :
        print('**************************')
        print('0.3 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')

    pg1 = tr_rot.Transform(pg).Buffer(-10 * dut)

    if check_print :
        print('**************************')
        print('0.4 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')

    env = pg1.EnvelopeInternal
    bnds = (env.MinX, env.MinY, env.MaxX, env.MaxY)

    sizes = (env.Width, env.Height)

 

    steps = [int(math.ceil(s/max_step)) for s in sizes]

    step_len = (sizes[0]/steps[0], sizes[1]/steps[1])
  
    if check_print :
        print('**************************')
        print('1 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')
  
    xx = [bnds[0] + step_len[0] / 2 + i *step_len[0] for i in range(steps[0])]
    yy =[bnds[1] + step_len[1] / 2 + i * step_len[1] for i in range(steps[1])]

    from itertools import product

    pnts = [geoms.Point(x,y) for x,y in product(xx, yy)]
    pnts = geoms.MultiPoint(System.Array[geoms.Point](pnts))

    pnts_in = pg1.Intersection(pnts)

    points_out = pnts.Difference(pnts_in)


    prot_area = pg1.Intersection(pnts_in.Buffer(prot_radius))
    unprot_area = pg1.Difference(prot_area)

    print('get_sprinkler_pos : 2')
    
    if unprot_area.NumGeometries < 2 :
        unprot_area = geoms.MultiPolygon(System.Array[geoms.Polygon]([unprot_area]))


    new_points = geoms.MultiPoint.Empty

    if check_print :
        print('**************************')
        print('2 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')

    for unp  in unprot_area.Geometries :

        i__ = 0 

        while unp.Area > 0.0000001 :
            i__ += 1
            if i__ > 100 : 
                break
    
            nloc = geoms.Point(
                nts.Operation.Distance.DistanceOp(
                                            unp, points_out).NearestPoints()[0])

            pot_p = nloc

            new_points = new_points.Union(pot_p)


            try :
                unp = unp.Difference(pot_p.Buffer(prot_radius))
            except :
                unp = geoms.Point(geoms.Coordinate(0,0))

    if check_print :
        print('**************************')
        print('3 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')
   
    try :
        
        all_points = pnts_in.Union(new_points)
        allowed_area = pg1.Buffer(allowed_buffer)   
        good_points = all_points.Intersection(allowed_area)      
        wrong_points = all_points.Difference(good_points)

        if type(wrong_points) == geoms.Point :
            wrong_points = geoms.MultiPoint(System.Array[geoms.Point]([wrong_points]))


        wrong_points_new = geoms.MultiPoint.Empty

        if not wrong_points.IsEmpty :
            for p in wrong_points.Geometries :   
                try :
                    p1 = geoms.Point(nts.Operation.Distance.DistanceOp(allowed_area, p).NearestPoints()[0])
                except Exception as ex :
                    print('Ошибка в функции p1 = nts.Operation.Distance.DistanceOp(allowed_area, p).NearestPoints()[0] ')
                    print('\n{}\n{}'.format(ex, ex.clsException))
                    raise 
                wrong_points_new = wrong_points_new.Union(p1)

    except Exception as ex :
        print('---Ошибка в функции get_sprinkler_pos ')
        print('\n{}\n{}'.format(ex, ex.clsException))
        raise

    if check_print :
        print('**************************')
        print('4 get_sprinkler_pos ----------')
        print('get_sprinkler_pos')

    all_points_new = wrong_points_new.Union(good_points)


    tr_rot_rev = tr_rot.GetInverse()
    all_points_rot = tr_rot_rev.Transform(all_points_new)



    return all_points_rot



class dm_dict(dict) :
    def __repr__(self) :
        res = "{}\n".format(self.__class__)
        for k in self.keys() :
            res += "{} : {}\n".format(k, self[k])
        return res

    def gi(self, i) :
        if type(i) == int :
            keys = self.keys()
            return self[keys[i]]



class dm_list(list) :
    def __repr__(self) :
        res = "Содержимое: \n".format(type(self))
        for i in self :
            res += "{}\n".format(i)
        return res

def get_LinearRingFromCurveLoop(cl) :
    pnts = []
    res = None
    try :
        for c in cl :
            if type(c) == Line :
                p = c.GetEndPoint(0)
                pnts.append(p)

            else :
                pp = list(c.Tessellate())

                pnts.extend(list(pp)[:-1])


        coords = []
        for p in pnts :
            coords.append(Coordinate(p.X, p.Y))
        coords.append(coords[0])
        res = LinearRing(System.Array[Coordinate](coords))
    except Exception as ex :
        print("Ошибка в get_LinearRingFromCurveLoop\n{}".format(ex))
    return res



def get_geometry_from_text(t) :
    res = None
    res = nts.IO.WKTReader().Read(t)    
    return res
def get_PointsFromMultiPoint(mp, elevation = 0) :

    if type(mp) == geoms.Point :
        mp = geoms.MultiPoint(System.Array[geoms.Point]([mp]))
    
    res = []
    
    for p in mp :
        # print(type(p))
        if type(p) == geoms.Point :
            res.append(XYZ(p.X, p.Y, elevation))
    return res

def get_PointsFromMultiPoint_proj(mp, face) :
    """
    ***************************************************************
    * Преобразует точки nettopologysuit в XYZ и проецирует координаты
    * на заданную плоскость
    * 
    ***************************************************************
    """

    if type(mp) == geoms.Point :
        mp = geoms.MultiPoint(System.Array[geoms.Point]([mp]))
    
    res = []
    
    for p in mp :
        # print(type(p))
        if type(p) == geoms.Point :
            xyz = XYZ (p.X, p.Y, 0)
            ir = face.Project(xyz)
            #pnt = face.Evaluate(uv)
            res.append(ir.XYZPoint)
    return res

def get_CurveLoopFromLinearRing(lr, elevation = 0) :
    """
    Преобразуется LinearRing из NetTopologySuite в CurveLoop
    """
    # print("Обновленная процедура get_CurveLoopFromLinearRing")
    lines = []
    crds_ = [XYZ(c.X,c.Y, elevation) for c in lr.Coordinates]

    crds = []

    p_prev = crds_[0]

    min_dist = 5 * dut

    for i in range(1, len(crds_)) :
        p = crds_[i]
        if p_prev.DistanceTo(p) > min_dist :
            crds.append(p_prev)
            p_prev = p 
        else :
            continue

    if p_prev.DistanceTo(p_prev) > min_dist :
        crds.append(p)



    if crds[0].DistanceTo(crds[-1]) > 0.000001 :
        if crds[0].DistanceTo(crds[-1]) < 2 * dut :
            crds.pop()
        crds.append(crds[0])

    for p1, p2 in zip(crds[:-1],crds[1:]) :
        try :
            l1 = Line.CreateBound(p1, p2)
            lines.append(l1)
        except :
            pass

    cl = CurveLoop.Create(System.Array[Curve](lines))
    return cl

def get_Face_borders(face) :
    plane = face.GetSurface()







class dm_FilledRegion(object) :


    def __init__(self, fr) :
        self.fr = fr
        self.doc = fr.Document

    def _get_sprinkler_params(self) :
        px = self.fr.LookupParameter("DM_Позиция_спринклера_Х").AsDouble()
        py = self.fr.LookupParameter("DM_Позиция_спринклера_У").AsDouble() 
        pz = self.fr.LookupParameter("DM_Отметка_низа").AsDouble()
        p_level_n = self.fr.LookupParameter("DM_Уровень").AsString() 
        res = dm_dict({'x' : px,
            'y' : py,
            'z' : pz,
            "level_name" : p_level_n,
            "XYZ" : XYZ(px,py,pz),
            
        })
        try :
            res['level'] = last_app.levels[res['level_name']]
        except :
            pass
        return res

    sprinkler_params = property(_get_sprinkler_params)

    def get_contours_region(self) :
        """
        Вычисляет и возвращает контуры региона в виде объектов NTS (Shapely)
        """
        curve_loops = self.fr.GetBoundaries()
        # print("Проверка get_contours_text \n{}\n{}".format(curve_loops, len(curve_loops)))
        pg = get_PolygonFromCurveLoops(curve_loops)
        return pg

    contour_nts = property(get_contours_region)

    def CalculateSprinklerPositions(self, max_step = 3000 * dut) :

        try :
            rot = math.degrees(self.fr.LookupParameter("DM_Поворот").AsDouble())
        except :
            rot = 0 

        prot_radius = max_step * 2**0.5 / 2
    


        try :
            res = get_sprinkler_pos(self.contour_nts, max_step, prot_radius, rot)
        except Exception as ex :
            print("Ошибка методе dm_FilledRegion.CalculateSprinklerPositions\nпри вызове\nres = get_sprinkler_pos(self.contour_nts, max_step, prot_radius, rot) ")
            print("{}\n{}".format(ex, ex.clsException))
            raise 


        self.sprinkler_pos_nts  = res     
        if self.sprinkler_pos_nts.NumGeometries == 1 :
            self.sprinkler_pos_nts = MultiPoint(System.Array[nts.Geometries.Point]([self.sprinkler_pos_nts]))

        self.sprinkler_points_list = get_PointsFromMultiPoint(self.sprinkler_pos_nts)
       
        return self.sprinkler_points_list

    def draw_sprinklers(self, view=None, rad=1, lstype=None, max_step = 3000 * dut) :
        if not view :
            view_id = self.doc.GetElement(self.fr.OwnerViewId)

        if hasattr(self, 'spriklers_pos') :
            spos = self.sprinklers_pos
        else :
            self.sprinklers_pos = self.CalculateSprinklerPositions(
                max_step=max_step
            )
            spos = self.sprinklers_pos

        with trans(self.doc) :
            for p in spos :
                arc = Arc.Create(p, rad, 0, pi2, XYZ.BasisX, XYZ.BasisY)
                nl = self.doc.Create.NewDetailCurve(view_id, arc)
                if lstype :
                    nl.LineStyle = lstype

    def draw_sprinkler_covering(self, view=None, filled_reg_type=None, max_step = 3000*dut) :

        if not filled_reg_type :
            filled_reg_type = last_app.sprinkler_covering_area_type

        print("draw_sprinkler_covering")
        if not hasattr(self, "sprinkler_covering_zones") :
            prot_radius = max_step * 2**0.5 / 2
            self.calculate_sprinkler_covering(prot_radius=prot_radius)

        if view :
            view_id = view.Id
        else :
            view_id = self.fr.OwnerViewId

        try :
            lev_name = self.fr.LookupParameter("DM_Уровень").AsString()
        except :
            pass
        try :
            elevation = self.fr.LookupParameter("DM_Отметка_низа").AsDouble()
        except :
            pass


        with trans(self.doc) :
            for z, px, py in self.sprinkler_covering_zones:
                try :
                    cl = get_CurveLoopFromLinearRing(z.ExteriorRing)
                    fr = FilledRegion.Create(self.doc, 
                                            filled_reg_type.Id, 
                                            view_id, System.Array[CurveLoop]([cl]))
                    try :
                        fr.LookupParameter("DM_Уровень").Set(lev_name)
                    except :
                        pass

                    try :
                        fr.LookupParameter("DM_Отметка_низа").Set(elevation)
                    except :
                        pass
                    try :
                        
                        fr.LookupParameter("DM_Позиция_спринклера_Х").Set(px)
                        fr.LookupParameter("DM_Позиция_спринклера_У").Set(py)

                    except :
                        pass

                except Exception as ex: 
                    print("ошибка\n{}".format(ex))
                    raise
                    

    def create_sprinkler(self, trans = True) :
        tid = self.fr.GetTypeId()
        fr_type = self.doc.GetElement(tid)
        tname = en(fr_type)
        
        
        spr_type = last_app.sprinkler_types ["Вверх свободный в/н"]

        # print(tname)
        
        if not tname.Contains("Зона_орошения_спринклера") :
            return 
        try : 
            spr_id = ElementId(int(self.fr.LookupParameter("DM_спринклер_id").AsString()))
            old_spr = self.doc.GetElement(spr_id)
        except Exception as ex:
            print(ex.clsException)
            spr_id = None
            old_spr = None

        

        sp_params = self.sprinkler_params
        level = sp_params['level']
        pnt = sp_params['XYZ']


        if trans :
            trans = Transaction(self.doc)
            trans.Start("Создание спринклера")
        try :
            spr = self.doc.Create.NewFamilyInstance(pnt, spr_type, level, nonstr)
        except :
            print("ошибка при создании спринклера")

        try :
            self.fr.LookupParameter("DM_спринклер_id").Set(str(spr.Id.IntegerValue))
        except Exception as ex:
            print("ошибка установки параметр DM_cпринклер_id")
            print(ex.clsException)

            print(str(spr.Id))
        try : 
            self.doc.Delete(spr_id)
        except :
            print("Не удалось удалить")
            pass

        if trans :
            trans.Commit()

        return spr

        



        

        



    def calculate_sprinkler_covering(self, prot_radius = 3000*dut * 2**0.5/2) :
        
        if not hasattr(self, "sprinkler_pos_nts") :
            self.CalculateSprinklerPositions()
        self.sprinkler_covering_zones = []
        for pos in self.sprinkler_pos_nts :
            try :
                z = get_sprinkler_covering_area(self.contour_nts, pos, prot_radius)

                self.sprinkler_covering_zones.append((z, pos.X, pos.Y))
            except :
                pass





class dm_Space(object) :
    def __init__(self, s, app = None) :
        self.space = s
        self.doc = s.Document
        self.app = app
    def __repr__(self) :
        return "Пространство\n{}\n{}".format(self.space.Number, en(self.space))

    def get_view_name(self) :
        lev_name = self.space.Level.Name
        v_name = "DM_Пространства_{}".format(lev_name)
        return v_name

    def get_draft_view(self, create=False) :
        """
        Ищет и возвращает вид на котором можно отобразить границы пространства
        если не нахдит то может создать
        """
        view_name = self.get_view_name()
        fc = {en(e) : e for e in FilteredElementCollector(self.doc).OfClass(ViewDrafting).ToElements()}

        try :
            res = fc[view_name]
            return res
        except :
            if not create :
                return
            else :
                with trans(self.doc) :
                    new_view = ViewDrafting.Create(
                        self.doc,
                        self.app.space_drafting_view_type.Id 
                        )

                    new_view.Name = view_name
                return new_view 


    def delete(self) :
        with trans(self.doc) :
            self.doc.Delete(self.space.Id)


    def get_contours(self) :
        g = self.space.Geometry[Options()]
        vz = -XYZ.BasisZ
        wf = None
        for s in g :
            if type(s) == Solid :
                for f in s.Faces :
                    try :
                        if f.FaceNormal.IsAlmostEqualTo(vz) :
                            wf = f
                    except :
                        pass
        if wf :
            return wf.GetEdgesAsCurveLoops()

    def draw_contours(self, view, linestyle = None, displace = None) :
        clps = self.get_contours()
        with trans(self.doc) :
            for cl in clps : 
                for c in cl : 
                    nl = self.doc.Create.NewDetailCurve(view, c)
                    if linestyle :
                        nl.LineStyle = linestyle

    def draw_space_as_region(self, view=None, fill_type = None) :
        if not view :
            view = self.get_draft_view()
        if not fill_type :
            fill_type = self.app.sprinkler_plan_area_type
        print(50*'-')
        clps = self.get_contours()
        doc = view.Document
        with trans(doc) :
            try :
                fr = FilledRegion.Create(doc, fill_type.Id, view.Id, clps)
            except :
                try :

                    pg = self.get_contours_polygon().Buffer(.2).Buffer(-.2)
                    clps = get_CurveLoopsFromPolygon(pg)
                    fr = FilledRegion.Create(doc, fill_type.Id, view.Id, clps)
                except Exception as ex:
                    print("Не удалось создать контур")
                    print(ex)
                    


            try :
                level_name = self.space.Level.Name            
                fr.LookupParameter("DM_Уровень").Set(level_name)
            except Exception as ex:
                print('Параметр DM_Уровень установить не удалось')
                print(ex)
                print(ex.clsException)
                
                #fr.LookupParameter("DM_Уровень").Set('Не определен')

            try :
                protation = self.space.LookupParameter('DM_Поворот')
                
                if protation :
                    par_rotation = protation.AsDouble()
                else :
                    par_rotation = 0
                
                fr.LookupParameter("DM_Поворот").Set(par_rotation)
            except Exception as ex:
                print('Параметр DM_Поворот установить не удалось')
                print(ex)
                print(ex.clsException)

            try :
                sp_height = self.space.UnboundedHeight
                fr.LookupParameter("DM_Отметка_низа").Set(sp_height)
            except Exception as ex:
                print('Параметр DM_Отметка_низа установить не удалось')
                print(ex)
                print(ex.clsException)

        return dm_FilledRegion(fr)


    def draw_space_as_region_(self, view=None, fill_type=None) :

        if not view :
            view = self.get_draft_view()
        if not fill_type :
            fill_type = self.app.sprinkler_plan_area_type

        curve_loops = []
        clps = self.get_contours() 
        for cl in clps :
            pnts = []
            for c in cl :
                if type(c) == Line :
                    pnts.append(c.GetEndPoint(0))
                if type(c) == Arc :
                    pnts += list(c.Tessellate())[:-1]
            pnts.append(pnts[0])
            lines = []
            for p1, p2 in zip(pnts[:-1], pnts[1:]) :
                l = Line.CreateBound(p1,p2)
                lines.append(l)

            alines = CurveLoop.Create(lines)
            curve_loops.append(alines)
        a_curve_loops = System.Array[CurveLoop](curve_loops)

        with trans(self.doc) :
            fr = FilledRegion.Create(self.doc, fill_type.Id, view.Id, a_curve_loops)

        return fr

    def CalculateSprinklerPositions(self, max_step = 3000 * dut, rot = 0) :
        
        try :
            rot = math.degrees(self.space.LookupParameter("DM_Поворот").AsDouble())
        except :
            rot = 0 

        prot_radius = max_step * 2**0.5 / 2
    


        try :
            contour_nts = self.get_contours_polygon()
            res = get_sprinkler_pos(contour_nts, max_step, prot_radius, rot)
        except Exception as ex :
            print("Ошибка методе dm_FilledRegion.CalculateSprinklerPositions\nпри вызове\nres = get_sprinkler_pos(self.contour_nts, max_step, prot_radius, rot) ")
            print("{}\n{}".format(ex, ex.clsException))
            raise 


        self.sprinkler_pos_nts  = res     
        if self.sprinkler_pos_nts.NumGeometries == 1 :
            self.sprinkler_pos_nts = MultiPoint(System.Array[nts.Geometries.Point]([self.sprinkler_pos_nts]))

        self.sprinkler_points_list = get_PointsFromMultiPoint(self.sprinkler_pos_nts)
       
        return self.sprinkler_points_list

    def _get_rot_angle(self) :
        try :
            rot = math.degrees(self.space.LookupParameter("DM_Поворот").AsDouble())
        except :
            rot = 0 
        return rot

    rot_angle = property(_get_rot_angle)

    def _is_to_protect_get(self) :
        try :
            res = self.space.LookupParameter("DM_Защита спринклерами").AsInteger()
        except :
            res = 0 
        return res 
        
    
    def _is_to_protect_set(self, v) :
        try :
            with trans(doc) :
                self.space.LookupParameter("DM_Защита спринклерами").Set(v)
        except Exception as ex:
            print("Ошибка при установке параметра DM_Защита спринклером")
            print(ex)
            pass


    to_protect = property(_is_to_protect_get, _is_to_protect_set)




    def get_contours_polygon(self) :
        curve_loops = self.get_contours()
        # print("Проверка get_contours_text \n{}\n{}".format(curve_loops, len(curve_loops)))
        lrs = []
        for cl in curve_loops :
            try :
                # print("cl = {}".format(cl))
                lrs.append(get_LinearRingFromCurveLoop(cl))
            except Exception as ex:
                print("ошибка \n{}".format(ex))
                pass
        
        curve_loops = sorted(lrs, key = lambda x : Polygon(x).Area, reverse=True)
        pg = nts.Geometries.Polygon(curve_loops[0], System.Array[LinearRing](curve_loops[1:]))
        self.contour_nts = pg
        return pg

    def get_contours_text(self) :
        pg = self.get_contours_polygon()
        return pg.AsText()

    def _get_geometry(self) :
        """
            Функция для доступа к объемному телу представляющего объем пространства.
        """
        g = self.space.Geometry[Options()]
        return list(g)[0]
    
    space_solid = property(_get_geometry)

    def create_space_solid(self) :
        s = self.space_solid
        create_direct_shape(s)

    def _get_top_face(self) :
        """
        Возвращает верхнуюю грань solid 
        """
        s1 = self.space_solid
        # create_ds(s1)
        bz = XYZ.BasisZ
        for f in s1.Faces :
            try :
                if bz.IsAlmostEqualTo(f.FaceNormal) :
                    return f
            except :
                pass
    def get_free_ceiling_contour(self, 
                            barrier_categories = None, 
                            include_links=True, 
                            create_shape = False, 
                            dist = 100*dut, 
                            thickness = 2 * dut,
                            create_filled_region = False,
                            fr_view = None,
                            fr_type = None,
                            
                            ) :
        """
        Вычисляем свободное пространство на заданном расстоянии от перекрытия, по умолчанию 100 мм 
        от высоты пространства, чтобы определить наличие препятствий.
        barrier_categories = перечень категорий которые будем искать и воспринимать как потенциальные барьеры
        include_links - ищем препятствия во вложенных файлах.
        """
        space_sld = self.space_solid
        ceil_sld = self.get_ceiling_contour(dist =dist, thickness=thickness)

        if barrier_categories is None :
            barrier_categories = [bic.OST_Floors, 
                                        bic.OST_Ceilings, 
                                        bic.OST_StructuralColumns
                                        ]
        if barrier_categories == 1 :
            barrier_categories = [bic.OST_Floors, 
                            bic.OST_Ceilings, 
                            bic.OST_StructuralColumns,
                            bic.OST_DuctCurves,
                            bic.OST_DuctFitting
                            ]

        if True :
            print('**************************')
            print('1 Контрольная точка ----------')
            print('get_free_ceiling_contur')
            print('barrier_categories : {} '.format(barrier_categories))

        cat_filter = ElementMulticategoryFilter(System.Array[bic](barrier_categories))
        solid_filter = ElementIntersectsSolidFilter(ceil_sld)

        doc_elements = FilteredElementCollector(self.doc).WherePasses(cat_filter).WherePasses(solid_filter).ToElements()
        doc_solids = []
        for e in doc_elements :
            g = list(e.Geometry[Options()])
            for ge in g :
                if type(ge) == Solid :
                    doc_solids.append(ge)


        for s1 in doc_solids :
            try :
                ceil_sld = BooleanOperationsUtils.ExecuteBooleanOperation(ceil_sld, 
                                                                s1, 
                                                                BooleanOperationsType.Difference)
            except Exception as ex:
                print("ошибка при операции\n{}".format(ex))
                pass

        l_doc_solids = []
        if include_links :
            lnks = self.app.linked_files

            for ld in lnks :
                ldoc = ld.GetLinkDocument()
                ltrans_d = ld.GetTotalTransform()
                ltrans = ld.GetTotalTransform().Inverse

                l_ceil_sld = SolidUtils.CreateTransformed(ceil_sld, ltrans)
                l_cat_filter = ElementMulticategoryFilter(System.Array[bic](barrier_categories))
                l_solid_filter = ElementIntersectsSolidFilter(l_ceil_sld)
                lfc = FilteredElementCollector(ldoc).WherePasses(l_cat_filter).WherePasses(l_solid_filter).ToElements()

                for e in lfc :
                    g = list(e.Geometry[Options()].GetTransformed(ltrans_d))
                    for ge in g :
                        if type(ge) == Solid :
                            l_doc_solids.append(ge)

            
                for s1 in l_doc_solids :
                    try :
                        ceil_sld = BooleanOperationsUtils.ExecuteBooleanOperation(ceil_sld, s1, BooleanOperationsType.Difference)
                    except Exception as ex:
                        print("ошибка при операции\n{}".format(ex))
                        pass

        if create_shape :
            create_direct_shape(ceil_sld)

        zb = XYZ.BasisZ
        res_face = None
        for f in ceil_sld.Faces :
            try :
                if zb.IsAlmostEqualTo(f.FaceNormal) :
                    res_face = f
                    break
            except :
                pass

        cloops = res_face.GetEdgesAsCurveLoops()

        if create_filled_region :
            fr = draw_region_from_curve_loops(cl = cloops, 
                                                view = fr_view, 
                                                fregion_type = fr_type)

            try :
                level_name = self.space.Level.Name
                with trans(self.doc) :
                    fr.LookupParameter("DM_Уровень").Set(level_name)
            except Exception as ex:
                print('Параметр DM_Уровень установить не удалось')
                print(ex)
                print(ex.clsException)
                with trans(self.doc) :
                    fr.LookupParameter("DM_Уровень").Set('Не определен')

            try :
                par_rotation = self.space.LookupParameter('DM_Поворот').AsDouble()
                with trans(self.doc) :
                    fr.LookupParameter("DM_Поворот").Set(par_rotation)
            except Exception as ex:
                print('Параметр DM_Поворот установить не удалось')
                print(ex)
                print(ex.clsException)

            try :
                sp_height = self.space.UnboundedHeight - dist +  thickness / 2
                with trans(self.doc) :
                    fr.LookupParameter("DM_Отметка_низа").Set(sp_height)
            except Exception as ex:
                print('Параметр DM_Отметка_низа установить не удалось')
                print(ex)
                print(ex.clsException)



        return cloops
        

    def get_free_ceiling_contour_by_intersection(self, 
                                                    barrier_categories = None, 
                                                    include_links=True, 
                                                    create_shape = False, 
                                                    dist = 100*dut, 
                                                    thickness = 2 * dut,
                                                    create_filled_region = False,
                                                    fr_view = None,
                                                    fr_type = None,

                                                    ) :
        """
        Вычисляем свободное пространство на заданном расстоянии от перекрытия, методом пересечения
        от высоты пространства, чтобы определить наличие препятствий.
        barrier_categories = перечень категорий которые будем искать и воспринимать как потенциальные барьеры
        include_links - ищем препятствия во вложенных файлах.
        create_shape - создает тело в модели
        create_filled_region - создает регион на укказанном виде
        fr_view - вид на котором создаать доступную область
        fr_type - семейство, тип закрашенной области
        """
        check_print = True

        if check_print :
            print('**************************')
            print('1 get_free_ceiling_contour_by_intersection Контрольная точка ----------')
            print('Начало')
        space_sld = self.space_solid
        ceil_sld = self.get_ceiling_contour(dist =dist, thickness=thickness)
        print(ceil_sld)

        if check_print :
            print('**************************')
            print('1 get_free_ceiling_contour_by_intersection Контрольная точка ----------')
            print('Начало')

        # create_direct_shape(ceil_sld)



        

        zb = -XYZ.BasisZ
        res_face = None
        for f in ceil_sld.Faces :
            try :
                if zb.IsAlmostEqualTo(f.FaceNormal) :
                    res_face = f
                    break
            except :
                pass

        cloops = res_face.GetEdgesAsCurveLoops()
        bot_plane = cloops[0].GetPlane()

        # contour_pg - полигон представляющий контуры помещения
        contour_pg = get_PolygonFromCurveLoops(cloops)

        # bot_plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        print("этап 2")

        

        if barrier_categories is None :
            barrier_categories = [bic.OST_Floors, bic.OST_Ceilings, bic.OST_StructuralColumns]

        if barrier_categories == 1 :
            barrier_categories = [bic.OST_Floors, 
                            bic.OST_Ceilings, 
                            bic.OST_StructuralColumns,
                            bic.OST_DuctCurves,
                            bic.OST_DuctFitting
                            ]

        #Выбор элементов, которые попадают в искомую зону
        cat_filter = ElementMulticategoryFilter(System.Array[bic](barrier_categories))
        solid_filter = ElementIntersectsSolidFilter(ceil_sld)

        doc_elements = FilteredElementCollector(self.doc).WherePasses(cat_filter).WherePasses(solid_filter).ToElements()

        # Собираем геометрию найденых элементов в список
        doc_solids = []
        for e in doc_elements :
            g = list(e.Geometry[Options()])
            for ge in g :
                if type(ge) == Solid :
                    doc_solids.append(ge)
        # doc_solids - содержит геометрию элементов

        print('Этап 3')
        doc_solids_m = []
        for s1 in doc_solids :
            try :
                s2 = BooleanOperationsUtils.ExecuteBooleanOperation(ceil_sld, 
                            s1, 
                            BooleanOperationsType.Intersect)
                doc_solids_m.append(s2)


            except Exception as ex:
                print("ошибка при операции\n{}".format(ex))
                pass
        if len(doc_solids_m) > 0 :
            res_solids = doc_solids_m[0]
            print("Этап 4")
            for s1 in doc_solids_m[1:] :
                try : 
                    res_solids = BooleanOperationsUtils.ExecuteBooleanOperation(res_solids, 
                                        s1, BooleanOperationsType.Union)
                except :
                    pass
        # res_solids - содержит объединенный солид всех элементов которые попали в зону

        # create_direct_shape(res_solids)

        if check_print :
            print('**************************')
            print('5 Контрольная точка ----------')
            print('get_free_ceiling_by_intersection')

        # link_polygons - контуры искомых объектов, которые вычтем из контура помещения
        link_polygons = []
        l_doc_solids = []
        if include_links :
            lnks = self.app.linked_files

            for ld in lnks :
                ldoc = ld.GetLinkDocument()
                ltrans_d = ld.GetTotalTransform()
                ltrans = ld.GetTotalTransform().Inverse

                l_ceil_sld = SolidUtils.CreateTransformed(ceil_sld, ltrans)
                l_cat_filter = ElementMulticategoryFilter(System.Array[bic](barrier_categories))
                l_solid_filter = ElementIntersectsSolidFilter(l_ceil_sld)
                lfc = FilteredElementCollector(ldoc).WherePasses(l_cat_filter).WherePasses(l_solid_filter).ToElements()
                
                for e in lfc :
                    g = list(e.Geometry[Options()].GetTransformed(ltrans_d))
                    for ge in g :
                        if type(ge) == Solid :
                            try :
                                s2 = BooleanOperationsUtils.ExecuteBooleanOperation(ceil_sld, ge, BooleanOperationsType.Intersect)
                                l_ex_an = ExtrusionAnalyzer.Create(s2, bot_plane, XYZ.BasisZ)
    
                                #Добавляем контур объекта который далее будем вычитать
                                l_s2_cnt = l_ex_an.GetExtrusionBase().GetEdgesAsCurveLoops()

                                l_s2_pg = get_PolygonFromCurveLoops(l_s2_cnt)
                                link_polygons.append(l_s2_pg)

                                s2 = GeometryCreationUtilities.CreateExtrusionGeometry(l_s2_cnt, XYZ.BasisZ, thickness) 
                                l_doc_solids.append(s2)
                            except Exception as ex :
                                # print(ex.clsException)
                                pass
                            


            if check_print :
                print('**************************')
                print('6 Контрольная точка ----------')
                print('get_free_ceiling_by_intersection')
            # В списке l_doc_solids попали элементы из всех вставленных моделей, причем уже после операции пересечения и их осталось объединить.
            # 

            l_res_solids = ceil_sld
            for s1 in l_doc_solids :
                try :
                    l_res_solids = BooleanOperationsUtils.ExecuteBooleanOperation(l_res_solids, s1, BooleanOperationsType.Difference)
                    
                except Exception as ex:
                    # print("ошибка при вычитании solid из зоны телу\n{}\{}".format(ex, ex.clsException))
                    pass

        # res_solids - суммарный solid  для всех объектов попадающих в зону.

        if check_print :
            print('**************************')
            print('7 Контрольная точка ----------')
            print('get_free_ceiling_by_intersection')


        if create_shape :
            # create_direct_shape(ceil_sld)
            create_direct_shape(l_res_solids)
            pass

        zn = -XYZ.BasisZ
        for f in l_res_solids.Faces :
            try :
                if zn.IsAlmostEqualTo(f.FaceNormal) :
                    break
            except :
                pass

        ex_base = f.GetEdgesAsCurveLoops()
        
        
        try :  
            alt_res_pg = contour_pg
            for pg in link_polygons :
                alt_res_pg = alt_res_pg.Difference(pg)

            alt_res = get_CurveLoopsFromPolygon(alt_res_pg)


            # ex_base = clean_curve_loops(ex_base)     
            # curve_loops = get_PolygonFromCurveLoops(ex_base).Buffer(-10*dut).Buffer(20*dut).Buffer(-10*dut)
            # ex_base = get_CurveLoopsFromPolygon(curve_loops)
            # 
            pass    
        except Exception as ex :
            print('Ошибка в функции get_free_ceiling_contour_by_intersection')
            print("При исправлении контуров")
            print('\n{}\n{}'.format(ex, ex.clsException))
    
    
            raise

        if check_print :
            print('**************************')
            print('8 Контрольная точка ----------')
            print('get_free_ceiling_by_intersection')


        if create_filled_region :
            if not fr_view :
                fr_view = self.get_draft_view()
            if not fr_type :
                fr_type = last_app.sprinkler_plan_area_type

            pg1 = get_PolygonFromCurveLoops(ex_base)
            fr = draw_region_from_polygon(pg = pg1, 
                                                view = fr_view, 
                                                fregion_type = fr_type)


            """
            fr = draw_region_from_curve_loops(cl = ex_base, 
                                                view = fr_view, 
                                                fregion_type = fr_type)
            """


            try :
                level_name = self.space.Level.Name
                with trans(self.doc) :
                    fr.LookupParameter("DM_Уровень").Set(level_name)
            except Exception as ex:
                print('Параметр DM_Уровень установить не удалось')
                print(ex)
                print(ex.clsException)
                with trans(self.doc) :
                    fr.LookupParameter("DM_Уровень").Set('Не определен')

            try :
                par_rotation = self.space.LookupParameter('DM_Поворот').AsDouble()
                with trans(self.doc) :
                    fr.LookupParameter("DM_Поворот").Set(par_rotation)
            except Exception as ex:
                print('Параметр DM_Поворот установить не удалось')
                print(ex)
                print(ex.clsException)

            try :
                sp_height = self.space.UnboundedHeight - dist +  thickness / 2
                with trans(self.doc) :
                    fr.LookupParameter("DM_Отметка_низа").Set(sp_height)
            except Exception as ex:
                print('Параметр DM_Отметка_низа установить не удалось')
                print(ex)
                print(ex.clsException)

        
        return ex_base
               


    def get_free_ceiling_contour_by_intersection2(self, 
                                                    barrier_categories = None, 
                                                    include_links=True, 
                                                    create_shape = False, 
                                                    dist = 100*dut, 
                                                    thickness = 2 * dut,
                                                    create_filled_region = False,
                                                    fr_view = None,
                                                    fr_type = None,

                                                    ) :
        """
        Вычисляем свободное пространство на заданном расстоянии от перекрытия, 
        вычисления будем делать так: находим пересечение объекта с искомым объемом
        вычисляем проекцию этого объекта при помощи ExtrusionAnalyzer. И формируем полигоны NTS.


        barrier_categories = перечень категорий которые будем искать и воспринимать как потенциальные барьеры
        include_links - ищем препятствия во вложенных файлах.
        create_shape - создает тело в модели
        create_filled_region - создает регион на укказанном виде
        fr_view - вид на котором создаать доступную область
        fr_type - семейство, тип закрашенной области
        """
        check_print = True

        if check_print :
            print('**************************')
            print('1 get_free_ceiling_contour_by_intersection2 Контрольная точка ----------')
            print('Начало')

        
        
        
        try :
            ceil_sld = self.get_ceiling_contour(dist =dist, thickness=thickness)
        except Exception as ex :
            print('Ошибка в функции \nceil_sld = self.get_ceiling_contour(dist =dist, thickness=thickness)')
            print('\n{}\n{}'.format(ex, ex.clsException))
    
    
            raise
        
        


        if check_print :
            print('**************************')
            print('2 get_free_ceiling_contour_by_intersection Контрольная точка ----------')
            print('Начало')

        # create_ds(ceil_sld)
        

        zb = -XYZ.BasisZ
        res_face = None
        for f in ceil_sld.Faces :
            try :
                if zb.IsAlmostEqualTo(f.FaceNormal) :
                    res_face = f
                    break
            except :
                pass

        cloops = res_face.GetEdgesAsCurveLoops()
        bot_plane = cloops[0].GetPlane()

        print(cloops)
        print(hasattr(cloops[0],"__iter__"))


     
        

        # contour_pg - полигон представляющий контуры помещения
        contour_pg = get_PolygonFromCurveLoops(cloops)

        create_ds(contour_pg)
        
        

        # bot_plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        print("этап 2")

        

        if barrier_categories is None :
            barrier_categories = [bic.OST_Floors, bic.OST_Ceilings, bic.OST_StructuralColumns]

        if barrier_categories == 1 :
            barrier_categories = [bic.OST_Floors, 
                            bic.OST_Ceilings, 
                            bic.OST_StructuralColumns,
                            bic.OST_DuctCurves,
                            bic.OST_DuctFitting
                            ]

        #Выбор элементов, которые попадают в искомую зону
        cat_filter = ElementMulticategoryFilter(System.Array[bic](barrier_categories))
        solid_filter = ElementIntersectsSolidFilter(ceil_sld)

        doc_elements = FilteredElementCollector(self.doc).WherePasses(cat_filter).WherePasses(solid_filter).ToElements()

        # Собираем геометрию найденых элементов в список
        doc_solids = []
        for e in doc_elements :
            g = list(e.Geometry[Options()])
            for ge in g :
                if type(ge) == Solid :
                    doc_solids.append(ge)
                    # create_ds(ge)
        # doc_solids - содержит геометрию элементов
    
        print('Этап 3')
        doc_solids_m = []
        for s1 in doc_solids :
            try :
                s2 = BooleanOperationsUtils.ExecuteBooleanOperation(ceil_sld, 
                            s1, 
                            BooleanOperationsType.Intersect)
                doc_solids_m.append(s2)



            except Exception as ex:
                print("ошибка при операции\n{}".format(ex))
                pass

        if len(doc_solids_m) > 0 :
            res_solids = doc_solids_m[0]
            print("Этап 4")
            for s1 in doc_solids_m[1:] :
                try : 
                    res_solids = BooleanOperationsUtils.ExecuteBooleanOperation(res_solids, 
                                        s1, BooleanOperationsType.Union)
                except :
                    pass
        # res_solids - содержит объединенный солид всех элементов которые попали в зону

        # create_direct_shape(res_solids)

        if check_print :
            print('**************************')
            print('5 Контрольная точка ----------')
            print('get_free_ceiling_by_intersection')

        # link_polygons - контуры искомых объектов, которые вычтем из контура помещения
        link_polygons = []
        l_doc_solids = []
        if include_links :
            lnks = self.app.linked_files

            for ld in lnks :
                ldoc = ld.GetLinkDocument()
                ltrans_d = ld.GetTotalTransform()
                ltrans = ld.GetTotalTransform().Inverse

                l_ceil_sld = SolidUtils.CreateTransformed(ceil_sld, ltrans)
                l_cat_filter = ElementMulticategoryFilter(System.Array[bic](barrier_categories))
                l_solid_filter = ElementIntersectsSolidFilter(l_ceil_sld)
                lfc = FilteredElementCollector(ldoc).WherePasses(l_cat_filter).WherePasses(l_solid_filter).ToElements()
                
                for e in lfc :
                    g = list(e.Geometry[Options()].GetTransformed(ltrans_d))
                    for ge in g :
                        if type(ge) == Solid :
                            try :
                                s2 = BooleanOperationsUtils.ExecuteBooleanOperation(ceil_sld, ge, BooleanOperationsType.Intersect)
                                l_ex_an = ExtrusionAnalyzer.Create(s2, bot_plane, XYZ.BasisZ)
    
                                #Добавляем контур объекта который далее будем вычитать
                                l_s2_cnt = l_ex_an.GetExtrusionBase().GetEdgesAsCurveLoops()

                                l_s2_pg = get_PolygonFromCurveLoops(l_s2_cnt)
                                link_polygons.append(l_s2_pg)

                                s2 = GeometryCreationUtilities.CreateExtrusionGeometry(l_s2_cnt, XYZ.BasisZ, thickness) 
                                l_doc_solids.append(s2)
                                # create_ds(s2)
                                # print(type(e))
                            except Exception as ex :
                                # print(ex.clsException)
                                pass
                            

            
            if check_print :
                print('**************************')
                print('6 Контрольная точка ----------')
                print('get_free_ceiling_by_intersection')
            # В списке l_doc_solids попали элементы из всех вставленных моделей, причем уже после операции пересечения и их осталось объединить.
            # 

            l_res_solids = ceil_sld
            for s1 in l_doc_solids :
                try :
                    l_res_solids = BooleanOperationsUtils.ExecuteBooleanOperation(l_res_solids, s1, BooleanOperationsType.Difference)
                    
                except Exception as ex:
                    # print("ошибка при вычитании solid из зоны телу\n{}\{}".format(ex, ex.clsException))
                    pass

        # res_solids - суммарный solid  для всех объектов попадающих в зону.

        if check_print :
            print('**************************')
            print('7 Контрольная точка ----------')
            print('get_free_ceiling_by_intersection')

        zn = -XYZ.BasisZ
        for f in l_res_solids.Faces :
            try :
                if zn.IsAlmostEqualTo(f.FaceNormal) :
                    break
            except :
                pass

        ex_base = f.GetEdgesAsCurveLoops()
        
        
        try :  
            alt_res_pg = contour_pg
            for pg in link_polygons :
                alt_res_pg = alt_res_pg.Difference(pg)

            alt_res = get_CurveLoopsFromPolygon(alt_res_pg)


            # ex_base = clean_curve_loops(ex_base)     
            # curve_loops = get_PolygonFromCurveLoops(ex_base).Buffer(-10*dut).Buffer(20*dut).Buffer(-10*dut)
            # ex_base = get_CurveLoopsFromPolygon(curve_loops)
            # 
            pass    
        except Exception as ex :
            print('Ошибка в функции get_free_ceiling_contour_by_intersection')
            print("При исправлении контуров")
            print('\n{}\n{}'.format(ex, ex.clsException))
    
    
            raise

        if check_print :
            print('**************************')
            print('8 Контрольная точка ----------')
            print('get_free_ceiling_by_intersection')


        if create_filled_region :
            if not fr_view :
                fr_view = self.get_draft_view()
            if not fr_type :
                fr_type = last_app.sprinkler_plan_area_type

            pg1 = get_PolygonFromCurveLoops(ex_base)
            fr = draw_region_from_polygon(pg = pg1, 
                                                view = fr_view, 
                                                fregion_type = fr_type)


            """
            fr = draw_region_from_curve_loops(cl = ex_base, 
                                                view = fr_view, 
                                                fregion_type = fr_type)
            """


            try :
                level_name = self.space.Level.Name
                with trans(self.doc) :
                    fr.LookupParameter("DM_Уровень").Set(level_name)
            except Exception as ex:
                print('Параметр DM_Уровень установить не удалось')
                print(ex)
                print(ex.clsException)
                with trans(self.doc) :
                    fr.LookupParameter("DM_Уровень").Set('Не определен')

            try :
                par_rotation = self.space.LookupParameter('DM_Поворот').AsDouble()
                with trans(self.doc) :
                    fr.LookupParameter("DM_Поворот").Set(par_rotation)
            except Exception as ex:
                print('Параметр DM_Поворот установить не удалось')
                print(ex)
                print(ex.clsException)

            try :
                sp_height = self.space.UnboundedHeight - dist +  thickness / 2
                with trans(self.doc) :
                    fr.LookupParameter("DM_Отметка_низа").Set(sp_height)
            except Exception as ex:
                print('Параметр DM_Отметка_низа установить не удалось')
                print(ex)
                print(ex.clsException)

        return alt_res
        return ex_base

        
    def get_ceiling_contour(self, dist = 100 * dut, thickness = 2 * dut, create_shape = False) :
        """
        Создаем солид из геометрии простраства для вычисления пересечения с конструкциями.
        возвращает солид
        dist - расстояние от низа солида до верха простраства - ВАЖНО верх пространства - это в соответствии с верхом пространства и не привязан к объектам например перекрытиям. Надо уточнять
        thickness - толщина солида. по умолчанию 2 мм
        """


        # Нужен solid толщиной 2-3 мм который располагается на 100 мм ниже перекрытия. Для этого нужна верхняя грань.

        top_face = self._get_top_face()

        # print(top_face)
        #Нужно создать solid на основании этого поверхности
        try :
            cl = CorrectCurveLoops(top_face.GetEdgesAsCurveLoops())
            create_ds(cl)
            AnalyzeCurveLoops(cl)
        except Exception as ex:
            print("Ошибка  cl = top_face.GetEdgesAsCurveLoops()")
            print(ex)
            AnalyzeCurveLoops(cl)
            raise
        # pg = get_PolygonFromCurveLoops(cl)
        # cl = get_CurveLoopsFromPolygon(pg)
        try :
            solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
            sld = GeometryCreationUtilities.CreateExtrusionGeometry(cl, 
                                    XYZ.BasisZ, 
                                    thickness, 
                                    solid_opt)
            tr1 = Transform.CreateTranslation(XYZ(0,0,-dist))
            sld = SolidUtils.CreateTransformed(sld, tr1)
            if create_shape :
                create_direct_shape(sld)
        except Exception as ex :
            print("Ошибка при формирования Solid")
            
            AnalyzeCurveLoops(cl)
            raise


        return sld

    def _get_sprinkler_up(self) :
        try :
            return self.space.LookupParameter("DM_спринклер_вверх").AsElementId()
        except :
            return 
    sprinkler_up = property(_get_sprinkler_up)

    def _get_sprinkler_down(self) :
        try :
            return self.space.LookupParameter("DM_спринклер_вниз").AsElementId()
        except :
            return 
    sprinkler_down = property(_get_sprinkler_down)

    def _get_sprinkler(self) :
        try :
            return self.space.LookupParameter("DM_спринклер").AsElementId()
        except :
            return 
    sprinkler_type = property(_get_sprinkler)

   

    def _get_is_protected(self) :
        try :
            return self.space.LookupParameter("DM_Спринклеры расставлены").AsInteger()
        except :
            return False 
            pass
        return 
    def _set_is_protected(self, value) :
        try :
            with trans(doc) :
                self.space.LookupParameter("DM_Спринклеры расставлены").Set(value)
        except Exception as ex:
           
            print('**************************')
            print('1 Контрольная точка ----------')
            print('Исключение при установке значения DM_Спринклеры расставлены')
            print('ex : {} '.format(ex.clsException))
            pass
        return 

    is_protected = property(_get_is_protected, _set_is_protected)



    def _get_Name(self) :
        try :
            return en(self.space)
        except :

            pass
        return 
    Name = property(_get_Name)

    def _get_noise_level(self) :
        # Возвращает уровень шума в помещении заданного в параметре Шум_уровень_макс

        p = self.space.LookupParameter("Шум_уровень_макс")
        if p :
            return p.AsDouble()


    noise_level = property(_get_noise_level)

    def _get_loud_speakers(self) :
        if not hasattr(self.app, "_loud_speakers") :
            self.app._find_loud_speakers()

        if not self.space.Number in self.app._loud_speakers :
            return []

        else :
            return self.app._loud_speakers[self.space.Number]

        
        return []

    loud_speakers = property(_get_loud_speakers)

    def calc_sound_level(self, p) :
        # Рассчитываем уровень звука в определенной точке комнаты
        # p - в виде XYZ()

        levels = []

        for ls in self.loud_speakers :
            levels.append(ls.calc_sound_level_point(p))

        # print(levels)

        sllog = sum([10** (0.1 * sl) for sl in levels])
        # print(sllog)

        complex_level = 10 * math.log10(sllog)
        # print(complex_level)
        return complex_level

    def _get_points_inside(self) :
        # Составление списка точек внутри контура помещения
        size = 250 * dut
        size_2 = size / 2

        contour = self.get_contours_polygon()
        env = contour.EnvelopeInternal
        steps_x = math.floor(env.Width / (size * dut))
        steps_y = math.floor(env.Height / (size * dut))

        xs = [env.MinX + size_2 + size * step for step in range(int(steps_x))]
        ys = [env.MinY + size_2 +  size * step for step in range(int(steps_y))]
	
        pnts = [geoms.Point(x,y) for x, y in itertools.product(xs, ys)]
        pnts = [p for p in pnts if contour.Contains(p)]
        return pnts 

    def calc_sound_level_points(self) :
        # вычисляем уровень звука в каждой точке помещения

        pnts = self._get_points_inside() 

        pnts_xyz = [XYZ(p.X, p.Y,0) for p in pnts]

        res =  []

        for p in pnts_xyz :
            try :
                res.append((p, self.calc_sound_level(p)))
            except :
                pass 
        return res

    def draw_sound_level_images(self) :
        import System
        points = self.calc_sound_level_points()
        min_level = self.noise_level + 15

        p = points[0][0]
        slen = 250 * dut
        slen_2 = slen /2

        p1 = XYZ(p.X-slen_2, p.Y-slen_2, 0)
        p2 = p1 + XYZ.BasisY * slen
        p3 = p2 + XYZ.BasisX * slen
        p4 = p3 - XYZ.BasisY * slen
        
        lines = [Line.CreateBound(p1, p2),
        Line.CreateBound(p2, p3),
        Line.CreateBound(p3, p4),
        Line.CreateBound(p4, p1)]
            
        cl = CurveLoop()
        reg_type_id = ElementId(29560)
        
        for l in lines : 
            cl.Append(l)
            
        loops = System.Array[CurveLoop]([cl])
            
        view = uidoc.ActiveView

        ogs = OverrideGraphicSettings()

        
        with trans(doc) :
            fr = FilledRegion.Create(doc, reg_type_id, view.Id, loops)

            for p0 in points[:] :

                sl = p0[1]
                dlevel = sl - min_level
                print(dlevel, sl)
                dp = p0[0] - p 
                new_el_id = ElementTransformUtils.CopyElement(self.doc, fr.Id, dp)[0]

                if dlevel > 30 :
                    oc = 0
                    gc = 100

                    color = Color(oc, gc, oc)
                elif dlevel > 5 :
                    gc = 100 +  150 * (30-dlevel) / 25
                    oc = 0    
                    color = Color(oc, gc, oc)
                elif dlevel > 0 :
                    gc = 255
                    oc = ((5-dlevel) / 5) * 255
                    color = Color(oc, gc, oc)


                elif dlevel < -0.1 :
                    oc = 250 + dlevel * 10 
                    if oc > 255 :
                        oc = 255
                    if oc < 0 :
                        oc = 0
                    color = Color (255, oc, oc)
                else :
                    color = Color(255, 255, 255)
                ogs.SetSurfaceForegroundPatternColor(color)
                view.SetElementOverrides(new_el_id, ogs)

            doc.Delete(fr.Id)

                
class dm_Space_linked(dm_Space) :
    def __init__(self, s, app = None, link = None) :
        super(dm_Space_linked, self).__init__(s, app)
        self.link = link

    def get_contours(self) :
        trans = self.link.GetTotalTransform()
        _g = self.space.Geometry[Options()]
        g = _g.GetTransformed(trans)
        
        vz = XYZ.BasisZ
        wf = None
        for s in g :
            if type(s) == Solid :
                for f in s.Faces :
                    try :
                        if f.FaceNormal.IsAlmostEqualTo(vz) :
                            wf = f
                    except :
                        pass
        if wf :

            return wf.GetEdgesAsCurveLoops()

        
class dmLoudSpeaker(object) :
    # Класс для работы с громкоговорителями
    def __init__(self, e, app = None) :
        self.e = e 
        self.app = app

    def _get_power(self) :
        # Возвращает мощность на которую включен громкоговоритель
        if hasattr(self, "_power") :
            return self._power 
        param = self.e.LookupParameter("ADSK_Полная мощность")
        
        if param :
            self._power = param.AsDouble() / 10.763910416709722
            return self._power
            

    def _set_power(self, v) :
        param = self.e.LookupParameter("ADSK_Полная мощность")
        if param :
            try :
                param.Set(v * 10.763910416709722)
            except :
                if not self.app : return 
                with trans(self.app.doc) :
                    param.Set(v * 10.763910416709722)

    power = property(_get_power, _set_power)

    def _get_base_sound_level(self) :
        # Возвращает базовый уровень звука для оповещателя
        # подразумевается что он хранится в параметре Базовый_уровень_звука_1Вт
        try :
            return self._base_level 
        except :
            param = self.e.LookupParameter("Базовый_уровень_звука_1Вт")
            if param :
                self._base_level =  param.AsDouble()
                return self._base_level
            else :
                return 91
    base_sound_level = property(_get_base_sound_level)

    def _get_sound_level(self) :
        try :
            power = self.power
            bsl = self.base_sound_level

            return bsl + 10 * math.log10(power)
        except Exception as ex:
            print(power, bsl)
            print(ex)
            return

    sound_level = property(_get_sound_level)

    def calc_sound_level_distance(self, l) :
        # Расчитываем уровень звука  на расстоянии l, l в миллиметрах
        sl = self.sound_level
        dist = l / 1000 - 1
        if dist <= 0 :
            dist = 0.1
        return sl - 20 * math.log10(dist)

    def calc_sound_level_point(self, p, dh = 1500) :
        # расчитывает уровень звука который будет создавать громкоговорить
        # в конкретной точке при этом не будет учитываться реальная координата Z
        # При этом будет считаться что разница между громкоговорителем и плоскостью
        # составляет h в миллиметрах

        p0 = self.e.Location.Point
        ps = XYZ(p0.X, p0.Y,0)
        p2 = XYZ(p.X, p.Y, 0)

        dist = ps.DistanceTo(p2)
        dist = (dist**2 + (dh * dut)) ** 0.5 / dut 

        sound_level = self.calc_sound_level_distance(dist)
        return sound_level



    

    def __repr__(self) :
        return "Громкоговоритель, мощность {}".format(self.power)


last_app = None 

class dmLinkedElement(object) :
    def __init__(self, e, linst) :
        self.e = e
        self.doc = linst.doc
        self.link_instance = linst
        # ceil_distance - рассторяние на которое будет увеличена высота воздуховода
        self.ceil_distance = 195 * dut 
    def __repr__(self) :
        s = """
        Элемент базовый из вставленного файла
        {}
        {}
        """.format(self.e.Id, self.e.Id)
        return s

    def _get_geometry(self) :
        return self.e.Geometry[Options()].GetTransformed(self.link_instance.total_transform)
    
    geometry = property(_get_geometry)

    def create_ds(self) :
        with trans(self.doc) :    
            ds = create_ds(self.geometry)
            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            except Exception as ex:
                print(ex)
                pass
        return ds
    
    def modify_solids(self) :
        """
        ***************************************************************
        * Вычисляет измененную геометрию воздуховода или
        * 
        * 
        ***************************************************************
        """

        # Создать плоскость для проецирования
        # print(self.e.Location)

        g_solid = [g for g in self.geometry if isinstance(g, Solid)]
        g_solid = max(g_solid, key = lambda x : x.Volume)
        # print(g_solid)
        # print(g_solid.Volume)

        if isinstance(self.e.Location, LocationCurve) :
            location = self.e.Location.Curve
            dr = location.Direction
            if abs(dr.Z) > 0.95 :
                location = location.GetEndPoint(0)
        elif isinstance(self.e.Location, LocationPoint) :
            location = self.e.Location.Point

        if isinstance(location, Curve) :
            
            l = self.e.Location.Curve.CreateTransformed(self.link_instance.total_transform)
            p1 = l.GetEndPoint(0)
            p2 = l.GetEndPoint(1)

            d = p2- p1 
            d_ = XYZ(d.Y, -d.X, 0)
            p3 = p1 + d_.Normalize()

            valign = self.e.LookupParameter("Выравнивание по вертикали")
            valign_v = valign.AsInteger()

            diam = self.e.LookupParameter("Диаметр")
            width = self.e.LookupParameter("Ширина")
            height = self.e.LookupParameter("Высота")


            if diam :
                diam_v = diam.AsDouble()
                dy_b = XYZ(0,0, -diam_v)
                dy_t = XYZ(0,0,diam_v + self.ceil_distance)

                if valign_v == 0 :  
                    dy_b = XYZ(0,0, -diam_v/2)
                    dy_t = XYZ(0,0,diam_v/2 + self.ceil_distance)
                elif valign_v == 1 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, 0)
                    dy_t = XYZ(0,0,diam_v + self.ceil_distance)
                elif valign_v == 2 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, -diam_v)
                    dy_t = XYZ(0,0, self.ceil_distance)
            elif height :

                if valign_v == 0 :           
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, -height_v/2)
                    dy_t = XYZ(0,0,height_v/2 + self.ceil_distance)
                elif valign_v == 1 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, 0)
                    dy_t = XYZ(0,0,height_v + self.ceil_distance)
                elif valign_v == 2 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, -height_v)
                    dy_t = XYZ(0,0, self.ceil_distance)


            p1_1 = p1 + dy_b
            p2_1 = p2 + dy_b
            p3_1 = p3 + dy_b

            p1_2 = p1 + dy_t
            p2_2 = p2 + dy_t
            p3_2 = p3 + dy_t

            pl_b = Plane.CreateByThreePoints(p1_1, p2_1, p3_1)
            pl_t = Plane.CreateByThreePoints(p1_2, p2_2, p3_2)

            # with trans(self.doc) :
            #     l1 = Line.CreateBound(p1_1, p2_1)
            #     l2 = Line.CreateBound(p1_2, p2_2)
            #     ds1 = create_ds(l1)
            #     ds2 = create_ds(l2)

            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #         ds2.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #     except Exception as ex:
            #         print(ex)
            #         pass

            ex_analizer_1 = ExtrusionAnalyzer.Create(g_solid, pl_b, dy_b)
            ex_base_1 = ex_analizer_1.GetExtrusionBase()
            ex_analizer_2 = ExtrusionAnalyzer.Create(g_solid, pl_t, dy_t)
            ex_base_2 = ex_analizer_2.GetExtrusionBase()

            # with trans(self.doc) :
            #     ds1 = create_ds(ex_base_1)
            #     ds2 = create_ds(ex_base_2)

            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #         ds2.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #     except Exception as ex:
            #         print(ex)
            #         pass

            loops = System.Array[CurveLoop]([ex_base_1.GetEdgesAsCurveLoops()[0],
                                             ex_base_2.GetEdgesAsCurveLoops()[0],
                                             ])
            solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
            res_solid = GeometryCreationUtilities.CreateLoftGeometry(loops, solid_opt)

            # with trans(self.doc) :
            #     ds1 = create_ds(res_solid)


            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")

            #     except Exception as ex:
            #         print(ex)
            #         pass

        elif isinstance(location, XYZ) :
            # print("Размещение точка")

            bb = self.e.get_BoundingBox(None)
            p1 = self.link_instance.total_transform.OfPoint(bb.Min)
            p1 = XYZ(0,0, p1.Z)
            p2 = self.link_instance.total_transform.OfPoint(bb.Max)
            p2 = XYZ(0,0, p2.Z + self.ceil_distance)
            # print(p1, p2)

            pl_b = Plane.CreateByNormalAndOrigin(-XYZ.BasisZ, p1)
            pl_t = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, p2)


            ex_analizer_1 = ExtrusionAnalyzer.Create(g_solid, pl_b, -XYZ.BasisZ)
            ex_base_1 = ex_analizer_1.GetExtrusionBase()
            ex_analizer_2 = ExtrusionAnalyzer.Create(g_solid, pl_t, XYZ.BasisZ)
            ex_base_2 = ex_analizer_2.GetExtrusionBase()

            # with trans(self.doc) :
            #     ds1 = create_ds(ex_base_1)
            #     ds2 = create_ds(ex_base_2)

            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #         ds2.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #     except Exception as ex:
            #         print(ex)
            #         pass

            loops = System.Array[CurveLoop]([ex_base_1.GetEdgesAsCurveLoops()[0],
                                             ex_base_2.GetEdgesAsCurveLoops()[0],
                                             ])
            solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
            res_solid = GeometryCreationUtilities.CreateLoftGeometry(loops, solid_opt)

            # with trans(self.doc) :
            #     ds1 = create_ds(res_solid)


            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")

            #     except Exception as ex:
            #         print(ex)
            #         pass
        self.solid_mod = res_solid

    
    def create_ds_with_space(self) :
        """
        ***************************************************************
        * Создает модель с модифицированной геометрией - которая позволяет
        * определить можно ли размещать спринклер. то есть она вытянута вверх
        * так чтобы при вычитании из объема пространства воздуховод исключил зи
        * тела пространства грань которая находится над воздуховодом, если 
        * воздуховод находится слишком близко к потолкку.
        ***************************************************************
        """
        self.modify_solids()
        if not self.solid_mod : return 
        with trans(self.doc) :    
            ds = create_ds(self.solid_mod)
            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            except Exception as ex:
                print(ex)
                pass
        return ds
        

class dmLinkedDuctElement(dmLinkedElement) :
    def __init__(self, e, linst) :
        self.e = e
        self.doc = linst.doc
        self.link_instance = linst
        # ceil_distance - рассторяние на которое будет увеличена высота воздуховода
        self.ceil_distance = 195 * dut 
    def __repr__(self) :
        s = """
        Элемент воздуховода из вставленного файла
        {}
        {}
        """.format(self.e.Id, self.e.Id)
        return s

    def _get_geometry(self) :
        return self.e.Geometry[Options()].GetTransformed(self.link_instance.total_transform)
    
    geometry = property(_get_geometry)

    def create_ds(self) :
        with trans(self.doc) :    
            ds = create_ds(self.geometry)
            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Типовая модель")
            except Exception as ex:
                print(ex)
                pass
        return ds
    
    def modify_solids(self) :
        """
        ***************************************************************
        * Вычисляет измененную геометрию воздуховода или
        * 
        * 
        ***************************************************************
        """

        # Создать плоскость для проецирования
        # print(self.e.Location)

        g_solid = [g for g in self.geometry if isinstance(g, Solid)]
        g_solid = max(g_solid, key = lambda x : x.Volume)
        # print(g_solid)
        # print(g_solid.Volume)

        if isinstance(self.e.Location, LocationCurve) :
            location = self.e.Location.Curve
            dr = location.Direction
            if abs(dr.Z) > 0.95 :
                location = location.GetEndPoint(0)
        elif isinstance(self.e.Location, LocationPoint) :
            location = self.e.Location.Point

        if isinstance(location, Curve) :
            
            l = self.e.Location.Curve.CreateTransformed(self.link_instance.total_transform)
            p1 = l.GetEndPoint(0)
            p2 = l.GetEndPoint(1)

            d = p2- p1 
            d_ = XYZ(d.Y, -d.X, 0)
            p3 = p1 + d_.Normalize()

            valign = self.e.LookupParameter("Выравнивание по вертикали")
            valign_v = valign.AsInteger()

            diam = self.e.LookupParameter("Диаметр")
            width = self.e.LookupParameter("Ширина")
            height = self.e.LookupParameter("Высота")


            if diam :
                diam_v = diam.AsDouble()
                dy_b = XYZ(0,0, -diam_v)
                dy_t = XYZ(0,0,diam_v + self.ceil_distance)

                if valign_v == 0 :  
                    dy_b = XYZ(0,0, -diam_v/2)
                    dy_t = XYZ(0,0,diam_v/2 + self.ceil_distance)
                elif valign_v == 1 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, 0)
                    dy_t = XYZ(0,0,diam_v + self.ceil_distance)
                elif valign_v == 2 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, -diam_v)
                    dy_t = XYZ(0,0, self.ceil_distance)
            elif height :

                if valign_v == 0 :           
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, -height_v/2)
                    dy_t = XYZ(0,0,height_v/2 + self.ceil_distance)
                elif valign_v == 1 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, 0)
                    dy_t = XYZ(0,0,height_v + self.ceil_distance)
                elif valign_v == 2 :
                    height_v = height.AsDouble()
                    dy_b = XYZ(0,0, -height_v)
                    dy_t = XYZ(0,0, self.ceil_distance)


            p1_1 = p1 + dy_b
            p2_1 = p2 + dy_b
            p3_1 = p3 + dy_b

            p1_2 = p1 + dy_t
            p2_2 = p2 + dy_t
            p3_2 = p3 + dy_t

            pl_b = Plane.CreateByThreePoints(p1_1, p2_1, p3_1)
            pl_t = Plane.CreateByThreePoints(p1_2, p2_2, p3_2)

            # with trans(self.doc) :
            #     l1 = Line.CreateBound(p1_1, p2_1)
            #     l2 = Line.CreateBound(p1_2, p2_2)
            #     ds1 = create_ds(l1)
            #     ds2 = create_ds(l2)

            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #         ds2.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #     except Exception as ex:
            #         print(ex)
            #         pass

            ex_analizer_1 = ExtrusionAnalyzer.Create(g_solid, pl_b, dy_b)
            ex_base_1 = ex_analizer_1.GetExtrusionBase()
            ex_analizer_2 = ExtrusionAnalyzer.Create(g_solid, pl_t, dy_t)
            ex_base_2 = ex_analizer_2.GetExtrusionBase()

            # with trans(self.doc) :
            #     ds1 = create_ds(ex_base_1)
            #     ds2 = create_ds(ex_base_2)

            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #         ds2.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #     except Exception as ex:
            #         print(ex)
            #         pass

            loops = System.Array[CurveLoop]([ex_base_1.GetEdgesAsCurveLoops()[0],
                                             ex_base_2.GetEdgesAsCurveLoops()[0],
                                             ])
            solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
            res_solid = GeometryCreationUtilities.CreateLoftGeometry(loops, solid_opt)

            # with trans(self.doc) :
            #     ds1 = create_ds(res_solid)


            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")

            #     except Exception as ex:
            #         print(ex)
            #         pass

        elif isinstance(location, XYZ) :
            # print("Размещение точка")

            bb = self.e.get_BoundingBox(None)
            p1 = self.link_instance.total_transform.OfPoint(bb.Min)
            p1 = XYZ(0,0, p1.Z)
            p2 = self.link_instance.total_transform.OfPoint(bb.Max)
            p2 = XYZ(0,0, p2.Z + self.ceil_distance)
            # print(p1, p2)

            pl_b = Plane.CreateByNormalAndOrigin(-XYZ.BasisZ, p1)
            pl_t = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, p2)


            ex_analizer_1 = ExtrusionAnalyzer.Create(g_solid, pl_b, -XYZ.BasisZ)
            ex_base_1 = ex_analizer_1.GetExtrusionBase()
            ex_analizer_2 = ExtrusionAnalyzer.Create(g_solid, pl_t, XYZ.BasisZ)
            ex_base_2 = ex_analizer_2.GetExtrusionBase()

            # with trans(self.doc) :
            #     ds1 = create_ds(ex_base_1)
            #     ds2 = create_ds(ex_base_2)

            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #         ds2.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            #     except Exception as ex:
            #         print(ex)
            #         pass

            loops = System.Array[CurveLoop]([ex_base_1.GetEdgesAsCurveLoops()[0],
                                             ex_base_2.GetEdgesAsCurveLoops()[0],
                                             ])
            solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
            res_solid = GeometryCreationUtilities.CreateLoftGeometry(loops, solid_opt)

            # with trans(self.doc) :
            #     ds1 = create_ds(res_solid)


            #     try :
            #         ds1.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")

            #     except Exception as ex:
            #         print(ex)
            #         pass
        self.solid_mod = res_solid

    
    def create_ds_with_space(self) :
        """
        ***************************************************************
        * Создает модель с модифицированной геометрией - которая позволяет
        * определить можно ли размещать спринклер. то есть она вытянута вверх
        * так чтобы при вычитании из объема пространства воздуховод исключил зи
        * тела пространства грань которая находится над воздуховодом, если 
        * воздуховод находится слишком близко к потолкку.
        ***************************************************************
        """
        self.modify_solids()
        if not self.solid_mod : return 
        with trans(self.doc) :    
            ds = create_ds(self.solid_mod)
            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            except Exception as ex:
                print(ex)
                pass
        return ds
        
class dmLinkedFloorElement(dmLinkedElement) :
    def __init__(self, e, linst) :
        self.e = e
        self.doc = linst.doc
        self.link_instance = linst
        # ceil_distance - рассторяние на которое будет увеличена высота воздуховода
        self.ceil_distance = 195 * dut 
        self.height = 15000 * dut
    def __repr__(self) :
        s = """
        Элемент перекрытие из вставленного файла
        {}
        {}
        """.format(self.e.Id, self.e.Id)
        return s

    def _get_geometry(self) :
        return self.e.Geometry[Options()].GetTransformed(self.link_instance.total_transform)
    
    geometry = property(_get_geometry)

    def create_ds(self) :
        ds = create_ds(self.geometry)
        try :
            ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Перекрытие")
        except :
            with trans(self.doc) :     
                try :
                    ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Перекрытие")
                except Exception as ex:
                    print(ex)
                    pass
        return ds
    
    def modify_solids(self) :
        """
        ***************************************************************
        * Вычисляет измененную геометрию перекрытия
        * 
        * 
        ***************************************************************
        """

        # Создать плоскость для проецирования
        # print(self.e.Location)

        g_solid = [g for g in self.geometry if isinstance(g, Solid)]
        #g_solid = max(g_solid, key = lambda x : x.Volume)
        faces = []
        for s1 in g_solid :
            for f1 in s1.Faces :
                if not isinstance(f1, PlanarFace) : continue
                if f1.FaceNormal.Z < -0.1 :
                    faces.append(f1)
        shadow_solids = []
        for face in faces :
            try :
                cnt = face.GetEdgesAsCurveLoops()
                solid = GeometryCreationUtilities.CreateExtrusionGeometry(cnt, XYZ.BasisZ, self.height)
                solids = SolidUtils.SplitVolumes(solid)
                shadow_solids.extend(solids)
            except :
                print("ошибка в функции calc_faces_shadow_solids")
        
        self.solid_mod = shadow_solids


    def create_ds_with_space(self) :
        """
        ***************************************************************
        * Создает модель с модифицированной геометрией - которая позволяет
        * определить можно ли размещать спринклер. то есть она вытянута вверх
        * так чтобы при вычитании из объема пространства воздуховод исключил зи
        * тела пространства грань которая находится над воздуховодом, если 
        * воздуховод находится слишком близко к потолкку.
        ***************************************************************
        """
        self.modify_solids()
        if not self.solid_mod : return 
        with trans(self.doc) :    
            ds = create_ds(self.solid_mod)
            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Вентиляция")
            except Exception as ex:
                print(ex)
                pass
        return ds
        


class dmLinkInstance(object) :
    def __init__(self, e) :
        self.lnk = e 
        self.doc = e.Document
        self.ldoc = e.GetLinkDocument()
        self.total_transform = e.GetTotalTransform()
        self.items = None
        #Поле чтобы задать Solid для отфильтровывания объектов которые нужны
        self.FilterGeometry = None 
        self.FilterSolid = None
    def __repr__(self) :
        s = """
        Вставленная модель
        {}
        {}
        """.format(self.lnk.Name, self.ldoc.PathName)
        return s
    
    def _get_duct_elements(self) :
        fc = FilteredElementCollector(self.ldoc).OfClass(Mechanical.Duct).ToElements()
        res = [dmLinkedDuctElement(e, self) for e in fc]

        mcf = ElementMulticategoryFilter(System.Array[bic]([bic.OST_DuctFitting, bic.OST_DuctAccessory]))
        fc = FilteredElementCollector(self.ldoc).WherePasses(mcf)
        fc = fc.WhereElementIsNotElementType().ToElements()
        res1 = [dmLinkedDuctElement(e, self) for e in fc]
        res.extend(res1)
        res = sorted(res, key = lambda x : x.e.Id.IntegerValue)
        return res
    duct_elements = property(_get_duct_elements)

    def _get_duct_elements_in_solid(self) :
        # print("_get_duct_elements_in_solid")
        res = []
        if not self.FilterGeometry : return []
        inv_tr = self.total_transform.Inverse

        g1 = self.FilterGeometry.GetTransformed(inv_tr)
        bb = g1.GetBoundingBox()

        moutln = Outline(bb.Min, bb.Max)

        bbflt = BoundingBoxIntersectsFilter(moutln)

        # fc = FilteredElementCollector(self.ldoc).OfClass(Mechanical.Duct).ToElements()
        # res = [dmLinkedDuctElement(e, self) for e in fc]

        mcf = ElementMulticategoryFilter(System.Array[bic]([bic.OST_DuctCurves,
                                                            bic.OST_DuctFitting, 
                                                            bic.OST_DuctAccessory]))
        fc = FilteredElementCollector(self.ldoc).WherePasses(mcf)
        fc.WherePasses(bbflt)
        fc = fc.WhereElementIsNotElementType().ToElements()
        res = [dmLinkedDuctElement(e, self) for e in fc]
        
        res = sorted(res, key = lambda x : x.e.Id.IntegerValue)
        return res


    duct_elements_filtered = property(_get_duct_elements_in_solid)


    def _get_floors_elements(self) :
        # print("_get_duct_elements_in_solid")
        res = []

        mcf = ElementMulticategoryFilter(System.Array[bic]([bic.OST_Floors]))
        fc = FilteredElementCollector(self.ldoc).WherePasses(mcf)

        fc = fc.WhereElementIsNotElementType().ToElements()
        res = [dmLinkedFloorElement(e, self) for e in fc]
        
        res = sorted(res, key = lambda x : x.e.Id.IntegerValue)
        return res
    
    floors_elements = property(_get_floors_elements)



    def show_floors_geometry(self) :
        for f in self.floors_elements_filtered :
            print("modify_solids")
            f.modify_solids()
            
            print("ds create_ds")
            ds = create_ds(f.solid_mod)
            set_color(ds, 0, 125, 0, 75)
            ds = f.create_ds()
            set_color(ds, 125, 0, 125, 75)


    def _get_floors_elements_in_solid(self) :
        # print("_get_duct_elements_in_solid")
        res = []
        if not self.FilterGeometry : return []
        inv_tr = self.total_transform.Inverse

        g1 = self.FilterGeometry.GetTransformed(inv_tr)
        bb = g1.GetBoundingBox()

        minz = bb.Min.Z + 500 * dut 

        moutln = Outline(bb.Min, bb.Max)

        bbflt = BoundingBoxIntersectsFilter(moutln)

        # fc = FilteredElementCollector(self.ldoc).OfClass(Mechanical.Duct).ToElements()
        # res = [dmLinkedDuctElement(e, self) for e in fc]

        mcf = ElementMulticategoryFilter(System.Array[bic]([bic.OST_Floors]))
        fc = FilteredElementCollector(self.ldoc).WherePasses(mcf)
        fc.WherePasses(bbflt)
        fc = fc.WhereElementIsNotElementType().ToElements()
        fc = [e for e in fc if e.get_BoundingBox(None).Max.Z > minz ]
        res = [dmLinkedFloorElement(e, self) for e in fc]
        
        res = sorted(res, key = lambda x : x.e.Id.IntegerValue)
        return res


    floors_elements_filtered = property(_get_floors_elements_in_solid)



    

    def __getitem__(self, index) :
        e = self.ldoc.GetElement(ElementId(index))

        try :
            return dmLinkedDuctElement(e, self)
        except :
            return 
        


class dmDirectShapeSpace(object) :
    """
    ***************************************************************
    * Класс, работающий с пространствами, которые представлены
    * DirectShape в модели.
    * 
    ***************************************************************
    """   

    def __init__(self, ds, app) :
        self.ds = ds
        self.app = app 
        self.doc = ds.Document
        self._solids = None 
        
    def __repr__(self) :
        s = "Пространство DirectShape"
        return s

    def _get_solids(self) :
        if self._solids : return self._solids
        g = self.ds.Geometry[Options()]

        res = [e for e in g if isinstance(g, Solid)]
        res = [e for e in g if e.Volume > 0]
        self._solids = res 
        return self._solids
    solids = property(_get_solids)
    
    def substract_solid(self, solid) :
        import random
        res = []
        for s in self.solids :
            try :
                s1 = BooleanOperationsUtils.ExecuteBooleanOperation(s, solid, BooleanOperationsType.Difference)
                res.append(s1)
            except Exception as ex :

                print("Ошибка при вычитании солида пробуем подвигать в случайном порядке")
                print(ex)
                for i in range(10) :
                    dv = XYZ((random.random()-0.5) * 10 * dut, (random.random()-0.5) * 10 * dut, (random.random()-0.5) * 10 * dut)
                    tr1 = Transform.CreateTranslation(dv)
                    s2 = SolidUtils.CreateTrarnsformed(s, tr1)
                    try :
                        s1 = BooleanOperationsUtils.ExecuteBooleanOperation(s, solid, BooleanOperationsType.Difference)
                        res.append(s1)
                        print("Получилось")
                        break

                    except :
                        continue

        self._solids = res

    def update_geometry(self) :
        if self._solids :
            try :
                self.ds.SetShape(self._solids)
            except :
                with trans(self.doc):
                    self.ds.SetShape(self._solids)


    def _get_faces2protect(self) :
        """
        ***************************************************************
        * Возвращает список граней которые подходят для защиты спринклерами
        * 
        * 
        ***************************************************************
        """

        res = []

        for s in self.solids :
            for f in s.Faces :
                if not isinstance(f, PlanarFace) : continue

                cl_len = get_contour_length(f.GetEdgesAsCurveLoops())
                ar = cl_len / f.Area

                if f.FaceNormal.Z > 0.1 and f.Area > 2.7 and ar < 2:

                    res.append(f)

        return res
    
    faces2protect = property(_get_faces2protect)

    def calc_sprinkler_pos(self) :
        spr_pos = []

        for face in self.faces2protect :
            try :
                pg = get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                print("перед поворотом")
                a = 0
                print("Поворачиваем на {}".format(a))
                spr_pos_ = get_sprinkler_pos(pg=pg, 
                                             max_step =3500 * dut, 
                                             prot_radius = 2450*dut, rot_angle=a,
                                             allowed_buffer = -250*dut
                                             )
                spr_pos_ = get_PointsFromMultiPoint_proj(spr_pos_, face)
                spr_pos.extend(spr_pos_)

            except Exception as ex:
                print(ex)
                pass   
        self.spr_pos = spr_pos   

    def show_sprinkler_pos(self) :
        ds = create_ds(self.spr_pos)

    def create_sprinklers_copy(self, spr_id, dh = -100 * dut) :
        """
        ***************************************************************
        * Создаем спринклеры для пространства используя копирование
        * передаем Id элемента спринклера который будет копироваться.
        * а также величину смещения по высоте
        ***************************************************************
        """
        self.sprinklers = []
        tr = Transaction(self.doc)
        tr.Start('add sprinklers')
        dhv = XYZ(0,0, dh)
        sprinkler2copy = self.doc.GetElement(spr_id)
        p0 = sprinkler2copy.Location.Point

        for pos in self.spr_pos :
            pos1 = pos + dhv
            dp = pos1 - p0
            spr2 = ElementTransformUtils.CopyElement(doc, spr_id, dp) [0]
            self.sprinklers.append(spr2)

        tr.Commit()
    


    


class dmApp(object) :
    def __init__(self, doc) :
        global last_app
        self.doc = doc
        self._linked_inst_dict = None
        last_app = self
        self._prepare()
        


    def _prepare(self) :
        
        try :
            self.sprinkler_view = self.views["Потолки для спринклеров"]
        except :
            # print("Вид 'Потолки для спринклеров' не найден")
            pass
        try :
            self.sprinkler_plan_area_type = self.f_region_types['DM_Зона_размещения_спринклеров']
        except :
            pass

        try :
            self.sprinkler_covering_area_type = self.f_region_types['DM_Зона_орошения_спринклера']
        except :
            # print("Ошибка при установке sprinkler_covering_area_type")
            pass

        try :
            self.space_drafting_view_type = self.drafting_view_types['Вид узла 1']
        except :
            pass 

    
    def _get_views(self) :
        if hasattr(self, "_views") :
            return self._views
        fc = FilteredElementCollector(self.doc).OfClass(View).ToElements()
        self._views = dm_dict({e.Name : e for e in fc})
        return self._views

    views = property(_get_views)

    def _get_view_names(self) :
        return dm_list([k for k in self.views.keys()])
        
    view_names = property(_get_view_names)

    def _get_linked_files(self) :
        fc = FilteredElementCollector(self.doc).OfCategory(bic.OST_RvtLinks).WhereElementIsNotElementType().ToElements()
        return fc
    linked_files = property(_get_linked_files)

    def _get_linked_instances(self) :
        fc = FilteredElementCollector(self.doc).OfCategory(bic.OST_RvtLinks).WhereElementIsNotElementType().ToElements()
        res = [dmLinkInstance(e) for e in fc]
        return res
    linked_instances = property(_get_linked_instances)

    def _get_linked_instaces_dict(self) :
        if not self._linked_inst_dict :
            self._linked_inst_dict = {l.lnk.Name : l for l in self.linked_instances}
        return self._linked_inst_dict
    
    linked_instances_dict = property(_get_linked_instaces_dict)


    def _load_detail_linestyles(self) :
        #print("Загружаем стили линий")
        for v in self.views.values() :
            vt = type(v)
            if vt == ViewPlan or vt == ViewDrafting :
                view = v

        l = Line.CreateBound(XYZ(0,0,0), XYZ(0,1,0))
        trans = Transaction(self.doc)
        trans.Start("get_linestyles")
        
        nl = self.doc.Create.NewDetailCurve(view, l)

        lsids = nl.GetLineStyleIds()
        lss = [self.doc.GetElement(lsid) for lsid in lsids]
        self._linestyles = dm_dict({s.Name : s for s in lss})

        trans.RollBack()


    def _get_detail_linestyles(self) :
        if hasattr(self, "_linestyles") :
            return self._linestyles 
        self._load_detail_linestyles()
        return self._linestyles 

    detail_linestyles = property(_get_detail_linestyles)

    def _get_spaces(self) :
        fc = FilteredElementCollector(self.doc).OfCategory(bic.OST_MEPSpaces).ToElements()
        res = {s.Number : dm_Space(s, self) for s in fc}
        return dm_dict(res)

    spaces = property(_get_spaces)


    def _get_filled_region_types(self) :
        if not hasattr(self, "_f_region_types") :
            fc = FilteredElementCollector(self.doc).OfClass(FilledRegionType).ToElements()
            res = dm_dict({en(e) : e for e in fc})
            self._f_region_types = res
        return self._f_region_types

    f_region_types = property(_get_filled_region_types)

    def _get_drafting_view_types(self) :
        fc = FilteredElementCollector(self.doc).OfClass(ViewDrafting).FirstElement()
        valid_types = [self.doc.GetElement(eid) for eid in fc.GetValidTypes()]
        res = dm_dict({en(e) : e for e in valid_types })

        return res
    drafting_view_types = property(_get_drafting_view_types)


    def _get_levels(self) :
        fc = FilteredElementCollector(self.doc).OfClass(Level).ToElements()
        self._levels = dm_dict({en(e) : e for e in fc})
        return self._levels

    levels = property(_get_levels)

    def _get_sprinkler_types(self) :
        fc = FilteredElementCollector(self.doc).OfCategory(bic.OST_Sprinklers).WhereElementIsElementType().ToElements()
        res = dm_dict({en(e) :  e for  e in fc})
        return res 

    sprinkler_types = property(_get_sprinkler_types)

    def _get_worksets(self) :
        fc = FilteredWorksetCollector(self.doc).OfKind(WorksetKind.UserWorkset)
        return dm_dict({e.Name : e for e in fc})

    worksets = property(_get_worksets)

    def _find_loud_speakers(self) :
        # Находит громкоговорители и связывает их с помещениями. создает поле 
        # _loud_speaker которое является словарем, ключом которого является номер пространства.
        # далее методы класса dmSpace смогут обратиться к этом словарю и найти все громкоговорители, которые относятся к пространству.

        fc = FilteredElementCollector(self.doc).OfCategory(bic.OST_NurseCallDevices).WhereElementIsNotElementType().ToElements()
        self._loud_speakers = collections.defaultdict(list)

        for e in fc :
            ph = self.doc.GetElement(e.CreatedPhaseId)
            space = e.Space[ph]
            if not space : continue    
            self._loud_speakers[space.Number].append(dmLoudSpeaker(e, self))

    def _get_spaces_to_protect(self) :
        """
        ***************************************************************
        * Составляет список пространств, которые нужно защитить спринклерами
        * выбирает пространства и из них оставляет те, которые DM_Защита спринклерами стоит в Да
        * 
        ***************************************************************
        """
        fc = FilteredElementCollector(self.doc).OfCategory(bic.OST_MEPSpaces).ToElements()
        res = []
        for s in fc :
            try :
                if s.LookupParameter("DM_Защита спринклерами").AsInteger() :
                    res.append(dm_Space(s, app = self))
            except :
                pass

        return res
    spaces_to_protect = property(_get_spaces_to_protect)

    def _get_spaces_not_protected(self) :
        res = []
        for s in self.spaces_to_protect :
            if not s.is_protected :
                res.append(s)
        return res
    
    spaces_not_protected = property(_get_spaces_not_protected)

    def _get_direct_models_space(self) :
        """
        ***************************************************************
        * Возвращает список directShape, у которых DM_Тип_Обобщенной_модели
        * равен Пространство
        * 
        * 
        ***************************************************************
        """

        # if hasattr(self, "_ds_spaces") :
            
        #     return self._ds_spaces

        fc = FilteredElementCollector(self.doc).OfClass(DirectShape).ToElements()
        res = []
        for e in fc :
            try :
                if e.LookupParameter("DM_Тип_Обобщенной_модели").AsString() == "Пространство" :
                    res.append(e)
            except :
                pass
        res = [dmDirectShapeSpace(e, self) for e in res] 
        self._ds_spaces = res

        
        return self._ds_spaces
    
    ds_spaces = property(_get_direct_models_space)

    def _get_linked_floors(self) :
        for li in self.linked_instances :
            for e in li.duct_elements :
                yield e


        return 
    
    linked_floors = property(_get_linked_floors)
    


   
class dmSprinklerCalculations(object) :
    def __init__(self, pg, 
            max_step, 
            prot_radius=None, 
            rot_angle = 0, 
            base_elevation = 0,
            ref_intersector = None,
            spr_gap = 150 * dut
            ) :
        self.pg = pg
        self.max_step = max_step
        if prot_radius :
            self.prot_radius = prot_radius
        else :
            self.prot_radius = max_step * 2 ** 0.5 / 2
        self.base_elevation = base_elevation
        self.rot_angle = rot_angle
        self.ref_intersector = ref_intersector
        self.spr_gap = spr_gap
        

    def CalculatePositions(self) :    
        try :
            self.pos = get_sprinkler_pos(
                pg =self.pg, 
                max_step=self.max_step,
                prot_radius=self.prot_radius,
                rot_angle=self.rot_angle
                    )
            return self.pos
            
        except Exception as ex :
            print('Ошибка в функции CalculatePositions')
            print('\n{}\n{}'.format(ex, ex.clsException))
    
    
            raise


    def PositionsAsXYZ(self, ref_intersector = None) :
        self.posXYZ = get_PointsFromMultiPoint(self.pos, 
                                            elevation=self.base_elevation)
        pos = []
        if self.ref_intersector :
            for pnt in self.posXYZ :
                p1 = XYZ(pnt.X, pnt.Y, self.base_elevation)
                ref = self.ref_intersector.FindNearest(p1, XYZ.BasisZ)
                if ref :
                    z_ = ref.GetReference().GlobalPoint
                else :
                    z_ = XYZ(p1.X, p1.Y, self.base_elevation + 10000 * dut)
                p = XYZ(z_.X, z_.Y, z_.Z - self.spr_gap)
                pos.append(p)

        self.posXYZ = pos
        return pos

    def PositionsAsPoint(self) :
        """
        ***************************************************************
        * ВОЗВРАТ ПОЗИЦИЙ СПРИНКЛЕРОВ КАК ОБЪЕКТЫ POINT
        * вспомогательная функция для упрощения отображения в
        * DirectShape
        ***************************************************************
        """

        if not hasattr(self, 'posXYZ') :
            self.PositionsAsXYZ()
        pos = []
        for p in self.posXYZ :
            p1 = Point.Create(p)
            pos.append(p1)

        self.posPoint = pos
        return pos 


class dmSprinklerCalculations2(object) :
    def __init__(self, face, step, prot_radius, rotation = 0) :
        self.face = face
        self.step = step
        self.prot_radius = prot_radius
        self.rotation = rotation



    def draw_face(self) :
        face = create_ds(self.face)
        




        


class dmPipeLineUtils(object) :
    def __init__(self, pipe) :
        self.pipe = pipe 

    

class dmFreeSpaceSolid(object) :
    def __init__(self, sp, height = 15000*dut) :
        self.sp = sp # dmSpace
        self.doc=sp.doc
        self.app = sp.app
        self.space_solid = None
        self.parking_solid = None 
        self.height = height
        self.slabs = None
        self.wrong_shadows = []

        self.pipe_base_solid = None
        self.pipe_space_solid = None 

        
    def calc_solid(self) :
        g = self.sp.space.Geometry[Options()]	
        contour = self.sp.get_contours()	
        self.space_solid = GeometryCreationUtilities.CreateExtrusionGeometry(contour, XYZ.BasisZ, self.height)
        self.solid_mod = self.space_solid
        return self.space_solid
    
    def calc_solid_parking(self, park_height = 2350 * dut) :
        g = self.sp.space.Geometry[Options()]	
        contour = self.sp.get_contours()	
        self.parking_solid = GeometryCreationUtilities.CreateExtrusionGeometry(contour, XYZ.BasisZ, park_height)
        return self.parking_solid
    
    def take_solid_from_direct_shape(self, ds_id) :
        if isinstance(ds_id, int) :
            ds_id = ElementId(ds_id)
            el = self.doc.GetElement(ds_id)
        elif isinstance(ds_id, ElementId) :
            el = self.doc.GetElement(ds_id)
        elif isinstance(ds_id, Element) :
            el = ds_id 
            ds_id = el.Id

        g = el.Geometry[Options()]
        solids = [s for s in g if isinstance(s, Solid)]
        solids = sorted(solids, key= lambda x : x.Volume, reverse=True)

        self.space_solid = solids[0]
        self.unshadow_solid = self.space_solid

    def take_pipe_solid_from_direct_shape(self, ds_id) :
        if isinstance(ds_id, int) :
            ds_id = ElementId(ds_id)
            el = self.doc.GetElement(ds_id)
        elif isinstance(ds_id, ElementId) :
            el = self.doc.GetElement(ds_id)
        elif isinstance(ds_id, Element) :
            el = ds_id 
            ds_id = el.Id

        g = el.Geometry[Options()]
        solid = max([s for s in g if isinstance(s, Solid)], key = lambda x : x.Volume)


        

        self.pipe_base_solid = solid 
        self.pipe_space_solid = solid 

    def modify_pipe_space_for_pipelines(self, DN=150) :
        """
        ***************************************************************
        * Выполняется модификация self.pipe_base_solid для вычисления
        * пространства, пригодного для размещения труб заданного диаметра
        * 
        ***************************************************************
        """
        print("Модификация объема пространства для вычисления мест прохода труб")

        s1 = self.pipe_base_solid
        ex_height = DN/2 * dut

        ds = create_ds(s1)

        tr1 = Transaction(self.doc)
        tr1.Start('Вычисление мест для трубопроводов')

        solids = []
        solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
        print(len(list(s1.Faces)))

        faces = sorted(list(s1.Faces), key=lambda x : x.Area, reverse=True)
        total_area = sum([f.Area for f in faces])
        proc_area  = 0
        proc_faces = 0
        for f in faces[:] :
            if not isinstance(f, PlanarFace) : continue
            print(f)
            normal = -f.FaceNormal
            contour = f.GetEdgesAsCurveLoops()
            print(contour)
            try :
                s2 = GeometryCreationUtilities.CreateExtrusionGeometry(contour, normal, ex_height)
                solids.append(s2)
                #create_ds(s2)
                #print("вычитаем")
                s1_mod = BooleanOperationsUtils.ExecuteBooleanOperation(s1, s2, BooleanOperationsType.Difference)
                ds.SetShape(System.Array[GeometryObject]([s1_mod]))
                s1 = s1_mod 
                
            except Exception as ex:
                print("ошибка при формировании солида")
                print(ex)

            proc_area += f.Area
            proc_faces += 1
            if proc_area / total_area > 0.95 : break

        self.doc.Delete(ds.Id)
        tr1.Commit()

        print("Всего обработали {} граней".format(proc_faces))


        
        self.pipe_space_solid = s1
        return self.pipe_space_solid


    def show_parking_solid(self) :
        if not self.parking_solid :
            self.calc_solid_parking()
        ds = create_ds(self.parking_solid)
        set_color(ds, 0, 125, 125, 75)

    def show_space_solid(self, r=0, g=255, b =0, a = 80) :
        ds = create_ds(self.space_solid)
        set_color(ds, r, g, b, a)
        

    def substract_floors(self, update_ds = False) :
        import random
        print("Вычитаем полы")
        ss = self.space_solid
        res = []
        if update_ds :
            tr = Transaction(self.doc)
            tr.Start("Вычисление пространства")
            ds = create_ds(ss)
            print("Вычитание полов с созданием DirectShape. Id =".format(ds.Id))
        for li in self.app.linked_instances : 
            print(li)
            li.FilterGeometry = self.sp.space.Geometry[Options()] 
            ef = li.floors_elements_filtered 
            ef= sorted(ef, key=lambda x : x.e.LookupParameter("Площадь"), reverse=True)
            print(len(ef))
            for e in ef :
                try :
                    # print(e.e.Location)
                    e.ceil_distance = 20000 * dut
                    #e.create_ds()
                    
                except :
                    print("ошибкка формирования солида для потолка")
                    continue
                # print(e.solid_mod)
                
                #slds = [s for s in e.e.Geometry[Options()] if isinstance(s, Solid)]
                e.modify_solids()

                for s in e.solid_mod :
                    try :
                        ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss, s, BooleanOperationsType.Difference)
        
                    except Exception as ex :

                        print("Ошибка при вычитании геометрии полов")
                        print(ex)

                        for i in range(10) :
                            dv = XYZ((random.random()-0.) * 10 * dut, (random.random()-0.) * 10 * dut, (random.random()-0.) * 10 * dut)
                            tr1 = Transform.CreateTranslation(dv)
                            s2 = SolidUtils.CreateTransformed(s, tr1)
                            try :
                                ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss, s2, BooleanOperationsType.Difference)
                                #res.append(s1)
                                print("Получилось")
                                break

                            except :
                                print("не получилось")
                                continue

                
                if update_ds :
                    try :
                        ds.SetShape(System.Array[GeometryObject]([ss_mod]))
                        ss = ss_mod
                    except Exception as ex:
                        print("Не получилось обновить модель")
                        print(ex)
                        ds1 = create_ds(e.solid_mod)
                        set_color(ds1, 255, 0,0,0)
                        pass 
                else :
                    ss = ss_mod
                pass
        if update_ds :
            tr.RollBack()
            #tr.Commit()
        try :
            tr.RollBack()
        except :
            pass
        self.space_solid = ss 
        self.unshadow_solid = ss 
        self.pipe_base_solid = ss
        self.pipe_space_solid = ss
        return self.unshadow_solid
    
    def substract_ducts(self, update_ds = False, ceil_distance = 195 * dut) :
        pass
        import random
        print("вычитание воздуховодов")
        ss = self.space_solid
        res = []
        if update_ds :
            tr = Transaction(self.doc)
            tr.Start("Вычисление пространства с вычитанием воздуховодов")
            ds = create_ds(ss)
            print(ds.Id)
        for li in self.app.linked_instances : 
            print(li)
            li.FilterGeometry = self.sp.space.Geometry[Options()] 
            ef = li.duct_elements_filtered
            print(len(ef))
            for e in ef[:] :              
                try :
                    e.ceil_distance = ceil_distance
                    e.modify_solids()
                except :
                    print("ошибкка формирования солида для воздуховода")
                    continue
                # print(e.solid_mod)
                
                #slds = [s for s in e.e.Geometry[Options()] if isinstance(s, Solid)]

                for s in [e.solid_mod] :
                    try :
                        ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss, s, BooleanOperationsType.Difference)
        
                    except Exception as ex :

                        print("Ошибка при вычитании геометрии воздуховодов")
                        print(ex)

                        for i in range(10) :
                            dv = XYZ((random.random()-0.) * 10 * dut, (random.random()-0.) * 10 * dut, (random.random()-0.) * 10 * dut)
                            tr1 = Transform.CreateTranslation(dv)
                            s2 = SolidUtils.CreateTransformed(s, tr1)
                            try :
                                ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss, s2, BooleanOperationsType.Difference)
                                #res.append(s1)
                                print("Получилось")
                                break

                            except :
                                print("не получилось")
                                continue

                
                if update_ds :
                    try :
                        ds.SetShape(System.Array[GeometryObject]([ss_mod]))
                        ss = ss_mod
                    except Exception as ex:
                        print("Не получилось обновить модель")
                        print(ex)
                        pass 
                else :
                    ss = ss_mod
                pass
        if update_ds :
            tr.RollBack()
            #tr.Commit()
        self.unshadow_solid = ss 
        return self.unshadow_solid
    
    def substract_ducts_geometry(self, update_ds = False) :
        pass
        import random
        print("вычитание воздуховодов")
        ss = self.pipe_space_solid
        
        res = []
        if update_ds :
            tr = Transaction(self.doc)
            tr.Start("Вычисление пространства с вычитанием воздуховодов")
            ds = create_ds(ss)
            print(ds.Id)
        for li in self.app.linked_instances : 
            #print(li)
            li.FilterGeometry = self.sp.space.Geometry[Options()] 
            ef = li.duct_elements_filtered
            print(len(ef))
            for e in ef[:] :  

                g_ = list(e.e.Geometry[Options()])
                print(g_)
                g = []
                print(20*"*")
                while g_ :
                    g_1 = g_.pop()
                    print(g_1)
                    if isinstance(g_1, Solid) :
                        g.append(g_1)
                    elif isinstance(g_1, GeometryInstance):
                        g_.extend(list(g_1.GetInstanceGeometry()))
                        pass

                #ds = create_ds(g)
                #set_color(ds, 40, 150, 200, 75)
                        
                
                print(g)
                slds = [s for s in g if isinstance(s, Solid)]
                if len(slds) == 0 : continue
                print(slds)       




                #slds = [s for s in e.e.Geometry[Options()] if isinstance(s, Solid)]
                ss_mod = ss 

                for s in slds :
                    try :
                        ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss_mod, s, BooleanOperationsType.Difference)
                        
        
                    except Exception as ex :

                        print("Ошибка при вычитании геометрии воздуховодов")
                        print(ex)

                        for i in range(10) :
                            dv = XYZ((random.random()-0.) * 10 * dut, (random.random()-0.) * 10 * dut, (random.random()-0.) * 10 * dut)
                            tr1 = Transform.CreateTranslation(dv)
                            s2 = SolidUtils.CreateTransformed(s, tr1)
                            try :
                                ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss, s2, BooleanOperationsType.Difference)
                                #res.append(s1)
                                print("Получилось")
                                break

                            except :
                                print("не получилось")
                                continue

                
                if update_ds :
                    try :
                        ds.SetShape(System.Array[GeometryObject]([ss_mod]))
                        ss = ss_mod
                    except Exception as ex:
                        print("Не получилось обновить модель")
                        print(ex)
                        pass 
                else :
                    ss = ss_mod
                pass
        if update_ds :
            tr.RollBack()
            #tr.Commit()
        self.pipe_space_solid = ss 
        self.pipe_base_solid = ss
        return self.pipe_space_solid

    def substract_parking_solid(self) :
        ss = self.space_solid
        if not self.parking_solid :
            ss_p = self.calc_solid_parking()
        else :
            ss_p = self.parking_solid
        try :
            ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss, ss_p, BooleanOperationsType.Difference)
            #res.append(s1)
            print("Получилось")
            ss_p = ss_mod

        except :
            ss_p = ss_mod
            print("не получилось")

        fc = FilteredElementCollector(self.doc).OfCategory(bic.OST_Parking)
        fc = list(fc.ToElements())
        print(fc)
        print("Количество парковок {}".format(len(fc)))
        

        for e in fc :
            print(20*'-')
            print(e)
            g_ = list(e.Geometry[Options()])
            print(g_)
            g = []
            print(20*"*")
            while g_ :
                g_1 = g_.pop()
                print(g_1)
                if isinstance(g_1, Solid) :
                    g.append(g_1)
                elif isinstance(g_1, GeometryInstance):
                    g_.extend(list(g_1.GetInstanceGeometry()))
                    pass

            #ds = create_ds(g)
            #set_color(ds, 40, 150, 200, 75)
                    
            
            print(g)
            slds = [s for s in g if isinstance(s, Solid)]
            if len(slds) == 0 : continue
            print(slds)

            sld = max(slds, key= lambda x : x.Volume)
            
            try :
                #ds = create_ds(sld)
                #set_color(ds, 40, 150, 200, 75)
                ss_mod = BooleanOperationsUtils.ExecuteBooleanOperation(ss_p, sld, BooleanOperationsType.Difference)
                #print("Получилось")
                ss_p = ss_mod

            except :
                print("не получилось")

            
        
        self.space_solid = ss_p        
        self.pipe_space_solid = ss_p


    def show_pipe_space_solid(self, type_param = "Пространство;проходы_труб", color = (125, 125, 0, 75)) :
        ds = create_ds(self.pipe_space_solid)
        set_color(ds, *color)
        if type_param :
            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set(type_param)
            except :
                try :
                    with trans(self.doc) :
                        ds.LookupParameter("DM_Тип_Обобщенной_модели").Set(type_param)
                except :
                    pass

    
    def find_slabs(self, type_param = None) :
        """
            Находим все перекрытия которые пересекаются с объемом помещения
            выбираем тела этих перекрытий, вычисляем тело, которое располагается внутри пространства
            и сохраняется в список self.slabs - в списке тела Solid, которые пересекаются с объемом пространства 
            если type_param = None, тогда выбираются обобщенные модели без учета значения параметров
            если дано значение то проверяется значение параметр DM_Тип_Обобщенной_модели
        """
        fc = FilteredElementCollector(self.doc).OfClass(DirectShape).ToElements()
        g1 = []
        if not type_param :
            for e in fc :
                g = e.Geometry[Options()]	
                for s in g :
                    if type(s)== Solid :
                        s2 = BooleanOperationsUtils.ExecuteBooleanOperation(s, self.space_solid, BooleanOperationsType.Intersect)
                        if s2.Volume > 0 :
                            g1.append(s2)
        else :
            for e in fc :
                if not e.LookupParameter("DM_Тип_Обобщенной_модели").AsString() == type_param : continue
                g = e.Geometry[Options()]	
                for s in g :
                    if type(s)== Solid :
                        s2 = BooleanOperationsUtils.ExecuteBooleanOperation(s, self.space_solid, BooleanOperationsType.Intersect)
                        if s2.Volume > 0 :
                            g1.append(s2)

        self.slabs = g1
        
    def show_slabs(self, in_one = False) :
        """
            Создать директ шейп для плит которые могут быть оградителем для помещения
        """
        
        for slab in self.slabs :
            ds = create_ds(slab, ElementId(bic.OST_Floors))
            set_color(ds, 0, 255, 255, 80)
                                            
    def get_faces(self, e) :
        """
        ***************************************************************
        * Вычисление граней тела, направленных вниз
        * 
        * 
        ***************************************************************
        """
        if type(e) != Solid :
            g = e.Geometry[Options()]
        else :
            g = [e]
        res = []
        for eg in g :
            if type(eg) == Solid :
                for f in eg.Faces :
                    if type(f) == PlanarFace :
                        if f.FaceNormal.Z < -0.1 :
                            res.append(f)
        return res
        
                        
    def calc_down_faces(self) :
        """
        ***************************************************************
        * Выбираем у всех плит, которые находятся в пределах помещения все грани, которые направлены вниз
        * 
        * 
        ***************************************************************
        """
        faces = []
        for slab in self.slabs :
            fs = self.get_faces(slab)
            faces.extend(fs)

        self.slab_faces = faces

            
         
            
            
    def show_slabs_faces(self, color = (0, 0, 255, 80)) :
        """
        Создать DirectShape с найдеными гранями
        
        """
        try :
            ds = create_ds(self.slab_faces)
            set_color(ds, *color)
        except :
            for face in self.slab_faces :
                try :
                    ds = create_ds(face)
                    set_color(ds, *color)
                except :
                    pass

        
        
    def calc_faces_shadow_solids(self) :
        """
        ***************************************************************
        * Вычисление тел для вычитания из объема пространства
        * 
        * 
        ***************************************************************
        """

        shadow_solids = []
        for face in self.slab_faces :
            try :
                cnt = face.GetEdgesAsCurveLoops()
                solid = GeometryCreationUtilities.CreateExtrusionGeometry(cnt, XYZ.BasisZ, self.height)
                solids = SolidUtils.SplitVolumes(solid)
                shadow_solids.extend(solids)
            except :
                print("ошибка в функции calc_faces_shadow_solids")


        self.shadow_solids = shadow_solids

    def show_shadow_solids (self, color = (255, 0, 0, 80)) :
        for ss in self. shadow_solids :
            ds = create_ds(ss)
            set_color(ds, *color)

    def calc_unshadow_space(self) :
        res = self.space_solid

        for ss in self.shadow_solids :
            try :
                res = BooleanOperationsUtils.ExecuteBooleanOperation(res, ss, BooleanOperationsType.Difference)
            except :
                self.wrong_shadows.append(ss)

        self.unshadow_solid = res


    def show_unshadow_solid(self, color = (255, 255, 0, 80), type_param=None) :
        ds = create_ds(self.unshadow_solid)
        set_color(ds, *color)
        if type_param :
            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set(type_param)
            except :
                try :
                    with trans(self.doc) :
                        ds.LookupParameter("DM_Тип_Обобщенной_модели").Set(type_param)
                except :
                    pass
                    

    def calc_unshadow_faces(self) :
        self.unshadow_faces = []

        for face in self.unshadow_solid.Faces :
            if not isinstance(face, PlanarFace) : continue
            cl_len = get_contour_length(face.GetEdgesAsCurveLoops())
            ar = cl_len / face.Area 
            if face.FaceNormal.Z > 0.1 and face.Area > 2.7 and ar < 2 :
                
                print(cl_len, face.Area, cl_len / face.Area)
                self.unshadow_faces.append(face)

                

    def show_unshadow_faces(self) :
        for num, sf in enumerate(self.unshadow_faces) :
            ds = create_ds(sf)
            r = 50 * num % 255
            g = 25 * num % 255
            b = 70 * num % 255
            set_color(ds, r, g, b, 80)

            try :
                ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Грани;Для_защиты_спринклерами")
            except :
                try :
                    with trans(self.doc) :
                        ds.LookupParameter("DM_Тип_Обобщенной_модели").Set("Грани;Для_защиты_спринклерами")
                except :
                    pass

    def calc_sprinkler_pos(self, allowed_buffer= -100 * dut) :
        spr_pos = []

        for face in self.unshadow_faces :
            try :
                pg = get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                print("перед поворотом")
                a = self.sp.rot_angle
                print("Поворачиваем на {}".format(a))
                spr_pos_ = get_sprinkler_pos(pg=pg, max_step =3500 * dut, prot_radius = 2450*dut, rot_angle=a, allowed_buffer=allowed_buffer)
                spr_pos_ = get_PointsFromMultiPoint_proj(spr_pos_, face)
                spr_pos.extend(spr_pos_)

            except Exception as ex:
                print(ex)
                pass   
        self.spr_pos = spr_pos   

    def show_sprinkler_pos(self) :
        ds = create_ds(self.spr_pos)

    def create_sprinklers_copy(self, spr_id, dh = -250 * dut) :
        """
        ***************************************************************
        * Создаем спринклеры для пространства используя копирование
        * передаем Id элемента спринклера который будет копироваться.
        * а также величину смещения по высоте
        ***************************************************************
        """
        self.sprinklers = []
        tr = Transaction(self.doc)
        tr.Start('add sprinklers')
        dhv = XYZ(0,0, dh)
        sprinkler2copy = self.doc.GetElement(spr_id)
        p0 = sprinkler2copy.Location.Point

        for pos in self.spr_pos :
            pos1 = pos + dhv
            dp = pos1 - p0
            spr2 = ElementTransformUtils.CopyElement(doc, spr_id, dp) [0]
            self.sprinklers.append(spr2)

        tr.Commit()


class dmCreate3DViewFunc(object) :
    """
    ***************************************************************
    * Функция создания 3Д вида
    * 
    * 
    ***************************************************************
    """
    def __init__(self, doc, p)  :
        self.origin = p 

    def execute(self) :
        pass





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
        return ""
        
    def _get_id2(self) :
        return ""
    
    def _get_object1(self) :
        return 

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
            p3 = ds.LookupParameter("Комментрации")
            if p3 :
                p3.Set(self.pref)

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
            except :
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
            except :
                pass 

            t.Commit()

        return view 
    
    def create_planview_copy(self) :
        """
        ***************************************************************
        * Создание плана для отработки коллизи из копии
        * план для копии должен иметь имя которое содержит План шаблон коллизии
        * и соответственно должен быть план с соответствующим уровнем
        ***************************************************************
        """
        p1 = self.pos_transformed

        fc = FilteredElementCollector(self.doc).OfClass(Level).ToElements()

        bl = min([l for  l in fc if p1.Z - l.Elevation >= 0], key = lambda x : p1.Z - l.Elevation)
        view_types = FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()


        view_types_plans = [vt for vt in view_types if vt.ViewFamily == ViewFamily.FloorPlan]
        floor_plan_type  = view_types_plans[-1]

        fc = FilteredElementCollector(doc).OfClass(ViewPlan).ToElements()

        def pname_test(x) :
            if not re.match(".*шаблон.*", x.Name, re.I) : return False
            if not re.match(".*план.*",x.Name, re.I) : return False
            if not re.match(".*коллизии.*",x.Name, re.I) : return False
            return True
        plans = [p for p in fc if pname_test(p)]
        if len(plans) == 0 : return 
        pplan = plans[0]

        bmin = XYZ(p1.X - 20, p1.Y - 20, -10)
        bmax = XYZ(p1.X + 20, p1.Y + 20, +10)
        bb = BoundingBoxXYZ()
        bb.Min = bmin
        bb.Max = bmax

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
            try :
                nparam = view.LookupParameter("Вид_Примечание")
                nparam.Set("{}_{}".format(self.pref,self.name))
            except :
                pass 

            

            t.Commit()

        return view

  

class dmClashFile(object) :
    def __init__(self, fn, pref = "", doc = None) :
        self.pref = pref 
        if doc :
            self.doc = doc
        else :
            self.doc = uidoc.Document
        self.fn = fn
        with open(self.fn) as f:
            self.s = bs(f.read().decode("utf-8"), from_encoding="utf-8")
            
    
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

    