#  coding: utf-8
import Autodesk.Revit
from Autodesk.Revit import  DB, UI 
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import System
import dm_connect_2 as dm2 
bic = BuiltInCategory
dut = 0.0032808398950131233
import clr
import json
import sys 
import os 

buffersPath = r"C:\Users\Дмитрий\System.Buffers.4.4.0\lib\netstandard2.0\System.Buffers.dll"
NTSPath = r"C:\Users\Дмитрий\nettopologysuite.2.5.0\lib\netstandard2.0\NetTopologySuite.dll"
SQLPath = r"C:\Users\Дмитрий\AppData\Roaming\Autodesk\Revit\Addins\2023\RevitPythonShell\IronPython.SQLite.dll"
currentReferences = [assembly.Location for assembly in clr.References]

stopModelNameStr = ["(ТХ)"]
pipeGap = 12.5 * dut

if buffersPath not in currentReferences :
    clr.AddReferenceToFileAndPath(buffersPath)
if NTSPath not in currentReferences :
    clr.AddReferenceToFileAndPath(NTSPath)
if SQLPath not in currentReferences :
    clr.AddReferenceToFileAndPath(SQLPath)
    clr.AddReference("IronPython.SQLite, Version=3.4.0.0, Culture=neutral, PublicKeyToken=7f709c5b713576e1" )
#clr.AddReferenceToFileAndPath(SQLPath) 
print()  
import NetTopologySuite as nts
from NetTopologySuite.Geometries import *
import NetTopologySuite.Geometries as geoms
import sqlite3 as sql

class dmNotFoundSectionInDataBaseError(Exception) :
    pass 
class dmNotFoundLevelInDataBaseError(Exception) :
    pass 
class dmNotFoundPlanInDataBaseError(Exception) :
    pass
class dmNoLevelsOfPlan(Exception) :
    pass 
class dmNotFoundLevelOfPlan(Exception) :
    pass 

from types import FunctionType
from System.Diagnostics import Stopwatch
timer = Stopwatch()
times = {}

t3 = None 
try :
    from __main__ import t3  
except :
    pass 

def profiler_(fnc) :
    return fnc
def profiler(fnc) :
    def wrapped(*args, **keywargs) :
        global times
        if not timer.IsRunning :
            timer.Start()
        start 		= timer.ElapsedMilliseconds
        retVal 		= fnc(*args, **keywargs)
        timeTaken 	= timer.ElapsedMilliseconds - start
        
        name            = fnc.__name__
        function_times 	= times.setdefault(name, [])
        function_times.append(timeTaken)
        if t3 :
            function_times 	= t3.setdefault(name, [])
            function_times.append(timeTaken)
        try :
            function_times 	= __main__.t4.setdefault(name, [])
            function_times.append(timeTaken)
        except :
            __main__.t4 = {}
            function_times 	= __main__.t4.setdefault(name, [])
            function_times.append(timeTaken)

        return retVal
    return wrapped

def printProfiling(t) :
    for name, calls in sorted(times.items(), key = lambda x : sum(x[1]), reverse= True):
        print(f"Функция : {name}")
        print(f"Вызывалась {len(calls)} раз")
        print(f"Общее время вызовов {float(sum(calls)):.1f}")
        avg = (sum(calls) / float(len(calls)))
        print(f"Макс: {float(max(calls)):.1f}, Мин: {float(min(calls)):.1f}, Среднее: {avg:.1f}")
        print()

        


class ProfilingMetaclass(type) :
    def __new__(meta, classname, bases, classDict) :
        #print(0)
        for name, item in classDict.items() :
            if isinstance(item, FunctionType) :
                #print(f"Формируется {name}")
                classDict[name] = profiler(item)
        return type.__new__(meta, classname, bases, classDict)
    
_ProfilingMetaclass = type

plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)

def printReferences() :
    print(__revit__)
    print(__revit__.ActiveUIDocument)
    print(__revit__.ActiveUIDocument.Document.PathName)
    print(50*"-")
    print("sys.path")
    for pos, fld in enumerate(sys.path, 1):
        print("{} : {}".format(pos, fld))
    print(50*'-')
    print("clr.References")
    print(50*"-")

    for assembly in clr.References :
        print(assembly.Location)
    print(50*"-")

dbConnection = None 
def createDb(dbPath) :
    conn = sql.connect(dbPath)

    qt1 = """
    CREATE TABLE PLANS (
        Plan_code    INTEGER     PRIMARY KEY
                                UNIQUE,
        Plan_name TEXT (255),
        Level_name   TEXT (1000) 
    );
    """

    qt2 = """
        CREATE TABLE Eshelons (
            Elevation_code     INTEGER PRIMARY KEY,
            centerElevation    NUMERIC,
            levelElevation     INTEGER,
            Height             NUMERIC,
            Plan_code          INTEGER REFERENCES PLANS (Plan_code),
            wallsPolygonB      BLOB,
            archPolygonB       BLOB,
            ductPolygonB       BLOB,
            pipePolygonB       BLOB,
            electricalPolygonB BLOB
        );


    """

    conn.execute(qt1)
    conn.execute(qt2)
    conn.commit()
    conn.row_factory = sql.Row
    return conn

def tryToJoinMultiLine(ml) :
    normMl = ml.Normalized()
    segments = list(normMl)
    resMl = geoms.MultiLineString.Empty
    i = 0 
    while segments :
        i += 1
        if i > 100 : raise 
        #print('итерация {}'.format(i))
        #print("количество в segments {}".format(len(segments)))
        s1 = segments.pop()
        #print("количество в segments {}".format(len(segments)))
        newLs = None 
        for s2 in segments :
            if s1.Touches(s2) :
                #print("линии пересекаются")
                segments.remove(s2)
                p0 = s1.Intersection(s2)
                p1 = s1.StartPoint if s1.EndPoint.CompareTo(p0) == 0 else s1.EndPoint
                p2 = s2.StartPoint if s2.EndPoint.CompareTo(p0) == 0 else s2.EndPoint
                newLs = geoms.LineString(
                            System.Array[geoms.Coordinate](
                                [p1.Coordinate, p2.Coordinate]))
                segments.append(newLs)
                break 
        if not newLs :
            resMl = resMl.Union(s1)
    return resMl


def getSQLConnection() :
    global dbConnection
    
    if dbConnection : 
        #print("курсор определен")
        try :
            #print("проверяем, открыто ли соединение")
            dbConnection.cursor()
            #print("соединение открыто, возвращаем существующее")
            return dbConnection
        except :
            #print("соединение закрыто, надо создать")
            pass 
    docPath = __revit__.ActiveUIDocument.Document.PathName
    fld = "\\".join(docPath.split("\\")[:-1])
    name = docPath.split("\\")[-1]
    stem = ".".join(name.split(".")[:-1])

    dbPath = fld + "\\" + stem + ".db"
    
    if not os.path.exists(dbPath) :
        #print("базу данных надо создать")
        dbConnection = createDb(dbPath)
    else :
        #print("создаем новое соединение с существующей базой")
        dbConnection = sql.connect(dbPath)
        dbConnection.row_factory = sql.Row
    return dbConnection



@contextmanager
def trans(doc, a="труба") :
    #print("новый тип транзакций  обработкой ошибки")
    tr = None 
    if not doc.IsModifiable :
        tr = Transaction(doc)
        tr.Start(a)
    try :	
        yield tr
    except Exception as ex:
        print("Ошибка транзакции\n{}".format(ex))
        
    finally :
        if tr : tr.Commit()

def lineToLineString(l) :
    """
    Преобразование Line в  LineString
    """
    p0, p1 = l.GetEndPoint(0), l.GetEndPoint(1)
    coords = System.Array[geoms.Coordinate]([
        geoms.Coordinate(p0.X, p0.Y), 
        geoms.Coordinate(p1.X, p1.Y)
    ])
    return geoms.LineString(coords)
def getParallelLineString(ls, distance) :
    p00, p01 = ls.Coordinates[:2]
    dvX     = (p01.X - p00.X) / ls.Length
    dvY     = (p01.Y - p00.Y) / ls.Length
    dvnX, dvnY = -dvY * distance, dvX * distance
    newCoords = System.Array[geoms.Coordinate]([
        geoms.Coordinate(p00.X + dvnX, p00.Y+dvnY),
        geoms.Coordinate(p01.X + dvnX, p01.Y+dvnY),
    ])
    return geoms.LineString((newCoords))



dsid = ElementId(bic.OST_GenericModel)
def create_ds(l, doc =  None) :
    if not doc :  return 
    olist = []
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
        elif type(e) == geoms.LineString  :
            pass 
        elif type(e) == geoms.Polygon :
            olist.extend(dm2.get_CurveLoopsFromPolygon(e))
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

def create_ds_safe(l, doc =  None, dp = None) :
    if not doc :  return 
    olist = []
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
        elif isinstance(e, geoms.LineString) :
            for p1, p2 in zip(e.Coordinates[:-1], e.Coordinates[1:]) :
                p1_, p2_ = XYZ(p1.X, p1.Y,0), XYZ(p2.X, p2.Y, 0)
                shapes.append(Line.CreateBound(p1_, p2_))
        elif type(e) == geoms.Polygon :
            olist.extend(dm2.get_CurveLoopsFromPolygon(e))
        elif isinstance(e, GeometryObject) :
            shapes.append(e)

    shapes_a = System.Array[GeometryObject](shapes)

    try :
        ds = DirectShape.CreateElement(doc, catid)
        for shape in shapes_a :
            try :
                ds.AppendShape([shape])
                if dp :
                    ds.Location.Move(dp)

            except :
                pass 

    except :
        with trans(doc) :
            ds = DirectShape.CreateElement(doc, catid)
            for shape in shapes_a :
                try :
                    ds.AppendShape([shape])
                except :
                    pass 
            if dp :
                ds.Location.Move(dp)

    return ds

def drawPolygonAsFilledRegion(pg, doc, view, typeId = None) :
    if not typeId :
        typeId = FilteredElementCollector(doc).OfClass(FilledRegionType).FirstElementId()
    tr = None

    if not doc.IsModifiable :
        tr = Transaction(doc, "create filled region")
        tr.Start()
        
    cls = dm2.get_CurveLoopsFromPolygon(pg)
    try :
        fr = FilledRegion.Create(doc, typeId, view.Id, cls)
    except Exception as ex:
        print(ex)
        pg = pg.Buffer(-20 * dut).Buffer(20 * dut)
        cls = dm2.get_CurveLoopsFromPolygon(pg)
        fr = FilledRegion.Create(doc, typeId, view.Id, cls)
        pass
    if tr : tr.Commit()
    return fr
	

def minMaxToSolid(minPnt, maxPnt) :
    try :
        p1 = XYZ(minPnt.X, minPnt.Y, minPnt.Z)
        p2 = XYZ(minPnt.X, maxPnt.Y, minPnt.Z)
        p3 = XYZ(maxPnt.X, maxPnt.Y, minPnt.Z)
        p4 = XYZ(maxPnt.X, minPnt.Y, minPnt.Z)
        height = max(abs(maxPnt.Z - minPnt.Z), 0.01)

        cl  = System.Array [CurveLoop]([CurveLoop.Create(System.Array[Curve](
                [Line.CreateBound(p1, p2),
                Line.CreateBound(p2, p3),
                Line.CreateBound(p3, p4),
                Line.CreateBound(p4,p1)]))])

        solid = GeometryCreationUtilities.CreateExtrusionGeometry(cl, XYZ.BasisZ,height)
    except :
        p1 = XYZ(minPnt.X, minPnt.Y, minPnt.Z)
        p2 = XYZ(minPnt.X, minPnt.Y+0.01, minPnt.Z)
        p3 = XYZ(minPnt.X+0.010, minPnt.Y+0.01, minPnt.Z)
        p4 = XYZ(minPnt.X+0.01, minPnt.Y, minPnt.Z)
        height = max(abs(maxPnt.Z - minPnt.Z), 0.01)

        cl  = System.Array [CurveLoop]([CurveLoop.Create(System.Array[Curve](
                [Line.CreateBound(p1, p2),
                Line.CreateBound(p2, p3),
                Line.CreateBound(p3, p4),
                Line.CreateBound(p4,p1)]))])

        #print("ошибка при создании солида")
        #raise
        solid = GeometryCreationUtilities.CreateExtrusionGeometry(cl, XYZ.BasisZ,height)
        


    
    return solid

