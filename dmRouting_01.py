#  coding: utf-8 

#import dm_connect_pipe

import System
import math
import itertools
import collections

from Autodesk.Revit.DB import *
from Autodesk.Revit import DB
import clr

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
import NetTopologySuite as nts
from NetTopologySuite.Geometries import *
import NetTopologySuite.Geometries as geoms

from dm_connect_pipe import *
from dm_connect_2 import *

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

pi2 = math.pi * 2

dut = 0.0032808398950131233

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
dsid = ElementId(bic.OST_GenericModel)


spr2diams = {
    #1 : 20 * dut,
    3 : 25 * dut,
    5 : 32 * dut,
    9 : 40 * dut,
    18 : 50 * dut,
    28 : 65 * dut,
    46 : 80 * dut,
    150 : 100 * dut,
    10000 : 150 * dut,
}

def sprNum2diam(n) :
    n1 = min(filter(lambda x : x > n, spr2diams.keys()))
    return spr2diams[n1]





def connect_pipes(p1, p2, doc) :
    c1 = {c.Id : c for c in p1.ConnectorManager.Connectors}[1]
    c2 = {c.Id : c for c in p2.ConnectorManager.Connectors}[0]
    doc.NewElbow(c1, c2)


    


        
class dmCalcSprinkler(object) :
    def __init__(self, s, calc) :
        """
        ***************************************************************
        * Класс который хранит спринклеры для расчета 
        * s - спринклер (элемент Revit)
        * calc - расчет
        ***************************************************************
        """
        self.s = s
        self.calc = calc 
        self.doc = calc.doc

    def __repr__(self) :
        return "Представление спринклера для расчетов"
    def _get_3d_point(self) :
        c = [c for c in self.s.MEPModel.ConnectorManager.Connectors]
        p = c[0].Origin
        return p
    Point3d = property(_get_3d_point)

    def _get_2d_point(self) :
        xyz = self._get_3d_point()
        x, y  = xyz.X, xyz.Y
        return XYZ(x, y, 0)
    Point2d = property(_get_2d_point)

    def _get_connector(self) :
        c = [c for c in self.s.MEPModel.ConnectorManager.Connectors][0]
        return c 
    
    Connector = property(_get_connector)


    def _get_connector_direction(self) :
        c = [c for c in self.s.MEPModel.ConnectorManager.Connectors][0]
        d = c.CoordinateSystem.BasisZ
        return d
    ConnectorDirection = property(_get_connector_direction)
    def _get_connector_size(self) :
        c = [c for c in self.s.MEPModel.ConnectorManager.Connectors][0]
        return c.Radius*2
    ConnectorDiameter = property(_get_connector_size)

    def _get_connector_origin(self) :
        c = [c for c in self.s.MEPModel.ConnectorManager.Connectors][0]
        o = c.Origin
        return o

    ConnectorOrigin = property(_get_connector_origin)

    def get_pipe_normal(self) :
        """
        ***************************************************************
        * Вычисляет нормаль к трубе идущую от спринклера
        * вычисление идет по 2d координатам.
        * 
        ***************************************************************
        """
        pass 

    def _get_connection_point(self, dist_k = 5) :
        return self.Point3d + dist_k * self.ConnectorDirection * self.ConnectorDiameter
    
    ConnectionPoint = property(_get_connection_point)

    def _show_connection_point(self) :
        self.ds_connection_point = create_ds(self.ConnectionPoint)

    def _delete_connection_point(self) :
        if self.ds_connection_point :
            with tr(self.doc) :
                self.doc.Delete(self.ds_connection_point.Id)

class dmCalcSpinklerSet(object) :
    def __init__(self, ss, calc) :

        self.sprinklers = [dmCalcSprinkler(s, calc) for s in ss]
        self.calc = calc 
        self.ds_connection_points=None
        self.doc = calc.doc

    def __repr__(self) :
        return "Набор спринклеров"
    
    def __getitem__(self, index) :
        return self.sprinklers[index]
    
    def _get_3dPoints(self) :
        return [s.Point3d for s in self.sprinklers]
    
    Points3d = property(_get_3dPoints)

    def _get_2dPoints(self) :
        return [s.Point2d for s in self.sprinklers]
    Points2d = property(_get_2dPoints)

    def show_sprinklers_connectors(self) :
        pnts =  []
        for s in self.sprinklers :
            pnts.append(s.ConnectionPoint)

        self.ds_connection_points = create_ds(pnts)

    def delete_sprinklers_connectors(self) :
        if self.ds_connection_points :
            with trans(self.doc) :
                self.doc.Delete(self.ds_connection_points.Id)


