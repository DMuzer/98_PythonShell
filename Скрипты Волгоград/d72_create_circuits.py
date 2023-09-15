#  coding: utf-8 

from os import P_NOWAIT
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

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

	
import dm_connect_2 as dm
import dm_nearest_geometry as dm1

reload(dm)	
reload(dm1)

print("create_circuits")
import re

class dmEndSwitch(object) :
    def __init__(self, e) :
        self.e = e

    def _get_connectors(self) :
        conns = self.e.MEPModel.ConnectorManager.Connectors
        return [c for c in conns if c.Domain == Domain.DomainElectrical]

    connectors = property(_get_connectors)


class dmEndSwitches(object) :
    def __init__(self, name) :
        fc = FilteredElementCollector(doc).OfCategory(bic.OST_FireAlarmDevices).WhereElementIsNotElementType().ToElements()
        self.switches = [dmEndSwitch(e) for e in fc if re.match(".*{}.*".format(name), Element.Name.GetValue(e))]

    


class dmDevice(object) :
    def __init__(self, e) :
        self.e = e

    def __repr__(self) :
        # return "Устройство:\n{} : {}\n{} : {}".format(self.e.Category.Name)
        return "Устройство : {}\n{} : {}".format(self.e.Category.Name, Element.Name.GetValue(self.e), self.e.Id)
    
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
            c = list(self.e.MEPModel.AssignedElectricalSystems)
            return c
        except :
            return 

    circuits = property(_get_circuits)

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


panels = dmPanels()
panels.OfSpace("Насосная пожаротушения")


def set_rs485_data() :
    sensors = dmEquipment()
    sensors.OfName("Датчик положения")

    s1 = sensors[0]
    c1 = s1.connectors[0]

    equipments = dmEquipment()
    equipments.OfName("PU.1")
    equipments.OfSpace("Насосная пожаротушения")
    e1 = equipments[0]
    for e in equipments[:0] :
        print(e.name)

    cable1 = get_cable("КПСнг(А)-FRLS 2x2x0,75")
    cable2 = get_cable("КПСнг(А)-FRLS 1x2x0,75")

    es1 = ElementSet()

    print(50*"*")
    for c in e1.circuits :
        print(c.Name)
        c1 = dmDevice(c)
        nm = c1.get_parameter_value("Имя нагрузки")
        print(nm)
        if nm == "RS485-1" :
            num = 0
            with dm.trans(doc) :	
                c1.set_parameter("Выбор проводника",cable2.Id)
            for e2 in c.Elements :
                e3 = dmDevice(e2)
                print(e3)
                if e2.Category.Name != "Электрооборудование" :
                    es1.Insert(e2)
                else :
                    num += 1
                    with dm.trans(doc) :	
                        pn = e3.get_parameter_value("ADSK_Позиция")		
                        e3.set_parameter("ADSK_Имя устройства", pn)			
                        e3.set_parameter("Имя панели", "{}.{}".format(pn, num))
                        
                


                        
                    
            with dm.trans(doc) :
                c.RemoveFromCircuit(es1)
        



        




