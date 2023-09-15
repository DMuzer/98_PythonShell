#  coding: utf-8

#import dm_connect_pipe

import dm_nearest_geometry as dm1
import dm_connect_2 as dm
from Autodesk.Revit.DB import IFC as ifc
import NetTopologySuite.Geometries as nts_geom
import NetTopologySuite as nts
import System
import math

from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math
import sys
import clr
import System
from System.Collections.Generic import IList, List
from dm_connect_pipe import get_nearest_end_connector

clr.AddReferenceToFileAndPath(
    r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
clr.AddReferenceToFileAndPath(
    r"C:\Program Files\Autodesk\Revit 2021\RevitAPIIFC.dll")

lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path:
    sys.path.append(lib_path)


reload(dm)
reload(dm1)
check_print = True

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

pi2 = math.pi * 2

dut = 0.0032808398950131233


bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType

print("d59_renumber_equipment")

# Выбираем упорядочиваем оборудование на виде

av = uidoc.ActiveView

# line_ref = uidoc.Selection.PickObject(OT.Element)
# line = doc.GetElement(line_ref)
line_id = ElementId(2802864)
line = doc.GetElement(line_id)


class dmLine(object):
    def __init__(self, line, num, owner = None):
        self.line = line
        self.doc = owner.doc 
        self.view = owner.view
        self.num = num

    def show_line_number(self, tr1 = None) :

        lc = self.line
        p3 = lc.Evaluate(0.5, True)
        text_type = self.doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)
        opts = TextNoteOptions(text_type)
        opts.HorizontalAlignment = HorizontalTextAlignment.Center
        opts.Rotation = 0

        trans = None
        if not tr1 :
            trans = Transaction(self.doc)
            trans.Start("renumber")

        txt = TextNote.Create(self.doc, self.view.Id, p3, 10 * dut, str(self.num), opts)
        if trans :
            trans.Commit()

    def find_connected(self, line_list) :
        if len(line_list) > 0 : 
            l2 = line_list.pop()
            

        


def get_elements_by_grouping(view, groupping):
    """
    ***************************************************************
    * Выбор всех видимых на виде элементов, имеющих соответсвующее
    * группирование
    * 
    ***************************************************************
    """
    doc = view.Document

    vis_filt = VisibleInViewFilter(doc, view.Id)

    cats = System.Array[bic]([bic.OST_NurseCallDevices,
                              bic.OST_FireAlarmDevices,
                              bic.OST_DataDevices,
                              bic.OST_ElectricalEquipment,
                              ])
    cat_flt = ElementMulticategoryFilter(cats)
    vis_elements = FilteredElementCollector(doc).WherePasses(
        vis_filt).WherePasses(cat_flt).ToElements()
    res = []
    for e in vis_elements:
        if e.LookupParameter("ADSK_Группирование").AsString() == groupping:
            res.append(e)

    return res


def get_lines_by_grouping(view, groupping, type_id):
    """
    ***************************************************************
    * Выбор всех линий на указанном виде с заданным значением
    * группирования
    * Выбираются все линии принадлежащие к любому из типоразмеров семейства
    ***************************************************************
    """
    doc = view.Document

    vis_filt = VisibleInViewFilter(doc, view.Id)

    l_type = doc.GetElement(type_id)
    l_family = l_type.Family
    symbols = l_family.GetFamilySymbolIds()

    flts = []
    for symb in symbols:
        flts.append(FamilyInstanceFilter(doc, symb))

    flt_fam = LogicalOrFilter(System.Array[ElementFilter](flts))

    cat_flt = ElementMulticategoryFilter(cats)
    vis_elements = FilteredElementCollector(doc).WherePasses(
        vis_filt).WherePasses(flt_fam).ToElements()
    res = []
    for e in vis_elements:
        if e.LookupParameter("ADSK_Группирование").AsString() == groupping:
            res.append(e)

    return res


def get_nearest_lines(line, line_list):
    """
    ***************************************************************
    * Вычисление и возврат линий, которые пересекают или
    * начинаются от линии line
    * возвращается упорядоченный список относительно точки начала линии
    ***************************************************************
    """

    res = []
    res1 = []
    max_dist = 2 * dut

    for l1 in line_list:
        t = clr.Reference[IList[ClosestPointsPairBetweenTwoCurves]](
            List[ClosestPointsPairBetweenTwoCurves]())
        try:
            line.ComputeClosestPoints(l1, True, True, False, t)
            dist = t.Item[0].Distance
        except Exception as ex:
            dist = max_dist
            # print(ex)

        if dist < max_dist:
            res.append((dist, l1))
        else:
            res1.append(l1)

    res = sorted(res, key=lambda x: x[0])
    return res, res1


def renumber_equipment(eq_list, start_num=1, trans=True):
    num = start_num

    if not trans:
        Trans = Transaction(doc)
        Trans.Start("Нумерация приборов")

    for e in eq_list:
        try:
            e.LookupParameter("ITV_LCS_Номер в шлейфе").Set(num)
            num += 1
        except Exception as ex:
            print(ex)

            pass

    if not trans:
        Trans.Commit()


