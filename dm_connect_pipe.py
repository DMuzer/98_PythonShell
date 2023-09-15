#  coding: utf-8 

from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math
import clr

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


pi2 = math.pi * 2

dut = 0.0032808398950131233







class WarningSwallower(IFailuresPreprocessor):
    def PreprocessFailures(self, failuresAccessor):
        from System.Collections.Generic import List
        #print("Обработка ошибки")
        try :
            fail_list = List[FailureMessageAccessor]()
            #print("обрабатываем дальше")
            fail_acc_list = list(failuresAccessor.GetFailureMessages().GetEnumerator())
            #print("Количество ошибок {}".format(len(fail_acc_list)))
            for failure in fail_acc_list:
                #print("Предупреждение {0}\n with id:".format(failure))
                failuresAccessor.DeleteWarning(failure)
            return FailureProcessingResult.Continue
        except Exception as ex :
            print("Ошибка во время ошибки\n{}".format(ex))
            return FailureProcessingResult.Continue



@contextmanager
def trans(doc, a="труба") :
    #print("новый тип транзакций  обработкой ошибки")
    tr = Transaction(doc)
    tr.Start(a)
    options = tr.GetFailureHandlingOptions()
    options.SetFailuresPreprocessor(WarningSwallower())
    tr.SetFailureHandlingOptions(options)
    try :	
        yield tr
    except Exception as ex:
        print("Ошибка транзакции\n{}".format(ex))
        
    finally :
        tr.Commit()

bic = BuiltInCategory

def en(el) :
    return Element.Name.GetValue(el)

def show_var_(v) :
    flds = dir(v)
    print("Доступные поля")
    for f in flds :
        if not f.startswith("__") :
            try :
                print("{:15} : {}".format(f, getattr(v, f)))
            except Exception as ex:
                pass


def get_geometry(e, trans = None,opt=None) :
    print('get_geometry start')
    if opt is None :
        g = e.Geometry[Options()]
    else :
        g = e.Geometry[opt]
    if trans :
        g = g.GetTransformed(trans)

    g = list(g)
    res = []
    while len(g) > 0 :
        ge = g.pop()
        if type(ge) == GeometryInstance :
            g.extend(list(ge.GetInstanceGeometry()))
            continue
        if type(ge) == GeometryElement :
            g.extend(list(ge))
            continue
        res.append(ge)		
    return res

def get_inserted_models(doc) :
    res = FilteredElementCollector(doc).OfCategory(bic.OST_RvtLinks).WhereElementIsNotElementType().ToElements()
    return res



def get_pipe_box(pipe) :
    from System.Collections.Generic import List
    lc = pipe.Location.Curve
    p1 = lc.GetEndPoint(0)
    p2 = lc.GetEndPoint(1)
    d = lc.Direction

    plane = Plane.CreateByThreePoints(p1, p2, p1 - XYZ.BasisZ)

    p11 = p1 - d * 1000 - XYZ.BasisZ * 1000
    p12 = p11 + XYZ.BasisZ * 2000
    p13 = p12 + d * 2000
    p14 = p13 - XYZ.BasisZ * 2000

    lines = [
        Line.CreateBound(p11, p12),
        Line.CreateBound(p12, p13),
        Line.CreateBound(p13, p14),
        Line.CreateBound(p14, p11),
    ]

    rect = [CurveLoop.Create(lines)]
    solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
    solid = GeometryCreationUtilities.CreateExtrusionGeometry(List[CurveLoop](rect),
                                        plane.Normal, dut)
                                        
    return solid

def create_direct_shape(solid) :	
    category_id = ElementId(bic.OST_GenericModel)
    doc = __revit__.ActiveUIDocument.Document
    print(doc.PathName)
    with trans(doc, "solid_bbox_direct_shape") as tx:
        direct_shape = DirectShape.CreateElement(doc, category_id)
        direct_shape.SetShape([solid])
    return direct_shape
        
