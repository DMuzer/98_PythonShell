#  coding: utf-8 
"""
***************************************************************
*** СОЗДАНИЕ СПРИНКЛЕРОВ В ПРОСТРАНСТВАХ
*** 
***************************************************************
* Убрано ограничение на то чтобы спринклер проецировался на 
* трубу, при необходимости добавляется дополнительный участок трубы
* чтобы подойти к точке подключения
***************************************************************
"""
dut = 0.0032808398950131233

view_name = 'DM_ОТМЕТКИ'
margin_rel = False
margin = 200 * dut



# from ossaudiodev import control_labels
from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math, sys
import clr
import System
from System.Collections.Generic import IList, List
from time import time as tt

clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
clr.AddReferenceToFileAndPath(r"C:\Program Files\Autodesk\Revit 2021\RevitAPIIFC.dll")
import NetTopologySuite as nts
import NetTopologySuite.Geometries as nts_geom
from Autodesk.Revit.DB import IFC as ifc

lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
    sys.path.append(lib_path)
    
import dm_connect_2 as dm
import dm_nearest_geometry as dm1

reload(dm)	
reload(dm1)
check_print=True


pi2 = math.pi * 2

dut = 0.0032808398950131233


    
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

print('Работаем d56_create_sprinklers.py')


app = dm.dmApp(doc)

cont_1 = None
pg1 = None 

def create_sprinklers(space) :
    """
    ***************************************************************
    * СОЗДАНИЕ СПРИНКЛЕРОВ ДЛЯ ПРОСТРАНСТВА
    * 
    * 
    ***************************************************************
    """


    ref_view = app.views['DM_ОТМЕТКИ']
    check_print= True

    """
    ***************************************************************
    * Подготовка фильтра для ReferenceIntersector
    * ReferenceIntersector будет использоваться для определения
    * отметок установки спринклеров
    ***************************************************************
    """


    mcf = ElementMulticategoryFilter(System.Array[BuiltInCategory](
                                [bic.OST_PipeCurves, bic.OST_PipeFitting,
                                    bic.OST_DuctCurves, bic.OST_DuctFitting,
                                    bic.OST_GenericModel,
                                ]), True)

    flt = FilteredElementCollector(doc).WherePasses(mcf)
    objs = flt.WhereElementIsNotElementType().ToElements()
    fref_targ = FindReferenceTarget.Element
    ref_int = ReferenceIntersector(mcf, fref_targ, ref_view)
    ref_int.FindReferencesInRevitLinks = True

    level = space.space.Level
    sprinkler_symb = doc.GetElement(space.sprinkler_type)

    start_level = level.Elevation+1000*dut

    global cont_1

    tt_find_contour_start = tt()
    cont_1 = space.get_free_ceiling_contour_by_intersection2(dist = 400 * dut, 
                                                thickness = 200 * dut,
                                                barrier_categories = 1,
                                                create_shape = True,
                                                )

    tt_find_contour_end = tt()
    tt_find_contour = tt_find_contour_end - tt_find_contour_end




    if check_print :
        print('**************************')
        print('2.0 Контрольная точка ----------')
        print('После создания кривых')
        print("Время выполнения поиска контуров {}".format(tt_find_contour))

    global pg1 

    pg1 = dm.get_PolygonFromCurveLoops(cont_1)
    # pg2 = pg1.Buffer(-500*dut)
    # pg3 = pg2.Buffer(1000*dut)
    # pg4 = pg3.Buffer(-500*dut)


    # curves_1 = dm.get_CurvesFromPolygon(pg1)
    # curves_2 = dm.get_CurvesFromPolygon(pg2)
    # curves_3 = dm.get_CurvesFromPolygon(pg3)
    # curves_4 = dm.get_CurvesFromPolygon(pg4)

    

    if check_print :
        print('**************************')
        print('2.1 Контрольная точка ----------')
        print('После создания кривых')

    

    curves_1 = dm.get_CurvesFromCurveLoops(cont_1)

    if check_print :
        print('**************************')
        print('3 Контрольная точка ----------')
        print('Проверка количества линий в curves_1')
        print('curves_1 : {} '.format(curves_1))

    

    global level 
    level =   space.space.Level
    lvl = space.space.Level.Elevation

    rot_angle = space.rot_angle
    max_step = 3000 * dut 
    solid = space.space_solid

    


    global spr_z

    

    spr_z = dm.dmSprinklerCalculations(pg1, 						
                        max_step=max_step,
                        rot_angle=rot_angle,
                        base_elevation = start_level,
                        spr_gap=150*dut,
                        ref_intersector=ref_int
                        )

    

    if check_print :
        print('**************************')
        print('4 Контрольная точка ----------')
        print('После расчета позиций спринклеров')


    s_pos = spr_z.CalculatePositions()

    


    if check_print :
        print('**************************')
        print('5  Контрольная точка ----------')
        print('После расчета позиций')
    spr_pos = spr_z.PositionsAsXYZ()

    if check_print :
        print('**************************')
        print('6 Контрольная точка ----------')
        print('После вычисления  отметок')

    
    spr_pnt = spr_z.PositionsAsPoint()




    if check_print :
        print('**************************')
        print('7 Контрольная точка ----------')
        print('До создания списка для directshape')


    coverings = []

    for p1 in spr_pos[:] :
        p1_ = nts_geom.Point(p1.X, p1.Y)
        cov_zone = dm.get_sprinkler_covering_area(pg1, p1_, 3000*2**0.5*dut/2)
        cov_zone_curves = dm.get_CurvesFromPolygon(cov_zone)
        coverings.extend(cov_zone_curves)



    solid_a = ([]
                    + curves_1 
                    # + curves_2 
                    # + curves_3 
                    # + curves_4
                    + spr_pnt

                    # + [Point.Create(p1)]
                    + coverings
                                                )
    dm.create_ds(solid_a)

    

    global spr_list 

    with dm.trans(doc) :
        pass
      
        for p in spr_pos :
            
            
            
            try :
                p2 = XYZ(p.X, p.Y, p.Z - level.Elevation)
                spr = doc.Create.NewFamilyInstance(p2, sprinkler_symb, level, nonstr)
                spr.Location.Point = p2

                spr_list.append((p,spr))
                
            except Exception as ex :
                print('Ошибка в функции при установке спринклера')
                print('\n{}\n{}'.format(ex, ex.clsException))
                print("p : {}".format(p))
        
        
                raise

        

    with dm.trans(doc):
        for pnt, spr in spr_list :
            
            
            
            try :
                spr.Location.Point = pnt 
                
            except Exception as ex :
                print('Ошибка в функции spr.Location.Point = pnt ')
                print('\n{}\n{}'.format(ex, ex.clsException))
        
        
                raise
            

#Глобальные переменные
pg1 = None 
spr_z = None
spr_list = []
level = None


t1 = tt()


for space in app.spaces.values() :

    if space.is_to_protect :
        # print(space.Name)

        if not space.is_protected :
            print(space.Name)
            print("Надо установить спринклеры")
            try :
                create_sprinklers(space=space)
            except Exception as ex:
                print('ошибка при установке')
                print(ex)
                pass
            space.is_protected = 1


t2 = tt()

print("Время выполнения {}".format(t2-t1))