def pointToSolid(pnt, size) :
    size /= 2
    p1 = pnt - XYZ(size, size, size)
    p2 = pnt + XYZ(size, size, size)
    return minMaxToSolid(p1, p2)

opt = Options()
projectionPlane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)

class dmPlanNode :
    def __init__(self, pg) :
        self.pg = pg 
        self.neighbors = []
        

class dmSplitPoint :
    def __init__(self, parameter) :
        self.parameter    = parameter     #Значение параметра точк
    def __repr__(self) :
        return "Параметр : {}\n".format(self.parameter)

class dmSegment :
    def __init__(self, param1, param2, lineSegment, solver) :
        self.lineSegment = lineSegment
        self.lineLength = lineSegment.Length 
        self.solver     = solver

        self.minSegmentLength = 150 * 3.5 * dut / self.lineLength
        self.minSegmentLengthStd = 150 * 3.5 * dut

        self.startPoint = param1
        self.endPoint   = param2
        self.startParameter2    = None #применяются для вычисления позиции 
                                        #начала отрезка в случае, если он не может совпадать с 
                                        # точкой пересечения препятстстия
        self.endParameter2      = None  #применяются для вычисления позиции 
                                        #конца отрезка в случае, если он не может совпадать с 
                                        # точкой пересечения препятстстия
        self.prev       = None
        self.next       = None 
        self.status     = None #0 - это сегмент на исходной отметке, 1 - обходной сегмент
        self.translateX = None #Компонента X вектора смещения сегмента в сторону 
        self.translateY = None #Компонента Y вектора смещения сегмента в сторону

        self.initialElevation = self.solver.workEshelon.centerElevation
    def __repr__(self) :
        return "Сегмент {}, {} статус = {}\n".format(self.startPoint, self.endPoint, self.status)
    
    def checkSegmentLength(self) :
        # print("Проверка : {}".format(self))
        # print()
        if self.status == 0 :
            # если это сегмент на исходной отметке
            if self.endPoint.parameter - self.startPoint.parameter < self.minSegmentLength :
                # print("Короткий сегмент")
                #если длина сегмента меньше чем минимальная
                #то такой сегмент надо удалить и объединить два соседних сегмента
                #если это крайний сегмент то удалять не надо, надо сделать его с нулевой 
                #длиной

                if self.startPoint.parameter == 0 :
                    self.endPoint.parameter = 0
                    return self.next
                if self.endPoint.parameter == 1 :
                    self.startPoint.parameter = 1                    
                    return None 
                #если это не крайний сегмент то надо удалить его
                
                nextSegment = self.next.next
   

                self.prev.next = self.next.next
                self.prev.endPoint = self.next.endPoint
                
                if self.next.next :
                    self.next.next.prev = self.prev 

                self.next.next = None
                self.next.prev = None 
                self.prev = None
                self.next = None
                return nextSegment
            else :
                return self.next 
        else :
            if self.endPoint.parameter - self.startPoint.parameter < self.minSegmentLength :
                return self.next
            return self.next
    def findElevation (self) :
        # return None
        initialElevation = self.solver.workEshelon.centerElevation
        ls = self.getLineString()
        found = False 
        if not hasattr(self,"_elevation") :
            #print("отметки не найдено, ищем")
            if self.status == 0 :
                #print("сегмент на свободной зоне возвращаем исходный уровень")
                found = True 
                self._elevation = self.solver.workEshelon.centerElevation
                return self._elevation
            #print("ищем уровень")
            for eshelon in self.solver.plan.getEshelonsByDistance(initialElevation) :
                print('проверяем эшелон {}'.format(eshelon))
                if ls.Within(eshelon.getFreePolygon()) :
                    print("найдено пространство")
                    found = True 
                    self._elevation = eshelon.centerElevation
                    return self._elevation
                print("идем дальше")
        else :
            #print("Отметка раньше найдена, возвращаем ранее вычисленное значение")
            return self._elevation 
        return None
    def findSideBypass_(self) :
        """
        Нахождение варианта обхода в сторону на том же уровне
        """
        step        = 50 * dut # шаг в сторону
        maxDist     = 3000 * dut # максимальная длина смещения

        p1 = self.lineSegment.PointAlong(self.startPoint.parameter)
        p2 = self.lineSegment.PointAlong(self.endPoint.parameter)

        p1 = XYZ(p1.X, p1.Y, 0)
        p2 = XYZ(p2.X, p2.Y, 0)
        dVector = p2 - p1
        dVectorE = dVector.Normalize()
        dVectorN = XYZ(dVectorE.Y, - dVectorE.X, 0)

        # Циклически проверяем возможность прокладки отрезка удаляясь от исходной 
        # позиции
        found = False 
        dist    = 100 * dut 
        
        while dist <= maxDist :
            p1_ = p1 + dVectorN * dist
            p2_ = p2 + dVectorN * dist 
            coords = System.Array[geoms.Coordinate]([
                geoms.Coordinate(p1_.X, p1_.Y),
                geoms.Coordinate(p2_.X, p2_.Y)
            ])
            newLs = geoms.LineString(coords)
            if newLs.Within(self.solver.workEshelon.getFreePolygon(150*dut)) :
                found = True 
                self.translateX = (dVectorN * dist).X
                self.translateY = (dVectorN * dist).Y
                self._elevation = self.solver.workEshelon.centerElevation
                break 
            if dist > 0 :
                dist = -dist 
            else :
                dist = -dist + step
        if not found :
            # print("Обход не найден")
            return None 
  
        else : 
            # print("Обход найден")
            # print("dist = {}".format(dist))
            # print(self.translateX, self.translateY)
            return self._elevation
        
    def findSideBypass(self) :
        """
        Нахождение варианта обхода в сторону на том же уровне
        """
        step        = 50 * dut # шаг в сторону
        maxDist     = 3000 * dut # максимальная длина смещения
        baseLs      = self.getLineString() # это вертикальная линия

        p1 = self.lineSegment.PointAlong(self.startPoint.parameter)
        p2 = self.lineSegment.PointAlong(self.endPoint.parameter)

        p1 = XYZ(p1.X, p1.Y, 0)
        p2 = XYZ(p2.X, p2.Y, 0)
        dVector = p2 - p1
        dVectorE = dVector.Normalize()
        dVectorN = XYZ(dVectorE.Y, - dVectorE.X, 0)

        # Циклически проверяем возможность прокладки отрезка удаляясь от исходной 
        # позиции
        found = False 
        dist    = 100 * dut 

        
        def getNextPosition() :
            startElevation = self.initialElevation
            dist = 100 * dut 
            vertElevations  = self.solver.plan.getEshelonsByDistance(startElevation)
            vertEshelon = next(vertElevations)

            if not hasattr(self,"_elevation") :
                #print("отметки не найдено, ищем")
                if self.status == 0 :
                    #print("сегмент на свободной зоне возвращаем исходный уровень")
                    found = True 
                    self._elevation = self.solver.workEshelon.centerElevation
                    return self._elevation
                
            for eshelon in self.solver.plan.getEshelonsByDistance(startElevation) :
                if abs(startElevation - eshelon.centerElevation) < 100 * dut : continue 
                yield baseLs, eshelon, (0.,0.)       # выше


            
            

            while dist <= maxDist :
                p1_ = p1 + dVectorN * dist
                p2_ = p2 + dVectorN * dist 
                coords = System.Array[geoms.Coordinate]([
                    geoms.Coordinate(p1_.X, p1_.Y),
                    geoms.Coordinate(p2_.X, p2_.Y)
                ])

                p1_n = p1 - dVectorN * dist
                p2_n = p2 - dVectorN * dist 
                coordsN = System.Array[geoms.Coordinate]([
                    geoms.Coordinate(p1_n.X, p1_n.Y),
                    geoms.Coordinate(p2_n.X, p2_n.Y)
                ])

                newLs   = geoms.LineString(coords)
                newLsN  = geoms.LineString(coordsN)

                newEshelon      = next(self.solver.plan.getEshelonsByDistance(startElevation + dist * 0.5))
                newEshelon60      = next(self.solver.plan.getEshelonsByDistance(startElevation + dist))
                newEshelon60Dn    = next(self.solver.plan.getEshelonsByDistance(startElevation - dist))
                newEshelonDn    = next(self.solver.plan.getEshelonsByDistance(startElevation - dist * 0.5))
                newVector   = ((dVectorN * dist).X, (dVectorN * dist).Y)
                newVectorN  = (-(dVectorN * dist).X, -(dVectorN * dist).Y)

                yield baseLs, newEshelon, (0.,0.)       # выше
                yield baseLs, newEshelonDn, (0.,0.)     # ниже
                yield baseLs, newEshelon60, (0.,0.)       # выше
                yield baseLs, newEshelon60Dn, (0.,0.)     # ниже
                yield newLs, self.solver.workEshelon, newVector     #В сторону на уровне
                yield newLsN, self.solver.workEshelon, newVectorN   #В другую сторону на уровне

                yield newLs, newEshelon60, newVector            # в сторону выше под 60 град 
                yield newLsN, newEshelon60, newVectorN          # в другую сторону выше под 60 град 

                yield newLs, newEshelon60Dn, newVector          # сторону ниже под 60 град
                yield newLsN, newEshelon60Dn, newVectorN        # в др. сторону ниже под 60 град

                yield newLs, newEshelonDn, newVector            # сторону ниже под 45 град
                yield newLsN, newEshelonDn, newVectorN            # в др. сторону ниже под 45 град

                yield newLs, newEshelon, newVector 
                yield newLsN, newEshelon, newVectorN


                dist = dist + step

        for ls, eshelon, vec in getNextPosition() :
            # print(ls, eshelon, vec)
            if ls.Within(eshelon.getFreePolygon(150*dut)) :
                print("позицию нашли")
                print(vec)
                found = True 
                self.translateX = vec[0]
                self.translateY = vec[1]
                self._elevation = eshelon.centerElevation
                break 


            
        if not found :
            print("Обход не найден")
            return None 
  
        else : 
            print("Обход найден")
            # print("dist = {}".format(dist))
            # print(self.translateX, self.translateY)
            return self._elevation



        

        

    def showSegment(self) :
        elevation = self.findElevation()
        dp = XYZ(0,0, elevation)
        ls = self.getLineString()
        ds = create_ds_safe(ls, self.solver.doc, dp)

    def getLineString(self) :
        if self.startParameter2 :
            p1 = self.lineSegment.PointAlong(self.startParameter2)
        else :
            p1 = self.lineSegment.PointAlong(self.startPoint.parameter)
        if self.endParameter2 :
            p2 = self.lineSegment.PointAlong(self.endParameter2)
        else :
            p2 = self.lineSegment.PointAlong(self.endPoint.parameter)

        if not self.translateX is None :
            #Сюда вставляем код для смещения сегмента
            p1 = geoms.Coordinate(p1.X + self.translateX, p1.Y + self.translateY)
            p2 = geoms.Coordinate(p2.X + self.translateX, p2.Y + self.translateY)
            pass

        coords = System.Array[geoms.Coordinate]([p1, p2])
        ls = geoms.LineString(coords)
        return ls
    def getLine(self) :
        """
        вычисляет Line для сегмента
        если отметка не найдена, то возвращаем None
        """
        if self.findElevation() is None :
            print("getLine")
            return None 

        if self.startParameter2 :
            _p1 = self.lineSegment.PointAlong(self.startParameter2)
        else :
            _p1 = self.lineSegment.PointAlong(self.startPoint.parameter)
        if self.endParameter2 :
            _p2 = self.lineSegment.PointAlong(self.endParameter2)
        else :
            _p2 = self.lineSegment.PointAlong(self.endPoint.parameter)

        if self.translateX is not None :
            # сюда вставляем код для смещения сегмента
            # print("Делаем линию со смещением в сторону")
            _p1 = geoms.Coordinate(_p1.X + self.translateX, _p1.Y + self.translateY)
            _p2 = geoms.Coordinate(_p2.X + self.translateX, _p2.Y + self.translateY)
        else :
            # print("без смещения в сторону")
            pass 


        p1 = XYZ(_p1.X, _p1.Y, self.findElevation())
        p2 = XYZ(_p2.X, _p2.Y, self.findElevation())
        try :
            # print("формирование линии без ошибок")
            return Line.CreateBound(p1, p2)
        except :
            # print("Ошибка при формировании линии")
            pass


    def checkConnectionSegment(self) :
        """
        Проверяем, чтобы вертикальный сегменты был достаточной длины чтобы разместить 
        фитинги
        """
        #Проверяем только для обходных сегментов
        if self.status == 0 : 
            # print('Сегмент не обходной ничего не делаем возвращаемся')
            return
        # print("Сегмент обходной, пробуем проверить")
        thisLine = self.getLine()
        if not thisLine :
            return 
        # print("Координаты концов сегмента {}, {}".format(thisLine.GetEndPoint(0), thisLine.GetEndPoint(1)))

        if self.startPoint.parameter > 0 :
            prevSegment = self.prev.getLine()
        else :
            prevSegment = None 
        
        if self.endPoint.parameter < 1 :
            nextSegment = self.next.getLine()
        else :
            nextSegment = None 

        #Если исправляем предыдущий сегмент
        if prevSegment :
            # print("Исправляем предыдущий сегменты")
            p01 = prevSegment.GetEndPoint(1)
            p10 = thisLine.GetEndPoint(0)
            # print("Координаты конца предыдущего сегмента {}".format(p01))
            try :
                l0 = Line.CreateBound(p01, p10)
                # print("Длина соединяющего сегмента {} минимального {}".format(l0.Length/dut, self.minSegmentLengthStd/dut))

                if l0.Length < self.minSegmentLengthStd :
                    #Перемычка получается меньше, поэтому нужна корректировка
                    # положения предыдущего сегмента
                    # print('нужна корректировка')
                    #Длина смещения вычисл
                    dl = ((self.minSegmentLengthStd ** 2 - l0.Length ** 2) ** 0.5) / self.lineLength
                    # print("величина смещения {}".format(dl))
                    self.prev.endParameter2 = self.prev.endPoint.parameter -  dl 
            except :
                print("Ошибка при корректировке предыдущего сегмента для того чтобы вставить фиттинг")
                pass

        if nextSegment :

            # print("Исправляем следующий сегмент")
            p20 = nextSegment.GetEndPoint(0)
            p11 = thisLine.GetEndPoint(1)
            try :
                l2 = Line.CreateBound(p11, p20)
                # print("Длина соединяющего сегмента {} минимального {}".format(l2.Length/dut, self.minSegmentLengthStd/dut))

                if l2.Length < self.minSegmentLengthStd :
                    #Перемычка получается меньше, поэтому нужна корректировка
                    # положения предыдущего сегмента
                    # print('нужная корректировка')
                    #Длина смещения вычисл
                    dl = ((self.minSegmentLengthStd ** 2 - l2.Length ** 2) ** 0.5) / self.lineLength
                    # print("величина смещения {}".format(dl))
                    self.next.startParameter2 = self.next.startPoint.parameter +  dl 
            except :

                print("Ошибка при корректировке следующего сегмента для того чтобы вставить фиттинг")


                






    

