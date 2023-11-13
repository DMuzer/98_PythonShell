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

if buffersPath not in currentReferences :
    clr.AddReferenceToFileAndPath(buffersPath)
if NTSPath not in currentReferences :
    clr.AddReferenceToFileAndPath(NTSPath)
if SQLPath not in currentReferences :
    clr.AddReferenceToFileAndPath(SQLPath)
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
        Elevation_code    INTEGER PRIMARY KEY,
        centerElevation   NUMERIC,
        levelElevation    INTEGER,
        Height            NUMERIC,
        Plan_code         INTEGER REFERENCES PLANS (Plan_code),
        ductPolygon       TEXT,
        pipePolygon       TEXT,
        electricalPolygon TEXT,
        archPolygon       TEXT,
        wallsPolygon      TEXT
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

        self.initialElevation = self.solver.workEshelon.centerElevation
    def __repr__(self) :
        return "Сегмент {}, {} статус = {}\n".format(self.startPoint, self.endPoint, self.status)
    
    def checkSegmentLength(self) :
        print("Проверка : {}".format(self))
        print()
        if self.status == 0 :
            # если это сегмент на исходной отметке
            if self.endPoint.parameter - self.startPoint.parameter < self.minSegmentLength :
                print("Короткий сегмент")
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
        initialElevation = self.solver.workEshelon.centerElevation
        ls = self.getLineString()
        found = False 
        if not hasattr(self,"_elevation") :
            print("отметки не найдено, ищем")
            if self.status == 0 :
                print("сегмент на свободной зоне возвращаем исходный уровень")
                return self.solver.workEshelon.centerElevation
            print("ищем уровень")
            for eshelon in self.solver.plan.getEshelonsByDistance(initialElevation) :
                print('проверяем эшелон {}'.format(eshelon))
                if ls.Within(eshelon.getFreePolygon()) :
                    print("найдено пространство")
                    self._elevation = eshelon.centerElevation
                    return self._elevation
                print("идем дальше")
        else :
            print("Отметка раньше найдена, возвращаем ранее вычисленное значение")
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

        coords = System.Array[geoms.Coordinate]([p1, p2])
        ls = geoms.LineString(coords)
        return ls
    def getLine(self) :
        """
        вычисляет Line для сегмента
        """

        if self.startParameter2 :
            _p1 = self.lineSegment.PointAlong(self.startParameter2)
        else :
            _p1 = self.lineSegment.PointAlong(self.startPoint.parameter)
        if self.endParameter2 :
            _p2 = self.lineSegment.PointAlong(self.endParameter2)
        else :
            _p2 = self.lineSegment.PointAlong(self.endPoint.parameter)


        p1 = XYZ(_p1.X, _p1.Y, self.findElevation())
        p2 = XYZ(_p2.X, _p2.Y, self.findElevation())
        return Line.CreateBound(p1, p2)


    def checkConnectionSegment(self) :
        """
        Проверяем, чтобы вертикальный сегменты был достаточной длины чтобы разместить 
        фитинги
        """
        #Проверяем только для обходных сегментов
        if self.status == 0 : return
        thisLine = self.getLine()
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
            p01 = prevSegment.GetEndPoint(1)
            p10 = thisLine.GetEndPoint(0)
            l0 = Line.CreateBound(p01, p10)

            if l0.Length < self.minSegmentLength :
                #Перемычка получается меньше, поэтому нужна корректировка
                # положения предыдущего сегмента
                





    

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

            print("Начинается со свободного конца. ")
            segments = [dmSegment(pnt1, pnt2, lineSegment=pipeSegment, solver= self.solver) 
                        for pnt1, pnt2 
                        in zip(points[:-1], points[1:])]
            for status, segment in enumerate(segments) :
                segment.status = status % 2

        if points[-1].parameter != 1 :
            # Это на тот случай, если конец трубы попадает в препятствие
            # Добавляем конечную точку
            points.append(dmSplitPoint(1))
            segment = dmSegment(points[-2],points[-1], 
                                lineSegment=pipeSegment, 
                                solver= self.solver)
            segment.status = 1
            segments.append(segment)

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
        print("отрезки сформировали")

        print("Делаем проверку сегментов")
        segment = segments[0]
        while segment :
            i += 1
            if i > 100 : raise 
            print(20*"-")
            print(segment)
            print('предыдущий')
            print(segment.prev)
            print("следующий")
            print(segment.next)
            print(20*"-")
            #segment = segment.next
            segment = segment.checkSegmentLength()

        print("Проверка сделана")

        print(50*"*")
        segment = segments[0]
        resSegments= []
        while segment :
            i += 1
            if i > 100 : raise 
            resSegments.append(segment)
            segment = segment.next 

        for segment in resSegments :
            print(segment)
            
        for segment in resSegments :
            print(segment.getLineString())
            elevation = segment.findElevation()
            print(elevation)
            create_ds_safe(segment.getLineString(), 
                           doc = self.solver.doc,
                           dp=XYZ(0,0, elevation)
                           )
        return resSegments
        
        








    def _getSegments(self) :
        return []
    
    segments = property(_getSegments)
        

        

