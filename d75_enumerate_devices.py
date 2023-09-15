#  coding: utf-8 

from os import P_NOWAIT
from pickletools import markobject
from Autodesk.Revit import *
from Autodesk.Revit.DB import *

import math, sys
import clr

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
import NetTopologySuite as nts
import NetTopologySuite.Geometries as nts_geom


lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
	sys.path.append(lib_path)


pi2 = math.pi * 2

dut = 0.0032808398950131233
dut_v = 0.092903040000000006

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

	
import dm_connect_2 as dm
import dm_nearest_geometry as dm1

reload(dm)	
reload(dm1)

print("нумерация устройств")
import re
import collections 

class dmVertex(object) :
    def __init__(self, g, v) :
        self.v = v
        self.G = g 
        self.data = {}
        self.edges_in = set()
        self.edges_out = set()

    def __repr__(self) :
        return "Вершина графа: v = {}, Id = {}, pos = {}".format(self.v, self.Id, self.pos)

    def AddEdgeTo(self, u) :
        self.edges_out.add(u.v)
        u.edges_in.add(self.v)
    def AddEdgeFrom(self, v) :
        self.edges_in.add(v.v)
        v.edges_out(self)

class dmVertexes(object) :
    def __init__(self, g) :
        self.G = g 
        self.V = collections.defaultdict(None)

    def __len__(self) :
        return len(self.V)

    def AddVertex(self, v) :
        # Создаем и добавляем вершину.
        # v = это словарь в котором присутствуют элементы с ключами Id и pos
        vv = dmVertex(g=self.G, v=v)
        self.V[v] = vv
        return vv
        
    def __getitem__(self, item) :
        if item in self.V.keys() :
            return self.V.keys[item]
        else :
            return self.AddVertex(item)
        

    def __iter__(self) :
        return self

    def __next__(self) :
        for v in self.V.values() :
            yield v

        raise StopIteration
    def next(self) :
        for v in self.V.values() :
            yield v
        raise StopIteration

    def AddEdge(self, e) :
        v = self.V[e[0]]
        u = self.V[e[1]]
        v.AddEdgeTo(u)
        u.AddEdgeTo(v)

    
class dmEdge(object) :
    def __init__(self, g, e) :
        self.G = g 
        self.e = e 
        self.d = {}
        # Добавить ссылки на эту
        self.v = e[0]
        self.u = e[1]
        self.v.Add

    def __repr__(self) :
        return "Ребро {}".format(self.e)

class dmEdges(object) :
    def __init__(self, g) :
        self.G = g 
        self.E = collections.defaultdict(collections.defaultdict)
        self.d = {}

    def __len__(self) :
        return len(self.E)

    def AddEdge(self, e) :
        if isinstance(e[0], int) and isinstance(e[1], int) :
            print("AddEdges")
            try : 
                if e in self.E :
                    return self.E[e]
                else :
                    # Такого ребра нет, теперь необходимо проверить, что присутствуют вершины
                    # потому что при передаче индекса вершины создавать новую не будем
                    try :
                        v = self.G.V[e[0]]
                        u = self.G.V[e[1]]
                    except :
                        print("Одна или обе вершины отсутствуют")
                        raise 
                    ee = dmEdge(self.G, (v, u))
                    self.E[e] = ee
                    return ee 
            except Exception as ex :
                print(ex)
                raise
        else: 
            v_ = e[0]
            u_ = e[1]

            if isinstance(v_, dmVertex) and isinstance(v_, dmVertex) :

                



            


class dmGraph(object) :
    def __init__(self) :
        self.new_vertex_num = 0
        self.V = dmVertexes(self)
        self.E = dmEdges(self)
    def __repr__(self) :
        res = "Граф"
        return res
    

    def AddVertex(self, Id, pos) :
        # Добавляем вершину
        return self.V.AddVertex(Id = Id, pos = pos)

    def AddEdge(self, e) :    
        print("Добавляем {}".format(e))    
        self.E.AddEdge(e)

    def GetVertexByData(self, Id, pos) :
        print('GetVertexByData')
        v = self.V.AddVertex(Id=Id, pos=pos)
        print("возвращаем v {}".format(v))
        return v 










    