def create_point(p, r = 1, lines = True) :
    from System.Collections.Generic import List

    if lines :
        p11 = p - XYZ.BasisX * r
        p12 = p + XYZ.BasisX * r

        create_model_line(Line.CreateBound(p11, p12))

        p21 = p - XYZ.BasisY * r
        p22 = p + XYZ.BasisY * r

        create_model_line(Line.CreateBound(p21, p22))

        p31 = p - XYZ.BasisZ * r
        p32 = p + XYZ.BasisZ * r

        create_model_line(Line.CreateBound(p31, p32))
        
        

    else :
        plane = Plane.CreateByNormalAndOrigin(XYZ.BasisY, p)

        arc1 = Arc.Create(p + XYZ.BasisZ * r, p - XYZ.BasisZ*r, p + XYZ.BasisX * r)
        #create_model_line(arc1)

        line1 = Line.CreateBound(p-XYZ.BasisZ*r, p+XYZ.BasisZ *r)
        #create_model_line(line1)


        cl = [CurveLoop.Create([arc1, line1])]

        solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)

        fr = Frame(p, XYZ.BasisX, XYZ.BasisY, XYZ.BasisZ) 

        ball = GeometryCreationUtilities.CreateRevolvedGeometry(fr, List[CurveLoop](cl), 0, math.pi * 2)
        create_direct_shape(ball)
        return ball

	    
def create_model_line(curve) :
    uidoc = __revit__.ActiveUIDocument
    doc =uidoc.Document

    try :
        plane = Plane.CreateByNormalAndOrigin(curve.Normal, curve.Center)
    except :
        p1 = curve.GetEndPoint(0)
        p2 = curve.GetEndPoint(1)
        p3 = p1 + XYZ(0.1, 0.3, 0.8)
        plane = Plane.CreateByThreePoints(p1, p2, p3)
        
    with trans(doc, "1") :
        sk_p = SketchPlane.Create(doc, plane)
        ml = doc.Create.NewModelCurve(curve, sk_p)
        

def getCylinder(pipe, d, dist = 2000) :
    """
    Создает Solid - в виде цилиндра для поиска пересечения с трубой.
    цилиндр создается условно бесконечным 
    pipe - это труба
    d - диаметр цилиндра
    dist - это удлинение цилиндра в каждую сторону
    """
    from System.Collections.Generic import List
    lc = pipe.Location.Curve

    p1 = lc.GetEndPoint(0) - lc.Direction * dist
    plane = Plane.CreateByNormalAndOrigin(lc.Direction, p1)

    arc1 = Arc.Create(plane, d/2, 0, math.pi)
    arc2 = Arc.Create(plane, d/2, math.pi, math.pi* 2)
    cl = [CurveLoop.Create([arc1, arc2])]
    solid_opt = SolidOptions(ElementId.InvalidElementId, ElementId.InvalidElementId)
    cyl = GeometryCreationUtilities.CreateExtrusionGeometry(List[CurveLoop](cl), plane.Normal, dist*2, solid_opt)
    return cyl


class dmPipeConnect() :

    def __init__(self, pipe_1, pipe_2, min_gap_1_param = 2, min_gap_2_param = 3) :
        self.pipe_1 = pipe_1
        self.pipe_2 = pipe_2
        self.doc = pipe_1.Document
        self.min_gap_1_param = min_gap_1_param
        self.min_gap_2_param = min_gap_2_param
        self.d1 = pipe_1.LookupParameter('Диаметр').AsDouble()
        self.d2 = pipe_2.LookupParameter('Диаметр').AsDouble()
        self.min_gap_1 = self.d1 * self.min_gap_1_param
        self.min_gap_2 = self.d2 * self.min_gap_2_param

        self.cyl_01_1 = getCylinder(pipe_1, self.min_gap_1)

        lc_01_1 = pipe_1.Location.Curve

        self.lc_01_unb = Line.CreateUnbound(lc_01_1.GetEndPoint(0),  )
        

        print('Диаметр трубы 1 {}'.format(self.d1/dut))
        print('минимальный отступ трубы 1 {}'.format(self.min_gap_1/dut))
        print('Диаметр трубы 2 {}'.format(self.d2/dut))
        print('минимальный отступ трубы 2 {}'.format(self.min_gap_2/dut))

