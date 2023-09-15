#  coding: utf-8 
"""
***************************************************************
* Скрипт для переадресации устройств в цепи
* 
* 
***************************************************************
"""

from xml.dom.minidom import Element
from xml.etree.ElementPath import prepare_parent
from Autodesk.Revit import *
from Autodesk.Revit.DB import *
import Autodesk.Revit.Exceptions
import System 
import clr

import math, sys
import clr

import re

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\YC.QuickGraph.3.7.4\lib\net45\YC.QuickGraph.dll")
import QuickGraph as qg


clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
import NetTopologySuite as nts
import NetTopologySuite.Geometries as nts_geom


lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
	sys.path.append(lib_path)
	

lib_path = r"D:\18_проектирование\98_PythonShell\Создание фильтров"
if not lib_path in sys.path :
	sys.path.append(lib_path)
	



pi2 = math.pi * 2

dut = 0.0032808398950131233

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType


uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

	
import dm_connect_2 as dm
import dm_nearest_geometry as dm1
import collections

reload(dm)	
reload(dm1)

print("dm60_renumber_equipment.py")

import re


class dmElement(object) :
    def __init__(self, e, panel = None) :
        if isinstance(e, ElementId) :
            self.element = doc.GetElement(e)
        elif isinstance(e, Element) :
            self.element = e
        self.panel = panel

    def __repr__(self) :
        return "\n{}\n{}".format(Element.Name.GetValue(self.element), self.element.Id)
    
    def _get_connectors(self) :
        try :
            return self.element.ConnectorManager.Connectors
        except :
            return self.element.MEPModel.ConnectorManager.Connectors

    connectors = property(_get_connectors)

    def _get_connected_elements(self) :
        res = []
        for c1 in self.connectors :
            if c1.Domain != Domain.DomainCableTrayConduit : continue
            for c2 in c1.AllRefs :
                if c2.Owner.Id != self.element.Id :
                    res.append(dmElement(c2.Owner))

        return res
    connected_elements = property(_get_connected_elements)

    def _get_id(self) :
        return self.element.Id

    Id = property(_get_id)

    def __eq__(self, e) :
        if isinstance(e, dmElement)  :
            return self.Id == e.Id 
        if isinstance(e, Element) :
            return self.Id == e.Id 
        if isinstance(e, ElementId) :
            return self.Id == e
        return False


    def get_wfs(self) :
        """
        ***************************************************************
        * Возврат присоединенных элементов по алгоритму поиска в ширину
        * 1
        * 
        ***************************************************************
        """



        to_visit = collections.deque([self])
        visited = []
        prev = {}
        
        i = 0
        # print("начало обхода")
        while len(to_visit) > 0 :
            i += 1
            if i > 1000 : break 

            current = to_visit.popleft()
            visited.append(current)
            # print(current)
            

            for e1 in current.connected_elements :
                if e1.Id in visited : continue

                if not e1 in prev.keys() :
                    # print('1')
                    prev[e1.Id] = current

                if not e1 in to_visit :
                    to_visit.append(e1)


        return prev 

    def get_distances(self, system) :
        """
        ***************************************************************
        * Вычисляет расстояния до всех устройств в системе
        * учитываются только те, до которых можно добраться по лоткам и коробам
        * 
        ***************************************************************
        """ 
        def get_connector(el, prev_el) :
            """
            ***************************************************************
            * Возвращает коннектор, который соединяет el и prev_el
            * 
            * 
            ***************************************************************
            """
            # print('get_connector')
            # print(el)
            # print(prev_el)
            # print(80*"-")


            for c1 in el.connectors :
                for c2 in c1.AllRefs :
                    if c2.Owner.Id == prev_el.Id :
                        return c1 

        def get_wire_length(e) :
            """
            ***************************************************************
            * Вычисление расстояния до заданного элемента
            * 
            * 
            ***************************************************************
            """
            current = e 
            current_p = None
            prev_p = None 
            i_ = 0 
            i_max = len(prevs)
            distance = 0
            points = collections.deque([])
            while i_ < i_max :
                i_+=1
                # Находим предшествующий элемент в цепочке
                try :  
                    prev = prevs[current.Id]
                except :
                    # Если предыдущего элемента нет, значит, это послеедний в цепочке
                    break
                # Находим каким коннетором они соединяются
                conn1 = get_connector(current, prev)
                # Находим точку расположения коннектора
                current_p = conn1.Origin
                points.appendleft(current_p)
                try :
                    # Пытаемся найти расстояние с предыдущей точкой, если это первая точка, то будет исключение
                    distance += (prev_p - current_p).GetLength()
                except :
                    pass

                # Текущая точка становится предыдущей
                prev_p = current_p
                # Текущий элемент становится предыдущим
                current = prev 

            return distance, points 
            
        print("Начинаем расчеты расстояний")
        # print(type(system))
        prevs = self.get_wfs()

        
        # print(prevs)
        # print("Обход сделан")
        # elements = list(system.elements)
        elements = system 
        # print(len(elements))
        # print(elements)

        if self in elements :
            # print("Нашел себя в системе")
            elements.remove(self)
        res = {}
        points = {}
        # Для каждого элемента из системы пытаемся вычислить длину провода. Если не находится, то 
        # будет исключение и элемент будет пропущен.
        
        for el in elements :     
            try :
                # print(el.Id)
                print("get_wire_length")
                res[el.Id], points[el.Id] =  get_wire_length(el)
            except Exception as ex:
                print("get_wire_length ошибка")
                
                raise
                

        return res, points 
    def get_nearest(self, system, exclude = None) :
        """
        ***************************************************************
        * Возвращает ближайший элемент, который принадлежит системеме system
        * и подключен через систему гофрированных труб или лотков
        * 
        ***************************************************************
        """
        # print("get_nearest")
        # print(type(system))
        
        dist, points = self.get_distances(system=system)
        try :
            nearest = min(dist, key = dist.get)
            nearest = dmElement(nearest)
            return nearest, points[nearest.Id]
        except Exception as ex:
            # raise
            return 


        
                

