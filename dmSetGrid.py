dut = 0.0032808398950131233
from contextlib import contextmanager
import System, clr
from collections import deque
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
from Autodesk.Revit.DB import *

@contextmanager
def tr(doc = None, a="транзакция скрипта") :
    if not doc :
        doc = __revit__.ActiveUIDocument.Document
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

class dmElement :
    def __init__(self, e) :
        if isinstance(e, Element) :
            self.e = e
        elif isinstance(e, ElementId) :
            self.e = doc.GetElement(e)
        elif isinstance(e, int) :
            self.e = doc.GetElement(ElementId(e))
    def __hash__(self) :
        return self.e.Id.IntegerValue
    def __eq__(self, other) :
        return self.e.Id == other.e.Id
    def __repr__(self) :
        return f"dmElement Id=  {self.e.Id.IntegerValue}"
    def _getId(self) :
        return self.e.Id
    Id = property(_getId)

class dmGrid (dmElement):
    def __init__(self, grid, view) :
        dmElement.__init__(self, grid)
        self.grid = grid
        self.view = view #dmView
        self._projectedLine = None
    def __repr__(self) :
        return f"ось {self.grid.Name}"
    def __lt__(self, other) :
        return False
    def __gt__(self, other) :
        return False
    def _axisLine(self) :
        return self.grid.GetCurvesInView(DatumExtentType.ViewSpecific, self.view.view)[0]
        
    axisLine = property(_axisLine)
    def _getAxisLineUnbound(self) :
        al = self.axisLine
        return Line.CreateUnbound(al.GetEndPoint(0), al.Direction)
    axisLineUnbound = property(_getAxisLineUnbound)
    def _axisLineProjectedOnViewPlane(self) :
        #Возвращает линию оси спроецированную на плоскость вида
        if not self._projectedLine :
            viewLine = self.axisLine
            endP1, endP2 = viewLine.GetEndPoint(0), viewLine.GetEndPoint(1)
            newEndP1UV, newEndP2UV = self.view.plane.Project(endP1)[0], self.view.plane.Project(endP2)[0]
            newEndP1 = self.view.plane.Origin\
                        + self.view.plane.XVec * newEndP1UV.U \
                        + self.view.plane.YVec * newEndP1UV.V
            newEndP2 = self.view.plane.Origin \
                        + self.view.plane.XVec * newEndP2UV.U \
                        + self.view.plane.YVec * newEndP2UV.V
            self._projectedLine = Line.CreateBound(newEndP1, newEndP2)
        return self._projectedLine
    projectedLine = property(_axisLineProjectedOnViewPlane)
    def _checkIsEnd0InsideView(self) :
        #Проверяет, находится ли первый конец внутри вида
        p0 = self.projectedLine.GetEndPoint(0)
        if self.view.face.Project(p0) :
            return True
        else : return False
        
    IsEnd0InsideView = property(_checkIsEnd0InsideView)
    
    def _checkIsEnd1InsideView(self) :
        #Проверяет, находится ли первый конец внутри вида
        p1 = self.projectedLine.GetEndPoint(1)
        if self.view.face.Project(p1) :
            return True
        else : return False
        
    IsEnd1InsideView = property(_checkIsEnd1InsideView)
    
    def showOrHideBubbles(self) :
        #скрывает обозначения оси если конец попадает внутрь вида 
        #показывает если обозначение за пределами вида
        tr = None
        if not doc.IsModifiable :
            tr = Transaction(doc, "Показываем/скрываем обозначения осей")
            tr.Start()
        if self.IsEnd0InsideView :
            #надо скрыть 0 конец
            self.grid.HideBubbleInView(DatumEnds.End0, self.view.view)
        else :
            self.grid.ShowBubbleInView(DatumEnds.End0, self.view.view)
        if self.IsEnd1InsideView :
            #надо скрыть 1 конец
            self.grid.HideBubbleInView(DatumEnds.End1, self.view.view)
        else :
            self.grid.ShowBubbleInView(DatumEnds.End1, self.view.view)
        if tr : tr.Commit()

    
        
    def alignGridEnd(self, line, distance = 30 * dut) :
        print(self)
        #print(f"расстояние = {distance / dut} мм")
        irArray = clr.Reference[IntersectionResultArray]()		
        ir = line.line.Intersect(self.projectedLine, irArray)

        intersectionPoint = irArray.Item[0].XYZPoint
        axisLine = self.axisLine
        axisUnboundLine = Line.CreateUnbound(axisLine.GetEndPoint(0), axisLine.Direction)
        

        
        if intersectionPoint.DistanceTo(self.projectedLine.GetEndPoint(0)) <\
            intersectionPoint.DistanceTo(self.projectedLine.GetEndPoint(1)) :
            _newEndPoint = intersectionPoint - self.projectedLine.Direction * distance
            newEndPoint = axisUnboundLine.Project(_newEndPoint).XYZPoint
            #print(f"старая точка 0 {axisLine.GetEndPoint(0)}")
            #print(f"новая точка 0 {newEndPoint}")
            newLine = Line.CreateBound(newEndPoint, axisLine.GetEndPoint(1))

            if self.IsEnd0InsideView :
                datumEnd= DatumEnds.End0
            else :
                datumEnd= DatumEnds.End1
    
            leader = self.grid.GetLeader(datumEnd, self.view.view)
            
            with tr(a="добавляем выноску") : 
                self.grid.SetCurveInView(DatumExtentType.ViewSpecific, self.view.view, newLine)
                if not leader :
                    leader = self.grid.AddLeader(datumEnd, self.view.view)
    
                #leader.End = leader.Anchor
                leader.Elbow = leader.End
                self.grid.SetLeader(datumEnd, self.view.view, leader)
            
            
        else :
            _newEndPoint = intersectionPoint + self.projectedLine.Direction * distance
            newEndPoint = axisUnboundLine.Project(_newEndPoint).XYZPoint
            newLine = Line.CreateBound(axisLine.GetEndPoint(0), newEndPoint)
            #print(f"старая точка 0 {axisLine.GetEndPoint(0)}")
            #print(f"новая точка 0 {newEndPoint}")
            if self.IsEnd1InsideView :
                datumEnd= DatumEnds.End1
            else :
                datumEnd= DatumEnds.End0
            leader = self.grid.GetLeader(datumEnd, self.view.view)
            #leader = self.grid.GetLeader(DatumEnds.End0, self.view.view)
        
            with tr(a="добавляем выноску") :
                self.grid.SetCurveInView(DatumExtentType.ViewSpecific, self.view.view, newLine)
                if not leader :
                    leader = self.grid.AddLeader(datumEnd, self.view.view)
    
                #leader.End = leader.Anchor
                leader.Elbow = leader.End
                self.grid.SetLeader(datumEnd, self.view.view, leader)

                