def get_ordered_end_connectors(p) :
    """
    Возвращает упорядоченный список коннекторов трубы.
    Упорядочен так, что 0 - коннектор располагается на конце трубы который pipe.Location.Curve.GetEndPoint(0)
                        1 - коннектор соответствует pipe.Location.Curve.GetEndPoint(1)
    """
    pt = p.Location.Curve.GetEndPoint(0)
    conns = sorted([c for c in p.ConnectorManager.Connectors 
                        if c.ConnectorType == ConnectorType.End],
                        key = lambda x : pt.DistanceTo(x.Origin))
    return conns

def get_ordered_end_connected_elements(p) :
    """
    Возвращает список коннекторов элементов, которые присоединены к концам трубы.
    элемент 0 - присоединен в точке pipe.Location.Curve.GetEndPoint(0)
    элемент 1 - присоединен в точке pipe.Location.Curve.GetEndPoint(1)
    Если к концу не присоединен элемент то соответствующий элемент списка равен None.
    Удобно список применить для переключения со старой трубы на новую при помощи методов DisconnectFrom + ConnectTo
    """
    conns = get_ordered_end_connectors(p)
    res = []
    for c in conns :
        if not c.IsConnected :
            res.append(None)
        else :
            for c1 in c.AllRefs :
                if c1.Owner.Id != p.Id :
                    res.append(c1)
                    break

    return res
def get_takeoffs_data(p, lc1, lc2) :
    """
    Возвращает список с информацией о подключенных к трубе врезках которые нужно будут переподключать.
    p - труба
    lc1 - осевая линия трубы от которой не нужно подключать
    lc2 - осевая линия трубы от которой нужно будет отключить.
    то есть в список попадут врезки, которые находятся ближе к lc2 и не попадут те которые ближе к lc1.
    возвращает список кортежей в которых
    (takeoff, other_pipe_connector)
    takeoff - элемент врезка, чтобы можно было удалить при помощи метода doc.Delete(takeoff.Id)
    other_pipe_connector - коннектор присоединяемой трубы, чтобы удобно было использовать в методе doc.Create.NewTakeoffFitting(other_pipe_connector, pipe)
    """

    # формируется список  коннекторов. В список попадут только коннекторы типа Curve и только те, которые ближе к линии lc2 
    conns = [c for c in p.ConnectorManager.Connectors
                    if (c.ConnectorType == ConnectorType.Curve) and (lc1.Distance(c.Origin)>lc2.Distance(c.Origin))]

    res = []
    # Теперь надо извлечь информацию из коннекторов о врезке.
    takeoffs = []

    for c in conns :
        for c1 in c.AllRefs :
            if c1.Owner.Id != p.Id :
                takeoffs.append(c1.Owner)
                break 
    res = []
    for to in takeoffs :
        conns = [c for c in to.MEPModel.ConnectorManager.Connectors]

        for c in conns :
            for c1 in c.AllRefs :
                if (c1.Owner.Id != to.Id) and (c1.Owner.Id != p.Id) :
                    res.append((to, c1))
    print('---')
    for to, c in res :
        #print(to.Id)
        print(c.ConnectorType)
        print(c.Owner.Id)
    print('***')
    return res
                

def divide_pipe_at_point(p, pt) :
    """
    Разделение трубы на две части в переданной точке.
    возвращает кортеж из двух коннекторов новых труб в точке соединения.
    Эти коннекоры легко могут быть использованы для создания тройника    
    """

    # 1 шаг : собрать информацию о подключенных конечных элементах.


    cons = get_ordered_end_connectors(p)
    end_elements = get_ordered_end_connected_elements(p)
    # 2 шаг : собрать информацию о подключенных к трубе врезках
    lc = p.Location.Curve
    lc1 = Line.CreateBound(lc.GetEndPoint(0), pt)
    lc2 = Line.CreateBound(pt, lc.GetEndPoint(1))
    takeoffs = get_takeoffs_data(p, lc1, lc2)

    doc = p.Document

    with trans(doc) :
        #Создаем копию трубы
        p2_id = ElementTransformUtils.CopyElement(doc, p.Id, XYZ.Zero)[0]
        p2 = doc.GetElement(p2_id)
        p.Location.Curve = lc1
        p2.Location.Curve = lc2 

        cons2 = get_ordered_end_connectors(p2)

        if not end_elements[1] is None :
            
            cons2[1].ConnectTo(end_elements[1])

        for to in takeoffs :
            doc.Delete(to[0].Id)
            doc.Create.NewTakeoffFitting(to[1], p2)

    return ((p, p2), (cons[1], cons2[0])) 