class dmPipeLineSegmentAnalyzer :
    """
    класс для анализа сегментов трубы и корректировки сегментов
    """
    def __init__(self, pipe, solver) :
        """
        Вычисляем расположение  сегментов для трубы
        """
        self.pipe               = pipe
        self.solver             = solver
        self.minSegmentLength   = self.pipe.diameter * 3.5

    def doCalc(self) :
        print(100*"-")
        print("doCalc")
        pipeLocation = self.pipe.Location.Curve
        p1, p2 = pipeLocation.GetEndPoint(0), pipeLocation.GetEndPoint(1)
        startCoordinate = geoms.Coordinate(p1.X, p1.Y)

        pipeSegment = geoms.LineSegment(p1.X, p1.Y, p2.X, p2.Y)
        coords = System.Array[geoms.Coordinate]([
            geoms.Coordinate(p1.X, p1.Y),
            geoms.Coordinate(p2.X, p2.Y)
        ])

        eshelon = self.solver.workEshelon       
        freePg = eshelon.getFreePolygon(self.pipe.diameter)
        pipeLineString = geoms.LineString(coords)

        initialLevelSegments = pipeLineString.Intersection(freePg)
        print(initialLevelSegments)

        pipeLen = pipeSegment.Length
        projections = sorted(
            [pipeSegment.ProjectionFactor(_p0)   
             for _p0 in initialLevelSegments.Coordinates])
        
        print(projections)

        points = [dmSplitPoint(parameter) for parameter in projections]
        #Создаем сегменты и связываем их между собой
        if points[0].parameter != 0 :
            print("начинается не со свободного конца")
            #это случай, если начало трубы попадает внутрь препятствия и по сути
            #он становится первым обходным сегментом
            points = [dmSplitPoint(0)] + points
            segments = [dmSegment(pnt1, pnt2, lineSegment=pipeSegment, solver= self.solver) 
                        for pnt1, pnt2 
                        in zip(points[:-1], points[1:])]
            for status, segment in enumerate(segments,1) :
                segment.status = status %2
        else :
            # это на случай, когда добавлять в начало не надо, если
            # труба начинается на свободном пространстве

            #print("Начинается со свободного конца. ")
            segments = [dmSegment(pnt1, pnt2, lineSegment=pipeSegment, solver= self.solver) 
                        for pnt1, pnt2 
                        in zip(points[:-1], points[1:])]
            for status, segment in enumerate(segments) :
                segment.status = status % 2

        if points[-1].parameter != 1 :
            print("заканчивается в препятствии")
            # Это на тот случай, если конец трубы попадает в препятствие
            # Добавляем конечную точку
            points.append(dmSplitPoint(1))
            segment = dmSegment(points[-2],points[-1], 
                                lineSegment=pipeSegment, 
                                solver= self.solver)
            segment.status = 1
            segments.append(segment)
        print(points)
        prev = None 
        for i in range(len(segments)) :
            if i == len(segments)-1 :
                next =  None 
            else :
                next = segments[i+1]
            current = segments[i]
            current.prev = prev 
            current.next = next 
            prev = current

        i =  0
        # print("отрезки сформировали")

        # print("Делаем проверку сегментов")
        segment = segments[0]
        newSegments = [segment]
        while segment :
            i += 1
            if i > 100 : raise 
            # print(20*"-")
            # print(segment)
            # print('предыдущий')
            # print(segment.prev)
            # print("следующий")
            # print(segment.next)
            # print(20*"-")
            #segment = segment.next
            segment = segment.checkSegmentLength()
            newSegments.append(segment)

        # print("Проверка сделана")
        # print("Количество сегментов в трассе {}".format(len(segments)))
        # print("Количество сегментов в трассе {}".format(len(newSegments)))

        # print(50*"*")
        segment = segments[0]
        resSegments= []
        while segment :
            i += 1
            if i > 100 : raise 
            resSegments.append(segment)
            segment = segment.next 

        # for segment in resSegments :
        #     print(segment)

        # print(100*"*")
        # print("Нахождение отметки обхода или обходного пути")
            
        for segment in resSegments :
            print(segment.getLineString())
            elevation = segment.findSideBypass()
            # elevation = segment.findElevation()
            # if elevation is None :
            #     # print("Ищем обход в сторону")
            #     elevation = segment.findSideBypass()


            # print(elevation)
        # print(20* "*") 

        # print('Проверяем на наличие горизонтального смещения')
        # for num, segment in enumerate(resSegments) :
            # print("Проверяем сегмент {}".format(num))
            # print("смещения {} {}".format(segment.translateX, segment.translateY))
            

        # print('Проверяем на возможность минимальный вертикальный сегмента')
        for num, segment in enumerate(resSegments) :
            # print("Проверяем сегмент {}".format(num))
            segment.checkConnectionSegment()

        # segment = resSegments[0]
        # newSegments2 = [segment]
        # while segment :
        #     i += 1
        #     if i > 200 : raise 
        #     # print(20*"-")
        #     # print(segment)
        #     # print('предыдущий')
        #     # print(segment.prev)
        #     # print("следующий")
        #     # print(segment.next)
        #     # print(20*"-")
        #     #segment = segment.next
        #     segment = segment.checkSegmentLength()
        #     newSegments2.append(segment)

        # resSegments = newSegments2

        # # print("Проверка на соединяющие сегменты окончена")
        # print(100* "*")

        # for segment in resSegments :
        #     create_ds_safe(segment.getLine(), 
        #                    doc = self.solver.doc,
        #                    dp=XYZ(0,0, elevation)
        #                    )
            
        newPipes = []
        tr = Transaction(self.solver.doc, "newPipes") 
        tr.Start()
        # print(100 * "-")
        # print("создаем трубы")

        for segment in resSegments :
            newLocation = segment.getLine()
            if not newLocation :
                newPipes.append(None)
                print("не получилось получить локейшн")
                continue 
            newPipe = self.pipe.copy()
            newPipe.Location.Curve = newLocation
            newPipes.append(newPipe)

        print("трубы создали") 
        print(len(newPipes))   
        print(100 * "-")
        

        for pipe1, pipe2 in zip(newPipes[:-1], newPipes[1:]) :
            if not pipe1 or not pipe2 :
                continue
            p11 = pipe1.Location.Curve.GetEndPoint(1)
            p20 = pipe2.Location.Curve.GetEndPoint(0)
            try :
                newLocation = Line.CreateBound(p11, p20)
                newPipe = self.pipe.copy()
                newPipe.Location.Curve = newLocation
                c11 = pipe1.connectorsDict[1]
                c20 = pipe2.connectorsDict[0]
                c30 = newPipe.connectorsDict[0]
                c31 = newPipe.connectorsDict[1]
                try :
                    self.solver.doc.Create.NewElbowFitting(c11, c30)
                except :
                    pass
                try :
                    self.solver.doc.Create.NewElbowFitting(c31, c20)
                except :
                    pass
            except :
                pass
        tr.Commit()
        return resSegments
        
        








    def _getSegments(self) :
        return []
    
    segments = property(_getSegments)
        

        