class dmCalcPipe(object) :
    def __init__(self, pipe, calc) :
        self.calc = calc 
        self.pipe = pipe
        self.diameter = pipe.LookupParameter("Диаметр").AsDouble()
    def __repr__(self) :
        return "Представление для трубы для расчета"
    
    def get_line_3d(self) :
        return self.pipe.Location.Curve
    
    def get_line_2d(self) :
        line = self.pipe.Location.Curve
        p1 = line.GetEndPoint(0)
        p2 = line.GetEndPoint(1)
        p1_ = XYZ(p1.X, p1.Y,0)
        p2_ = XYZ(p2.X, p2.Y, 0)
        res = Line.CreateBound(p1_, p2_)
        return res
    
class dmTraceSegment(object) :
    def __init__(self, trace_variant, line, dn = 40* dut, prev = None, next = None, sprinklers=[]) :
        self.trace_variant = trace_variant
        self.calc = trace_variant.calc 
        self.doc = trace_variant.doc 
        self.pipe = trace_variant.calc.pipe 
        self.start_takeoff_fitting = None #указывает на фитинг врезки начала
        self.line = line 
        self.prev_segment = prev
        self.next_segment = next 
        self.sprinklers = sprinklers
        self.start_pipe = False 
        self.dn = dn
        self.start_sprinkler = False #если нужно подключить к спринклеру
        self.start_takeoff = False # если начало подключается как врезка
        self.end_takeoff = False # если конец подключается как врезка
        

    def create_pipe(self) :
        new_id = ElementTransformUtils.CopyElement(self.doc, self.calc.pipe.Id, XYZ.Zero )[0]  
        self.pipe = self.doc.GetElement(new_id)
        self.pipe.Location.Curve = self.line 
        self.pipe.LookupParameter("Диаметр").Set(self.dn)
    
    def delete_pipe(self) :
        if not self.pipe : return 
        

        c1 = {c.Id : c for c in self.pipe.ConnectorManager.Connectors}[0]
        c2 = {c.Id : c for c in self.pipe.ConnectorManager.Connectors}[1]

        if c1.IsConnected :
            for c1_ in c1.AllRefs :
                if c1_.Owner.Id != self.pipe.Id :
                    if c1_.Owner.Category.Id.IntegerValue == int(bic.OST_PipeFitting) :
                        self.doc.Delete(c1_.Owner.Id)
        if c2.IsConnected :
            for c2_ in c2.AllRefs :
                if c2_.Owner.Id != self.pipe.Id :
                    if c2_.Owner.Category.Id.IntegerValue == int(bic.OST_PipeFitting) :
                        self.doc.Delete(c2_.Owner.Id)

        if self.pipe :
            self.doc.Delete(self.pipe.Id)
        
        

        
        

    def connect_next(self) :
        if not self.next_segment : return 
        if not self.end_takeoff :
            c1 = {c.Id : c for c in self.pipe.ConnectorManager.Connectors}[1]
            c2 = {c.Id : c for c in self.next_segment.pipe.ConnectorManager.Connectors}[0]
            self.doc.Create.NewElbowFitting(c1, c2)
        else :
            c1 = {c.Id : c for c in self.pipe.ConnectorManager.Connectors}[1]
            self.doc.Create.NewTakeoffFitting(c1, self.next_segment.pipe)



    def connect_main_pipe(self) :
        c1 = {c.Id : c for c in self.pipe.ConnectorManager.Connectors}[0]
        self.doc.Create.NewTakeoffFitting(c1, self.calc.pipe)

    def connect_sprinkler(self) :
        print('проверка на спринклер')
        if not self.start_sprinkler : return 
        print("подлючаем спринклер")
        c1 = {c.Id : c for c in self.pipe.ConnectorManager.Connectors}[0]
        c2 = self.prev_segment.Connector
        c1.ConnectTo(c2)




        
        