def get_pnt_1(p1, p2) :
    """
    Вычисляет точку излома №1
    """
    import clr
    from System.Collections.Generic import IList, List
    k = 2
    d1 = p1.LookupParameter("Диаметр").AsDouble() 
    cyl = getCylinder(p1, d1 * k)

    lc1 = p1.Location.Curve
    lc2 = p2.Location.Curve

    lc3 = Line.CreateBound(lc2.GetEndPoint(0)- lc2.Direction * 2000, lc2.GetEndPoint(1) + lc2.Direction * 2000)
    int_res = cyl.IntersectWithCurve(lc3, None)

    if int_res.SegmentCount > 0 :       
        seg = int_res.GetCurveSegment(0)
        res = sorted([seg.GetEndPoint(0), seg.GetEndPoint(1)], key= lambda x : lc2.Distance(x))[0]
    else :
        
        t = clr.Reference[IList[ClosestPointsPairBetweenTwoCurves]](List[ClosestPointsPairBetweenTwoCurves]())
        lc1_ = Line.CreateBound(lc1.GetEndPoint(0)- lc1.Direction * 2000, lc1.GetEndPoint(1) + lc1.Direction * 2000)
        lc1_.ComputeClosestPoints(lc3, True, True, False, t)
        res = t.Item[0].XYZPointOnSecondCurve
   
    return res


def get_pnt_2(p1, p2, pnt_1, gap = 300 * dut) :
    """
    Вычисляем точку излома №2
    вход:
    p1 - труба в которую надо врезать
    p2 - труба которую подключаем в трубу p1
    pnt_1  - точка перелома №1
    gap - зазор который необходимо отступить от концов трубы.
    Будет ли точка излома №2 зависит от того, как взаимно располагаются
    трубы. Если вторую трубу можно подключить к первой в пределах допускаемого пространства, то такая точка не нужна
    если за пределами, тогда необходимо будет добавить еще один сегмент трубы для подвода вдоль направления первой трубы.
    возврат функции кортеж из двух точек:
    (pnt_1, pnt_2)
    pnt_1 - это точка врезки
    pnt_2 - это точка перелома №2. Если дополнительный сегмент не нужен, то pnt_2 = None

    Проверку на вычисление выполняем так, строим два вектора от точки перелома №1 к точкам границам допустимой зоны.
    Далее вычисляем проекции этих векторов на направление трубы и перемножаем их. Если точка перелома №1 находится за пределами
    допустимой зоны,  то проекции векторов будут направлены в одном направлении и их произведение будет положительным
    если внутри, то проекции будут разного знака и произведение будет отрицательным. 
    """
    lc1 = p1.Location.Curve
    lc2 = p2.Location.Curve
    p_01_1 = lc1.GetEndPoint(0) + lc1.Direction * gap
    
    p_01_2 = lc1.GetEndPoint(1) - lc1.Direction * gap

    v1p = (p_01_1 - pnt_1).DotProduct(lc1.Direction)
    v2p = (p_01_2 - pnt_1).DotProduct(lc1.Direction)

    vpm = v1p * v2p
    if vpm < 0 :
        p_0 = lc1.Project(pnt_1).XYZPoint

        return p_0, None

    else :
        p_0 = sorted([p_01_1, p_01_2], key= lambda x : pnt_1.DistanceTo(x))[0]
        v1p = (p_0-pnt_1).DotProduct(lc1.Direction)
        p_03_2 = pnt_1 + lc1.Direction * v1p

        return p_0, p_03_2
    res = (1,2)
    return res