class dmLinkedElement :
    def __init__(self, link, element) :
        self.link = link
        self.element = element 
    def __repr__(self) :
        return "Id - {} linkId {} категория {}".format(self.element.Id, self.link.linkInstance.Id, self.element.Category.Name)
    def getSolids(self, viewOpts=None) :
        if viewOpts :
            vopt = viewOpts
        else :
            vopt = opt 
        geometry = self.element.Geometry[vopt]
        if not geometry : return []
        geoms = [geometry.GetTransformed(self.link.Transform)]

        if isinstance(self.element, FamilyInstance) and \
                self.element.Category.Id.IntegerValue != int(bic.OST_StructuralFraming) \
                    and self.element.Category.Id.IntegerValue != int(bic.OST_Floors):
            geoms = geometry.GetTransformed(self.link.Transform)
            bb = geoms.GetBoundingBox()
            ptMin = bb.Transform.OfPoint(bb.Min)
            ptMax = bb.Transform.OfPoint(bb.Max)
            res = [minMaxToSolid(ptMin, ptMax)]
        else :
            geoms = [geometry.GetTransformed(self.link.Transform)]
            res = []
            while geoms :
                g = geoms.pop()
                if isinstance(g, Solid) :
                    res.append(g)
                elif isinstance(g, GeometryInstance) :
                    geoms.extend(list(g.GetInstanceGeometry()))
                elif isinstance(g, GeometryElement) :
                    geoms.extend(list(g))
        return res 
    
    def getSolidsSected(self, sectSolid, viewOpts=None) :
        """
        Вычисление пересечения солида элемента с заданным солидом.
        Например, может быть для вычисления части элемента который пересекается
        с эшелоном.
        """
        problem = 0
        solids2 = []
        res = self.getSolids(viewOpts)

        for solid in res :
            try :
                solid2 = None
                solid2 = BooleanOperationsUtils\
                    .ExecuteBooleanOperation(
                        sectSolid, solid, 
                            BooleanOperationsType.Intersect)
                solids2.append(solid2)

                    
            except Autodesk.Revit.Exceptions.InvalidOperationException :
                
                problem += 1
                
            except Exception as ex:
                print(ex)
                print(type(ex))
                print("{}\n{}\n{}\n---------".format(self.element.Category.Name, 
                                self.element.Id, 
                                self.link.linkInstance.Name))
                raise
                pass 
        #print("Вычисленно пересеченных солидов {}".format(len(solids2)))
        if problem :
            """
            print("{}\n{}\n{}\n---------".format(self.element.Category.Name, 
                                self.element.Id, 
                                self.link.linkInstance.Name))
            print("Количество проблем : {}".format(problem))
            print("Количество солидов : {}".format(len(res)))
            print("Количество в результате: {}".format(len(solids2)))
            for s in res :
                print(s)
            print("проблема с графикой")
            ds = create_ds_safe(res)
            #print("Id directShape = {} прекращаем".format(ds.Id))
            
            #raise 
            """
            pass
               
        return solids2
    
    def getPolygon(self, viewSolid, viewOpts=None) :
        # print("getPolygon")
        
        
        # print(self.element)
        if not isinstance(self.element, FamilyInstance) and\
            type(self.element.Location) == LocationCurve :

        #     if \
        # self.element.Category.Id.IntegerValue \
        #     in [
        #         # int(bic.OST_DuctCurves), 
        #         # int(bic.OST_DuctInsulations)
        #         ] :
        #         print("Воздуховод")
        #         # raise
        #         return geoms.Polygon.Empty
            

            # print("Создается граница для трубы и изоляции")
            # print(self.element.Category.Name)
            try :
                diameter = self.element.Diameter /2
            except Exception as ex :
                try :
                    diameter = self.element.Width /2 
                except Exception as ex:
                    # print(ex)
                    # print('ошибка при взятии размера')
                    return geoms.Polygon.Empty
                
             
            bb = viewSolid.GetBoundingBox()
            pntMin = bb.Transform.OfPoint(bb.Min)
            pntMax = bb.Transform.OfPoint(bb.Max)
            lc = self.element.Location.Curve.CreateTransformed(self.link.Transform)
            p0, p1 = lc.GetEndPoint(0), lc.GetEndPoint(1)
            lineVector = p1- p0 
            elementMaxZ = max(p0.Z, p1.Z)
            elementMinZ = min(p0.Z, p1.Z)
            resPg = geoms.Polygon.Empty
            # Первый вариант, если  труба выше или ниже эшелона...
            if elementMaxZ + diameter < pntMin.Z \
                or elementMinZ - diameter > pntMax.Z :
                return geoms.Polygon.Empty
            elif elementMaxZ - diameter > pntMax.Z \
                    or elementMinZ + diameter < pntMin.Z :
                # print("Труба пересекает эшелон")
                if lc.Direction.Z == 1 :
                    # print("Вертикально")
                    param0 = 0
                    param1 = 1
                
                elif lc.Direction.Z != 0 :
                    # print("с наклоном")
                    # print(p0.Z)
                    # print(pntMax, pntMin)
                          
                    params= sorted([(pntMax.Z - p0.Z)  / lineVector.Z,
                                (pntMin.Z - p0.Z)  / lineVector.Z])
                    
                    # print(params)

                    param0 = params[0]
                    if param0 > 1 :
                        param0 = 0.99
                    if param0 < 0 :
                        param0 = 0
                    param1 = params[1] 
                    if param1 > 1 :
                        param1 = 1
                    if param1 < 0 :
                        param1 = 0.01
                elif lc.Direction.Z == 0 :
                    # print("горизонтально")
                    param0 = 0
                    param1 = 1


                sPoint = p0 + lineVector * param0
                ePoint = p0 + lineVector * param1 

                coords = System.Array[geoms.Coordinate]([
                    Coordinate(sPoint.X, sPoint.Y),
                    Coordinate(ePoint.X, ePoint.Y)
                ])
                # print("4 GetPolygon") 
                

                # print("5 GetPolygon")   
                resPg = geoms.LineString(coords).Buffer(diameter)
                # print("6 GetPolygon") 
                # return geoms.Polygon.Empty
                return resPg

                return geoms.Polygon.Empty
            else :
                # print("Труба в пределах эшелона")

                sPoint = lc.GetEndPoint(0)
                ePoint = lc.GetEndPoint(1)
                coords = System.Array[geoms.Coordinate]([
                    Coordinate(sPoint.X, sPoint.Y),
                    Coordinate(ePoint.X, ePoint.Y)
                ])
                # print("4 GetPolygon") 
                try :
                    w = self.element.Diameter /2
                except Exception as ex:
                    # print("2 GetPolygon")
                    # print(ex)
                    w = self.element.Width /2

                # print("5 GetPolygon")   
                resPg = geoms.LineString(coords).Buffer(w)
                # print("6 GetPolygon") 
                # return geoms.Polygon.Empty
                return resPg



        else :
            # print("Создается граница для прочих элементов")
            plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
            resPg = geoms.Polygon.Empty
            for solid in self.getSolidsSected(viewSolid, viewOpts) :
                #print(solid.Volume)
                if solid.Volume < 0.0001 : continue
                #print("вычисляем полигон")
                try :
                    #print("getPolygon")
                    ea = ExtrusionAnalyzer.Create(solid, plane, XYZ.BasisZ)
                    face = ea.GetExtrusionBase()
                    pg = dm2.get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                    resPg = resPg.Union(pg)
                    if type(resPg) == geoms.GeometryCollection :
                        resPg = resPg.Buffer(0)
                except Exception as ex:
                    geometry = self.element.Geometry[opt].GetTransformed(self.link.Transform)
                    #create_ds_safe(geometry, self.link.linkInstance.Document)

                    print("исключение на элементе {}".format(self))
                    print(ex)
                    #raise
                    pass
        #print("getPolygon return {}".format(resPg))
        
        return resPg
    
    def showGeometry(self, viewOpts=None) :
        if viewOpts :
            vopt = viewOpts
        else :
            vopt = opt 
        geometry = self.element.Geometry[vopt]
        if not geometry : return []
        geoms = [geometry.GetTransformed(self.link.Transform)]
        create_ds_safe(geoms, self.link.linkInstance.Document)

        
    def showSolid(self) :
        create_ds_safe(self.getSolids(), self.link.linkInstance.Document)
    def showSolidSected(self) :
        create_ds_safe(self.getSolids(), self.link.linkInstance.Document)
    def showProjection(self) :
        create_ds_safe(self.getPolygon(), self.link.linkInstance.Document)
            


        
    

class dmLinkInstance :
    def __init__(self, linkInstance) :
        self.linkInstance = linkInstance
        self.linkDoc = linkInstance.GetLinkDocument()
        self.Transform = linkInstance.GetTotalTransform()
        self.InvTransform = self.Transform.Inverse
    def __repr__(self) :
        try :
            return "Вставленная модель {}\n".format(self.linkDoc.PathName)
        except:
            return "Вставленная модель {}\n".format(self.linkInstance.Name)
        
    def getElementsVisibleInView(self, view) :
        elements = FilteredElementCollector(self.linkDoc, view.Id)\
                .WhereElementsIsNotElementType().ToElements()
        return elements
    def getDuctElements(self) :
        
        if not self.linkDoc : return []

        pmin_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Min))
        pmax_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Max))

        pmin = XYZ(min(pmin_.X, pmax_.X), min(pmin_.Y, pmax_.Y), min(pmin_.Z, pmax_.Z))
        pmax = XYZ(max(pmin_.X, pmax_.X), max(pmin_.Y, pmax_.Y), max(pmin_.Z, pmax_.Z))


        outline = Outline(pmin, pmax)
        bbFlt = BoundingBoxIntersectsFilter (outline)

        mcatFlt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_DuctCurves, bic.OST_DuctFitting, bic.OST_DuctAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_DuctInsulations
        ]))
        elements = [dmLinkedElement(self, e) 
                        for e in FilteredElementCollector(self.linkDoc)\
                            .WherePasses(mcatFlt)\
                            .WherePasses(bbFlt)\
                            .WhereElementIsNotElementType().ToElements()]
        return elements
    
    def getPipeElements(self) :
        
        if not self.linkDoc : return []

        pmin_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Min))
        pmax_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Max))

        pmin = XYZ(min(pmin_.X, pmax_.X), min(pmin_.Y, pmax_.Y), min(pmin_.Z, pmax_.Z))
        pmax = XYZ(max(pmin_.X, pmax_.X), max(pmin_.Y, pmax_.Y), max(pmin_.Z, pmax_.Z))


        outline = Outline(pmin, pmax)
        bbFlt = BoundingBoxIntersectsFilter (outline)

        mcatFlt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_MechanicalEquipment, 
                bic.OST_PipeCurves, 
                bic.OST_PipeFitting,
                bic.OST_PipeAccessory, 
                bic.OST_PipeInsulations,
        ]))
        elements = [dmLinkedElement(self, e) 
                        for e in FilteredElementCollector(self.linkDoc)\
                            .WherePasses(mcatFlt)\
                            .WherePasses(bbFlt)\
                            .WhereElementIsNotElementType().ToElements()]
        return elements
    
    def getArchElements(self) :

        mcatFlt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_Walls, bic.OST_Columns,
                bic.OST_Ceilings, bic.OST_Ceilings, bic.OST_StructuralColumns
        ]))
        elements = [dmLinkedElement(self, e) 
                        for e in FilteredElementCollector(self.linkDoc)\
                            .WherePasses(mcatFlt)\
                            .WhereElementIsNotElementType().ToElements()]
        return elements
    


    
    def getElementsInsideBoundingBox(self, bb, flt = None) :
        #print(1)
        pmin_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Min))
        pmax_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Max))

        pmin = XYZ(min(pmin_.X, pmax_.X), min(pmin_.Y, pmax_.Y), min(pmin_.Z, pmax_.Z))
        pmax = XYZ(max(pmin_.X, pmax_.X), max(pmin_.Y, pmax_.Y), max(pmin_.Z, pmax_.Z))


        try :
            # print(pmin, pmax)
            outline = Outline(pmin, pmax)
            bbFlt = BoundingBoxIntersectsFilter (outline)
            fc = FilteredElementCollector(self.linkDoc)\
                                .WherePasses(bbFlt)
            if flt : 
                fc.WherePasses(flt)
            elements = [dmLinkedElement(self, e) 
                            for e in fc.ToElements()]
            return elements

        except Exception as ex: 
            print(ex)
            return []

    def getElectricalElements(self) :

        mcatFlt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_Walls, bic.OST_Columns,
                bic.OST_Ceilings, bic.OST_Ceilings, bic.OST_StructuralColumns
        ]))
        elements = [dmLinkedElement(self, e) 
                        for e in FilteredElementCollector(self.linkDoc)\
                            .WherePasses(mcatFlt)\
                            .WhereElementIsNotElementType().ToElements()]
        return elements
    

    


        
    def getGeometryAsSolidInsideBoundingBox(self, bb) :
        #print(1)
        pmin_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Min))
        pmax_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Max))

        pmin = XYZ(min(pmin_.X, pmax_.X), min(pmin_.Y, pmax_.Y), min(pmin_.Z, pmax_.Z))
        pmax = XYZ(max(pmin_.X, pmax_.X), max(pmin_.Y, pmax_.Y), max(pmin_.Z, pmax_.Z))


        try :
            # print(pmin, pmax)
            outline = Outline(pmin, pmax)
            bbFlt = BoundingBoxIntersectsFilter (outline)
            elements = FilteredElementCollector(self.linkDoc).WherePasses(bbFlt).ToElements()
            opt = Options()
            res = []
            for element in elements :
                #print(element)
                geometry = element.Geometry[opt]
                if not geometry : continue
                geoms = list(geometry.GetTransformed(self.Transform))
                while geoms :
                    g = geoms.pop()
                    #print(g)
                    if isinstance(g, Solid) :  res.append((element, g))
                    if isinstance(g, GeometryElement) : geoms.extend(g)
                    

            return res
        except Exception as ex: 
            print(ex)
            return []
