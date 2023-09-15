#  coding: utf-8 
"""
***************************************************************
*** СОЗДАНИЕ ВЕТКИ СПРИНКЛЕРОВ БЕЗ ОГРАНИЧЕНИЯ Н
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



from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math, sys
import clr
import System
from System.Collections.Generic import IList, List

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


pi2 = math.pi * 2

dut = 0.0032808398950131233


	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
OT = UI.Selection.ObjectType

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


mapp = dm.dmApp(doc)
view = mapp.views[view_name]

"""
# Заготовка для подключения
pipe1 = doc.GetElement(uidoc.Selection.PickObject(UI.Selection.ObjectType.Element).ElementId)
pipe2 = doc.GetElement(uidoc.Selection.PickObject(UI.Selection.ObjectType.Element).ElementId)

lc1 = pipe1.Location.Curve
lc2 = pipe2.Location.Curve

t = clr.Reference[IList[ClosestPointsPairBetweenTwoCurves]](List[ClosestPointsPairBetweenTwoCurves]())
    
lc1.ComputeClosestPoints(lc2, True, True, False, t)
pt1 = t.Item[0].XYZPointOnFirstCurve
pt2 = t.Item[0].XYZPointOnSecondCurve

lc3 = Line.CreateBound(pt1, pt2)
"""



print("Загрузился")

# spr_ref_list = uidoc.Selection.PickObjects(OT.Element)
# sprs = [doc.GetElement(ref) for ref in spr_ref_list]
# s = "[{}]".format(sprs_id_list)
# print(s)
sprs_id_list = [1758102, 1758103, 1758109, 1758259, 1758260]
sprs_id_list = [1758265]
sprs = [doc.GetElement(ElementId(eid)) for eid in sprs_id_list]

data = [
    {#0
        "pipe_id" : 5082135,
        "sprs_ids" : [5082117]
    },
    {#1
        "pipe_id" : 5074361,
        "sprs_ids" : [1758207, 1758102, 1758103, 1758109, 1758259, 1758260]
    },
    {#2
        "pipe_id" : 5074343,
        "sprs_ids" : [1758265]
    } ,
    {#3
        "pipe_id" :  5082288,
        "sprs_ids" : [5082323]
    },
        {#4
        "pipe_id" :  5070136,
        "sprs_ids" : [5082482]
    },
    
        {#5 Спринклер отклоняется от уровня трубы потребуется изменение положения перпендикуляра
        "pipe_id" :  5064490,
        "sprs_ids" : [5082517]
    },
        
    {#6 Спринклер примерно на отметке оси трубы, но при этом находится в проекции трубы
        "pipe_id" :  5070129,
        "sprs_ids" : [5082638]
    },
]

def set_pipe_size(pipe, d) :
    d_param = BuiltInParameter.RBS_PIPE_DIAMETER_PARAM
    try :
        pipe.Parameter[d_param].Set(d)
    except Autodesk.Revit.Exceptions.ModificationOutsideTransactionException :
        with dm.trans(pipe.Document) :
            pipe.Parameter[d_param].Set(d)

class dmConnectUtils(object) :
    def __init__(self, 
                        pipe_id, # Id трубы 
                        sprs_ids,  # массив Id спринклеров
                        end_cap = True, # если False то будет сформирован для последнего спринклера отвод
                        # если False то все спринклеры будут подключены как врезки
                        gap_d = 3, # Отступ от целевой трубы если нужно сделать отвод в диаметрахтруба
                        spr_pipe_d = None, # Задается размер трубы для спринклера, если None то размер автоматически будет выбран
                        spr_gap = 5, #Отступ от спринклера в диаметрах  коннектора спринклера
                        x_angle = 0, # угол осей построения по отношению к оси Х
                        ) :

        
        check_print = True

        if check_print :
            print('**************************')
            print('00 Контрольная точка ----------')
            print('dmConnectUtils.__init__() Точка входа')
        
        self.pipe_id = ElementId(pipe_id)
        self.pipe = doc.GetElement(self.pipe_id)
        self.sprs_ids =[ElementId(eid) for eid in  sprs_ids]
        self.sprinklers = [doc.GetElement(eid) for eid in self.sprs_ids]
        self.end_cap = end_cap
        self.diam = self.pipe.Diameter


        """
        ***************************************************************
        * Диаметр патрубка для подключения спринклера, если задается
        * то принимается диаметр тот, который задается, если не задан,
        * то устанавливается автоматически
        ***************************************************************
        """

        if spr_pipe_d :
            self.spr_pipe_d = spr_pipe_d 
        else :
            self.spr_pipe_d = 25 * dut

        self.gap_d = gap_d 
        self.gap = self.gap_d * self.diam 
        self.spr_gap = spr_gap
        self.x_angle = x_angle

        if check_print :
            print('**************************')
            print('0 Контрольная точка ----------')
            print('dmConnectUtils.__init__() до _calc_new_pipe_diameter')

        self._calc_new_pipe_diameter()

        

        if check_print :
            print('**************************')
            print('1 Контрольная точка ----------')
            print('dmConnectUtils.__init__ ')
            print('self.new_pipe_diameter : {} мм'.format(self.new_pipe_diameter/dut))

    def _calc_new_pipe_diameter(self) :
        """
        ***************************************************************
        * Вычисление диаметра создаваемой трубы в зависимости от
        * количества подключаемых оросителей
        * 
        ***************************************************************
        """
        pipe_diameters = {
                20 : 0,
                25 : 2,
                32 : 3,
                40 : 5,
                50 : 10,
                65 : 20,
                80 : 36,
                100 : 75, 
                125 : 140,
                150 : 800
            } 
        check_print = True
        spr_num = len(self.sprinklers)

        if check_print :
            print('**************************')
            print('1 Контрольная точка ----------')
            print('dmConnectUtils._calc_new_pipe_diameter')
            print('pipe_diameters : {} '.format(sorted(pipe_diameters.keys())))
            print('spr_num : {} '.format(spr_num))
            

        
        for k in sorted(pipe_diameters.keys()) :
            if check_print :
                print('**************************')
                print('2 Контрольная точка ----------')
                print('_calc_new_pipe_diameter')
                print('k : {} Ед изм.'.format(k))
            if pipe_diameters[k] > spr_num :
                self.new_pipe_diameter = k * dut
                return

        

    def Calculate(self) :
        print("Начало рассчета")
        pipe = self.pipe

        pipe_dir = pipe.Location.Curve.Direction

        """
        Необходимо оценить как располагается труба.
        И разделить решение на 3 случая, если труба горизонтальна
        труба вертикальна
        труба наклонна
        """

        if abs(pipe_dir.Z) > 0.95 :
            route = self._calc_vertical()
        elif abs(pipe_dir.Z) < 0.05 :
            route = self._calc_horizontal()
        else :
            route = self._calc_sloping()

        

        if self.end_cap :
            f_line = route[0]
            p1 = f_line.GetEndPoint(0)
            p2 = f_line.GetEndPoint(1)
            p1_ = p1 - f_line.Direction * 3 * self.new_pipe_diameter
            f_line_ = Line.CreateBound(p1_, p2)
            route = [f_line_] + route[1:]

        self.route = route
        return route

    def _get_pipe_connection_line(self) :
        """
        Вычисляет линию на трубе внутри которой можно сделать подключение ветки
        возвращает Line
        """
        lc = self.pipe.Location.Curve
        p1 = lc.GetEndPoint(0)
        p2 = lc.GetEndPoint(1)
        l = lc.Length

        if l > 2 * self.gap :
            gap = self.gap
        else :
            gap = l / 2 * 0.95
            

        p1 = p1 + gap * lc.Direction
        p2 = p2 - gap * lc.Direction
        res = Line.CreateBound(p1, p2)
        return res

    def _calc_horizontal(self) : 
        """
        ***************************************************************
        * РАССЧЕТ ТРАССЫ В СЛУЧАЕ ГОРИЗОНТАЛЬНОЙ ТРУБЫ
        * 
        * 
        ***************************************************************
        """
        check_print = False
        pipe = self.pipe 
         

        if check_print :
            print('*** Горизонтальная труба ***********************')
            print('1 Контрольная точка ----------')
            
        lc0 = pipe.Location.Curve

        lc2 = self._get_pipe_connection_line()

        sprs = self.sprinklers
        # Отсортировать спринклеры по расстоянию от трубы
        sprs = sorted(sprs, key = lambda x : lc2.Distance(x.Location.Point))
        self.sprinklers = sprs

        work_spr = sprs[-1]
        con1 = list(work_spr.MEPModel.ConnectorManager.Connectors)[0]

        if check_print :
            print('**************************')
            print('2 Контрольная точка ----------')
        
        """
        ******************************************************************
        * ВЫЧИСЛЕНИЕ ТОЧКИ ОТ КОТОРОЙ ВЫЧИСЛЯЕТСЯ ТРАССА ТРУБОПРОВОДА
        * Точка вычисляется от спринклера. Подключить к спринклеру нельзя, 
        * поэтому необходимо отсупить. Отступ считаем относительно диаметра 
        * соединителя. 
        * p0 - это точка на трубе к которой рассчитываем линию
        * d1 - вектор направления соединителя спринклера
        * p1 = это точка от которой начинаем считать трассу
        *****************************************************************
        """
        d1 = con1.CoordinateSystem.BasisZ
        r1 = con1.Radius 
        p1 = con1.Origin + d1 * r1 * self.spr_gap
        p0 = lc2.Project(p1).XYZPoint 

        """
        ***************************************************************
        * v1 - Линия которая идет от спринклера к точке присоединения к трубе
        * v - Вектор, построенный на концах линии v1
        *
        ***************************************************************
        """

        v1 = Line.CreateBound(p1, p0)
        v = p0 - p1

        """
        ***************************************************************
        * pd1 - Вектор направления трубы в горизонтальной плоскости
        * pd2 - Вектор вертикально вверх
        * Далее будем раскладывать прямое направление, которое выражается
        * вектором v на составляющие по базису, связанному с направлением трубы
        * v11 - Вектор вдоль направления трубы -  будет иметь длину если 
        *            проекция спринклера выходит за пределы трубы,
        *            если спринклер внутри, то будет равен 0
        * v12 - Вектор, вертикальный это опуск или подъем до осевой линиии трубы
        * v13 - Вектор, по направлению перпендикулярно трубе
        ***************************************************************
        """
        
        pd1 = XYZ(lc2.Direction.X, lc2.Direction.Y, 0) 
        pd2 = XYZ.BasisZ

        v11 = pd1 * pd1.DotProduct(v)
        v12 = pd2 * pd2.DotProduct(v)
        v13 = v -  v11 - v12 

        """
        ***************************************************************
        * Далее необходимо сделать уточнения, которые касаются минимальной длины труб
        * и взаимного расположения
        * Первый случай самый простой - если все линии достаточно большие, то ничего менять не 
        * нужно
        * Второй случай:
        *   когда вертикальная составляющая меньше 2 диаметров целевой трубы, но больше радиуса.
        *   в этом случае необходимо укоротить перпендикуляр и добавить еще один наклонный сегмент
        * Третий случай:
        *   когда вертикальная составляющая меньше радиуса трубы, 
        *   Тут есть проблема, что может получиться так, что отвот слишком маленьким углом и ревит
        *   при создании отвода выдаст ошибку. Поэтому чтобы ее избежать лучше трубу немного поднять 
        *   или опусить в зависимости от направления вектора соединителя спринклера. Так как двигать в сторону
        *   спринклера нельзя, т.к. можно наткнуться на проблему либо маленькой трубы, либо недостаток места
        *   для переходов и отводов. 
        *
        ***************************************************************
        """

        p11 = p1 + v13
        p12 = p11 + v11
        p13 = p12 + v12

        

        if (v12.GetLength() < 2 * self.diam) and (v12.GetLength() > 0.5 * self.diam) :
            # случай, если вертикальная составляющая маленькая, значит
            # спринклер находится на уровне центра трубы.

            p11 = p11 - 2 * self.diam * v13.Normalize()
            p12 = p11 + v11
            p13 = p12 + v12

        elif v12.GetLength() < 0.5 * self.diam  and v12.GetLength() > 0:

            if check_print :
                print('**************************')
                print('6 Контрольная точка ----------')
                print('Малая длина вертикального участка')


            """
            ***************************************************************
            * Необходимо выяснить на какую длину и в каком направлении надо
            * изменить отметку трубы, так как двигать ее нужно от точки p1,
            * соответственно необходимо определить новое положение точки p1
            * которое должно быть вдоль вектора нормали соединителя
            * соответственно решить вопрос можно двумя способами:
            * первый возможен если до оси расстояние от спринклера надо увеличивать
            * то увеличиваем расстояние от спринклера так чтобы трубы были в одной плоскости
            * второй случай, надо отодвинуть трубу от спринклера  на достаточное для расположение
            * отводов расстояние
            * d1 - направление коннектора спринклера
            ***************************************************************
            """
            add_direction = v12.DotProduct(d1)

            if add_direction > 0 :
                """
                ***************************************************************
                * Случай когда трубу надо поднять по направлению соединителя спринклера
                * Соответственно вычисляем длину вектора на которую надо сместить точку p1
                * 3 строка
                ***************************************************************
                """
           
                dlz = v12.GetLength() / XYZ.BasisZ.DotProduct(d1)
                p1 = p1 + d1 * dlz




                if check_print :
                    print('**************************')
                    print('7 Контрольная точка ----------')
                    print('Длина вертикального отрезка')
                    print('add_direction : {} мм'.format(add_direction/dut))
                if check_print :
                    print('**************************')
                    print('7 Контрольная точка ----------')
                    print('Длина вектора на который сместить точку')
                    print('dlz : {} мм'.format(dlz/dut))




            else :
                """
                ***************************************************************
                * Случай, когда ось целевой трубы слишком близко к с принклеру и
                * в сторону спринклера трубу не отодвинуть
                * В этом случае отодвигаем трубу от спринклера еще больше, чтобы
                * не возникло ошибки при создании отвода.
                ***************************************************************
                """
                dlz = v12.GetLength() / abs(XYZ.BasisZ.DotProduct(d1))
                p1 = p1 + d1 * (dlz + self.diam)

            
            """
            ***************************************************************
            * Поскольку сместилась стартовая точка,
            * необходимо пересчитать другие векторы
            * Кроме того, если есть составляющая вдоль трубы, тогда надо 
            * укоротить перпендикулярный отрезок, чтобы труба ветки не шла по 
            * трубе в которую врезаем
            ***************************************************************
            """

            v = p0 - p1

            v11 = pd1 * pd1.DotProduct(v)
            v12 = pd2 * pd2.DotProduct(v)
            v13 = v -  v11 - v12 

            p11 = p1 + (v13.GetLength() - self.diam) * v13.Normalize()
            p12 = p11 + v11
            p13 = p12 + v12

        """
        ***************************************************************
        * Далее вычисляем непосредственно линии
        * ln1 - линия перпендикулярная трубе
        * ln2 - линия параллельная трубе
        * ln3 - линия вертикальная
        ***************************************************************
        """     

        route = []

        if  v11.GetLength() == 0   and v12.GetLength() == 0:
            ln1 = Line.CreateBound(p1, p0)
            route.append(ln1)
        
        else :
            if p1.DistanceTo(p11) > self.diam :
                ln1 = Line.CreateBound(p1, p11)
                route.append(ln1)
            if p11.DistanceTo(p12) > self.diam :
                ln2 = Line.CreateBound(p11, p12)  
                route.append(ln2)  
            if p12.DistanceTo(p0) > self.diam : 
                ln3 = Line.CreateBound(p12, p0)
                route.append(ln3)
        
        if check_print :
            geoms = [
                p0
                ] + route
            geoms_ = []
            for g in geoms :
                if type(g) == XYZ :
                    g_ = Point.Create(g)
                    geoms_.append(g_)
                else :
                    geoms_.append(g)
                
            shape = System.Array[GeometryObject](geoms_)

            with dm.trans(doc) :
                ds = DirectShape.CreateElement(doc, ElementId(bic.OST_GenericModel))
                ds.SetShape(shape)

        return route 

    def _calc_sloping(self) :

        """
        ***************************************************************
        * РАССЧЕТ ТРАССЫ В СЛУЧАЕ НАКЛОННОЙ ТРУБЫ
        * 
        * 
        ***************************************************************
        """

        """
        ***************************************************************
        * Необходимо вычислить целевую точку подключения к трубе
        * Для этого вычисляем линию с возможным подключением
        * 
        ***************************************************************
        """

        check_print = False
        pipe = self.pipe 
         

        if check_print :
            print('*** Наклонная труба ***********************')
            print('1 Контрольная точка _calc_sloping ----------')
            
        lc = pipe.Location.Curve

        lc2 = self._get_pipe_connection_line()

        sprs = self.sprinklers
        # Отсортировать спринклеры по расстоянию от трубы
        sprs = sorted(sprs, key = lambda x : lc2.Distance(x.Location.Point))
        self.sprinklers = sprs
        
        work_spr = sprs[-1]
    
        con1 = list(work_spr.MEPModel.ConnectorManager.Connectors)[0]

        d1 = con1.CoordinateSystem.BasisZ
        r1 = con1.Radius
        p1 = con1.Origin + d1 * r1 * self.spr_gap

        if check_print :
            print('**************************')
            print('2 Контрольная точка ----------')

        """
        ***************************************************************
        * ВЫЧИСЛЕНИЕ ТОЧКИ ОТ КОТОРОЙ ВЫЧИСЛЯЕТСЯ ТРАССА ТРУБОПРОВОДА
        * И К КОТОРОЙ ДОЛЖНА ПРИДТИ ТРАССА ТРУБОПРОВОДА
        * Поскольку труба наклонная, будем подходить к ней
        * вдоль направления проекции трубы на  горизонтальную плоскость
        ***************************************************************
        """

        lс2 = self._get_pipe_connection_line()
        p0 = lc2.Project(p1).XYZPoint

        """
        ***************************************************************
        * v1 - Линия которая идет от спринклера к точке присоединения к трубе
        * v - Вектор, построенный на концах линии v1
        *
        ***************************************************************
        """

        v1 = Line.CreateBound(p1, p0)
        v = p0 - p1

        """
        ***************************************************************
        * pd1 - Вектор направления трубы в горизонтальной плоскости
        * pd2 - Вектор вертикально вверх
        * Далее будем раскладывать прямое направление, которое выражается
        * вектором v на составляющие по базису, связанному с направлением трубы
        * v11 - Вектор вдоль направления трубы -  будет иметь длину если 
        *            проекция спринклера выходит за пределы трубы,
        *            если спринклер внутри, то будет равен 0
        * v12 - Вектор, вертикальный это опуск или подъем до осевой линиии трубы
        * v13 - Вектор, по направлению перпендикулярно трубе
        ***************************************************************
        """
        
        pd1 = XYZ(lc2.Direction.X, lc2.Direction.Y, 0) 
        pd2 = XYZ.BasisZ



        v11 = pd1 * pd1.DotProduct(v)
        v12 = pd2 * pd2.DotProduct(v)
        v13 = v -  v11 - v12 

        pd3 = XYZ(pd1.Y, -pd1.X, 0)
        if pd3.DotProduct(v) < 0 :
            pd3 = -pd3

        p15 = p0 - pd3 * self.gap

        v = p15-p1

        v11 = pd1 * pd1.DotProduct(v)
        v12 = pd2 * pd2.DotProduct(v)
        v13 = v -  v11 - v12 
        v13 = pd3 * pd3.DotProduct(v)

        

        """
        ***************************************************************
        * Далее необходимо сделать уточнения, которые касаются минимальной длины труб
        * и взаимного расположения
        * Первый случай самый простой - если все линии достаточно большие, то ничего менять не 
        * нужно
        * Второй случай:
        *   когда вертикальная составляющая меньше 2 диаметров целевой трубы, но больше радиуса.
        *   в этом случае необходимо укоротить перпендикуляр и добавить еще один наклонный сегмент
        * Третий случай:
        *   когда вертикальная составляющая меньше радиуса трубы, 
        *   Тут есть проблема, что может получиться так, что отвот слишком маленьким углом и ревит
        *   при создании отвода выдаст ошибку. Поэтому чтобы ее избежать лучше трубу немного поднять 
        *   или опусить в зависимости от направления вектора соединителя спринклера. Так как двигать в сторону
        *   спринклера нельзя, т.к. можно наткнуться на проблему либо маленькой трубы, либо недостаток места
        *   для переходов и отводов. 
        *
        ***************************************************************
        """

        p11 = p1 + v13
        p12 = p11 + v11
        p13 = p12 + v12

        

        if (v12.GetLength() < 2 * self.diam) and (v12.GetLength() > 0.5 * self.diam) :
            # случай, если вертикальная составляющая маленькая, значит
            # спринклер находится на уровне центра трубы.

            p11 = p11 - 2 * self.diam * v13.Normalize()
            p12 = p11 + v11
            p13 = p12 + v12

        elif v12.GetLength() < 0.5 * self.diam  and v12.GetLength() > 0:

            if check_print :
                print('**************************')
                print('6 Контрольная точка ----------')
                print('Малая длина вертикального участка')


            """
            ***************************************************************
            * Необходимо выяснить на какую длину и в каком направлении надо
            * изменить отметку трубы, так как двигать ее нужно от точки p1,
            * соответственно необходимо определить новое положение точки p1
            * которое должно быть вдоль вектора нормали соединителя
            * соответственно решить вопрос можно двумя способами:
            * первый возможен если до оси расстояние от спринклера надо увеличивать
            * то увеличиваем расстояние от спринклера так чтобы трубы были в одной плоскости
            * второй случай, надо отодвинуть трубу от спринклера  на достаточное для расположение
            * отводов расстояние
            * d1 - направление коннектора спринклера
            ***************************************************************
            """
            add_direction = v12.DotProduct(d1)

            if add_direction > 0 :
                """
                ***************************************************************
                * Случай когда трубу надо поднять по направлению соединителя спринклера
                * Соответственно вычисляем длину вектора на которую надо сместить точку p1
                * 3 строка
                ***************************************************************
                """
           
                dlz = v12.GetLength() / XYZ.BasisZ.DotProduct(d1)
                p1 = p1 + d1 * dlz




                if check_print :
                    print('**************************')
                    print('7 Контрольная точка ----------')
                    print('Длина вертикального отрезка')
                    print('add_direction : {} мм'.format(add_direction/dut))
                if check_print :
                    print('**************************')
                    print('7 Контрольная точка ----------')
                    print('Длина вектора на который сместить точку')
                    print('dlz : {} мм'.format(dlz/dut))




            else :
                """
                ***************************************************************
                * Случай, когда ось целевой трубы слишком близко к с принклеру и
                * в сторону спринклера трубу не отодвинуть
                * В этом случае отодвигаем трубу от спринклера еще больше, чтобы
                * не возникло ошибки при создании отвода.
                ***************************************************************
                """
                dlz = v12.GetLength() / abs(XYZ.BasisZ.DotProduct(d1))
                p1 = p1 + d1 * (dlz + self.diam)

            
            """
            ***************************************************************
            * Поскольку сместилась стартовая точка,
            * необходимо пересчитать другие векторы
            * Кроме того, если есть составляющая вдоль трубы, тогда надо 
            * укоротить перпендикулярный отрезок, чтобы труба ветки не шла по 
            * трубе в которую врезаем
            ***************************************************************
            """

            v = p0 - p1

            v11 = pd1 * pd1.DotProduct(v)
            v12 = pd2 * pd2.DotProduct(v)
            v13 = v -  v11 - v12 

            p11 = p1 + (v13.GetLength() - self.diam) * v13.Normalize()
            p12 = p11 + v11
            p13 = p12 + v12

        """
        ***************************************************************
        * Далее вычисляем непосредственно линии
        * ln1 - линия перпендикулярная трубе
        * ln2 - линия параллельная трубе
        * ln3 - линия вертикальная
        ***************************************************************
        """     

        route = []

        if  v11.GetLength() == 0   and v12.GetLength() == 0:
            ln1 = Line.CreateBound(p0, p1)
            route.append(ln1)

        
        else :
            if p1.DistanceTo(p11) > self.diam :
                ln1 = Line.CreateBound(p1, p11)
                route.append(ln1)
            if p11.DistanceTo(p12) > self.diam :
                ln2 = Line.CreateBound(p11, p12)  
                route.append(ln2)  
            if p12.DistanceTo(p0) > self.diam : 
                ln3 = Line.CreateBound(p12, p15)
                route.append(ln3)
            ln5 = Line.CreateBound(p15, p0)
            route.append(ln5)
            
        
        if check_print :
            geoms = [
                p0, v1, p15
                ] + route
            geoms_ = []
            for g in geoms :
                if type(g) == XYZ :
                    g_ = Point.Create(g)
                    geoms_.append(g_)
                else :
                    geoms_.append(g)
                
            shape = System.Array[GeometryObject](geoms_)

            with dm.trans(doc) :
                ds = DirectShape.CreateElement(doc, ElementId(bic.OST_GenericModel))
                ds.SetShape(shape)

    
        return route 



    def _calc_vertical(self) :
        """
        ***************************************************************
        * РАССЧЕТ ТРАССЫ В СЛУЧАЕ ВЕРТИКАЛЬНОЙ ТРУБЫ
        * 2 строка
        * 3 строка
        ***************************************************************
        """
        print("Вертикальная труба")

        """
        ***************************************************************
        * Необходимо вычислить целевую точку подключения к трубе
        * Для этого вычисляем линию с возможным подключением
        * 3 строка
        ***************************************************************
        """

        check_print = False
        pipe = self.pipe 
         

        if check_print :
            print('*** Вертикальная труба ***********************')
            print('1 Контрольная точка _calc_vertical ----------')
            
        lc = pipe.Location.Curve

        lc2 = self._get_pipe_connection_line()

        sprs = self.sprinklers
        # Отсортировать спринклеры по расстоянию от трубы
        sprs = sorted(sprs, key = lambda x : lc2.Distance(x.Location.Point))
        self.sprinklers = sprs
        
        work_spr = sprs[-1]
    
        con1 = list(work_spr.MEPModel.ConnectorManager.Connectors)[0]

        d1 = con1.CoordinateSystem.BasisZ
        r1 = con1.Radius
        p1 = con1.Origin + d1 * r1 * self.spr_gap

        if check_print :
            print('**************************')
            print('2 Контрольная точка ----------')

        XBasis = Transform.CreateRotation(XYZ.BasisZ, self.x_angle).OfVector(XYZ.BasisX)


        """
        ***************************************************************
        * ВЫЧИСЛЕНИЕ ТОЧКИ ОТ КОТОРОЙ ВЫЧИСЛЯЕТСЯ ТРАССА ТРУБОПРОВОДА
        * И К КОТОРОЙ ДОЛЖНА ПРИДТИ ТРАССА ТРУБОПРОВОДА
        * Поскольку труба вертикальная, будем подходить к ней
        * вдоль осей, это плохо в случае, если оси не соответствуют
        * направлению осей
        * lc2 - отрезок, к которому можно подключать, он несколько короче целевой трубы
        *   т.к. нельзя делать врезки близко к торцам трубы
        ***************************************************************
        """

        lс2 = self._get_pipe_connection_line()
        p0 = lc2.Project(p1).XYZPoint


        
        ve = (p0 - p1).Normalize()
        ve0 = XYZ(ve.X, ve.Y, 0).Normalize()

        if abs(ve.Z) > 0.00001 :
            p13 = p0 - ve0 * self.gap
        else :
            p13 = p0 

        if check_print :
            print('**************************')
            print('2 Контрольная точка ----------')
            print('Отметки Z для точек p13 и p0')
            print('p13.Z : {} p0.Z {}'.format(p13.Z, p0.Z))
            print("ve {} {} {}".format(ve.X, ve.Y, ve.Z))

        """
        ***************************************************************
        * ПОЛУЧИЛИ ТОЧКУ p13 это точка от которой придет патрубок и кэтой
        * точке надо подвести трубу
        * 3 строка
        ***************************************************************
        """

        """
        ***************************************************************
        * Теперь необходимо разложить направление на 3 составляющих
        * по осям базиса
        * v - вектор направленный от точки p1 (от спринклера)
        *       к точке p13 - точка подключения на вертикальном участке
        ***************************************************************
        """
        v = p13 - p1

        vx = XBasis * XBasis.DotProduct(v)
        vz = XYZ.BasisZ * XYZ.BasisZ.DotProduct(v) 
        vy = v - vx - vz 

        p11 = p1 + vx 
        p12 = p11 + vy 
        p13_ = p12 + vz 

        route = []

        if vx.GetLength() > r1 :
            ln1 = Line.CreateBound(p1, p11)
            route.append(ln1)

        if vy.GetLength() > r1 :
            ln2 = Line.CreateBound(p11, p12)
            route.append(ln2)
        if vz.GetLength() > r1 :
            ln3 = Line.CreateBound(p12, p13_)
            route.append(ln3)

        if p0.DistanceTo(p13_) > 0.0001 :
            ln4 = Line.CreateBound(p13_, p0)
            route.append(ln4)
       
        ln_c0 = Line.CreateBound(p1, p13)

        if check_print :
            geoms = [p0, p13, p1, lc2, ln_c0]

            geoms_ = []
            geoms = geoms + route
            for g in geoms :
                if type(g) == XYZ :
                    g_ = Point.Create(g)
                    geoms_.append(g_)
                else :
                    geoms_.append(g)
            
            print(geoms_)
            shape_a = System.Array[GeometryObject](geoms_)
            with dm.trans(doc) :
                ds = DirectShape.CreateElement(doc, ElementId(bic.OST_GenericModel))
                ds = ds.SetShape(shape_a) 

        return route

    def CreatePipesFromRoute(self) :
        assert hasattr(self, "route")

        with dm.trans(doc) :
            new_pipes= []
            for l in self.route :
                new_pipe_id = ElementTransformUtils.CopyElement(doc, self.pipe.Id, XYZ(0,0,0))[0]
                new_pipe = doc.GetElement(new_pipe_id)
                new_pipe.Location.Curve = l
                set_pipe_size(new_pipe, self.new_pipe_diameter)
                new_pipes.append(new_pipe)

            if len(new_pipes) > 1 :
                for pipe1, pipe2 in zip(new_pipes[:-1], new_pipes[1:]) :
                    pnt1 = pipe1.Location.Curve.GetEndPoint(1)
                    c1 = dm.get_nearest_end_connector(pipe1, pnt1)
                    c2 = dm.get_nearest_end_connector(pipe2, pnt1)
                    doc.Create.NewElbowFitting(c1, c2)

            pipe1 = new_pipes[-1]
            p1 = pipe1.Location.Curve.GetEndPoint(1)
            c1 = dm.get_nearest_end_connector(pipe1, p1)
            doc.Create.NewTakeoffFitting(c1, self.pipe)

        self.new_pipes = new_pipes

    def _connect_sprinkler(self, pipe, spr) :
        """
        ***************************************************************
        * ПОДКЛЮЧЕНИЕ ЗАДАННОГО СПРИНКЛЕРА К ЗАДАННОЙ ТРУБЕ
        * 
        * 
        ***************************************************************
        """

        """
        ***************************************************************
        * Вычисляем основные параметры относительного расположения и точки
        * подключения спринклера в трубу
        * 
        ***************************************************************
        """
        d_param = BuiltInParameter.RBS_PIPE_DIAMETER_PARAM
        check_print = True

        if check_print :
            print('**************************')
            print('1 _connect_sprinkler  Контрольная точка ----------')
            print('Начало функции')

        lc = pipe.Location.Curve
        pipe_dir = lc.Direction
        spr_con = list(spr.MEPModel.ConnectorManager.Connectors)[0]
        p1 = spr_con.Origin
        r1 = spr_con.Radius
        p2 = lc.Project(p1).XYZPoint
        d1 = spr_con.CoordinateSystem.BasisZ

        

        v = p2-p1

        

        ve = (p2-p1).Normalize()

        lc2 = Line.CreateBound(p1, p2)


    
        """
        ***************************************************************
        * Определяем расстояние которое окажется между осью трубы и
        * осью спринклера чтобы сделать вывод, можно ли подключать
        * спринкле напрямую
        * lc - линия целевой трубы
        * lc3 - это линия построенная по направлению коннектора спринклера
        * при этом надо чтобы линии не вычислялись с продолжением
        ***************************************************************
        """
        lc3 = Line.CreateBound(p1, p1 + d1 * 1000)
    
        spr_gap_min = r1 * 5
        pipe_elbow_gap = (self.spr_pipe_d + self.pipe.Diameter) * 0.6
        t = clr.Reference[IList[ClosestPointsPairBetweenTwoCurves]](List[ClosestPointsPairBetweenTwoCurves]())

        lc.ComputeClosestPoints(lc3, True, True, False, t)
        dist = t.Item[0].Distance

        closest_pnt_axe  = t.Item[0].XYZPointOnSecondCurve
        closest_pnt_pipe = t.Item[0].XYZPointOnFirstCurve

        lc2_ = Line.CreateBound(p1, closest_pnt_axe)

        ax_pipe_project = d1.DotProduct(pipe_dir) #Проекция оси спринклера на ось трубы.

        v1 = closest_pnt_axe - p1 
        v2 = closest_pnt_pipe - closest_pnt_axe

        if check_print :
            print('**************************')
            print('3 Контрольная точка ----------')
            print('Расстояние между осями')
            print('dist : {} self.spr_gap : {}'.format(dist/dut, spr_gap_min/dut))
            print('Проекция вектора направления коннектора на направление трубы')
            print("{}".format(ax_pipe_project))
            print("Расстояние от спринклера до трубы {}".format(v.GetLength()/dut))
            print("v1 {}".format(v1.GetLength()/dut))
            print("v2 {}".format(v2.GetLength()/dut))
            print("v1.GetLength({}) >= spr_gap_min({}) {} ".format(v1.GetLength(), spr_gap_min, v1.GetLength() >= spr_gap_min*0.99))
            print("(v2.GetLength() > pipe_elbow_gap) {}".format((v2.GetLength() > pipe_elbow_gap)))
            print("(abs(ax_pipe_project) < 0.03) {}".format((abs(ax_pipe_project) < 0.03)))
            
            


        if ((v1.GetLength() >= spr_gap_min*0.99) 
                and (v2.GetLength() > pipe_elbow_gap)
                and (abs(ax_pipe_project) < 0.03) ) :
            """
            ***************************************************************
            * Случай если расстояния от спринклера достаточно большие
            * чтобы разместить отводы и ось спринклера достаточно близка к перпендикуляру
            * к оси трубы
            * в этом случае просто делаем две трубы, вдоль направления спринклера
            * и далее к целевой трубе и объединяем их отводами и фитингами
            ***************************************************************
            """
            if check_print :
                print('**************************')
                print('4 Контрольная точка ----------')
                print('Подключение спринклера в случае, когда спринклер находится в стороне от трубы и достаточном расстоянии чтобы вставить горизонтальный участок')

            try :
                segment_1 = Line.CreateBound(p1, closest_pnt_axe)
                segment_2 = Line.CreateBound(closest_pnt_axe, closest_pnt_pipe)

                pipe_seg_1_id = ElementTransformUtils.CopyElement(doc, pipe.Id, XYZ.Zero)[0]
                pipe_seg_1 = doc.GetElement(pipe_seg_1_id)
                pipe_seg_1.Parameter[d_param].Set(self.spr_pipe_d)
                pipe_seg_1.Location.Curve = segment_1
                c11, c12 = dm.get_ordered_end_connectors(pipe_seg_1)

                pipe_seg_2_id = ElementTransformUtils.CopyElement(doc, pipe.Id, XYZ.Zero)[0]
                pipe_seg_2 = doc.GetElement(pipe_seg_2_id)
                pipe_seg_2.Parameter[d_param].Set(self.spr_pipe_d)
                pipe_seg_2.Location.Curve = segment_2
                c21, c22 = dm.get_ordered_end_connectors(pipe_seg_2)

                if spr_con.Radius != c11.Radius :
                    doc.Create.NewTransitionFitting(spr_con, c11)
                else :
                    spr_con.ConnectTo(c11)

                doc.Create.NewElbowFitting(c12, c21)
                doc.Create.NewTakeoffFitting(c22, pipe)
            
            except Exception as ex :
                print('Ошибка при подключении спринклера с отводом ')
                print('\n{}\n{}'.format(ex, ex.clsException))
                raise

            return 
        if check_print :
            print('**************************')
            print('4.5 Контрольная точка ----------')
            print('Перед проверкой')
     

        if ((dist > 0.5 * r1) 
                and abs(ax_pipe_project) < 0.03) :
      
            """
            ***************************************************************
            * Случай, когда спринклер смещен относительно оси трубы, но
            * Расстояние не позволяет вставить горизонтальный участок, в этом случае
            * Пододвинем спринклер чтобы попал на ось трубы
            ***************************************************************
            """

            if check_print :
                print('**************************')
                print('5 Контрольная точка ----------')
                print('Подключение спринклера в случае, когда спринклер находится'+
                        ' в стороне от трубы и недостаточном расстоянии '+
                        'чтобы вставить горизонтальный участок')

            try :

                spr_move_vector = closest_pnt_pipe - closest_pnt_axe

                ElementTransformUtils.MoveElement(doc, spr.Id, spr_move_vector)

                p1 = spr_con.Origin
                
                
                segment_1 = Line.CreateBound(p1, closest_pnt_pipe)
                
                pipe_seg_1_id = ElementTransformUtils.CopyElement(doc, pipe.Id, XYZ.Zero)[0]
                pipe_seg_1 = doc.GetElement(pipe_seg_1_id)
                pipe_seg_1.Parameter[d_param].Set(self.spr_pipe_d)
                pipe_seg_1.Location.Curve = segment_1
                c11, c12 = dm.get_ordered_end_connectors(pipe_seg_1)


                if spr_con.Radius != c11.Radius :
                    doc.Create.NewTransitionFitting(spr_con, c11)
                else :
                    spr_con.ConnectTo(c11)

      
                doc.Create.NewTakeoffFitting(c12, pipe)
            
            except Exception as ex :
                print('Ошибка при подключении спринклера с отводом ')
                print('\n{}\n{}'.format(ex, ex.clsException))
                raise

            return 

        """
        ***************************************************************
        * МОЖЕТ БЫТЬ НЕСКОЛЬКО ВАРИАНТОВ ПОДКЛЮЧЕНИЯ
        * ПЕРВЫЙ - Самый простой вариант когда спринклер направлен коннектором
        * напрямую в трубу
        * ВТОРОЙ - когда спринклер находится в стороне от трубы, но направлен в сторону трубы
        *
        * ТРЕТИЙ
        *
        * ЧЕТВЕРТЫЙ
        ***************************************************************
        """     

        if (dist > 0.5 * r1) or not ve.IsAlmostEqualTo(d1) : 
            if check_print :
                try :
                    print('**************************')
                    print('5 Контрольная точка ----------')
                    print('_connect_sprinker вектор коннектора не совпадает с вектором подключения')
                    print('v : {} {} {} '.format(ve.X, ve.Y, ve.Z))
                    print('d1 : {} {} {} '.format(d1.X, d1.Y, d1.Z))
                    print('dist: {} '.format(dist))
                    v_d1 = ve.DotProduct(d1)
                    print('v*d1 : {}  r1* 0.5 {}'.format(v_d1, r1 * 0.5))

                    if abs(v_d1) < 0.98 :
                        print("Условия не выполняются, подключение не делаем")
                        return

                    print("Подключение возможно")
                except Exception as ex :
                    print("Ошибка на печати")
                    print(ex.clsException)

      
        try :
            new_pipe_id = ElementTransformUtils.CopyElement(doc, pipe.Id, XYZ.Zero)[0]
            new_pipe = doc.GetElement(new_pipe_id)
            new_pipe.Parameter[d_param].Set(self.spr_pipe_d)

            new_pipe.Location.Curve = lc2 

            c1, c2 = dm.get_ordered_end_connectors(new_pipe)

            """
            ***************************************************************
            * ПОДКЛЮЧАЕМ СПРИНКЛЕР К ТРУБЕ
            * Нужно выяснить является ли диаметр спринклера одинаковым с трубой
            * и при необходимости вставить переход
            ***************************************************************
            """
            if spr_con.Radius !=  c1.Radius :
                doc.Create.NewTransitionFitting(c1, spr_con)
            else :
                c1.ConnectTo(spr_con)

            """
            ***************************************************************
            * ПОДКЛЮЧАЕМ ПАТРУБОК К ТРУБЕ
            * при помощи отвода
            * 
            ***************************************************************
            """

            doc.Create.NewTakeoffFitting(c2, pipe)

        except Exception as ex:
            print(ex)
            pass





    def nearest_new_pipe(self, spr) :
        """
        ***************************************************************
        * ПОИСК И ВЫЧИСЛЕНИЕ БЛИЖАЙШЕЙ ТРУБЫ К СПРИНКЛЕРУ
        * Ближайшая труба из перечня вновь созданных труб
        * 
        ***************************************************************
        """

        p1 = list(spr.MEPModel.ConnectorManager.Connectors)[0].Origin

        pipes = sorted(self.new_pipes, key= lambda x : x.Location.Curve.Distance(p1))
        return pipes[0]


    def ConnectSprinklers(self) :
        """
        ***************************************************************
        * ПОДКЛЮЧЕНИЕ СПРИНКЛЕРОВ К СОЗДАННОЙ ТРУБЕ
        * Выполняет последовательное подключение спринклеров к 
        * созданным трубам. Для каждого спринклера выбирается ближайшая труба
        * и к ней осуществляется подключение
        * в зависимости от настройки самый дальний спринклер может быть
        * подключен как с помощью врезки так и отводом, это настраивается параметром
        * end_cap в конструкторе
        ***************************************************************
        """

        with dm.trans(doc) :
            for spr in self.sprinklers :
                try :
                    n_pipe = self.nearest_new_pipe(spr)
                    self._connect_sprinkler(n_pipe, spr)
                except :
                    print("Ошибка")


      

if False :
    for data_1 in data[1:2]: 
        calc = dmConnectUtils( x_angle = math.radians(0), 
                                end_cap= True, 
                            **data_1)
        route = calc.Calculate()
        calc.CreatePipesFromRoute()
        calc.ConnectSprinklers()


    # route_a = System.Array[GeometryObject](route)
    # with dm.trans(doc) :
    #     ds = DirectShape.CreateElement(doc, ElementId(bic.OST_GenericModel))
    #     ds = ds.SetShape(route_a)

    print("Выполнен")