class dmGridSected(dmGrid) :
    #Класс для представления осей, которые пересекает конкретная граница обрезки
    def __init__(self, axe, view, cropLine) :
        if isinstance(axe, Grid) :
            self.axe = dmGrid.__init__(axe, view)
        elif isinstance(axe, dmGrid) :
            self.axe = dmGrid.__init__(self, axe.grid, view)
        self.cropLine = cropLine
        self.bubbleSize = 8 * dut * self.view.view.Scale
        self.bubbleSize2 = self.bubbleSize/2
        
    def _getPosition (self) :
        return self.projectedLine.Distance(self.cropLine.line.GetEndPoint(0))
    position = property(_getPosition) 
    def __lt__(self, other) :
        return self.position < other.position
    def __gt__(self, other) :
        return self.position > other.position
    def __eq__(self, other) :
        return self.position == other.position
    def __hash__(self, other) :
        return self.grid.Id.IntegerValue
    def _getLeftRange(self) :
        return self.position - self.bubbleSize2
    leftRange = property(_getLeftRange)
    
    def getDatumEnd(self) :	
        #Возвращает DatumEnd для конца оси, которое связана с границей вида
        lineDirection = self.axisLine.Direction
        p0 = self.borderIntersectionPoint
        p1 = p0 + lineDirection
        if self.view.face.Project(p1) :
            return DatumEnds.End0
        else :
            return DatumEnds.End1

    datumEnd = property(getDatumEnd)

    def _getLeader(self) :
        return self.grid.GetLeader(self.datumEnd, self.view.view)
    leader = property(_getLeader)

    def _getBorderIntersectionPoint(self) :
        #Возвращает точку пересечения с границей вида
        #print(self)
        #print(f"расстояние = {distance / dut} мм")
        irArray = clr.Reference[IntersectionResultArray]()		
        ir = self.cropLine.line.Intersect(self.projectedLine, irArray)
        return irArray.Item[0].XYZPoint
    borderIntersectionPoint = property(_getBorderIntersectionPoint)

    def _getBorderIntersectionPointOnAxis(self) :
        ul = self.axisLineUnbound
        return ul.Project(self.borderIntersectionPoint).XYZPoint

    borderIntersectionPointOnAxis = property(_getBorderIntersectionPointOnAxis)

    def getOutViewDirection(self) :
        #Возвращает направление вдоль оси наружу вида от точки пересечения с границей вида
        lineDirection = self.axisLine.Direction
        p0 = self.borderIntersectionPoint
        p1 = p0 + lineDirection
        if self.view.face.Project(p1) :
            return -lineDirection
        else :
            return lineDirection
        
    def setEndPoint(self, distance = 30 * dut) :
        distanceScale = distance * self.view.view.Scale
        direction = self.getOutViewDirection()
        axisLine = self.axisLine
        _p0 = self.borderIntersectionPointOnAxis
        p0, p1 = axisLine.GetEndPoint(0), axisLine.GetEndPoint(1)
        datumEnd = self.datumEnd
        _p0 = _p0 + direction * distanceScale
        if datumEnd == DatumEnds.End0 :
            newLine = Line.CreateBound(_p0, p1)
        else :
            newLine = Line.CreateBound(p0, _p0)
        with tr() :
            self.grid.SetCurveInView(DatumExtentType.ViewSpecific, self.view.view, newLine)
            #self.grid.Document.Regenerate()
            #self.grid.Document.Regenerate()

        
        
    def setBubblePosition(self, bubblePosition) :   
        #Устанавливаем положение обозначения оси.
        selfPos         = self.position
        dBubblePosition = bubblePosition - selfPos

        outDirection    = self.getOutViewDirection()
        cropDirection   = self.cropLine.line.Direction
        borderIntersectPoint    = self.borderIntersectionPointOnAxis
        endPoint        = borderIntersectPoint \
                                + outDirection * 10 * dut * self.view.view.Scale
        elbowPoint = endPoint \
            + outDirection * 3 * dut * self.view.view.Scale\
            +  cropDirection * dBubblePosition
        leader = self.leader

        with tr(a="устанавливаем положение выносок на оси") :
            if not leader :
                leader = self.grid.AddLeader(self.datumEnd, self.view.view)
            #self.grid.SetLeader(self.datumEnd, self.view.view, leader)    
            leader.End = endPoint
            leader.Elbow = elbowPoint
            self.grid.SetLeader(self.datumEnd, self.view.view, leader)
            #self.grid.Document.Regenerate()
            self.grid.SetLeader(self.datumEnd, self.view.view, leader)


    def resetBubble(self) :
        leader = self.leader
        if not leader : return 
        with tr(a="сбрасываем выноски на осях") :
            print(self)
            leader.Elbow = leader.End
            self.grid.SetLeader(self.datumEnd, self.view.view, leader)
            self.grid.Document.Regenerate()

    
    def _setLeaderPosition_(self, elbowPosition, endPosition, offset) :
        print(f"Устанавливаем выноску:\n{self}\n{elbowPosition} {endPosition}")
        datumEnd = self.datumEnd
        print(f"datumEnd = {datumEnd}")
        grid = doc.GetElement(self.grid.Id)
        drawPoint(self.view.view, elbowPosition)
        drawPoint(self.view.view, endPosition)
        #return
        print(grid.GetDatumExtentTypeInView(datumEnd, self.view.view))

        leader = grid.GetLeader(datumEnd, self.view.view)
        if not leader :
            with tr() :
                leader = grid.AddLeader(datumEnd, self.view.view)
        z = leader.End.Z
        endPos = XYZ(endPosition.X, endPosition.Y, z)
        elbowPos = XYZ(elbowPosition.X, elbowPosition.Y, z)
        print(f"Устанавливаем выноску:\n{self}\nendPos={endPos}\nelbowPos={elbowPos}")
        trans = Transaction(self.view.view.Document, "установка выноски")
        trans.Start()
        leader.End = endPos
        leader.Elbow = elbowPos
        grid.SetLeader(datumEnd, self.view.view, leader)
        trans.Commit()

        leader = grid.GetLeader(datumEnd, self.view.view)
        print(self.view.view.Name)
        print(f"Устанавливаем выноску:\n{self}\nend={leader.End}\nElbow={leader.Elbow}\nAnchor={leader.Anchor}")
        print(grid.Id)
        with tr() :
            leader.End = endPos
            leader.Elbow = elbowPos
            grid.SetLeader(datumEnd, self.view.view, leader)

            


            
            

        
        
        