class dmElectricalSystem(object) :
    def __init__(self, system) :
        self.system = system 

    def _get_elements(self) :
        for e in  self.system.Elements :
            yield(dmElement(e))
    elements = property(_get_elements)

    def __repr__(self) :
        return "Электрическая система : {}".format(self.system.Name)

    def _get_panel(self) :
        return dmPanel(self.system.BaseEquipment)
    
    panel = property(_get_panel) 

    def _get_equipment_ordered(self) :
        equipment_list = list(self.elements)
        

        next1, points = self.panel.get_nearest(equipment_list) 
   
        for i in range(1000) :
            print("Выдача следующего {} {}".format(next1, type(next1)))
            yield next1, points
            try :
                next1, points = next1.get_nearest(equipment_list)
            except :
                print("Ошибка. Поиск следующего")
                print("{} {}".format(next1.Id, type(next1)))
            
            if not next1 : 
                raise StopIteration          
            if len(equipment_list) == 0 : 
                raise StopIteration

            equipment_list.remove(next1)

        return

    def renumber_equipment(self, start = 1) :
        equipment_list = self._get_equipment_ordered()

        tr = Transaction(doc) 
        tr.Start("Renumber equipment in line")
        num = start

        for e, pnts in equipment_list :
            param = e.element.LookupParameter("ADSK_Номер в шлейфе").Set(num)

            try :
                adrs = e.element.LookupParameter("ADSK_Количество занимаемых адресов").AsInteger()
                print("Количество адресов {}".format(adrs))
                num += adrs
            except :
                print(num)
                num += 1

        tr.Commit()

    def set_wire_trace(self, closed = True) :
        """
        ***************************************************************
        * Устанавливаем трассу как проходит провод
        * 
        * 
        ***************************************************************
        """

        equipment_list = list(self._get_equipment_ordered())
        if closed :
            panel = equipment_list[-1][0].get_nearest([self.panel])
            equipment_list.append(panel)
        self.equipment_list = equipment_list

        print(equipment_list[-1])


        points = []
        for num, (eq, pnts) in enumerate(equipment_list) :
            if num > 1000 : break

            if True :        
                try :
                    # print(eq)
                    # print(pnts)
                    points.extend(pnts)
                    # print(80 * "---")
                except :
                    break
        # print(points)
        self.points = points

        old_points = self.system.GetCircuitPath()

        

        prev_point = old_points[0]

        points_ = [prev_point]

        print(len(points))
        

        for num, p in enumerate(points) :
            if num > 5000 : break

            p1 = p - prev_point

            if abs(p1.X) > dut :
                print(p1.X)
                prev_point = prev_point + XYZ.BasisX * p1.X
                points_.append(prev_point)
            
            if abs(p1.Y) > dut :
                print(p1.Y)
                prev_point = prev_point + XYZ.BasisY * p1.Y
                points_.append(prev_point)
            if abs(p1.Z) > dut : 
                prev_point = prev_point + XYZ.BasisZ * p1.Z
                points_.append(prev_point)

        print(num)
        print("Количество новых точек : {} ".format(len(points_)))
            


        tr1 = Transaction(doc)
        tr1.Start("Modify circuit path")

        self.system.SetCircuitPath(points_[:])

        tr1.Commit()




class dmPanel(dmElement) :
    def __init__(self, e) :
        super(dmPanel, self).__init__(e)
        self.panel = e  
    def __repr__(self) :
        return "Панель {} {} {}".format(self.panel.Name, Element.Name.GetValue(self.panel.Symbol), self.Id)

    def _get_systems(self) :
        return [dmElectricalSystem(e) for e in self.panel.MEPModel.AssignedElectricalSystems]

    systems = property(_get_systems)

    

class dmPanels(object) :
    def __init__(self) :
        pass
        self.panels = [dmPanel(e) for e in FilteredElementCollector(doc).OfCategory(bic.OST_ElectricalEquipment).WhereElementIsNotElementType().ToElements()]

    def __getitem__(self, index) :
        return self.panels[index]
    def __repr__(self) :
        return "Количество панелей : {}".format(len(self.panels))

import clr 
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System.Windows import Forms
from System import Drawing
def create_form() :
    f = Forms.Form()
    f.Size = Drawing.Size(1000, 520)
    f.Show()

    tv = Forms.TreeView()

    tv.Size = Drawing.Size(450, 450)
    tv.Location = Drawing.Point(20, 20)
    f.Controls.Add(tv)

    to_visit = [panel]
    prev = {}
    visited = []


    nodes = {}
    
    i_ = 0
    while len(to_visit) > 0 :
        i_ += 1
        if i_ > 100 : break
        current = to_visit.pop()
        visited.append(current)

        # Добавляем в ноды

        try :
            node = nodes[current]
        except :
            node = tv.Nodes.Add(str(current))

        


        connected = current.connected_elements

        for ce in connected :
            if ce in visited : continue

            if not ce in to_visit :
                to_visit.append(ce)
                prev[ce] = current

                # nodes[ce] = node.Nodes.Add(str(ce))

    lv = Forms.ListView()
    lv.Size = Drawing.Size(450, 450)
    lv.Location = Drawing.Point(500, 20)
    f.Controls.Add(lv)







print("Начало работы") 

panels = dmPanels()	
panel = panels[0]

# graph = qg.UndirectedGraph.new()

#create_form()


	