class dmDocument :
    def __init__(self, doc) :
        self.doc = doc

    def _getLinkInstances(self) :

        links =  [dmLinkInstance(l) 
                for l in FilteredElementCollector(self.doc)\
                    .OfClass(RevitLinkInstance).ToElements()]
        return [l for l in links if l.linkDoc]
    linkInstances = property(_getLinkInstances)

import heapq, math 

class dmNode:
    def __init__(self, graph, parent, pnt, step) :
        self.graph = graph
        self.pnt = pnt
        self.step = step 
        self.g = 0
        self.h = 0
        if parent :
            self.parentDir = (pnt - parent.pnt).Normalize()
        else :
            self.parentDir = XYZ.Zero
        d = graph.end - pnt
        self.f = abs(d.X) + abs(d.Y) + abs(d.Z)
        self.parent =  parent

    def __hash__(self) :
        return int(self.f * 1000000)
    
    def __lt__(self, other) :
            return self.f < other.f
    def __eq__(self, other) :
        print(self.pnt.DistanceTo(other.pnt)/dut, self.step/dut)
        return self.pnt.DistanceTo(other.pnt) < self.step 
    def _getNeighborsAlong(self, d) :
        directions = (d,)
        r1 = [self.graph.ri1.FindNearest(self.pnt, d) for d in directions]
        res = []
        for ref, d in zip(r1, directions) :
            #proximity = math.floor(ref.Proximity - self.graph.diameter / self.step) * self.step
            proximity = ref.Proximity - self.graph.diameter
            while proximity > 3.5 * self.graph.diameter :
                p = self.pnt + d * proximity
                neighbor = dmNode(self.graph, self, p, self.step)
                res.append(neighbor)
                proximity -= self.step

        return res
    def _getNeighbors(self) :
        if self.parent :
            d = self.pnt - self.parent.pnt 

        n1 = d.CrossProduct(XYZ.BasisZ).Normalize()

        if n1.GetLength() == 0 :
            n1 = d.CrossProduct(XYZ.BasisX).Normalize()
        n2 = d.CrossProduct(n1).Normalize()

    
        directions = (n1, -n1, n2, -n2)

        r1 = [self.graph.ri1.FindNearest(self.pnt, d) for d in directions]
        res = []
        #return res
        for ref, d in zip(r1, directions) :
            #proximity = math.floor(ref.Proximity - self.graph.diameter / self.step) * self.step
            proximity = ref.Proximity - self.graph.diameter
            while proximity > 3.5 * self.graph.diameter :
                p = self.pnt + d * proximity
                neighbor = dmNode(self.graph, self, p, self.step)
                res.append(neighbor)
                proximity -= self.step

        return res
    def show(self, doc) :
        s = pointToSolid(self.pnt, 50 * dut)
        create_ds(s, doc=doc)
    Neighbors = property(_getNeighbors) 

class dmGraph :
    def __init__(self, start, end, step, diameter, eId, view) :
        self.start = start
        self.end = end 
        self.step = step 
        self.diameter = diameter 

        self.view = view 
        self.ri1 = ReferenceIntersector(eId, 
                        FindReferenceTarget.Face, 
                        view)
       



    
def astar(start, end, step) :
    start_node = dmNode(None, start, end, )
    end_node = dmNode(None, end, end)
    open_list = []
    closed_set = set()

    while open_list :
        current_node = heapq.heappop(open_list)

        if current_node == end_node :
            path = []

            while current_node is not None :
                path.append(current_node)
                current_node = current_node.parent
            return path[::-1]
        
        closed_set.add(current_node)
        neighbors = current_node.Neighbors

        for neighbor in neighbors :
            if neighbor in closed_set : continue

            new_g = current_node.g + 1

            if neighbor in open_list :
                if new_g < neighbor.g :
                    neighbor.g = new_g
                    neighbor.h = 2 # нужно вставить расчет
                    neighbor.f = neighbor.g + neighbor.h
                    neighbor.parent = current_node
                    heapq.heapify(open_list)
            else :
                neighbor.g = new_g
                neighbor.h = 2 # уточить способ вычисления
                neighbor.f = neighbor.g + neighbor.h
                neighbor.parent = current_node
                heapq.heappush(open, neighbor)

    return None 