def drawPoint(view, p) :

    p1 = p - XYZ.BasisX
    p2 = p + XYZ.BasisX
    p3 = p - XYZ.BasisY
    p4 = p + XYZ.BasisY
    l1, l2 = Line.CreateBound(p1, p2), Line.CreateBound(p3, p4)
    with tr() :
        doc.Create.NewDetailCurve(view, l1)
        doc.Create.NewDetailCurve(view, l2)

class dmCropLine :
    def __init__(self, view, line) :
        self.view = view #dmView
        self.line = line
        self.cropEnd0 = line.GetEndPoint(0)
        self._sectedGridList = None 
    def __repr__(self) :
        return f"Линия границы {self.line.GetEndPoint(0), self.line.GetEndPoint(1)}"
    def _getSectedGrid(self) :
        for g in self.view.Grid :
            if self.line.Intersect(g.projectedLine) == SetComparisonResult.Overlap : 
                yield dmGridSected(g, self.view, self)
    sectedGrid = property(_getSectedGrid)

    def __getitem__(self, index) :
        try :
            return self._sectedGridList[index]
        except :
            self._sectedGridList = sorted(list(self.sectedGrid), key = lambda x : x.position)
            return self._sectedGridList[index]
    def drawLine(self) :
        with tr(a = "Рисуем линию границы") :
            doc.Create.NewDetailCurve(self.view.view, self.line)
    def alignGridEnds(self, distance = 30 * dut) :
        with tr(a = "выравнивание осей") :
            for grid in self.sectedGrid :
                grid.setEndPoint(distance)

    def alignGridBubbles(self, bubbleSize = 0) :
        #Выстраивание обозначений осей так чтобы они не перекрывались
        startPnt = self.line.GetEndPoint(0) 
        #self.view.view.Document.Regenerate()
        if bubbleSize == 0 :
            bubbleSize = 8 * dut * self.view.view.Scale
        else :
            bubbleSize = bubbleSize * self.view.view.Scale
        grids = deque(sorted([grid for grid in self.sectedGrid]))
        groups = []
        
        for grid in grids :
            print(grid, grid.position)
        
        
        i = 0
        if len(grids) < 2 : return
        prevAxe = grids.popleft()
        group = dmGridGroup(bubbleSize)
        group.addGrid(prevAxe)
        
        while grids :
            i += 1 
            if i > 1000 : raise
            
            axe = grids.popleft()
            print(20*"-")
            #print(prevAxe)
            print(f"Взяли ось {axe}")
            #print(group < axe)
            
            if group < axe :
                #Ось пересекает группу, значит ось добавляем в группу
                print("Ось пересекает, добавляем...")
                group.addGrid(axe)
                continue
            else :
                #Ось не пересекает группу, значит, надо проверить, не пересекает ли группа предыдущую группу помещаем в очередь
                print("Ось не пересекается с активной группой")
                if len(groups) > 0 and groups[-1] < group :
                    print("группы пересекаются, надо объединить")
                    prevGroup = groups.pop()
                    prevGroup.addGroup(group)
                    group = prevGroup
                    print(f"Проверяем пересекается ли получившаяся группа с осью {axe}")
                    if group < axe :
                        print("Ось пересекается, надо добавить ее в группу")
                        group.addGrid(axe)
                    else :
                        print("Ось не пересекается, текущую группу помещаем в очередь, создаем новую группу")
                        groups.append(group)
                        group = dmGridGroup(bubbleSize)
                        group.addGrid(axe)
                    
                elif len(groups) > 0:
                    print("В списке есть обработанные группы, надо проверить, не пересекает ли текущая группа последнюю из групп")
                    print("группы не пересекаются, помещаем в групу в очередь, создаем новую группу   в которую помещаем ось и двигаемся дальше")
                    groups.append(group)	
                    group= dmGridGroup(bubbleSize)
                    group.addGrid(axe)
                    
                else :
                    print("это первая группа, помещаем ее в очередь и создаем нову группу в которую помещаем ось")
                    groups.append(group)	
                    group= dmGridGroup(bubbleSize)
                    group.addGrid(axe)
                
                
        
        groups.append(group)
        print(f"Создано {len(groups)} групп")
        #return
        self.groups = groups
        for num, group in enumerate(groups) :
            print(20*"-")
            print(f"группа {num}")
            print(f"{group.center/dut}")
            for axis in group.grids :
                print(axis)


        
                
        
        print(80 * "|")
        print(f"Начинаем создание выносок")
        
        self.groups = groups
        
        
        for num, group in enumerate(groups[:]) :
            print(f" группа {num}" +  20 * "*"  )
            for pos, grid in group.calcBubblePositions() :
                print(pos, grid, grid.position)
                grid.setBubblePosition(pos)

    def resetGridBubbles(self) :
        with tr(a="Сбрасываем положения  метотк для осей") :
            for grid in self.sectedGrid :
                grid.resetBubble()

                
    def createDimensionForAll(self, distance = 5 * dut, hide = True) :
        #Создание размера для всех осей
        distance = -distance * self.view.view.Scale
        refArray = ReferenceArray()
        sortedGrids = sorted(self.sectedGrid, key = lambda x : x.position)
        if len(sortedGrids) < 2 : return
        currentPos = -1000
        for grid in sortedGrids :
            if abs(grid.position - currentPos) > 15 * dut :
                refArray.Append(Reference(grid.grid))
                currentPos = grid.position

        dimLine = self.line.CreateOffset(distance, self.view.view.ViewDirection)
        
        with tr(a="Создаем размер для осей у границы") :
            newDim = self.view.view.Document.Create.NewDimension(self.view.view, 
                                                                 dimLine, refArray)
            if hide :
                self.view.hideElementOnOtherViews(newDim)
            
    def createDimensionForEnds(self, distance = 10 * dut, hide = True) :
        #Создание размера для всех осей
        distance = -distance * self.view.view.Scale
        refArray = ReferenceArray()
        sortedGrids = sorted(self.sectedGrid, key = lambda x : x.position)
        if len(sortedGrids) < 2 : return
        refArray.Append(Reference(sortedGrids[0].grid))
        refArray.Append(Reference(sortedGrids[-1].grid))
        
        dimLine = self.line.CreateOffset(distance, self.view.view.ViewDirection)
        with tr(a="Создаем размер для крайних осей у границы") :
            newDim = self.view.view.Document.Create.NewDimension(self.view.view, 
                                                                 dimLine, refArray)
            self.view.hideElementOnOtherViews(newDim)
        



                
            
            
                
                    
        
        