def get_nearest_end_connector(p, pnt) :
    """
    Возвращает ближайший коннектор трубы к заданной точке
    """
    try :
        return sorted([c for c in p.ConnectorManager.Connectors], 
                    key = lambda x : pnt.DistanceTo(x.Origin))[0]
    except :
        return sorted([c for c in p.MEPModel.ConnectorManager.Connectors], 
            key = lambda x : pnt.DistanceTo(x.Origin))[0]
        



def connect_pipes_m1(pipe_1, pipe_2) :
    lc1 = pipe_1.Location.Curve
    lc2 = pipe_2.Location.Curve

    p_03_1 = get_pnt_1(pipe_1, pipe_2)
    p_0, p_03_2 = get_pnt_2(pipe_1, pipe_2, p_03_1)

    
    div_result = divide_pipe_at_point(pipe_1, p_0)
    
    if p_03_1.DistanceTo(lc2.GetEndPoint(0)) < p_03_1.DistanceTo(lc2.GetEndPoint(1)) :  
        p_02_1 = lc2.GetEndPoint(0) 
    else : 
        p_02_1 = lc2.GetEndPoint(1)


    p2_con = get_nearest_end_connector(pipe_2, p_02_1)

    p_end = []
    if p_03_2 is None :
        p_end.append((p_0, p_03_1))
        p_end.append((p_03_1, p_02_1))    
    else :
        p_end.append((p_0, p_03_2))
        p_end.append((p_03_2, p_03_1))
        p_end.append((p_03_1, p_02_1))

    n_pipes = []
    n_cons = []
    with trans(doc) :
        for e_ in p_end :
            np = doc.GetElement(ElementTransformUtils.CopyElement(doc, pipe_2.Id, XYZ.Zero)[0])
            nlc = Line.CreateBound(e_[0], e_[1])
            np.Location.Curve = nlc
            n_pipes.append(np)
            n_cons.append(get_ordered_end_connectors(np))

        #создаем отводы
        for c1, c2 in zip(n_cons[:-1], n_cons[1:]) :        
            doc.Create.NewElbowFitting(c1[1], c2[0])

        c2[1].ConnectTo(p2_con)

        #создаем тройник

        doc.Create.NewTeeFitting(div_result[1][0], div_result[1][1], n_cons[0][0])


def connect_pipes_m2(p1, p2) :
    import clr
    from System.Collections.Generic import IList, List

    lc1 = p1.Location.Curve
    lc2 = p2.Location.Curve
    t = clr.Reference[IList[ClosestPointsPairBetweenTwoCurves]](List[ClosestPointsPairBetweenTwoCurves]())    
    lc1.ComputeClosestPoints(lc2, False, True, False, t)
    res = t.Item[0].XYZPointOnSecondCurve
    global int_res
    int_res = lc1.Project(res)

def connect_pipes_gen(meth = 1) :
    _i = 0
    while True :
        pipe_id1 = uidoc.Selection.PickObject(UI.Selection.ObjectType.Element)
        pipe_id2 = uidoc.Selection.PickObject(UI.Selection.ObjectType.Element)

        try :
            pipe_1 = doc.GetElement(pipe_id1)
            pipe_2 = doc.GetElement(pipe_id2)

            if meth == 1 :
                connect_pipes_m1(pipe_1, pipe_2)
        except Exception as ex:
            print(ex)
            break

        _i +=1
        if _i > 10 : 
            break