class dmLinkedElement :
    def __init__(self, link, element) :
        self.link = link
        self.element = element 
    def __repr__(self) :
        return "Id - {} {}".format(self.element.Id, self.element.Category.Name)
    def getSolids(self, viewOpts) :
        if viewOpts :
            vopt = viewOpts
        else :
            vopt = opt 
        geometry = self.element.Geometry[vopt]
        if not geometry : return []
        geoms = [geometry.GetTransformed(self.link.Transform)]

        if isinstance(self.element, FamilyInstance) and \
                self.element.Category.Id.IntegerValue != int(bic.OST_StructuralFraming) :
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
        #print("getPolygon")
        """
        #Учтасток для дальнейшей доработки чтобы напрямую формировать контуры
        if self.element.Id.IntegerValue in [int(bic.OST_DuctCurves)] :
            bb = viewSolid.BoundingBox()
            pntMin = bb.Transform.OfPoint(bb.Min)
            pntMan = bb.Transform.OfPoint(bb.Max)
            lc = self.element.Location.Curve 
            d = lc.Direction
            if
            dn = d.CrossProduct(XYZ.BasisZ)
            if d.Z > = 0 :
                sPoint = lc.GetEndPoint(0)
                ePoint = lc.GetEndPoint(1)
                coords = System.Array[geoms.Coordinate]([
                    Coordinate(sPoint.X, sPoint.Y),
                    Coordinate(ePoint.X, ePoint.Y)
                ])
                w = self.element.Width / 2 if hasattr(self.element, "Width") \
                        else self.element.Radius
                ls = geoms.LineSegment(sPoint.X, sPoint.Y, ePoint.X, ePoint.Y).Buffer(w)




        else :
        """
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
                print("исключение на элементе {}".format(self))
                print(ex)
                #raise
                pass
        #print("getPolygon return {}".format(resPg))
        
        return resPg
            


        
    

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

            self._wallsPolygon      = nts.IO.WKTReader().Read(fromDict['wallsPolygon'])
            self._ductPolygon       = nts.IO.WKTReader().Read(fromDict['ductPolygon'])
            self._pipePolygon       = nts.IO.WKTReader().Read(fromDict['pipePolygon'])
            self._electricalPolygon = nts.IO.WKTReader().Read(fromDict['electricalPolygon'])
            self._archPolygon       = nts.IO.WKTReader().Read(fromDict['archPolygon'])
            
        viewBB                  = self.view.get_BoundingBox(None)
        pnt                     = viewBB.Transform.OfPoint(viewBB.Min)
        self.minPnt             = XYZ(pnt.X, pnt.Y, centerElevation - height / 2)
        pnt                     = viewBB.Transform.OfPoint(viewBB.Max)
        self.maxPnt             = XYZ(pnt.X, pnt.Y, centerElevation + height / 2)
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
        maxArea = self.eshelonPolygon.Area * 0.1
        ducts = []
        flt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_DuctCurves, bic.OST_DuctFitting, bic.OST_DuctAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_DuctInsulations
        ]))
        opt = Options()
        opt.View = self.view
        for li in self.dmDoc.linkInstances :        
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            ducts.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))
        pgs = []
        #print("Количество найденых воздуховодов {}".format(len(ducts)))
        for element in ducts :
            pgs.append(element.getPolygon(self.eshelonSolid, opt))

        for pg in pgs :
            try :
                finalPg = finalPg.Union(pg)
                if type(finalPg) == geoms.GeometryCollection :
                    finalPg = finalPg.Buffer(0)

            except Exception as ex:
                print("Ошибка при объединении воздуховодов")
                print(ex)
                pass

        #print("Количество полигонов воздуховодов {}".format(len(pgs)))

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

        pgs = []
        #print("Количество найденых труб {}".format(len(pipes)))
        for element in pipes :
            #solids.extend(pipe.getSolidsSected(self.eshelonSolid, opt))
            pgs.append(element.getPolygon(self.eshelonSolid, opt))
        for pg in pgs :
            try :
                finalPg = finalPg.Union(pg)
            except :
                pass

        #print("Количество полигонов труб {}".format(len(pgs)))
        self._pipePolygon = finalPg.Buffer(0) if type(finalPg) == geoms.GeometryCollection else finalPg
        return finalPg
    
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
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            arches.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        pgs = []
        
        for arch in arches :
            pgs.append(arch.getPolygon(self.eshelonSolid, opt))
        
        for pg in pgs :
            try :
                finalPg = finalPg.Union(pg)
            except :
                pass

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
                finalPg = finalPg.Union(pg)
                if type(finalPg) == geoms.GeometryCollection :
                    finalPg = finalPg.Buffer(0)
            except :
                pass
        

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
            #if not  li.linkInstance.Name.Contains("E") : print(li);continue
            els.extend(li.getElementsInsideBoundingBox(self.eshelonBB, flt = flt))

        solids = []
        pgs = []
        for el in els :
            pgs.append(el.getPolygon(self.eshelonSolid, opt))

        for pg in pgs :
            try :
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
            self._freePolygon = self.eshelonPolygon.Difference(self.ductPolygon)\
                .Difference(self.pipePolygon)\
                .Difference(self.electricalPolygon)\
                .Difference(self.archPolygon).Buffer(-pipeD)
        return self._freePolygon
    
    def showFreePolygon(self, pipeD = 100*dut) :
        
        ds = create_ds_safe(
            self.getFreePolygon(pipeD=pipeD),
                self.doc, 
                dp= XYZ(0,0,self.centerElevation))
         
    def loadFromDb(self) :
        """
        Считывание полигонов для эшелонов из БД
        """
        qs1 = """
        SELECT Elevation_code,
            centerElevation,
            levelElevation,
            Height,
            Plan_code,
            ductPolygon,
            pipePolygon,
            electricalPolygon,
            archPolygon,
            wallsPolygon
        FROM Eshelons
        WHERE levelElevation = ?;
            """
        #print(1)
        conn = getSQLConnection()
        #print(2)
        res     = conn.execute(qs1, (self.levelElevation,)).fetchone()
        #print(res)
        if not res :
            raise dmNotFoundSectionInDataBaseError
        
        #print(3)
        
        self._getArchPolygon        = nts.IO.WKTReader().Read(res['archPolygon'])
        self._getDuctPolygon        = nts.IO.WKTReader().Read(res['ductPolygon'])
        self._getPipePolygon        = nts.IO.WKTReader().Read(res['pipePolygon'])
        self._getElectricalPolygon  = nts.IO.WKTReader().Read(res['electricalPolygon'])
        self._getWallsPolygon       = nts.IO.WKTReader().Read(res['wallsPolygon'])
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
                         wallsPolygon,
                         archPolygon,
                         electricalPolygon,
                         pipePolygon,
                         ductPolygon,
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

        data = (self.wallsPolygon.ToText(), 
                self.archPolygon.ToText(), 
                self.electricalPolygon.ToText(),
                self.pipePolygon.ToText(),
                self.ductPolygon.ToText(),
                Plan_code,
                self.height,
                self.centerElevation,  
                self.levelElevation  
                )

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
        







    def makeDict(self) :
        return {
            "centerElevation"     : self.centerElevation,
            "height"        : self.height,
            "electricalPolygon"   : self.electricalPolygon.ToText() ,
            "archPolygon" : self.archPolygon.ToText(),
            "ductPolygon" : self.ductPolygon.ToText(),
            "pipePolygon" : self.pipePolygon.ToText(),
            "wallsPolygon" : self.wallsPolygon.ToText(),
            "viewName"    : self.view.Name
        }
        

    