class dmGridGroup :
    #Класс для реализации группирования осей и вычисления расположения обозначений
    def __init__(self, bubbleSize = 8 * dut * 200) :
        self.bubbleSize = bubbleSize	
        self.bubbleSize2 = bubbleSize/2
        self.grids = []
        self.centers = []
        self.leftRange = 0
        self.rightRange = 0
        self.center = 0
    def addGrid(self, grid) :
        self.grids.append(grid)
        self.centers.append(grid.position)
        self.center = sum(self.centers) / len(self.centers)
        self.leftRange = self.center - self.bubbleSize * len(self.centers) / 2
        self.rightRange = self.center + self.bubbleSize * len(self.centers) / 2
        
    def checkIfIntersect(self, other) :
        if isinstance(other, dmGridSected) or isinstance(other, dmGridGroup) :
            return self.rightRange >= other.leftRange
        return False
        
    def __lt__(self, other) :
        if isinstance(other, dmGridGroup) or isinstance(other, dmGridSected) :	
            return self.rightRange > other.leftRange
            
    def calcBubblePositions(self) :
        for num, grid in enumerate(self.grids) :
            yield (self.leftRange + self.bubbleSize * num + self.bubbleSize2, grid)
            
    def addGroup(self, other) :
        for grid in other.grids :
            self.addGrid(grid)
                        
        
