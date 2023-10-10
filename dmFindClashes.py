from Autodesk.Revit import *
from Autodesk.Revit.DB import *
#from contextlib import contextmanager
import math, sys
import clr
import System
import time

bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
dsid = ElementId(bic.OST_GenericModel)

#System.Array[bic](barrier_categories)

    
barrier_categories = [bic.OST_Floors, 
                bic.OST_Ceilings, 
                bic.OST_StructuralColumns,
                bic.OST_DuctCurves,
                bic.OST_DuctFitting,
                bic.OST_Walls,
                bic.OST_Conduit,
                bic.OST_CableTray,
                bic.OST_PipeCurves,
                bic.OST_MechanicalEquipment,
                bic.OST_PipeAccessory,
                bic.OST_PipeFitting,
                bic.OST_PipeInsulations
                ]

lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
    sys.path.append(lib_path)
from pathlib import Path
from imp import reload
print(2)


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
    tr = None 
    try : 
        p = e.Parameter[BuiltInParameter.ELEM_PARTITION_PARAM]
        if p :
            if not doc.IsModifiable :
                tr = Transaction(doc, "set workset for element")
                tr.Start()
                
            p.Set(ws.Id.IntegerValue)
        
            if tr :
                tr.Commit()
            
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
        # elif type(e) == geoms.Polygon :
        #     olist.extend(get_CurveLoopsFromPolygon(e))
        elif isinstance(e, GeometryObject) :
            shapes.append(e)
        elif isinstance(e, GemetryElement) :
            shapes.extend(e)

    shapes_a = System.Array[GeometryObject](shapes)
    tr = None 
    if not doc.IsModifiable :
        tr = Transaction(doc, "new direct shape")
        tr.Start()

    ds = DirectShape.CreateElement(doc, catid)
    ds.SetShape(shapes_a)

    if tr :
        tr.Commit()

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



class dmLinkInstance :
    def __init__(self, instance, dmDoc) :
        self.instance = instance
        self.dmDoc = dmDoc
        self.doc = instance.GetLinkDocument()
    def __repr__(self) :
        return f"Вставленная модель {self.instance}"
    
    def getElementsBoundingBox(self, bb) :
        global barrier_categories
        print(20*"-")
        categoryFilter = ElementMulticategoryFilter(
            System.Array[bic](barrier_categories)
        )
        if not self.doc : return 
        transform = self.instance.GetTotalTransform().Inverse

        p1 = transform.OfPoint(bb.Min)
        p2 = transform.OfPoint(bb.Max)
        filterOutline = Outline(p1, p2)
        if filterOutline.IsEmpty : return 
        bbIntersectsFilter = BoundingBoxIntersectsFilter(filterOutline)

        elements = FilteredElementCollector(self.doc)\
                .WherePasses(categoryFilter)\
                .WherePasses(bbIntersectsFilter).ToElements()

        for element in elements :
                yield dmElement(element, self.dmDoc, self)

    def getBBSectedElements(self, element) :
        bb = element.element.get_BoundingBox(None)
        return self.getElementsBoundingBox(bb)
    
    def getSolidSectedElements(self, element) :
        global barrier_categories
        print(20*"-")
        categoryFilter = ElementMulticategoryFilter(
            System.Array[bic](barrier_categories)
        )
        if not self.doc : return 
        transform = self.instance.GetTotalTransform().Inverse

        bb = element.element.get_BoundingBox(None)

        p1 = transform.OfPoint(bb.Min)
        p2 = transform.OfPoint(bb.Max)
        filterOutline = Outline(p1, p2)
        if filterOutline.IsEmpty : return 
        bbIntersectsFilter = BoundingBoxIntersectsFilter(filterOutline)
        g1 = list(element._get_Geometry().GetTransformed(transform))
        g2 = []

        while g1 :
            e = g1.pop()
            if hasattr(e, "__iter__") :
                g1.extend(list(e))
            elif isinstance(e, Solid) :
                g2.append(e)
            elif isinstance(e, GeometryElement) :
                g1.extend(e)
        if not g2 : return
        solid = g2[0]

        solidIntersectsFilter = ElementIntersectsSolidFilter(solid)

        sectedBbIds = FilteredElementCollector(self.doc)\
                .WherePasses(categoryFilter)\
                .WherePasses(bbIntersectsFilter).ToElementIds()
        if not sectedBbIds : return
        print(f"количество элементов {len(sectedBbIds)}")
        sectedSolid = FilteredElementCollector(self.doc, sectedBbIds)\
                .WherePasses(solidIntersectsFilter).ToElements()
        for element in sectedSolid :
                yield dmElement(element, self.dmDoc, self)
   


class dmModel :
    def __init__(self, doc) :
        self.doc = doc
    def __repr__(self) :
        return f"Обект работы с моделью {self.doc.PathName}"
    def _getLinkedInstances(self) :	
        for instance in FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements() :
            yield dmLinkInstance(instance, self)
    linkedInstances = property(_getLinkedInstances)
    def _getWorksets(self) :
        return {ws.Name : ws for ws 
                    in FilteredWorksetCollector(doc)\
                    .OfKind(WorksetKind.UserWorkset).ToWorksets()}
    worksets = property(_getWorksets)

    def _getAuxWorkset(self) :
        try :
            return self._AuxWorkset
        except :
            self._AuxWorkset = self.worksets["Вспомогательный"]
            return self._AuxWorkset
    auxWorkset = property(_getAuxWorkset)
        
    
class dmElement :
    def __init__(self, element, dmDoc, fromLink = None) :
        self.element = element
        self.doc = dmDoc
        self.fromLink = fromLink
    def __repr__(self) :
        return f"Элемент {self.element.Category.Name} : {self.element.Id}"
    def _get_Geometry(self) :
        opt = Options()
        return self.element.Geometry[opt]
    def createDs(self) :
        if not self.fromLink :
            directShape = create_ds(self._get_Geometry())
        else :
            g = self._get_Geometry().GetTransformed(self.fromLink.instance.GetTotalTransform())
            directShape = create_ds(g)

        set_workset(directShape, self.doc.auxWorkset)       
        return directShape

    def findIntersectionBbElements(self) :
        for linkedModel in self.doc.linkedInstances :
            for sectedElement in linkedModel.getBBSectedElements(self) :
                yield sectedElement

    def findIntersectionElements(self) :
        for linkedModel in self.doc.linkedInstances :
            for sectedElement in linkedModel.getSolidSectedElements(self) :
                yield sectedElement

    def _getIntersectsElements(self) :
        try :
            return self._intersectsElements
        except :
            self._intersectsElements = list(self.findIntersectionElements())
            return self._intersectsElements
    intersectsElements = property(_getIntersectsElements)
    
        
            
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
            
class dmMain :
    def execute(self) :		
        self.dmDoc = dmModel(doc)
        print(self.dmDoc)
        print(list(self.dmDoc.linkedInstances))
        print("создаем элемент")
        #self.pipe = dmElement(doc.GetElement(ElementId(6602929)), self.dmDoc)
        self.pipe = dmElement(doc.GetElement(ElementId(6588424)), self.dmDoc)
        self.newDS = []
        for eref in uidoc.Selection.GetElementIds() :
            self.pipe = dmElement(doc.GetElement(eref), self.dmDoc)
            self.pipeDs = self.pipe.createDs()
            for e in self.pipe.findIntersectionElements() :
                    print(e)
                    ds = e.createDs()
                    self.newDS.append(ds)