class dmSectionLevelCreation :
    """
    класс для создания уровня эшелона,
    вычисляет свободное пространство для прохода труб
    """
    def __init__(self, doc, 
                 centerElevation=None, 
                 height=None, 
                 view = None, 
                 fromDict= None) :
        if height and height > 0.98425196850393704 : 
            #Корректировка эшелона, максимальная высота 300 мм (пока)
            # При большом эшелоне может сильно увеличиться время обработки
            height = 0.98425196850393704
        self.doc                = doc 
        self.dmDoc              =  dmDocument(self.doc)
        if not fromDict :
            levelElevation          = view.GenLevel.Elevation
            self.centerElevation    = centerElevation
            self.levelElevation     = int((centerElevation - levelElevation) / dut)
            self.height             = height
            self.view               = view
        else :
            
            self.centerElevation    = fromDict["centerElevation"]
            centerElevation         = self.centerElevation
            self.height             = fromDict["height"]
            height                  = self.height
            views = {v.Name : v  for v in FilteredElementCollector(doc).OfClass(View).ToElements()} 
            self.view               = views[fromDict['viewName']]


            
        viewBB                  = self.view.get_BoundingBox(None)
        pnt                     = viewBB.Transform.OfPoint(viewBB.Min)
        self.minPnt             = XYZ(pnt.X, pnt.Y, centerElevation - height )
        pnt                     = viewBB.Transform.OfPoint(viewBB.Max)
        self.maxPnt             = XYZ(pnt.X, pnt.Y, centerElevation + height )
        self.eshelonBB          = BoundingBoxXYZ()
        self.eshelonBB.Min      = self.minPnt
        self.eshelonBB.Max      = self.maxPnt
        self.eshelonSolid       = minMaxToSolid(self.minPnt, self.maxPnt)
        coords                  = System.Array[geoms.Coordinate]([
                                        Coordinate(self.minPnt.X, self.minPnt.Y),
                                        Coordinate(self.minPnt.X, self.maxPnt.Y),
                                        Coordinate(self.maxPnt.X, self.maxPnt.Y),
                                        Coordinate(self.maxPnt.X, self.minPnt.Y),
                                        Coordinate(self.minPnt.X, self.minPnt.Y),
                                    ])
        eshelonRing             = geoms.LinearRing(coords)
        self.eshelonPolygon     = geoms.Polygon(eshelonRing)
        
            

    def __repr__(self) :
        return "dmEshelonLevelCreation center = {}, height = {}".format(self.centerElevation/dut, self.height/dut)
    
    def calcDuctPolygon(self) :
        ducts = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.05
        ducts = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_DuctCurves, bic.OST_DuctFitting, bic.OST_DuctAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_DuctInsulations
        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances : 
            nextModel = False 
            for stopStr in stopModelNameStr :       
                if li.linkInstance.Name.Contains(stopStr) : 
                    print(li);
                    print("Пропускаем")
                    nextModel = True 
                    break 
            if nextModel : continue
            ducts.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))
        pgs = []
        #print("Количество найденых воздуховодов {}".format(len(ducts)))
        for element in ducts :
            pgs.append(element.getPolygon(self.eshelonSolid, opt))

        for pg in pgs :
            try :
                if pg.Area > maxArea : continue
                finalPg = finalPg.Union(pg)
                if type(finalPg) == geoms.GeometryCollection :
                    finalPg = finalPg.Buffer(0)

            except Exception as ex:
                print("Ошибка при объединении воздуховодов")
                print(ex)
                pass

        #print("Количество полигонов воздуховодов {}".format(len(pgs)))

        smpl = nts.Simplify.DouglasPeuckerSimplifier(finalPg)
        smpl.DistanceTolerance = 20 * dut
        finalPg  = smpl.GetResultGeometry()

        self._ductPolygon = finalPg
        return finalPg

    
    def calcDuctSolids(self) :
        ducts = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        ducts = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_DuctCurves, bic.OST_DuctFitting, bic.OST_DuctAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_DuctInsulations
        ]))
        opt = Options()
        #opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            ducts.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        solids = []
        
        for duct in ducts :
            solids.extend(duct.getSolidsSected(self.eshelonSolid, opt))
        return solids
    
    def testDuctCalc(self) :
        """
        Тестируем что получается в процессе вычисления 
        эшелона труб
        """
        ducts = []
        
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        ducts = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_DuctCurves, bic.OST_DuctFitting, bic.OST_DuctAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_DuctInsulations
        ]))
        opt = Options()
        #opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            ducts.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        for duct in ducts :
            duct.showGeometry()

      
        
    
    def createEshelonSolid(self) :
        """
        Больше для визуализации процесса
        """
        solids = [self.eshelonSolid]
        solids.extend(self.calcDuctSolids())
        solids.extend(self.calcPipeSolids())
        solids.extend(self.calcArchSolids())
        solids.extend(self.calcElectricalSolids())

        return solids
    def showEshelonSolid(self) :
        return dm2.create_ds(self.createEshelonSolid())

        
    def calcPipePolygon(self) :
        pipes = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.05
        pipes = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_PipeCurves, bic.OST_PipeFitting, bic.OST_PipeAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_PipeInsulations
        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            nextModel = False 
            for stopStr in stopModelNameStr :       
                if li.linkInstance.Name.Contains(stopStr) : 
                    print(li);
                    print("Пропускаем")
                    nextModel = True 
                    break 
            if nextModel : continue
            pipes.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        pgs = []
        #print("Количество найденых труб {}".format(len(pipes)))
        for element in pipes :
            #solids.extend(pipe.getSolidsSected(self.eshelonSolid, opt))
            pgs.append(element.getPolygon(self.eshelonSolid, opt))
        for pg in pgs :
            try :
                if pg.Area > maxArea : continue
                finalPg = finalPg.Union(pg)
            except :
                pass

        #print("Количество полигонов труб {}".format(len(pgs)))
        smpl = nts.Simplify.DouglasPeuckerSimplifier(finalPg)
        smpl.DistanceTolerance = 20 * dut
        finalPg  = smpl.GetResultGeometry()

        self._pipePolygon = finalPg.Buffer(0) if type(finalPg) == geoms.GeometryCollection else finalPg
        return finalPg
    
    def testPipeCalc(self) :
        """
        Тестируем что получается в процессе вычисления 
        эшелона труб
        """
        pipes = []
        
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        pipes = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_PipeCurves, bic.OST_PipeFitting, bic.OST_PipeAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_PipeInsulations
        ]))
        opt = Options()
        #opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            pipes.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        for pipe in pipes :
            pipe.showGeometry()
    
    def calcPipeSolids(self) :
        pipes = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        pipes = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_PipeCurves, bic.OST_PipeFitting, bic.OST_PipeAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_PipeInsulations
        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            pipes.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        solids = []
        
        for pipe in pipes :
            solids.extend(pipe.getSolidsSected(self.eshelonSolid, opt))
        return solids
    def calcArchPolygon(self) :
        arches = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        arches = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_Columns, bic.OST_Floors,
                bic.OST_Columns, bic.OST_StructuralColumns, 
                bic.OST_StructuralFraming

        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            nextModel = False 
            for stopStr in stopModelNameStr :       
                if li.linkInstance.Name.Contains(stopStr) : 
                    print(li);
                    print("Пропускаем")
                    nextModel = True 
                    break 
            if nextModel : continue
            arches.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        pgs = []
        
        for arch in arches :
            pgs.append(arch.getPolygon(self.eshelonSolid, opt))
        
        for pg in pgs :
            try :
                finalPg = finalPg.Union(pg)
            except :
                pass

        smpl = nts.Simplify.DouglasPeuckerSimplifier(finalPg)
        smpl.DistanceTolerance = 20 * dut
        finalPg  = smpl.GetResultGeometry()

        self._archPolygon = finalPg
        return finalPg
    
    def calcWallsPolygon(self) :
        walls = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        walls = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_Walls

        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            walls.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        pgs = []
        
        for wall in walls :
            pgs.append(wall.getPolygon(self.eshelonSolid, opt))
        
        for pg in pgs :
            try :
                if pg.Area > maxArea : continue
                finalPg = finalPg.Union(pg)
                if type(finalPg) == geoms.GeometryCollection :
                    finalPg = finalPg.Buffer(0)
            except :
                pass

        smpl = nts.Simplify.DouglasPeuckerSimplifier(finalPg)
        smpl.DistanceTolerance = 20 * dut
        finalPg  = smpl.GetResultGeometry()        

        self._wallsPolygon = finalPg
        return finalPg
    
    def calcArchSolids(self) :
        arhces = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        arhces = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_Walls, bic.OST_Columns, bic.OST_Floors,
                bic.OST_Columns, bic.OST_StructuralColumns, 
                bic.OST_StructuralFraming

        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            arhces.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))
        print(len(arhces))
        solids = []
        
        for arch in arhces :
            solids.extend(arch.getSolidsSected(self.eshelonSolid, opt))
        return solids
    def calcElectricalPolygon(self) :
        els = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        els = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_CableTray, bic.OST_CableTrayFitting, 
                bic.OST_Conduit, bic.OST_ConduitFitting
        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            nextModel = False 
            for stopStr in stopModelNameStr :       
                if li.linkInstance.Name.Contains(stopStr) : 
                    print(li);
                    print("Пропускаем")
                    nextModel = True 
                    break 
            if nextModel : continue
            els.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        print("Количество найденых лотков и коробов {}".format(len(els)))
        solids = []
        pgs = []
        for el in els :
            pgs.append(el.getPolygon(self.eshelonSolid, opt))

        for pg in pgs :
            try :
                if pg.Area > maxArea : continue
                finalPg = finalPg.Union(pg)
            except :
                pass

        
        self._electricalPolygon = finalPg
        return finalPg
    def calcElectricalSolids(self) :
        electrics = []
        plane 		= Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)
        finalPg = geoms.Polygon.Empty
        maxArea = self.eshelonPolygon.Area * 0.1
        electrics = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_CableTray, bic.OST_CableTrayFitting, 
                bic.OST_Conduit, bic.OST_ConduitFitting
        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            electrics.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        solids = []
        
        for el in electrics :
            solids.extend(el.getSolidsSected(self.eshelonSolid, opt))
        return solids

    def showEshelonExtent(self) :
        solids = [self.eshelonSolid]
        solids.extend()
        create_ds(self.eshelonSolid, self.doc)
    def showEshelonExtentOnView(self, view = None)  :
        if not view :
            view = doc.ActiveView 
        drawPolygonAsFilledRegion(self.eshelonPolygon,
                                  self.doc, view)
    def _getArchPolygon(self) :
        if hasattr(self, "_archPolygon") : return self._archPolygon 
        else : return self.calcArchPolygon()
    def _getDuctPolygon(self) :
        if hasattr(self, "_ductPolygon") : return self._ductPolygon 
        else : return self.calcDuctPolygon()
    def _getPipePolygon(self) :
        if hasattr(self, "_pipePolygon") : return self._pipePolygon 
        else : return self.calcPipePolygon()
    def _getElectricalPolygon(self) :
        if hasattr(self, "_electricalPolygon") : return self._electricalPolygon 
        else : return self.calcElectricalPolygon()
    def _getWallsPolygon(self) :
        if hasattr(self, "_wallsPolygon") : return self._wallsPolygon 
        else : return self.calcWallsPolygon()
                
    archPolygon     = property(_getArchPolygon)
    ductPolygon     = property(_getDuctPolygon)
    pipePolygon     = property(_getPipePolygon)
    electricalPolygon = property(_getElectricalPolygon) 
    wallsPolygon    = property(_getWallsPolygon)

    def getFreePolygon(self, pipeD=100*dut) :
        if not hasattr(self, '_freePolygon') :
            try :
                self._freePolygon = self.eshelonPolygon.Buffer(20*dut).Difference(self.ductPolygon.Buffer(0)).Buffer(0)\
                    .Difference(self.pipePolygon.Buffer(0)).Buffer(0)\
                    .Difference(self.electricalPolygon.Buffer(0)).Buffer(0)\
                    .Difference(self.archPolygon.Buffer(0)).Buffer(-pipeD)
            except :
                print("Обнаружена ошибка при формировании свободного полигона")
                print(self)
                try :
                    pg1 = self.eshelonPolygon.Difference(self.ductPolygon)\
                        .Buffer(-2*dut).Buffer(4*dut).Buffer(-2*dut)
                except :
                    print("pg1 ductPolygon")
                    pg1 = self.eshelonPolygon
                try :
                    pg2 = pg1.Difference(self.pipePolygon.Buffer(-10*dut).Buffer(20*dut).Buffer(-10*dut))
                except :
                    print("pg2 pipePolygon")
                    pg2 = pg1
                try :
                    pg3 = pg2.Difference(self.electricalPolygon)
                except :
                    print("pg3 electricalPolygon")
                    pg3 = pg2
                try :
                    pg4 = pg3.Difference(self.archPolygon.Buffer(-10*dut).Buffer(20*dut).Buffer(-10*dut))
                except :
                    print("pg4 archPolygon")
                    pg4 = pg3
                self._freePolygon = pg4.Buffer(-pipeD).Buffer(-5*dut).Buffer(10*dut).Buffer(-5*dut)
        return self._freePolygon
    
    def showFreePolygon(self, pipeD = 100*dut) :
        
        ds = create_ds_safe(
            self.getFreePolygon(pipeD=pipeD),
                self.doc, 
                dp= XYZ(0,0,self.centerElevation))
        
    def showPipePolygon(self) :
        ds = create_ds_safe(
            self.pipePolygon,
                self.doc, 
                dp= XYZ(0,0,self.centerElevation))
    def showDuctPolygon(self) :
        ds = create_ds_safe(
            self.ductPolygon,
                self.doc, 
                dp= XYZ(0,0,self.centerElevation))
    def showElectricalPolygon(self) :
        ds = create_ds_safe(
            self.electricalPolygon,
                self.doc, 
                dp= XYZ(0,0,self.centerElevation))
    def showArchPolygon(self) :
        ds = create_ds_safe(
            self.archPolygon,
                self.doc, 
                dp= XYZ(0,0,self.centerElevation))


         
    def loadFromDb(self) :
        """
        Считывание полигонов для эшелонов из БД
        """
        conn = getSQLConnection()
        qs1 = """
            SELECT Plan_code,
                Plan_name,
                Level_name
            FROM PLANS
            WHERE Plan_name = '{}';
        """.format(self.view.Name)

        row = conn.execute(qs1).fetchone()
        Plan_code = row['Plan_code']
        qs1 = """
        SELECT Elevation_code,
            centerElevation,
            levelElevation,
            Height,
            Plan_code,
            ductPolygonB,
            pipePolygonB,
            electricalPolygonB,
            archPolygonB,
            wallsPolygonB
        FROM Eshelons
        WHERE Plan_code = ? AND levelElevation = ?;
            """
        #print(1)
        
        #print(2)
        res     = conn.execute(qs1, (Plan_code, self.levelElevation,)).fetchone()
        #print(res)
        if not res :
            raise dmNotFoundSectionInDataBaseError
        
        #print(3)
        from System.IO import MemoryStream
        
        self._archPolygon        = nts.IO.WKBReader()\
                                        .Read(
                                            MemoryStream(
                                            System.Array[System.Byte](res['archPolygonB'])))
        self._ductPolygon        = nts.IO.WKBReader()\
                                        .Read(
                                            MemoryStream(
                                            System.Array[System.Byte](res['ductPolygonB'])))
        self._pipePolygon        = nts.IO.WKBReader()\
                                        .Read(
                                            MemoryStream(
                                            System.Array[System.Byte](res['pipePolygonB'])))
        self._electricalPolygon  = nts.IO.WKBReader()\
                                        .Read(
                                            MemoryStream(
                                            System.Array[System.Byte](res['electricalPolygonB'])))
        self._wallsPolygon       = nts.IO.WKBReader()\
                                        .Read(
                                            MemoryStream(
                                                System.Array[System.Byte](res['wallsPolygonB'])))
        #print(4)
    def writeToDb(self) :
        conn = getSQLConnection()
        #conn.row_factory = sql.Row

        qs1 = """
            SELECT Plan_code,
                Plan_name,
                Level_name
            FROM PLANS
            WHERE Plan_name = '{}';
        """.format(self.view.Name)

        row = conn.execute(qs1).fetchone()
        if not row :
            qs2 = """
                INSERT INTO PLANS (
                      Plan_name
                  )
                  VALUES (
                      '{}'
                  );
            """.format(self.view.Name)
            conn.execute(qs2)
            conn.commit()
            row = conn.execute(qs1).fetchone()
        Plan_code = row['Plan_code']

        sq3 = """
            INSERT INTO Eshelons (
                         wallsPolygonB,
                         archPolygonB,
                         electricalPolygonB,
                         pipePolygonB,
                         ductPolygonB,
                         Plan_code,
                         Height,
                         centerElevation,
                         levelElevation
                     )
                     VALUES (
                         ?,
                         ?,
                         ?,
                         ?,
                         ?,
                         ?,
                         ?,
                         ?,
                         ?
                     );
        """
        try :
            data = (self.wallsPolygon.ToBinary(), 
                    self.archPolygon.ToBinary(), 
                    self.electricalPolygon.ToBinary(),
                    self.pipePolygon.ToBinary(),
                    self.ductPolygon.ToBinary(),
                    Plan_code,
                    self.height,
                    self.centerElevation,  
                    self.levelElevation  
                    )
        except :
            print("Ошибка при формировании строки в БД")
            print(self)
            raise

        conn.execute(sq3, data)
        conn.commit()
    def updateOrWriteToDb(self) :
        conn = getSQLConnection()
        #conn.row_factory = sql.Row

        qs1 = """
            SELECT Plan_code,
                Plan_name,
                Level_name
            FROM PLANS
            WHERE Plan_name = '{}';
        """.format(self.view.Name)

        row = conn.execute(qs1).fetchone()
        print(row)
        if not row :
            print("Не найден  план")
            qs2 = """
                INSERT INTO PLANS (
                      Plan_name
                  )
                  VALUES (
                      '{}'
                  );
            """.format(self.view.Name)
            conn.execute(qs2)
            conn.commit()
            row = conn.execute(qs1).fetchone()
        Plan_code = row['Plan_code']

        sq4 = """
            SELECT Elevation_code
            FROM Eshelons
            WHERE levelElevation = ? AND Plan_code = ?;
        """

        elevationRow = conn.execute(sq4, (self.levelElevation, Plan_code)).fetchone()

        if not elevationRow :
            print("Такой записи нет...")
            # Если записи нет, то запись вставляется
            sq3 = """
                INSERT INTO Eshelons (
                            wallsPolygonB,
                            archPolygonB,
                            electricalPolygonB,
                            pipePolygonB,
                            ductPolygonB,
                            Plan_code,
                            Height,
                            centerElevation,
                            levelElevation
                        )
                        VALUES (
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        );
            """
            try :
                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.wallsPolygon)
                smpl.DistanceTolerance = 20 * dut
                wallPg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.archPolygon)
                smpl.DistanceTolerance = 20 * dut
                archPg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.pipePolygon)
                smpl.DistanceTolerance = 20 * dut
                pipePg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.ductPolygon)
                smpl.DistanceTolerance = 20 * dut
                ductPg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.electricalPolygon)
                smpl.DistanceTolerance = 20 * dut
                elPg  = smpl.GetResultGeometry()


                data = (wallPg.ToBinary(), 
                        archPg.ToBinary(), 
                        elPg.ToBinary(),
                        pipePg.ToBinary(),
                        ductPg.ToBinary(),
                        Plan_code,
                        self.height,
                        self.centerElevation,  
                        self.levelElevation  
                        )
            except :
                print("Ошибка при формировании строки в БД")
                print(self)
                raise

            conn.execute(sq3, data)
            conn.commit()
        else :
            # Если запись есть, то обновляем информацию
            print("Запись найдена, обновляем...")
            pass

            sq3 = """
                UPDATE Eshelons
                    SET 

                        wallsPolygonB = ?,
                        archPolygonB = ?,
                        ductPolygonB = ?,
                        pipePolygonB = ?,
                        electricalPolygonB = ?
                    WHERE levelElevation = ? AND Plan_code = ?
            """
            try :
                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.wallsPolygon)
                smpl.DistanceTolerance = 20 * dut
                wallPg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.archPolygon)
                smpl.DistanceTolerance = 20 * dut
                archPg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.pipePolygon)
                smpl.DistanceTolerance = 20 * dut
                pipePg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.ductPolygon)
                smpl.DistanceTolerance = 20 * dut
                ductPg  = smpl.GetResultGeometry()

                smpl = nts.Simplify.DouglasPeuckerSimplifier(self.electricalPolygon)
                smpl.DistanceTolerance = 20 * dut
                elPg  = smpl.GetResultGeometry()


                data = (wallPg.ToBinary(), 
                        archPg.ToBinary(), 
                        ductPg.ToBinary(),
                        pipePg.ToBinary(),
                        elPg.ToBinary(),
                        self.levelElevation,                       
                        Plan_code,                     
                        )
            except :
                print("Ошибка при формировании строки в БД")
                print(self)
                raise

            conn.execute(sq3, data)
            conn.commit()

    def createEshelonContursDs(self) :
        """
        Создаем DirectShape с контурами эшелона
        """
        #pg = geoms.Polygon.Empty

        pg 	= self.ductPolygon.Union(self.pipePolygon)\
                    .Union(self.electricalPolygon)\
                        .Union(self.archPolygon)\
                            .Buffer(-2*dut).Buffer(4*dut).Buffer(-2*dut)
        tr = None
        if not self.doc.IsModifiable :
            tr = Transaction(self.doc, "Создаем контуры эшелона")
            tr.Start()
        ds = create_ds_safe(pg, self.doc)
        ds.Location.Move(XYZ(0,0, self.centerElevation))

        if tr : tr.Commit()

    def simplifyPolygon(self) :
        """
        Эксперименты с упрощением полигонов
        """
        pipePg = self.pipePolygon
        # .Buffer(200*dut)
        pipeB = pipePg.ToBinary()
        #create_ds_safe(pipePg, self.doc, XYZ(0,0,0))
        print("размер бинарного представления {}".format(len(pipeB)))
        smpl = nts.Simplify.DouglasPeuckerSimplifier(pipePg)
        # smpl.AreaDeltaRatio = 0.0001
        smpl.DistanceTolerance = 20 * dut
        sPipeB  = smpl.GetResultGeometry()
        print("размер бинарного представления после упрощения{}".format(len(sPipeB.ToBinary())))
        #create_ds_safe(sPipeB, self.doc, XYZ(0,0,1))
        sPipeB2 = sPipeB.Buffer(100*dut)
        print(" после операции буфер {}".format(len(sPipeB2.ToBinary())))
        #create_ds_safe(sPipeB, self.doc, XYZ(0,0,1))

        smpl = nts.Simplify.DouglasPeuckerSimplifier(sPipeB2)
        # smpl.AreaDeltaRatio = 0.0001
        smpl.DistanceTolerance = 50 * dut
        sPipeB  = smpl.GetResultGeometry()
        print("размер бинарного представления после упрощения{}".format(len(sPipeB.ToBinary())))
        self.pipePolygon = sPipeB
    def simplifyPolygon(self, pg, buferLen=0) :
        
        
        pipeB = pg.ToBinary()
        #create_ds_safe(pg, self.doc, XYZ(0,0,0))
        print("размер бинарного представления {}".format(len(pipeB)))
        smpl = nts.Simplify.DouglasPeuckerSimplifier(pg)
        # smpl.AreaDeltaRatio = 0.0001
        smpl.DistanceTolerance = 20 * dut
        sPipeB1  = smpl.GetResultGeometry()
        print("размер бинарного представления после упрощения{}".format(len(sPipeB1.ToBinary())))
        #create_ds_safe(sPipeB, self.doc, XYZ(0,0,1))
        size1 = len(sPipeB1.ToBinary())
        sPipeB2 = sPipeB1.Buffer(100*dut)
        print(" после операции буфер {}".format(len(sPipeB2.ToBinary())))
        #create_ds_safe(sPipeB, self.doc, XYZ(0,0,1))

        smpl = nts.Simplify.DouglasPeuckerSimplifier(sPipeB2)
        # smpl.AreaDeltaRatio = 0.0001
        smpl.DistanceTolerance = 50 * dut
        sPipeB2  = smpl.GetResultGeometry()
        size2   = len(sPipeB2.ToBinary())
        print("размер бинарного представления после упрощения{}".format(len(sPipeB2.ToBinary())))
        if size1 < size2 :
            return sPipeB1
        else :
            return sPipeB2
    def simplifyPolygonsLoggin(self) :
        """
        Упрощение полигонов с выводом результатов на экран
        """
        print(100*"*")
        print("Упрощение полигонов")
        print(100*"*")
        # Полигон с венткоробами

        print('Упрощаем полигон вентиляции на отм.  {}'.format(self.levelElevation))
        ductPntNum = len(self.ductPolygon.Coordinates)
        print("Количество координат полигона        {}".format(ductPntNum))
        ductLen = len(self.ductPolygon.ToBinary())
        print("Размер объекта в байтах :            {}".format(ductLen))

        updDuctPg = self.simplifyPolygon(self.ductPolygon)

        simpDuctPntNum = len(updDuctPg.Coordinates)
        print("Кол-во точек упрощенного полигона    {}".format(simpDuctPntNum))
        updDuctLen = len(updDuctPg.ToBinary())
        print("Размер упрощенного пг в байтах :     {}".format(updDuctLen))
        self._ductPolygon = updDuctPg

        if ductPntNum > 0 :
            print("Сокращение количества точек {:.2f}%"\
                .format((ductPntNum-simpDuctPntNum)/ductPntNum*100))
            print("Сокращение размера объекта {:.2f}%"\
                .format((ductLen-updDuctLen)/ductLen*100))
        print(20*'-')

        # Полигон с трубами
        print('Упрощаем полигон трубопроводов на отм.  {}'.format(self.levelElevation))
        pipePntNum = len(self.pipePolygon.Coordinates)
        print("Количество координат полигона        {}".format(pipePntNum))
        pipeLen = len(self.pipePolygon.ToBinary())
        print("Размер объекта в байтах :            {}".format(pipeLen))

        updPipePg = self.simplifyPolygon(self.pipePolygon)

        simpPipePntNum = len(updPipePg.Coordinates)
        print("Кол-во точек упрощенного полигона    {}".format(simpPipePntNum))
        updPipeLen = len(updPipePg.ToBinary())
        print("Размер упрощенного пг в байтах :     {}".format(updPipeLen))
        self._pipePolygon = updPipePg

        if pipePntNum > 0 :
            print("Сокращение количества точек {:.2f}%"\
                .format((pipePntNum-simpPipePntNum)/pipePntNum*100))
            print("Сокращение размера объекта {:.2f}%"\
                .format((pipeLen-updPipeLen)/pipeLen*100))
        print(20*'-')

        # Полигон электрики
        print('Упрощаем полигон электрики на отм.  {}'.format(self.levelElevation))
        electricalPntNum = len(self.electricalPolygon.Coordinates)
        print("Количество координат полигона        {}".format(electricalPntNum))
        electricalLen = len(self.electricalPolygon.ToBinary())
        print("Размер объекта в байтах :            {}".format(electricalLen))

        updElectricalPg = self.simplifyPolygon(self.electricalPolygon)

        simpElectricalPntNum = len(updElectricalPg.Coordinates)
        print("Кол-во точек упрощенного полигона    {}".format(simpElectricalPntNum))
        updElectricalLen = len(updElectricalPg.ToBinary())
        print("Размер упрощенного пг в байтах :     {}".format(updElectricalLen))
        self._electricalPolygon = updElectricalPg

        if electricalPntNum > 0 :
            print("Сокращение количества точек {:.2f}%"\
                .format((electricalPntNum-simpElectricalPntNum)/electricalPntNum*100))
            print("Сокращение размера объекта {:.2f}%"\
                .format((electricalLen-updElectricalLen)/electricalLen*100))
        print(20*'-')

        # Полигон архитектуры
        print('Упрощаем полигон архитектуры на отм.  {}'.format(self.levelElevation))
        archPntNum = len(self.archPolygon.Coordinates)
        print("Количество координат полигона        {}".format(archPntNum))
        archLen = len(self.archPolygon.ToBinary())
        print("Размер объекта в байтах :            {}".format(archLen))

        updArchPg = self.simplifyPolygon(self.archPolygon)

        simpArchPntNum = len(updArchPg.Coordinates)
        print("Кол-во точек упрощенного полигона    {}".format(simpArchPntNum))
        updArchLen = len(updArchPg.ToBinary())
        print("Размер упрощенного пг в байтах :     {}".format(updArchLen))
        self._archPolygon = updArchPg

        if archPntNum > 0 :
            print("Сокращение количества точек {:.2f}%"\
                .format((archPntNum-simpArchPntNum)/archPntNum*100))
            print("Сокращение размера объекта {:.2f}%"\
                .format((archLen-updArchLen)/archLen*100))
        print(20*'-')

        # Полигон стен
        print('Упрощаем полигон стен на отм.  {}'.format(self.levelElevation))
        wallsPntNum = len(self.wallsPolygon.Coordinates)
        print("Количество координат полигона        {}".format(wallsPntNum))
        wallsLen = len(self.wallsPolygon.ToBinary())
        print("Размер объекта в байтах :            {}".format(wallsLen))

        updWallsPg = self.simplifyPolygon(self.wallsPolygon)

        simpWallsPntNum = len(updWallsPg.Coordinates)
        print("Кол-во точек упрощенного полигона    {}".format(simpWallsPntNum))
        updWallsLen = len(updWallsPg.ToBinary())
        print("Размер упрощенного пг в байтах :     {}".format(updWallsLen))
        self._wallsPolygon = updWallsPg
        
        if wallsPntNum > 0 :
            print("Сокращение количества точек {:.2f}%"\
                .format((wallsPntNum-simpWallsPntNum)/wallsPntNum*100))
            print("Сокращение размера объекта {:.2f}%"\
                .format((wallsLen-updWallsLen)/wallsLen*100))
        
        print(20*'-')
        self.updateOrWriteToDb()








    



     


