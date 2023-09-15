#  coding: utf-8 


from Autodesk.Revit import *
from Autodesk.Revit.DB import *
import Autodesk.Revit.Exceptions
import System 
import clr

import math, sys
import clr

import re

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

reload(dm)	
reload(dm1)

print("dm60_renumber_equipment.py")

import re

def get_equipment(name) :
    panels_col = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalEquipment)
    panels_col.WhereElementIsNotElementType()
    panels = panels_col.ToElements()
    res = []
    
    for p in panels :
        if re.match(name, Element.Name.GetValue(p), re.I) :
            res.append(p)
            
    if len(res) > 0 :
        return res
    else :
        return

def get_connected_conduits(element_id) :
    """
    ***************************************************************
    * Возвращает список подключенных к устройству элементов коробов
    * 
    * 
    ***************************************************************
    """
    check_print = False

    e = doc.GetElement(element_id)
    try :
        connectors = e.ConnectorManager.Connectors
    except :
        connectors = e.MEPModel.ConnectorManager.Connectors

    connectors = [c for c in connectors if c.Domain == Domain.DomainCableTrayConduit]

    if check_print :
        print('**************************')
        print('get_connected_conduits Контрольная точка ----------')
        print('Количество коннекторов')
        print('len(connectors) : {} Ед изм.'.format(len(connectors)))

    res = []

    for c in connectors :
        for c1 in c.AllRefs :
            if c1.Owner.Id != element_id :
                res.append(c1.Owner.Id)

    if check_print :
        print('**************************')
        print('get_connected_counduits Контрольная точка ----------')
        print('Количество подключенных элементов')
        print('len(res) : {} шт.'.format(len(res)))

    return res


def get_circuit_len(e, lst) :
    check_print = True
    """
    ***************************************************************
    * Находим длину линии до прибора
    * На входе прибор id прибора и словарь с предыдущими элементами
    * структура словаря : ключ - id элемента значение - id предшествующего элемента
    ***************************************************************
    """
    plen = 0

    while True :
        try :
            prev = lst[e]
            try :
                plen += doc.GetElement(prev).Location.Curve.Length
            except :
                pass 
            e = prev 
        except :
            break

    return plen


def get_nearest_device(device, device_list, num_to_compare = 5) :
    """
    ***************************************************************
    * Находит ближайшее устройство в сети коробов из тех, которое
    * входит в переданный список
    * Ближайшее означает, что к нему минимальное расстояние вдоль
    * коробов
    
    Входные данные:
    device - ElementId - устройство от которого начинаем поиск
    device_list - список устройств ближайшее из которых надо найти
    ***************************************************************
    """


    # создаем переменные для работы алгоритма
    found = []
    to_visit = deque([device])
    visited  = []
    previous = {}
    lengths = {}

    # проходом в ширину, находим ближайшие несколько устройств
    while len(to_visit) > 0 and len(found) < num_to_compare :
        this = to_visit.pop()
        connected_conduits = get_connected_conduits(this)

        if this in device_list :
            found.append(this)
            device_list.remove(this)

        visited.append(this)

        for c in connected_conduits :
            if c in visited : continue
            if c in to_visit : continue

            to_visit.appendleft(c)

            if not c in previous.keys() :
                previous[c] = this

    #  Вычисляем для этих устройств длинну необходимой линии и выбираем ближайший

    for e in found :
        lengths[e] = get_circuit_len(e, previous)
    try :
        nearest = min(lengths, key = lengths.get)
        found.remove(nearest)
        device_list.extend(found)
    except :
        nearest = None 

    # Возвращаем элементы, которые не являются ближайшим, обратно в список


    return nearest




        



       