class dmView:
    def __init__(self, view) :
        self.view = view
        self._face = None
        self._getAreaAsFace()
        self.plane = Plane.CreateByNormalAndOrigin(self.view.ViewDirection, self._face.Origin)
        self._borderLinesList = None 
    def __repr__(self) :
        return f"dmView {self.view.Name} - для работы с осями"
    def _getVisibleGrid(self) :
        fc = FilteredElementCollector(doc, self.view.Id).OfClass(Grid).ToElements()
        #print(f"Количество видимых осей {len(fc)}")
        return [dmGrid(grid, self) for grid in fc if grid.CanBeVisibleInView(self.view)]
    Grid = property(_getVisibleGrid)
    
    def _getAreaAsFace(self) :
        if not self._face :
            cropManager = self.view.GetCropRegionShapeManager()
            cropShape = cropManager.GetCropShape()
            solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
            solid = GeometryCreationUtilities\
                        .CreateExtrusionGeometry(cropShape, 
                                                    self.view.ViewDirection, 
                                                    1, solid_opt)									
            for _face in solid.Faces :
                if _face.FaceNormal.DotProduct(self.view.ViewDirection) == -1 :
                    self._face = _face
        return self._face
    face = property(_getAreaAsFace)
    
    def showHideGridBubbles(self) :
        tr = None
        if not doc.IsModifiable :
            tr = Transaction(doc, "Показываем/скрываем обозначения осей")
            tr.Start()
        for g in self.Grid :
            g.showOrHideBubbles()
        if tr : tr.Commit()
        
    def _getBorderLines(self) :
        cropManager = self.view.GetCropRegionShapeManager()
        cropShapes = cropManager.GetCropShape()
        for cropShape in cropShapes :
            for line in cropShape :
                yield dmCropLine(self, line)
    borderLines = property(_getBorderLines)

    def __getitem__(self, index) :
        try :
            return self._borderLinesList[index]
        except :
            self._borderLinesList = list(self.borderLines)
            return self._borderLinesList[index]
    
    def alignGridEnds(self, distance = 30 * dut) :
        for bl in self.borderLines :
            bl.alignGridEnds(distance)
    def alignGridBubbles(self) :
        with tr(a="выравнивание меток осей на всем виде") :
            for bl in self.borderLines :
                bl.alignGridBubbles()
    def resetGridBubbles(self) :
        with tr(a="сброс положения маркеров осей на виде") :
            for bl in self.borderLines :
                bl.resetGridBubbles()

    def createDimensions(self) :
        for bl in self.borderLines :
            bl.createDimensionForAll()
            bl.createDimensionForEnds()

    def hideElementOnOtherViews(self, element) :
        primaryViewId = self.view.GetPrimaryViewId()
        if primaryViewId :
            #Значит, элемент является подчиненным, скрываем элемент на  основном виде
            primaryView = doc.GetElement(primaryViewId)
            dependentViews = [doc.GetElement(eId) for eId in primaryView.GetDependentViewIds()]
            
        else :
            dependentViews = [doc.GetElement(eId) for eId in self.view.GetDependentViewIds()]
        elementArray = System.Array[ElementId]([element.Id])
        with tr(a ="прячем элементы на зависимых видах") :
            if primaryView :
                primaryView.HideElements(elementArray)
            for dependentView in dependentViews :
                if dependentView.Id != self.view.Id :
                    dependentView.HideElements(elementArray)

    def deleteAxisDemensionsInView(self) :
        viewFlt = VisibleInViewFilter(self.view.Document, self.view.Id)
        classFlt = ElementClassFilter(Dimension)
        andFlt = LogicalAndFilter(viewFlt, classFlt)
        elSet = set()
        for axis in self.Grid :
            print(axis)
            depElements = axis.e.GetDependentElements(andFlt)
            for e in depElements :
                elSet.add(dmElement(e))
        with tr(a='удаляем размеры для осей') :
            for e in elSet :
                print(e)
                self.view.Document.Delete(e.Id)


        



import re
class dmApp4Views :
    def __init__(self) :
        self.doc = __revit__.ActiveUIDocument.Document
        self.uidoc = __revit__.ActiveUIDocument

    def getViewsStartsWith(self, s = "") : 
        fc = FilteredElementCollector(self.doc).OfClass(View).WhereElementIsNotElementType().ToElements()
        for view in fc :
            if view.Name.StartsWith(s) : yield dmView(view)


        
        
        