class dmRenumberEqupmentByLine(object):
    """
    ***************************************************************
    * Класс команды для выполнения нумерации оборудования вдоль     
    * кабельных линий c одинаковым значением параметра ADSK_Группирование
    * нумерация будет рабоать и у оборудования и у линии с одинаковым значением
    * параметра
    ***************************************************************
    """
    
    def __init__(self, start_num=1, line_id=None, doc = None):
        """
        ***************************************************************
        * 
        * 
        * 
        ***************************************************************
        """
        if not doc :
            doc = uidoc.Document

        self.view = uidoc.ActiveView
        
        self.doc = doc 
        self.start_num = start_num
        if line_id :
            self.line = self.doc.GetElement(line_id)
            self.line_type_id = self.line.GetTypeId()
            self.grouping = self.line.LookupParameter("ADSK_Группирование").AsString()
        else :
            self.line = None 
            self.grouping = ""
            self.line_type_id = None 
        pass

        


        self.get_lines_by_grouping()
        self.get_equipment_by_grouping()

    def _show_line_num(self) :
        for num, l in enumerate(self.lines) :
            lc = l.Location.Curve
            line_obj = dmLine(lc, num, self)
            line_obj.show_line_number()


    def get_lines_by_grouping(self):
        """
        ***************************************************************
        * Выбор всех линий на указанном виде с заданным значением
        * группирования
        * Выбираются все линии принадлежащие к любому из типоразмеров семейства
        ***************************************************************
        """
        check_print = False
        try :
            doc = self.view.Document

            vis_filt = VisibleInViewFilter(self.doc, self.view.Id)

            l_type = doc.GetElement(self.line_type_id)
            l_family = l_type.Family
            symbols = l_family.GetFamilySymbolIds()

            flts = []
            for symb in symbols:
                symb_el = self.doc.GetElement(symb)
                if check_print :
                    print('**************************')
                    print('1 Контрольная точка ----------')
                    print('get_lines_by_groupping')
                    print('symb_el.Name : {} Ед изм.'.format(dm.en(symb_el)))

                flts.append(FamilyInstanceFilter(self.doc, symb))

            flt_fam = LogicalOrFilter(System.Array[ElementFilter](flts))

            vis_elements = FilteredElementCollector(doc).WherePasses(
                vis_filt).WherePasses(flt_fam).ToElements()
            res = []
            for e in vis_elements:
                if e.LookupParameter("ADSK_Группирование").AsString() == self.grouping:
                    if e.Id == self.line.Id : continue
                    res.append(e)
            self.lines  = [self.line] + res
            

        except Exception as ex :
                print('Ошибка в функции get_lines_by_grouping')
                print('\n{}\n{}'.format(ex, ex.clsException))    
                raise
        
        return self.lines

    def get_equipment_by_grouping(self) :
        """
        ***************************************************************
        * Метод выбирает оборудование, видимое на виде и которое относится
        * к заданное группировке
        * результат возвращается в виде списка.
        ***************************************************************
        """

        doc = self.view.Document

        vis_filt = VisibleInViewFilter(doc, self.view.Id)

        cats = System.Array[bic]([bic.OST_NurseCallDevices,
                                bic.OST_FireAlarmDevices,
                                bic.OST_DataDevices,
                                bic.OST_ElectricalEquipment,
                                ])
        cat_flt = ElementMulticategoryFilter(cats)
        vis_elements = FilteredElementCollector(doc).WherePasses(
            vis_filt).WherePasses(cat_flt).ToElements()
        res = []
        for e in vis_elements:
            if e.LookupParameter("ADSK_Группирование").AsString() == self.grouping:
                res.append(e)

        self.equipment = res 
        return res

    def sort_lines(self) :
        pass
        



if False : 
# region Выбор видимых линий
    """
    ***************************************************************
    * Выбор и упорядочивание элементов.
    * для начала соберем линии кабелей
    * 
    ***************************************************************
    """

    group_val = line.LookupParameter("ADSK_Группирование").AsString()
    lines = get_lines_by_grouping(av, group_val, line.GetTypeId())


# endregion
    """
    ***************************************************************
    * Выбор оборудования, которое видимо на виде, и которое нужно
    * будет пронумеровать
    * 
    ***************************************************************
    """
    equipment = get_elements_by_grouping(av, group_val)


# Нумерация оборудования




class dmRenumerator(object) :
    """
    ***************************************************************
    * Класс для выполнение нумерации оборудования по линиям
    * 
    * 
    ***************************************************************
    """
    def __init__(self, view, line_id= None, pnt = None) :
        self.view = view 
        self.line_id = line_id
        self.pnt = pnt 



class dmRenumeratorLines(object) :
    def __init__(self) :
        pass 


class dmRenumeratorLine(object) :
    """
    ***************************************************************
    * Класс для работы с линиями для упрощения топологической сортировки
    * 
    * 
    ***************************************************************
    """
    def __init__(self, element, enumerator) :
        self.line = element 
        self.enumerator = enumerator

    
class dmRenumeratorDevices(object) :
    def __init__(self) :
        pass 

class dmRenumeratorDevice(object) :
    def __init__(self, element, enumerator) :
        self.device = element
        self.enumerator = enumerator

print("Перенумерация")
view = uidoc.ActiveView
line_id = ElementId(-1)
pnt = XYZ(0,0,0)
command = dmRenumerator(view = view, line_id=line_id, pnt=pnt) 