class dmDevice(object) :
    def __init__(self, e) :
        self.e = e

    def __repr__(self) :
        # return "Устройство:\n{} : {}\n{} : {}".format(self.e.Category.Name)
        try :
            return "Устройство : {}\n{} : {}".format(self.e.Category.Name, Element.Name.GetValue(self.e), self.e.Id)
        except :
            return "none"
    
    def _get_connectors(self) :
        if hasattr(self, '_connectors') :
            return self._connectors
        if hasattr(self.e, "MEPModel") :
            connectors = self.e.MEPModel.ConnectorManager.Connectors
        elif hasattr(self.e, "ConnectorManager") :
            connectors = self.e.ConnectorManager.Connectors
        else :
            return 
        self._connectors = [c for c in connectors if c.Domain == Domain.DomainElectrical]
        return self._connectors

    connectors = property(_get_connectors) 


    def _get_conduit_connectors(self) :
        if hasattr(self.e, "MEPModel") :
            connectors = self.e.MEPModel.ConnectorManager.Connectors
        elif hasattr(self.e, "ConnectorManager") :
            connectors = self.e.ConnectorManager.Connectors
        else :
            return 
        connectors = [c for c in connectors if c.Domain == Domain.DomainCableTrayConduit]
        return connectors

    conduit_connectors = property(_get_conduit_connectors)


    def connector_names(self) :
        for c in self.connectors :
            print(c.Description)
    
    def __getitem__(self, item) :
        return self.connectors[item]

    def _get_space_name(self) :
        try :
            bp = BuiltInParameter.RBS_SYSTEM_NAME_PARAM
            ph = doc.GetElement(self.e.CreatedPhaseId)
            return self.e.Space[ph].LookupParameter("Имя").AsString()
        except :
            return ""

    space_name = property(_get_space_name)

    def _get_name(self) :
        try :
            # return self.e.Parameter[BuiltInParameter.RBS_SYSTEM_NAME_PARAM].AsString()
            return Element.Name.GetValue(self.e)
        except :
            raise
    name = property(_get_name)

    def _has_dpls(self) :
        try :
            for c in self.connectors :
                print(c.Description)
        except :
            return False

    def _get_circuits(self) :
        """
        ***************************************************************
        * Возвращает список цепей, которые подключены к панели
        * 
        * 
        ***************************************************************
        """
        try :
            c = [dmCircuit(e) for e in self.e.MEPModel.AssignedElectricalSystems]
            return c
        except :
            return 

    circuits = property(_get_circuits)

    def _get_mark(self) :
        """
        ***************************************************************
        * Возвращает марку оборудования из ADSK_Марка
        * 
        * 
        ***************************************************************
        """
        return self.get_parameter_value("ADSK_Марка")
    mark = property(_get_mark)

    def get_parameter_value(self, name) :
        p = self.e.LookupParameter(name)
        if not p :
            t = doc.GetElement(self.e.GetTypeId())
            p = t.LookupParameter(name)
        if not p : return 

        if p.HasValue :
            st = p.StorageType
            if st == StorageType.Integer :
                return p.AsInteger()
            elif st == StorageType.Double :
                return p.AsDouble()
            elif st == StorageType.String :
                return p.AsString()
            elif st == StorageType.ElementId :
                return p.AsElementId()

    def set_parameter(self, name, v) :
        p = self.e.LookupParameter(name) 
        if not p :
            t = doc.GetElement(self.e.GetTypeId())
            p = t.LookupParameter(name)
        if not p :
            return
        p.Set(v)
    def _set_parameter(self, name, v) :
        with dm.trans(doc) :
            self.set_parameter(name, v)

    
    def _get_cable_carrier_graph(self) :
        g = dmGraph()





        return g

    cable_carrier_graph = property(_get_cable_carrier_graph)
            

import System


class dmEquipment(object) :
    def __init__(self) :
        mc = ElementMulticategoryFilter(System.Array[bic]([
            bic.OST_FireAlarmDevices, 
            bic.OST_ElectricalEquipment, 
            bic.OST_CommunicationDevices, 
            bic.OST_SecurityDevices,
            bic.OST_NurseCallDevices,
            bic.OST_TelephoneDevices
        ]))
        fc = FilteredElementCollector(doc).WherePasses(mc).WhereElementIsNotElementType().ToElements()
        self._equpment = [dmDevice(e) for e in fc]
    def OfName(self, name) :
        self._equpment = [e for e in self._equpment if e.name == name]

    def __getitem__(self, item) :
        return self._equpment[item]

    def OfSpace(self, name) :
        if name == "" :
            return self._equpment
        self._equpment = [p for p in self._equpment if p.space_name == name]
        return self._equpment

class dmCircuit(dmDevice) :

    def _get_panel(self) :
        return dmDevice(self.e.BaseEquipment)

    panel = property(_get_panel)

    def set_wire_type(self, wire, reserve = 100, additional_len = 1000 * dut) :
        with dm.trans(doc) :
            self.set_parameter('Выбор проводника', wire.Id)
            self.set_parameter("Запас проводника_Электрические цепи",reserve )
            self.set_parameter("Запас на разделку проводника_Электрические цепи", additional_len)

    def _get_LoadName(self) :
        #Возвращает название нагрузки цепи

        try :
            return self.get_parameter_value("Имя нагрузки")
        except :
            return

    def __repr__(self) :
        # return "Устройство:\n{} : {}\n{} : {}".format(self.e.Category.Name)
        try :
            res =  "Цепь : {}\n{} : {}".format(self.e.Category.Name, Element.Name.GetValue(self.e), self.e.Id)
            res += "\nИмя нагрузки: {}".format(self.e.LoadName)
            res += "\nТип цепи: {}".format(self.e.SystemType)
            return res 
        except :
            return "none"

    

    def _set_LoadName(self, name) :
        #Устанавливает название нагрузки
        try :
            self.set_parameter("Имя нагрузки", name)
        except :
            return 
    load_name = property(_get_LoadName, _set_LoadName)

    def _get_elements(self) :
        return [dmDevice(e) for e in self.e.Elements]

    elements = property(_get_elements)

