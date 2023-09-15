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


panels = dmPanels()
panels.OfSpace("Насосная пожаротушения")


def set_rs485_data() :


    equipments = dmEquipment()
    equipments.OfName("PU.1")
    equipments.OfSpace("Насосная пожаротушения")
    e1 = equipments[0]
    for e in equipments[:0] :
        print(e.name)

    cable1 = get_cable("КПСнг(А)-FRLS 2x2x0,75")

    es1 = ElementSet()

    print(50*"*")
    for c in e1.circuits :
        print(c.e.Name)
        # c1 = dmDevice(c)
        c1 = c
        nm = c1.get_parameter_value("Имя нагрузки")
        print(nm)
        if nm == "RS485-1" :
            num = 0
            with dm.trans(doc) :	
                c1.set_parameter("Выбор проводника",cable1.Id)
            for e2 in c.e.Elements :
                e3 = dmDevice(e2)
                print(e3)
                if e2.Category.Name != "Электрооборудование" :
                    es1.Insert(e2)
                else :
                    num += 1
                    with dm.trans(doc) :	
                        pn = e3.get_parameter_value("ADSK_Позиция")		
                        e3.set_parameter("ADSK_Имя устройства", pn)		
                        e3.set_parameter("ADSK_Имя панели", "1")	
                        e3.set_parameter("ADSK_Номер контроллера", str(num))
                        e3.set_parameter("Имя панели", "{}.{}".format(pn, num))
                        

def set_circuits() :
    circuits = dmCircuits()
    cable1 = get_cable("КПСнг(А)-FRLS 1x2x0,75")
    rs_cable = get_cable("КПСнг(А)-FRLS 2x2x0,75")

    power_cable = get_cable('ВВГнг-FRLS 3x1,5')


    for c in circuits :
        print(c.e.SystemType)
        print(c.name)

        p_name = c.panel.name
        try :
            c_num = int(c.name)
        except :
            pass

        with dm.trans(doc) :
            c.set_parameter("ADSK_Имя панели", p_name)
            c.set_parameter("ADSK_Номер линии", c_num)
        
        if c.e.SystemType == Electrical.ElectricalSystemType.FireAlarm :
        
            if c.e.LoadName.startswith("RS485") :
                c.set_wire_type(rs_cable)
                rs = c
            else :	
                c.set_wire_type(cable1)

                # Дальше действуем взависимости от типа устрйства
                panel_name = c.panel.name


            
        if c.e.SystemType == Electrical.ElectricalSystemType.PowerCircuit :
            if c.e.Voltage*dut_v < 50 :
                c.set_wire_type(cable1)
            else :
                pass 
                #c.set_wire_type(power_cable)
            p_source = c.panel.name

            
            with dm.trans(doc) :
                c.panel.set_parameter("Марка", p_source) 
                for e in c.elements :
                    e.set_parameter("ADSK_Имя источника питания", p_source)
                    e_pos = e.get_parameter_value("Марка")

                c.load_name = e_pos

            
            print(c.e.Voltage*dut_v)


def set_dpls(c) :
    p_source = c.panel.get_parameter_value("ADSK_Имя источника питания")
    if not p_source :
        p_source = "-"

    p_num = c.panel.get_parameter_value("ADSK_Имя панели") 
    if not p_num :
        p_num = "-"

    print(c.panel)
    print(p_num)

    cont_num = c.panel.get_parameter_value("ADSK_Номер контроллера")

    with dm.trans(doc) :
        num = 1 
        for e in c.elements :	
            try :	
                if p_source :
                    e.set_parameter("ADSK_Имя источника питания", p_source)
                
                e_name = e.get_parameter_value("ADSK_Имя устройства")
                if not e_name :
                    print("нет имении у устройтсва")
                    e_name = e.get_parameter_value("ADSK_Позиция")
                    e.set_parameter("ADSK_Имя устройства", e_name)
                e.set_parameter("ADSK_Имя панели", p_num)
                e.set_parameter("ADSK_Номер контроллера", cont_num)
                e_pos = "{}.{}.{}.{}".format(e_name,p_num, cont_num, num)
                e_num_adrs = e.get_parameter_value("ADSK_Количество занимаемых адресов")
                e.set_parameter("ADSK_Номер устройства", str(num))
                
                e.set_parameter("Марка", e_pos)
                if e.e.Category.Name == "Электрооборудование" :
                    e.set_parameter("Имя панели", e_pos)
                if e_num_adrs :
                    num += e_num_adrs
                else :
                    num += 1
            except Exception as ex:
                print(80*"-")
                print("ошибка при установке ДПЛС")
                print(p_source)
                print(e_name)
                print(e_pos)
                print(e_num_adrs)
                print(ex)
                print(80*"-")

        c.load_name = "ДПЛС"
	
	
def update_panel_names() :
    panels = dmPanels()
    for p in panels :
        try :
            p_name = p.get_parameter_value("Имя панели")
            p.set_parameter("Марка", p_name)
        except :
            print("Ошибка при установке панели")
            pass

def set_sp2(d) :
    # Устанавливаем параметры С2000-СП2 и подключенных к нему цепей
    # На входе - устройство d

    # Обработать все цепи которые подключены к устройству

    circuits = d.circuits

    for c in circuits :
        print(c.name)

def set_bs(e) :
    #Задаем параметры устройств в цепях блока сопряжения
    #
    cable1 = get_cable("КПСнг(А)-FRLS 1x2x0,75")
    circuits = e.circuits 
    print("Марка блока : {} -> Id {}".format(e.name, e.e.Id))
    if not circuits : return
    
    panel_num = e.get_parameter_value("ADSK_Имя панели")
    cont_num = e.get_parameter_value("ADSK_Номер контроллера")
    line_num = e.get_parameter_value("ADSK_Номер линии")
    
    for lnum, c in enumerate(circuits, 1) :
    
        e1_pos = "ИП 102-"
        
        c._set_parameter("Выбор проводника", cable1.Id)
        c._set_parameter("ADSK_Имя панели", e.name)
        c._set_parameter("ADKS_Номер линии", lnum)
        with dm.trans(doc) :
            c.load_name = e1_pos
        
        try :
        
            for e1_num, e1 in enumerate(c.elements, 1) :
                print("Оборудование в цепи БС {}".format(e1_num))
                e1_name = e1.get_parameter_value("ADSK_Имя устройства")
                
                e1_pos = "{}.{}.{}.{}.{}".format(e1_name,panel_num, cont_num, line_num,   e1_num)
                
                with dm.trans(doc) :
                    e1.set_parameter("Марка", e1_pos)
                    e1.set_parameter("ADSK_Имя панели",panel_num)
                    e1.set_parameter("ADSK_Номер контроллера", cont_num)
                    e1.set_parameter("ADSK_Номер линии", line_num)
                    e1.set_parameter("ADSK_Номер устройства", e1_num)
        except :
            raise
            pass
            
        print(e1_pos)
        with dm.trans(doc) :
            c.load_name = e1_pos	
