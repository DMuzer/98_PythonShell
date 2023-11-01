#  coding: utf-8
import Autodesk.Revit
from Autodesk.Revit import  DB, UI 
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import System
import dm_connect_2 as dm2 
bic = BuiltInCategory
dut = 0.0032808398950131233
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
def create_ds(l, category = None, doc =  None) :
    if not doc :  return 
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
        #elif type(e) == geoms.Polygon :
        #    olist.extend(get_CurveLoopsFromPolygon(e))
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
        geometry = self.element.Geometry[vOpt]
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
        solids2 = []
        for solid in res :
            try :
                solid2 = BooleanOperationsUtils\
                    .ExecuteBooleanOperation(
                        sectSolid, solid, 
                            BooleanOperationsType.Intersect)
                if solid2.Volume > 0.0001 :
                    solids2.append(solid2)
            except :
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
    def getPipeDuctElements(self) :

        mcatFlt = ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_DuctCurves, bic.OST_DuctFitting, bic.OST_DuctAccessory,
                bic.OST_MechanicalEquipment, bic.OST_PipeCurves, bic.OST_PipeFitting,

                bic.OST_PipeAccessory, bic.OST_PipeInsulations,
                bic.OST_DuctInsulations
        ]))
        elements = [dmLinkedElement(self, e) 
                        for e in FilteredElementCollector(self.linkDoc)\
                            .WherePasses(mcatFlt)\
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
    


    
    def getElementsInsideBoundingBox(self, bb) :
        #print(1)
        pmin_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Min))
        pmax_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Max))

        pmin = XYZ(min(pmin_.X, pmax_.X), min(pmin_.Y, pmax_.Y), min(pmin_.Z, pmax_.Z))
        pmax = XYZ(max(pmin_.X, pmax_.X), max(pmin_.Y, pmax_.Y), max(pmin_.Z, pmax_.Z))


        try :
            # print(pmin, pmax)
            outline = Outline(pmin, pmax)
            bbFlt = BoundingBoxIntersectsFilter (outline)
            elements = [dmLinkedElement(self, e) 
                            for e in FilteredElementCollector(self.linkDoc)\
                                .WherePasses(bbFlt).ToElements()]
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
                for g in geometry.GetTransformed(self.Transform) :
                    #print(g)
                    if isinstance(g, Solid) :  res.append((element, g))
            return res
        except Exception as ex: 
            print(ex)
            return []
class dmDocument :
    def __init__(self, doc) :
        self.doc = doc

    def _getLinkInstances(self) :

        return [dmLinkInstance(l) 
                for l in FilteredElementCollector(self.doc)\
                    .OfClass(RevitLinkInstance).ToElements()]
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




        


    

    