class dmPlan :
    def __init__(self, view, height = 150 * dut, width = 150 * dut) :
        self.view               = view
        self.doc                = view.Document  
        self.eshelons           = None
        self.eshelonsLevels     = None
        self.height             = height
        self.width              = width 
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
        self.eshelons = {}
        for level in self.loadEshelonLevels() :
            #print(level)
            self.eshelons[level] = self.loadEshelonByElevation(level)
    def getNearestEshelon(self, elevation) :
        return min(self.eshelons.values(), key = lambda x : abs(x.centerElevation - elevation))
    
    def getEshelonsByDistance(self, elevation) :
        eshelons = sorted(self.eshelons.values(), 
                          key = lambda x : abs(x.centerElevation - elevation))
        for eshelon in eshelons :
            yield eshelon

    def showAllFreeEshelons(self, pipeD = 150 * dut) :
        for eshelon in self.eshelons.values() :
            eshelon.showFreePolygon(pipeD)
    def __repr__(self) :
        return "План для работы с эшелонами :\nИмя: {}".format(self.view.Name)
    
    
         
class dmPipeSolver :
    def __init__(self, pipe, plan) :
        """
        pipe = тип dmElement
        plan  - тип dmPlan
        """
        self.pipe   = pipe 
        self.plan   = plan
        self.doc    = plan.doc 

    def _getNearestEshelon (self) :
        if not hasattr(self, "_workEshelon") :
            p = self.pipe.Location.Curve.GetEndPoint(0)
            self._workEshelon = self.plan.getNearestEshelon(p.Z)
        return self._workEshelon
    workEshelon = property(_getNearestEshelon)

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
        print(eshelon)
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
    
        

        
