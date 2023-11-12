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
        conn.row_factory = sql.Row
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
    def __init__(self, doc, centerElevation=None, height=None, view = None, fromDict= None) :
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
        return self.eshelonPolygon.Difference(self.ductPolygon)\
            .Difference(self.pipePolygon)\
            .Difference(self.electricalPolygon)\
            .Difference(self.archPolygon).Buffer(pipeD)
    
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
        conn = getSQLConnection()
        res     = conn.execute(sq1, self.levelElevation).fetchone()
        if not res :
            raise dmNotFoundSectionInDataBaseError
        
        self._getArchPolygon        = geoms.IO.WKTReader().Read(conn['archPolygon'])
        self._getDuctPolygon        = geoms.IO.WKTReader().Read(conn['ductPolygon'])
        self._getPipePolygon        = geoms.IO.WKTReader().Read(conn['pipePolygon'])
        self._getElectricalPolygon  = geoms.IO.WKTReader().Read(conn['electricalPolygon'])
        self._getWallsPolygon       = geoms.IO.WKTReader().Read(conn['wallsPolygon'])
     
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
    def __init__(self, models, model, doc, name, data) :
        self.models     = models
        self.model      = model
        self.doc        = doc 
        self.name       = name
        self.data       = data['data']
        self.sections   = {}
        # создаем сечения
        for k in self.data :
            elevation = float(k)
            self.sections[elevation] = dmSectionLevelCreation(
                    doc = self.doc,
                    fromDict = self.data[k]
                )


        
        self.eshelons   = None
    def __repr__(self) :
        return "План {}".format(self.name)

    

class dmModel :
    def __init__(self, models, doc, name, data) :
        #print(data.keys())
        self.models = models
        self.data = data
        self.doc = doc 
        self.pathName = name
        self.planNames = sorted(list(data.keys()))
    
    def __repr__(self) :
        s = "Модель {}\nПланы:".format(self.pathName)
        for pn in self.data :
            s += "\nПлан : {}".format(pn)
        return s
    
    def __getitem__(self, index) :
        planName = self.planNames[index]
        return dmPlan(models=self.models, 
                      model=self,
                      doc = self.doc,
                      name=planName, 
                      data=self.data[planName])
    

class dmModels :
    def __init__(self, doc) :
        self.doc = doc
        self.app = doc.Application
        with open(r"d:\eshelon.json", "r") as f :
            self.models = json.load(f)
            self.modelsNames = sorted(list(self.models.keys()))
    def __repr__(self) :
        return "Доступ к моделям"
    def __getitem__(self, index) :
        doc = None 
        if isinstance(index, int) :
            mn = self.modelsNames[index]
            
            for od in self.app.Documents :
                if od.PathName == mn : 
                    doc = od 
            return dmModel(self, doc, mn,  self.models[mn])
        if isinstance(index, str) :
            for od in self.app.Documents :
                if od.PathName == index :
                    doc = od 
            return dmModel(self, index, doc,  self.models[index])
        
class dmPipeSolver :
    def __init__(self, pipe, eshelons) :
        """
        pipe = тип dmElement
        eshelons  - список ? с эшелонами
        """
        self.pipe       = pipe 
        self.eshelons   = eshelons

    
    def checkLocation(self) :
        """
        Возвращает возможно ли трубу проложить по существующему положению
        """
        pass




        
        



    

    



    
    





        


    

    