class dmPlan (metaclass = ProfilingMetaclass) :
    def __init__(self, view, height = 150 * dut, width = 150 * dut) :
        self.view               = view
        self.doc                = view.Document  
        self.eshelons           = None
        self.eshelonsLevels     = None
        self.eshelonsLevel      = None 
        self.height             = height
        self.width              = width 

    def __getitem__(self, index) :
        return self.eshelonsLevel[index] 
        
    def loadEshelonLevels (self) :
        conn = getSQLConnection()
        qs1     = """
            SELECT Plan_code
            FROM PLANS
            WHERE Plan_name = ?;

        """
        row = conn.execute(qs1, (self.view.Name,)).fetchone()
        if not row :
            raise dmNotFoundPlanInDataBaseError
        planNum = row['Plan_code']
        #print("Номер плана {}".format(planNum))

        qs2     = """
            SELECT DISTINCT 
                levelElevation,
                Plan_code
            FROM Eshelons
            WHERE Plan_code = ?
            ORDER BY levelElevation
        """
        rows = conn.execute(qs2, (planNum,)).fetchall()
        if not rows :
            raise dmNoLevelsOfPlan
        return [row['levelElevation'] for row in rows]
    def clearEshelons(self) :
        """
        Удаляет из БД все эшелоны связанные с уровнем
        """

        conn = getSQLConnection()
        qs1     = """
            SELECT Plan_code
            FROM PLANS
            WHERE Plan_name = ?;

        """
        row = conn.execute(qs1, (self.view.Name,)).fetchone()
        if not row :
            raise dmNotFoundPlanInDataBaseError
        planNum = row['Plan_code']

        qs2     = """
        DELETE FROM Eshelons
            WHERE Plan_code = ?;
        """
        rows = conn.execute(qs2, (planNum,))
        conn.commit()

    def loadEshelonByElevation(self, levelElevation) :
        conn = getSQLConnection()
        qs1     = """
            SELECT Plan_code
            FROM PLANS
            WHERE Plan_name = ?;

        """
        
        row = conn.execute(qs1, (self.view.Name,)).fetchone()
        if not row :
            raise dmNotFoundPlanInDataBaseError
        planNum = row['Plan_code']
        #print("Номер плана {}".format(planNum))

        qs2     = """
            SELECT 
                Plan_code, levelElevation, centerElevation
            FROM Eshelons
            WHERE Plan_code = ? AND levelElevation = ?
            ORDER BY levelElevation
        """
        row = conn.execute(qs2, (planNum, levelElevation)).fetchone()
        if not row :
            raise dmNotFoundLevelOfPlan
        eshelon = dmSectionLevelCreation(
            doc=self.doc,
            centerElevation=row['centerElevation'],
            height=self.height,
            view = self.view
            )
        eshelon.loadFromDb()
        
        return eshelon
    
    def loadAllEshelons(self) :
        self.eshelons       = {}
        self.eshelonsLevel  = {}
        for level in self.loadEshelonLevels() :
            # print(level)
            eshelon = self.loadEshelonByElevation(level)
            self.eshelons[level] = eshelon
            self.eshelonsLevel[eshelon.levelElevation] = eshelon

    def createIfAbsent(self, startElevation, endElevation, height = 180, createDs = False)  :
        """
        Загружает существующие эшелоны и  если эшелона нет, то
        создает эшелоны в диапазоне от startElevation до endElevation
        startElevation дается в миллиметрах и от рабочего уровня плана
        шаг 25 мм.
        
        """
        #height = 180 * dut
        if height > 250  :
            height = 250
        # self.loadAllEshelons()

        planElevation = self.view.GenLevel.Elevation
        try :
            levels = self.loadEshelonLevels()
        except :
            levels = []
        for elevation in range(startElevation, endElevation, 25) :
            if elevation in levels :
                print("Эшелон {} присутствует".format(elevation))
                continue
            else :
                print("Эшелон {} будет сформирован".format(elevation))

            centerElevation = planElevation + elevation * dut 

            eshelon = dmSectionLevelCreation(
                doc = self.doc,
                centerElevation = centerElevation,
                height = height * dut,
                view = self.view 
                )
            eshelon.writeToDb()
            if createDs :
                eshelon.showFreePolygon()

    def getNearestEshelon(self, elevation) :
        return min(self.eshelons.values(), key = lambda x : abs(x.centerElevation - elevation))
    
    def getEshelonsByDistance(self, elevation) :
        eshelons = sorted(self.eshelons.values(), 
                          key = lambda x : abs(x.centerElevation - elevation))
        for eshelon in eshelons :
            yield eshelon

    def showAllFreeEshelons(self, pipeD = 150 * dut) :
        for eshelon in self.eshelons.values() :
            try :
                eshelon.showFreePolygon(pipeD)
            except :
                print("ошибкка")
                print(eshelon)
    def __repr__(self) :
        return "План для работы с эшелонами :\nИмя: {}".format(self.view.Name)
    
    def createEshelons(self, startElevation, endElevation, height = 180) :
        """
        Создает эшелоны в диапазоне от startElevation до endElevation
        startElevation дается в миллиметрах и от рабочего уровня плана
        шаг 25 мм
        """
        #height = 180 * dut
        if height > 250  :
            height = 250
            
        planElevation = self.view.GenLevel.Elevation
        for elevation in range(startElevation, endElevation, 25) :
            centerElevation = elevation
            centerElevation = planElevation + elevation * dut 
            eshelon = dmSectionLevelCreation(
                doc = self.doc,
                centerElevation = centerElevation,
                height = height * dut,
                view = self.view 
                )
            eshelon.writeToDb()

        pass 
    def calcUnionFreeSpace(self) :
        """
        Вычисляет совмещенный полигон свободного места.
        с его помощью можно нати место для трассы, 
        где принципиально можно пройти.
        Вычисляет объединением всех полиготов свободного места
        """
        resPg = geoms.Polygon.Empty
        for eshelon in self.eshelons.values() :
            try :
                resPg = resPg.Union(eshelon.getFreePolygon())
            except :
                resPg = resPg.Buffer(10*dut).Buffer(-20*dut).Buffer(10*dut)
                eshelonPg = eshelon.getFreePolygon().Buffer(10*dut).Buffer(-20*dut).Buffer(10*dut)
                resPg = resPg.Union(eshelonPg)
                

        return resPg
    def showUnionFreeSpace(self) :
        create_ds_safe(self.calcUnionFreeSpace(), self.doc)

    def SimplifyAllEshelons(self) :
        for eshelon in self.eshelons.values() :
            eshelon.simplifyPolygonsLoggin()

    def calcAllFreeSpace(self, minElevation = None, maxElevation = None, showAfter = False) :
        """
        Вычисление свободного пространства, где принципиально можно пройти
        minElevation - минимальный уровень
        maxElevation - максимальный уровень
        showAfter    - создать полигон после вычисления
        """
        pgCenterElevation = float.PositiveInfinity
        resPg = geoms.Polygon.Empty
        for eshelon in sorted(self.eshelons.values(), key= lambda x : x.levelElevation) :
            if minElevation and eshelon.levelElevation < minElevation : continue
            if maxElevation and eshelon.levelElevation > maxElevation : continue
            pgCenterElevation = min([eshelon.centerElevation, pgCenterElevation])
            freePg = eshelon.getFreePolygon(150*dut)
            resPg = resPg.Union(freePg)

        if showAfter :
            create_ds_safe(freePg,
                           self.doc, 
                           XYZ(0,0, pgCenterElevation))

        return freePg
    
    def checkSpaceForStand(self, pnt, startElevation, targetElevation) :

        if startElevation < targetElevation :
            levels = sorted(filter(lambda x : x >= startElevation \
                            and x <= targetElevation, 
                            self.loadEshelonLevels()))
        else :
            levels = sorted(filter(lambda x : x <= startElevation \
                            and x >= targetElevation, 
                            self.loadEshelonLevels(), reverse= True))
        targetPoint     = geoms.Point(pnt.X, pnt.Y)

        for level in levels :
            eshelon = self.eshelonsLevel[level]
            freePg = eshelon.getFreePolygon()
            if not targetPoint.Within (freePg) :        
                return False
        return True
    
    def checkStand(self, pnt, startElevation) :

        
        levelsUp = sorted(filter(lambda x : x >= startElevation,               
                            self.loadEshelonLevels()))
        
        levelsDn = sorted(filter(lambda x : x <= startElevation, 
                            self.loadEshelonLevels()), reverse= True)
        targetPoint     = geoms.Point(pnt.X, pnt.Y)

        maxUp = startElevation
        maxDn = startElevation

        for level in levelsUp :
            eshelon = self.eshelonsLevel[level]
            freePg = eshelon.getFreePolygon()
            if targetPoint.Within (freePg) :        
                maxUp = level
            else : 
                break
        for level in levelsDn :
            eshelon = self.eshelonsLevel[level]
            freePg = eshelon.getFreePolygon()
            if targetPoint.Within(freePg) :
                maxDn = level
            else : 
                break

        return (maxDn, maxUp)
    
    def getGraph(self) :
        # Делаем связи между уровнями
        prev = None 
        next = None
        for current in sorted(self.eshelonsLevel) :
            print(current)
            self[current].prev = prev     
            if not prev is None :
                prev.next = self[current]
            prev = self[current]
        self[current].next = None 






        
            


    
         