class dmElectricalSystem(object) :
    def __init__(self, system, panel) :
        self.system = system
        self.panel = panel
    def __repr__(self) :
        panel_name = self.system.BaseEquipment.LookupParameter("Имя панели").AsString()
        return "Прибор: {}\nЦепь {}".format(panel_name, self.system.Name)
        
    def _get_devices(self) :		
        return self.system.Elements
        
    devices = property(_get_devices)
    
    def renumber_equipment(self) :
        panel_num = self.panel.device_num
        
        for dev_num, d in enumerate(self.ordered_devices, 1) :
            # print("Временная заглушка")
            # return 
            
            try :
                dpar = d.LookupParameter("ADSK_Имя устройства")
                #dname = dpar.AsString()
                
                dpos_par = d.LookupParameter("ADSK_Позиция")		
                if not dpos_par :
                    type_id = d.GetTypeId()
                    d_type = doc.GetElement(type_id)
                    dpos_par = d_type.LookupParameter("ADSK_Позиция")
                
                if dpos_par :
                    dpar.Set(dpos_par.AsString())

                num_par = d.LookupParameter("ADSK_Номер в шлейфе")
                num_par.Set(dev_num)
                # num_par.Set(0)

                d.LookupParameter("ADSK_Имя панели").Set(panel_num)
               
            except Exception as ex:
                print(ex)
                pass
            print(d.Name)

    def _get_ordered_devices(self) :
        """
        ***************************************************************
        * Возврат оборудования в цепи в упорядоченном виде
        * 
        * 
        ***************************************************************
        """

        res = []

        current_device = self.panel.panel.Id
        device_list = [e.Id for e in self.devices]

        while len(device_list) > 0 :

            next = get_nearest_device(
                                device=current_device,
                                device_list=device_list
                            )

            if next :
                res.append(next)

                
            else :
                break 

        res = [doc.GetElement(e) for e in res]

        return res


    ordered_devices = property(_get_ordered_devices)


        
        
class dmPanel(object) :
    def __init__(self, panel) :	
        self.panel = panel		
    def __repr__(self) :
        return "{}".format(Element.Name.GetValue(self.panel))
    
    def _get_electrical_systems(self) :
        systems = self.panel.MEPModel.GetAssignedElectricalSystems()		
        self._systems = [dmElectricalSystem(s, self) for s in systems]
        return self._systems
    electrical_systems = property(_get_electrical_systems)
    
    def _get_connectors(self) :
        return self.panel.MEPModel.ConnectorManager.Connectors
        
    connectors = property(_get_connectors)
    
    def _get_conduit_connectors(self) :
        return [c for c in self.connectors if c.Domain == Domain.DomainCableTrayConduit]	
    cond_connectors = property(_get_conduit_connectors)
    
    def _get_conduit_starts(self) :
        panel_id = self.panel.Id
        res = []
        for c in self.cond_connectors :
            for con1 in c.AllRefs :
                if con1.Owner.Id != panel_id :
                    res.append(doc.GetElement(con1.Owner.Id) )
                    
        return res
    cond_starts = property(_get_conduit_starts)
        
    def _get_conduit_circuit(self, num) :
        
        cond = self.cond_starts[num]
        panel_id = self.panel.Id
        visited_id = [panel_id]
        to_visit_id = [cond.Id]
        
        while len(to_visit_id) :
            current_part_id = to_visit_id.pop()
            current_part = doc.GetElement(current_part_id)
            
            try :
                connectors = current_part.ConnectorManager.Connectors
            except :
                connectors = current_part.MEPModel.ConnectorManager
                
                    
        return "wait"
 
    conduit_starts = property(_get_conduit_starts)

    def _get_device_num(self) :
        return self.panel.LookupParameter("ADSK_Номер устройства").AsString()

    device_num = property(_get_device_num)

  

panels = get_equipment("ARK.1")

kdl = dmPanel(panels[0])
print(kdl.electrical_systems)
system = kdl.electrical_systems[0]

from time import time 
import random

tt1 = time()



ordered_list = system.ordered_devices

for d in ordered_list :
    print(d)

tr1 = Transaction(doc)
tr1.Start("Переадресация устройств")
system.renumber_equipment()

tr1.Commit()
    

tt2 = time()

print("Время выполнения {} c".format(tt2-tt1))
# print("Количество найденых устройств {}".format(len(res)))

print("000")
    
    
		
	