def connect_sprinkler(p, s, increase_diameter = True, add_trans = False) :
    print("Подключаем спринклеры\n{}\n{}".format(p, s))

    doc = p.Document
    #вычисляем положение соединителя спринклера и его направление
    def get_spr_position(s) :
        con = list(s.MEPModel.ConnectorManager.Connectors)[0]
        return con.Origin, con.CoordinateSystem.BasisZ, con
    spr_p, spr_d, sp_con = get_spr_position(s)

    print("Спринклер\n {},\n {}".format(spr_p, spr_d))

    import clr
    from System.Collections.Generic import IList, List

    lc1 = p.Location.Curve
    lc2 = Line.CreateBound(spr_p, spr_p + spr_d*1000)

    # create_model_line(lc1)
    # create_model_line(lc2)


    t = clr.Reference[IList[ClosestPointsPairBetweenTwoCurves]](List[ClosestPointsPairBetweenTwoCurves]())
    
    lc1.ComputeClosestPoints(lc2, True, True, False, t)
    
    global int_res
    int_res = t.Item[0]
    # create_point(int_res.XYZPointOnFirstCurve, 0.1) 
    # create_point(int_res.XYZPointOnSecondCurve, 0.1)
    d1 = p.LookupParameter("Диаметр").AsDouble()
    d1 = sp_con.Radius * 2
    if increase_diameter :
        n_d1 = filter(lambda x : x > d1, [s_.NominalDiameter for s_ in p.PipeSegment.GetSizes()])[0]
    else :
        n_d1 = filter(lambda x : x >= d1, [s_.NominalDiameter for s_ in p.PipeSegment.GetSizes()])[0]
    print(d1)
    print(n_d1)

    max_dist = d1 * 2

    if (int_res.Distance > 0) and (int_res.Distance < max_dist) :
        #если спринклер не точно под трубой, то пододвинем спринклер.
        v = int_res.XYZPointOnFirstCurve - int_res.XYZPointOnSecondCurve
        np = s.Location.Point + v
        print("Передвигаем спринклер")


        with trans(doc) :
            ElementTransformUtils.MoveElement(doc, s.Id, v)

    dist2 = sp_con.Origin.DistanceTo(int_res.XYZPointOnFirstCurve)
   
    if dist2 < 6 * d1 :
        v = -spr_d * (6 * d1 - dist2)
        with trans(doc) :        
            ElementTransformUtils.MoveElement(doc, s.Id, v)
            





    if int_res.Distance < max_dist :
        #Строим линию и подключаем
        with trans(doc) :
            p2 = doc.GetElement(ElementTransformUtils.CopyElement(doc, p.Id, XYZ.Zero)[0])
            lc3 = Line.CreateBound(sp_con.Origin, int_res.XYZPointOnFirstCurve)
            p2.Location.Curve = lc3
            p2.LookupParameter("Диаметр").Set(n_d1)

            conns = get_ordered_end_connectors(p2)
            
            if add_trans :
                doc.Create.NewTransitionFitting(conns[0], sp_con)
            else :
                conns[0].ConnectTo(sp_con)
            
            doc.Create.NewTakeoffFitting(conns[1], p)




def connect_sprinkler_man() :
    global pipe_id1, spr_id1
    doc = uidoc.Document
    sprs = []
    spr_cat = int(bic.OST_Sprinklers)
    pipe_cat = int(bic.OST_PipeCurves)
    el_ids=uidoc.Selection.GetElementIds()
    print("Количество элементов {}".format(len(el_ids)))
    for id_ in  el_ids :
        el = doc.GetElement(id_)
        if el.Category.Id.IntegerValue == spr_cat :
            sprs.append(el)

    print("Количество спринклеров {}".format(len(sprs)))

    if len(sprs) < 1 :
        el_ids = uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element)

        
        print("Количество элементов {}".format(len(el_ids)))
        for id_ in  el_ids :
            el = doc.GetElement(id_.ElementId)
            if el.Category.Id.IntegerValue == spr_cat :
                sprs.append(el)

    print("Количество спринклеров {}".format(len(sprs)))

    pipe_id = uidoc.Selection.PickObject(UI.Selection.ObjectType.Element).ElementId
    pipe = doc.GetElement(pipe_id)

    if pipe.Category.Id.IntegerValue == pipe_cat :
        for s in sprs :
            print("---")
            connect_sprinkler(pipe, s)
    


    return
    #pipe_id1 = uidoc.Selection.PickObject(UI.Selection.ObjectType.Element)
    #spr_id1 = uidoc.Selection.PickObject(UI.Selection.ObjectType.Element)
    print()

    try :
        pipe_1 = doc.GetElement(ElementId(pipe_id1))
        spr_1 = doc.GetElement(ElementId(spr_id1))
        connect_sprinkler(pipe_1, spr_1)
    except Exception as ex:
        print(ex)
        





    

    








