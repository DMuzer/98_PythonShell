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

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\System.Buffers.4.4.0\lib\netstandard2.0\System.Buffers.dll")
clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\nettopologysuite.2.5.0\lib\netstandard2.0\NetTopologySuite.dll")
import NetTopologySuite as nts
from NetTopologySuite.Geometries import *
import NetTopologySuite.Geometries as geoms


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

def create_ds_safe(l, doc =  None) :
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
        for shape in shapes_a :
            try :
                ds.AppendShape([shape])
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

    return ds

def drawPolygonAsFilledRegion(pg, doc, view, typeId = None) :
    if not typeId :
        typeId = FilteredElementCollector(doc).OfClass(FilledRegionType).FirstElementId()
    tr = None
    if not tr :
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
    p1 = XYZ(minPnt.X, minPnt.Y, minPnt.Z)
    p2 = XYZ(minPnt.X, maxPnt.Y, minPnt.Z)
    p3 = XYZ(maxPnt.X, maxPnt.Y, minPnt.Z)
    p4 = XYZ(maxPnt.X, minPnt.Y, minPnt.Z)
    height = abs(maxPnt.Z - minPnt.Z)

    cl  = System.Array [CurveLoop]([CurveLoop.Create(System.Array[Curve](
            [Line.CreateBound(p1, p2),
            Line.CreateBound(p2, p3),
            Line.CreateBound(p3, p4),
            Line.CreateBound(p4,p1)]))])

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
    def getSolids(self) :
        geometry = self.element.Geometry[opt]
        if not geometry : return []
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
        if viewOpts :
            vOpt = viewOpts
        else :
            vOpt = opt
        try :
            geometry = self.element.Geometry[vOpt].GetTransformed(self.link.Transform)
        except System.MissingMemberException:
            return []
        if not geometry : return []
        geoms = [geometry]
        res = []
        while geoms :
            g = geoms.pop()
              
            if isinstance(g, Solid) :
                res.append(g)
            elif isinstance(g, GeometryInstance) :
                geoms.extend(list(g.GetSymbolGeometry()))
                #geoms.extend(list(g))
            elif isinstance(g, GeometryElement) :
                geoms.extend(list(g))
        solids2 = []
        problem = 0
        for solid in res :
            try :
                solid2 = BooleanOperationsUtils\
                    .ExecuteBooleanOperation(
                        sectSolid, solid, 
                            BooleanOperationsType.Intersect)
                if solid2.Volume > 0.0001 :
                    #print("маленьки объем")
                    pass 
                else :
                    #print("нормальный объем")
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
        resPg = geoms.Polygon.Empty
        for solid in self.getSolidsSected(viewSolid, viewOpts) :
            try :
                ea = ExtrusionAnalyzer.Create(solid, plane, XYZ.BasisZ)
                face = ea.GetExtrusionBase()
                pg = dm2.get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                resPg = resPg.Union(pg)
            except Exception as ex:
                print(ex)
                pass
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
            self.centerElevation    = centerElevation
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

        solids = []
        
        for duct in ducts :
            solids.extend(duct.getSolidsSected(self.eshelonSolid, opt))

        for solid in solids :
            print(solid)
            try :
                ea = ExtrusionAnalyzer.Create(solid, plane, XYZ.BasisZ)
                face = ea.GetExtrusionBase()
                pg = dm2.get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                pg2 = pg.Buffer(25 * dut).Buffer(-50*dut).Buffer(25*dut)
              
                if pg2.Area > maxArea :
                    #print(element.element.Category.Name)
                    #print(element.element.Id)
                    continue

                finalPg = finalPg.Union(pg2)  
            except Exception as ex:
                print(ex)
                #raise
                continue
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

        solids = []
        
        for pipe in pipes :
            solids.extend(pipe.getSolidsSected(self.eshelonSolid, opt))

        for solid in solids :
            try :
                ea = ExtrusionAnalyzer.Create(solid, plane, XYZ.BasisZ)
                face = ea.GetExtrusionBase()
                pg = dm2.get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                pg2 = pg.Buffer(25 * dut).Buffer(-50*dut).Buffer(25*dut)
              
                if pg2.Area > maxArea :
                    #print(element.element.Category.Name)
                    #print(element.element.Id)
                    continue

                finalPg = finalPg.Union(pg2)  
            except Exception as ex:
                print(ex)
                #raise
                continue
        self._pipePolygon = finalPg
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

        solids = []
        
        for arch in arches :
            #print(arch)
            solids.extend(arch.getSolidsSected(self.eshelonSolid, opt))

        for solid in solids :
            try :
                ea = ExtrusionAnalyzer.Create(solid, plane, XYZ.BasisZ)
                face = ea.GetExtrusionBase()
                pg = dm2.get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                pg2 = pg.Buffer(25 * dut).Buffer(-50*dut).Buffer(25*dut)
              
                if pg2.Area > maxArea :
                    #print(element.element.Category.Name)
                    #print(element.element.Id)
                    continue

                finalPg = finalPg.Union(pg2)  
            except Exception as ex:
                print(ex)
                #raise
                continue
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

        solids = []
        
        for wall in walls :
            solids.extend(wall.getSolidsSected(self.eshelonSolid, opt))

        for solid in solids :
            try :
                ea = ExtrusionAnalyzer.Create(solid, plane, XYZ.BasisZ)
                face = ea.GetExtrusionBase()
                pg = dm2.get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                pg2 = pg.Buffer(25 * dut).Buffer(-50*dut).Buffer(25*dut)
              
                if pg2.Area > maxArea :
                    #print(element.element.Category.Name)
                    #print(element.element.Id)
                    continue

                finalPg = finalPg.Union(pg2)  
            except Exception as ex:
                print(ex)
                #raise
                continue
        self._archPolygon = finalPg
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
        
        for el in els :
            solids.extend(el.getSolidsSected(self.eshelonSolid, opt))

        for solid in solids :
            try :
                ea = ExtrusionAnalyzer.Create(solid, plane, XYZ.BasisZ)
                face = ea.GetExtrusionBase()
                pg = dm2.get_PolygonFromCurveLoops(face.GetEdgesAsCurveLoops())
                pg2 = pg.Buffer(5 * dut).Buffer(-10*dut).Buffer(5*dut)
              
                if pg2.Area > maxArea :
                    #print(element.element.Category.Name)
                    #print(element.element.Id)
                    continue

                finalPg = finalPg.Union(pg2)  
            except Exception as ex:
                print(ex)
                #raise
                continue
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
        
        



    

    



    
    





        


    

    