class dmPipeSolver :
    def __init__(self, pipe, plan) :
        """
        pipe = тип dmElement
        plan  - тип dmPlan
        """
        self.pipe   = pipe 
        self.plan   = plan
        self.doc    = plan.doc 
        self.altElevation   = None 

    def _getNearestEshelon (self) :       
        if not hasattr(self, "_workEshelon") :
            if self.altElevation is None :
                z = self.pipe.Location.Curve.GetEndPoint(0).Z
            else :
                z = self.altElevation
            self._workEshelon = self.plan.getNearestEshelon(z)
        return self._workEshelon
    workEshelon = property(_getNearestEshelon)


    def updateElevation(self, z) :
        self.altElevation = z
        self._workEshelon = self.plan.getNearestEshelon(z)

    def pipeEnd0Free(self) :
        """
        Определяет, находится ли конец 0 трубы в свободном пространстве или 
        в замкнутом.
        """
        p0 = self.pipe.Location.Curve.GetEndPoint(0)
        pnt = geoms.Point(p0.X, p0.Y)
        return pnt.Within(self.plan.getFreePolygon())

    def checkLocation(self) :
        """
        Возвращает возможно ли трубу проложить по существующему положению
        """   
        pipeLocation = self.pipe.Location.Curve
        p1, p2 = pipeLocation.GetEndPoint(0), pipeLocation.GetEndPoint(1)
        eshelon = self.workEshelon
        # print(eshelon)
        pipeSegment = geoms.LineSegment(p1.X, p1.Y, p2.X, p2.Y)
        coords = System.Array[geoms.Coordinate]([
            geoms.Coordinate(p1.X, p1.Y),
            geoms.Coordinate(p2.X, p2.Y)
        ])
        pipeSegment = geoms.LineString(coords)
        freePg = eshelon.getFreePolygon(self.pipe.diameter)
        return pipeSegment.Within(freePg)

    def solvePipe(self) :
        """
        Нахождение трассы для трубы в одной вертикальной плоскости
        """

        #если нет пересечений, заканчиваем работу
        if self.checkLocation() :
            return 
        
        minSegmentLength = self.pipe.diameter * 3.5

        lineAnalyzer = dmPipeLineSegmentAnalyzer(
            pipe=self.pipe, 
            solver=self)
        
        segment = lineAnalyzer.doCalc()

        return segment
    
    def calcScroresForElevation(self, 
                                minElevation = None, 
                                maxElevation = None, 
                                toPrint = True) :
        """
        Вычисление насколько хороши уровни для прокладки трубопровода.
        Вычисляется длина трассы трубы, длина трассы, которая попадает в препятствия

        """
        res = {}
        pipeLocation = self.pipe.Location.Curve
        p1, p2 = pipeLocation.GetEndPoint(0), pipeLocation.GetEndPoint(1)
        

        pipeSegment = geoms.LineSegment(p1.X, p1.Y, p2.X, p2.Y)
        coords = System.Array[geoms.Coordinate]([
            geoms.Coordinate(p1.X, p1.Y),
            geoms.Coordinate(p2.X, p2.Y)
        ])

        pipeLineString = geoms.LineString(coords)
        pipeLength = pipeLineString.Length

        if toPrint :
            s = "Анализ расположения трубы: \n"\
                "Длина трубы\t\t: {:.4f} м".format(pipeLength/dut)
            print(s)

        for eshelon in sorted(self.plan.eshelons.values(), 
                              key = lambda x : x.levelElevation):
            freePg              = eshelon.getFreePolygon(self.pipe.diameter)
            # print(1)
            if minElevation and minElevation > eshelon.levelElevation :
                # print(2)
                continue
            if maxElevation and maxElevation < eshelon.levelElevation :
                # print(3)
                continue 
            # print(4)
            eshelonFreeLine     = pipeLineString.Intersection(freePg)
            freeLength          = eshelonFreeLine.Length

            if toPrint :
                print(100*"-")
                s = "Эшелон\t\t\t\t\t: {}\n"\
                    "Длина свободной трассы\t: {:.4f}\n"\
                    "Доля свободного места\t: {:.2f}%".format(eshelon.levelElevation,
                                                          freeLength/dut, 
                                                          freeLength/pipeLength * 100)
                print(s)

            res[eshelon.levelElevation] = \
                {
                    "level"     : eshelon.levelElevation,
                    "pipeLen"   : pipeLength,
                    "freeLength" : freeLength
                }
            

        if toPrint :
            print(100 * "-")
            freeLength = res[self.workEshelon.levelElevation]['freeLength']
            print("Труба находится на отметке\t: {}"\
                  .format(self.workEshelon.levelElevation))
            print("Свободное пространство на этом уровне : {:.2f}%".format(freeLength/pipeLength * 100))
            

        return res 
    





        
        

        
    
        

        