class dmTraceVariant(object) :
    """
    ***************************************************************
    * Представляет вариант расчета трассировки.
    * calc - расчет который содержит исходные данные
    * base_sprinkler - спринклер от которого будет строиться прямая ветка
    ***************************************************************
    """
    def __init__(self, calc, base_sprinkler, normal = True) :
        self.calc = calc
        self.base_sprinkler = base_sprinkler
        self.normal = normal #Ветка направлена вдоль подключаемой трубы или поперек
        # normal = True - по нормали, normal = False  - ветка направлена вдоль трубы.
        self.trace_lines = []
        self.trace_ds = None
        self.main_line = None 
        self.doc = calc.doc
        self.created_pipes = None 
        self._connection_point = None 
        self.dn = sprNum2diam(len(calc.sprinklers))
        self.do_precalc()
        
        

    def __repr__(self) :
        s = """
        ***************************************************************
        * Вариант трассировки ветки спринклерного трубопровода
        * 
        * 
        ***************************************************************
        """
        return s

    def do_precalc(self) :
        """
        ***************************************************************
        * Выполнение предварительного расчета для оценки оптимальности
        * варианта
        * 
        ***************************************************************
        """

        # 1. Составление списка спринклеров 
        pipe_line2d = self.calc.calc_pipe.get_line_2d()
        pipe_line3d = self.calc.calc_pipe.get_line_3d()

        if self.normal :
            trf = Transform.CreateRotation(XYZ.BasisZ, math.pi/2)
            ldirection = trf.OfVector(pipe_line2d.Direction)
        else :
            ldirection = pipe_line2d.Direction 

        base_line = Line.CreateUnbound(self.base_sprinkler.Point2d, ldirection)
        pnts = [base_line.Project(s.Point2d).XYZPoint for s in self.calc.sprinklersSet]
        pnts = sorted(pnts, key= lambda x : base_line.Project(x).Parameter)

        pp = self.base_sprinkler.Point2d
        for p in pnts :
            print(base_line.Project(p).Parameter)
            print(pp.DistanceTo(p))

        endp = [pnts[0], pnts[-1]]

        p1 = min(endp, key = lambda x : base_line.Distance(x))
        endp.remove(p1)
        p2 = endp[0]
        
        p0 = pipe_line2d.Project(p1).XYZPoint

        p3 = base_line.Project(p0).XYZPoint


        p1 = min([p3, p1], key = lambda x : p0.DistanceTo(x))


        l2 = Line.CreateBound(p1, p0)
        l1 = Line.CreateBound(p2, p1)



        create_ds([p1, p2, p0, p3, l2, l1])
        create_ds(pnts)



        return 

        p0 = self.base_sprinkler.Point2d

        pl2d = Line.CreateUnbound(pipe_line2d.GetEndPoint(0), pipe_line2d.Direction)
        pl3d = Line.CreateUnbound(pipe_line3d.GetEndPoint(0), pipe_line3d.Direction)

        pr_res = pipe_line2d.Project(p0)
        p1 = pr_res.XYZPoint
        self.startPoint3d = pipe_line3d.Project(p1).XYZPoint

        pr_res = pl2d.Project(p0)
        p1 = pr_res.XYZPoint
        self.startPoint3d = pl3d.Project(p1).XYZPoint

        _p1, _p2, _pd = pipe_line3d.GetEndPoint(0), pipe_line3d.GetEndPoint(1), pipe_line3d.Direction
        _p1, _p2 = _p1 + 25 * dut * _pd, _p2-25*dut*_pd
        _l1 = Line.CreateBound(_p1, _p2)

        self._connection_point2 = _l1.Project(p0).XYZPoint #Точка в месте подключения

        self._connection_point = p1 
        d1 = p1 - p0 

        u_line = Line.CreateUnbound(p0, d1)
        self.u_line = u_line 


        projs = []

        for s in self.calc.sprinklersSet :
            p2 = s.Point2d
            p2_ = u_line.Project(p2).XYZPoint
            projs.append((p2_, s))
            try :
                l2 = Line.CreateBound(p2, p2_)
                self.trace_lines.append(l2)
            except :
                pass

        projs = sorted(projs, key = lambda x : p1.DistanceTo(x[0]))

        l1 = Line.CreateBound(p1, projs[-1][0])

        self.startPoint2d = p1
        
        self.d1 = (-d1).Normalize()
        self.trace_lines.append(l1)
        self.sorted_sprinklers = [s[1] for s in projs]
        self.sprinkler_projections = [self.u_line.Project(s.ConnectionPoint).XYZPoint for s in self.sorted_sprinklers]
        self.middles = [0.5 * (s1 + s2) for s1, s2 in zip(self.sprinkler_projections[:-1], self.sprinkler_projections[1:])]
        self.middles += [self.sprinkler_projections[-1] + self.d1 * 0.5]
       

    def do_calc(self) :
        """
        ***************************************************************
        * Выполнение расчета трассировки 
        * 
        * 
        ***************************************************************
        """
        s0 = self.sorted_sprinklers[0]
        p0 = self.startPoint3d

        segment_ends = [p0] + self.middles
        segment_ends_ = [(p1,p2, s) for p1, p2,s in zip(segment_ends[:-1], segment_ends[1:], self.sorted_sprinklers)]

        
        
        pnts = []

        for p1_, p2_, s in segment_ends_ :
            con_point = s.ConnectionPoint

            p1 = XYZ(p1_.X, p1_.Y, con_point.Z)
            p2 = XYZ(p2_.X, p2_.Y, con_point.Z)
            pnts += [p1, p2]

        lines = []

        for p1, p2 in zip(pnts[:-1], pnts[1:]) :
            if p1.IsAlmostEqualTo(p2) : continue
            l1_u = Line.CreateUnbound(p1, self.d1)
            l1 = Line.CreateBound(p1, p2)
            lines.append(l1)

        lines_ = []
        l1 = lines.pop()

        while lines :
            l2 = lines.pop()
            if not l2.Direction.IsAlmostEqualTo(l1.Direction) :
                lines_.append(l1)
                l1 = l2 
                continue 
            else :
                l1 = Line.CreateBound(l2.GetEndPoint(0), l1.GetEndPoint(1))

        lines_.append(l1)
        if not p0.IsAlmostEqualTo(pnts[0]) :
            l1 = Line.CreateBound(p0, pnts[0])

        lines = [l1] + lines_[::-1]
        if lines[0].Length < 4 * 40 * dut :
            pass

        segments = [dmTraceSegment(self, l, dn=self.dn) for l in lines]
        for i in range (len(segments)) :
            s1 = segments[i]
            try :
                s1.next_segment = segments[i+1]
            except :
                pass 
            try :
                s1.prev_segment = segments[i-1]
            except  :
                pass

        self.base_lines = lines 
        self.segments = segments
        self.trace_lines_3d = lines 

        # теперь для спринклеров

        pnts = []
        sprinklers_lines = {}
        sprinklers_segments = []

        for s, pr_p in zip(self.sorted_sprinklers, self.sprinkler_projections):
            spr_p = s.ConnectionPoint 
            spr_o = s.ConnectorOrigin
            spr_d = s.ConnectorDirection
            sprinklers_lines[s] = []

            #Вектор из коннектора к ближайшей трубе

            d_ = spr_p - pr_p
            d = XYZ(d_.X, d_.Y, 0).Normalize()
            p0_ = self.u_line.Project(spr_p).XYZPoint
            p0 = XYZ(p0_.X, p0_.Y, spr_p.Z)

            v = p0 - spr_o 

            if (abs(v.X) + abs(v.Y)) < 0.001 :
                l1 = Line.CreateBound(spr_o, p0)
                sprinklers_lines[s].append(l1)

                next_pipe = min(segments, key = lambda x : x.line.Distance(p0))

                s_seg = dmTraceSegment(self, l1,dn = 25 * dut, prev=s, next=next_pipe, sprinklers=[s])
                s_seg.end_takeoff = True 
                s_seg.start_sprinkler = True
                
                sprinklers_segments.append(s_seg)
            else :              
                l1 = Line.CreateBound(spr_o, spr_p)
                sprinklers_lines[s].append(l1)
                d1 = spr_p-p0 
                d1n = d1.Normalize()
                p2 = spr_p + d1n * 0.5
                l2 = Line.CreateBound(p2, p0)
                sprinklers_lines[s].append(l2)

                pp = min(segments, key = lambda x : x.line.Distance(p0))

                s_seg2 = dmTraceSegment(self, l2, dn=25*dut, prev=None, next=pp)
                s_seg2.end_takeoff = True 

                s_seg1 = dmTraceSegment(self, l1, dn=25*dut, prev=s, next=s_seg2)
                s_seg1.end_takeoff = True
                s_seg1.start_sprinkler = True

                sprinklers_segments.append(s_seg2)
                sprinklers_segments.append(s_seg1)

            




            pnts.append(p0)
            pnts.append(spr_p)



        self.sprinklers_lines = sprinklers_lines
        self.sprinklers_segments = sprinklers_segments
   
        # create_ds(lines)
        # create_ds(sprinklers_lines)
        # create_ds(pnts)
            
    def show_trace(self) :
        #self.trace_ds = create_ds(self.trace_lines)
        self.trace_ds = create_ds(self.trace_lines + [self._connection_point2])
        print(self._connection_point2)
       
        

    def delete_trace(self) :
        if self.trace_ds :
            tr = Transaction(self.doc)
            tr.Start("Delete trace lines")
            self.doc.Delete(self.trace_ds.Id)
            tr.Commit()
            self.trace_ds = None

    def get_score(self) :
        """
        ***************************************************************
        * Оценочный балл для трассировки, в данном случае вычисляется суммарная длина всех труб
        * 
        * 
        ***************************************************************
        """
        return sum([l.Length for l in self.trace_lines])
    
    def create_pipes(self) :
        """
        ***************************************************************
        * Создание труб которое будет отражать вариант трассировки
        * 
        * 
        ***************************************************************
        """
        
        self.created_pipes = []
        created_pipes_el = []
        with trans(self.doc) :
            for segment in self.segments :
                segment.create_pipe()

            self.segments[0].connect_main_pipe()

        with trans(self.doc) :
            for segment in self.segments :
                segment.connect_next()

        with trans(self.doc) :
            for segment in self.sprinklers_segments :
                segment.create_pipe() 

            for segment in self.sprinklers_segments :
                segment.connect_next() 
                segment.connect_sprinkler()

            




    def delete_pipes(self) :
        with trans(self.doc) :
            for segment in self.segments :
                segment.delete_pipe()

            for segment in self.sprinklers_segments :
                segment.delete_pipe()



    def _get_connection_point(self) :
        """
        ***************************************************************
        * Вычисляет точку подключения ветки к магистрали
        * 
        * 
        ***************************************************************
        """
        
        return self._connection_point
    
    connection_point  = property(_get_connection_point)

    def show_connection_point(self) :
        ds = create_ds(self.connection_point)




        



    





    