class dmCircuits(object) :
    def __init__(self) :
        mc = ElementMulticategoryFilter(System.Array[bic]([
            bic.OST_ElectricalCircuit, 
        ]))
        fc = FilteredElementCollector(doc).WherePasses(mc).WhereElementIsNotElementType().ToElements()
        self._circuits = [dmCircuit(e) for e in fc]
    def OfName(self, name) :
        self._equpment = [e for e in self._circuits if e.name == name]

    def __getitem__(self, item) :
        return self._circuits[item]




class dmPanels(object) :
    def __init__(self) :
        fc = FilteredElementCollector(doc).OfCategory(bic.OST_ElectricalEquipment).WhereElementIsNotElementType().ToElements()
        self.panels = [dmDevice(e) for e in fc]
    def __getitem__(self, item) :
        return self.panels[item]

    def OfSpace(self, name) :
        if name == "" :
            return self.panels
        self.panels = [p for p in self.panels if p.space_name == name]
        return self.panels

    def OfName(self, name) :
        pass

def connect_control_line(panel, element) :
    """
    ***************************************************************
    * Присоединение контрольной цепи к приемному прибору
    * 
    * 
    ***************************************************************
    """

    pass



def get_cable (name) : 
	tbls_c = FilteredElementCollector(doc).OfClass(ViewSchedule).ToElements()	
	tbls = {e.Name : e for e in tbls_c}
	
	tbl = tbls["В_СС_КТ_Электрические цепи_Справочник кабеля"]

	cables = {e.Name : e for e in FilteredElementCollector(doc, tbl.Id).ToElements()}
	cable = cables["КПСнг(А)-FRHF 2x2x0,75"]
	
	return cables[name]




class Function(object) :
    


    def find_panel(self) :
        self.panel = None
        self.circuit = None
        for c in dmCircuits() :
            print(20*"*")
            print(c)
            print(10*"-")
            print("Панель")
            print(c.panel)
            
            print(c.panel.name)
            try :
                if c.panel.name == "ARK.24" :
                    self.panel  = c.panel
                    self.circuit = c
            except :
                pass

    def execute(self) :
        self.find_panel()
        print(self.panel)
        g = self.panel.cable_carrier_graph
        print(g)
           
import random
    
class test_graph(object) :
    def __init__(self) :
        
        self.g = dmGraph()

    def add_vertexes(self) :
        print("Проверка графа")
        vs = []
        vs_ = [(200+i, i) for i in range(10) ]
        for v in vs_ :
            self.g.AddVertex(Id=v[0], pos = v[1])
        vs += vs_ 
        
        vs_ = [(200+i, i) for i in range(10) ]
        for v in vs_ :
            self.g.AddVertex(Id=v[0], pos = v[1])
        vs += vs_ 
        vs_ = [(200+i, (i+10,i,i)) for i in range(10) ]
        for v in vs_ :
            self.g.AddVertex(Id=v[0], pos = v[1])
        vs += vs_ 
        vs_ = [(200+i, (i+400,i,i)) for i in range(10) ]
        for v in vs_ :
            self.g.AddVertex(Id=v[0], pos = v[1])
        vs += vs_ 
        for v in self.g.V.V.keys() :
            v_val = self.g.V[v]
            print("{} : {}".format(v, v_val))

        for i in range(10) :
            v = random.choice(self.g.V)          
            print(v)

        print(50*"-")

        for i in range(10) :   
            v_ = random.choice(vs_)
            print("ищем вершину {} {} ".format(v_, type(v_)))     
            v = self.g.GetVertexByData(v_[0], v_[1])
            print(v)



    def add_edges(self) :
        es = [(1,2), (4,5), (10,2), (2,12), (40,1), (50, 50)]

        for e in es :
            try : 
                self.g.AddEdge(e)
            except :
                pass

        for e_ in self.g.E.E :
            e = self.g.E.E[e_]
            print(e)


        pass


    def execute(self) :
        self.add_vertexes()
        self.add_edges()
            

class test_graph_device(object) :
    def __init__(self) :
        self.g = dmGraph()
        cs = dmCircuits()

        for c in cs :
            if c.panel.name == "ARK.24" :
                self.c = c
                self.panel = c.panel

    def execute(self) :
        from itertools import combinations
        cn = []
        for c in self.panel.conduit_connectors :
            print(c)
            o = c.Origin
            n = (c.Owner.Id.IntegerValue, (o.X, o.Y, o.Z))
            v = self.g.AddVertex(Id=n[0], pos = n[1])
            cn.append(v)
            print(v)

        print(50*'-')

        for e in combinations(cn, 2) :
            self.g.AddEdge(e)

        for e in self.g.E.E : 
            print(e)

        