class dmCreateSprinklerLine(object) :
    """
    ***************************************************************
    * Создание ветки со спринклерами
    * 
    * 
    ***************************************************************
    """
    def __init__(self, sprinklers, pipe) :
        self.sprinklers = sprinklers
        self.doc  = pipe.Document
        self.sprinklersSet = dmCalcSpinklerSet(sprinklers, self)
        self.pipe = pipe 
        self.calc_pipe = dmCalcPipe(pipe, self)
        self.traces_variants = []
        self.line_elements = []
        
        self.optimal_trace = None 

    def __repr__(self) :
        s =  """
        ***************************************************************
        * Расчет и трассировка линии для подключения спринклеров
        * 
        * 
        ***************************************************************
        спринклеры 
        {}
        труба 
        {}
        """

        

        return s
    
    def draw_lines_2d(self) :
        l1 = self.calc_pipe.get_line_2d()
        create_ds(l1)
        pnts = self.sprinklersSet.Points2d
        create_ds(pnts) 

    def draw_lines_3d(self) :
        l1 = self.calc_pipe.get_line_3d()
        create_ds(l1)
        pnts = self.sprinklersSet.Points3d
        create_ds(pnts)

    
    def calc2dCoords(self) :
        pass

    def do_precalc(self) :
        """
        ***************************************************************
        * Выполнение предварительных расчета вариантов трассировки и выбора оптимальной
        * трассировки
        * 
        ***************************************************************
        """

        for spr in self.sprinklersSet:
            trace = dmTraceVariant(self, spr, normal=True)
            self.traces_variants.append(trace)
            # trace = dmTraceVariant(self, spr, normal=False)
            # self.traces_variants.append(trace)
            break

        self.optimal_trace = min(self.traces_variants, key = lambda x : x.get_score())

    def show_optimal_trace(self) :
        self.optimal_trace.show_trace()

    def delete_optimal_trace(self) :
        self.optimal_trace.delete_trace()

    def show_sprinkler_connect_points(self) :
        """
        ***************************************************************
        * Показать точки присоединения спринкклеров.
        * По сути - это точка уже на трубе и вычисляется на определенном расстоянии от 
        * коннектора спринклера.
        * 
        ***************************************************************
        """

        self.sprinklersSet.show_sprinklers_connectors()

    def delete_sprinkler_connect_points(self) :
        self.sprinklersSet.delete_sprinkler_connect_points()

    def create_line(self) :
        """
        ***************************************************************
        * Создание труб и фитингов и подключение созданной ветки к
        * к трубопроводу, присоединение спринклеров
        * 
        ***************************************************************
        """
        print("Создаем ветку")
        self.optimal_trace.create_pipes()
        pass 

    def delete_line(self) :
        """
        ***************************************************************
        * Удаление только что созданных объектов спринклерной ветки
        * 
        * 
        ***************************************************************
        """
        print('Удаляем ветку')
        self.optimal_trace.delete_pipes()
        pass

        




 


        





