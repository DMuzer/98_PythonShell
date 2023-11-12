#  coding: utf-8 
from imp import reload
import dm_connect_pipe

reload(dm_connect_pipe)

from dm_connect_pipe import *
import Autodesk
from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
spr_cat = bic.OST_Sprinklers
ot_elem = UI.Selection.ObjectType.Element

def get_elements_from_doc(doc, cat) :
    d_ = doc
    trans1 = None
    if type(doc) == RevitLinkInstance :
        d_ = doc.GetLinkDocument()
        trans1 = doc.GetTotalTransform()

    fc = [(e, trans1) for e in FilteredElementCollector(d_).OfCategory(cat).ToElements()]
    return fc
def get_element_geometry_from_doc(doc, cat) :
    print("Выбираем геометрию типа {}\nиз документа {}".format(cat, doc))
    d_ = doc
    bo = DB.BooleanOperationsUtils
    bo_union = BooleanOperationsType.Union
    trans1 = None
    if type(doc) == RevitLinkInstance :
        d_ = doc.GetLinkDocument()
        trans1 = doc.GetTotalTransform()
    geom = []
    for e in FilteredElementCollector(d_).OfCategory(cat).ToElements() :
        g = e.Geometry[Options()]
        #print("{}".format(g))
        if g != None and trans1 !=None :
            #print("преобразовываем")
            g = list(g.GetTransformed(trans1))
            #print("получилось это: \n{}".format(g))
        elif g != None :
            g = list(g)   
        if g!= None :     
            geom += g

    #print("Всего элементов: {}".format(len(geom)))
    res = None
    if len(geom) > 0 :
        res = geom[0]
        if len(geom) > 1 :
            for g in geom[1:] :
                try :
                    res = bo.ExecuteBooleanOperation(res, g, bo_union)
                except Exception as ex:
                    try :
                        res = bo.ExecuteBooleanOperation(g, res, bo_union)
                    except Exception as ex :
                        print("Ошибка\n{}\n{}\n{}\n---------\n".format(ex, res, g))



                    



    return res 

    
bo = DB.BooleanOperationsUtils
bo_union = BooleanOperationsType.Union

def join_solids(l) :
    """
    объединяем объемные элементы в массиве в один
    """

    l2 = [e for e in l]

    res = l2.pop()

    for s in l2 :
        try :
            res = bo.ExecuteBooleanOperation(res, s, bo_union)
        except Exception as ex:
            print("Ошибка при объединении тел\n{}".format(ex))
            pass
    return res



class dm_Nearest_Geometry() :
    def __init__(self, cats, include_links = True) :
        self.docs = [uidoc.Document]
        self.linked_docs = []
        self.categories = cats
        if include_links :
            lnk_docs = FilteredElementCollector(doc).OfCategory(bic.OST_RvtLinks).WhereElementIsNotElementType()
            self.linked_docs = lnk_docs.ToElements()

        self.elements = []

        docs = self.docs + [d for d in self.linked_docs]
        for d_ in docs :
            for c_ in self.categories :
                doc_els = get_element_geometry_from_doc(d_, c_)
                if type(doc_els) == Solid :
                    self.elements.append(doc_els)
        print(len(self.elements))
        self.solid = join_solids(self.elements)
        return

    def nearest(self, p, d=XYZ.BasisZ, dist = 2000) :
        """
        Вычисляем ближайшую точку от заданной в заданном направлении
        """
        l = Line.CreateBound(p, p + d * dist)
        res = self.solid.IntersectWithCurve(l, None)

        pnts = []
        print("{}".format(res.SegmentCount))

        if res.SegmentCount > 0 :
            for c in res.GetEnumerator() :
                pnts += [c.GetEndPoint(0), c.GetEndPoint(1)]

            return sorted(pnts, key = lambda x : p.DistanceTo(x))[0]
        return None


def show_var_(v) :
    flds = dir(v)
    print("Доступные поля")
    for f in flds :
        if not f.startswith("__") :
            try :
                print("{:15} : {}".format(f, getattr(v, f)))
            except Exception as ex:
                pass
    



        
def hang_pipe(pipe, fam_sym) :

    try :
        if pipe.Category.Id.IntegerValue != int(bic.OST_PipeCurves) :
            return []
        
    except :
        raise
        return



    lc = pipe.Location.Curve
    p0 = lc.GetEndPoint(0)
    p = lc.Evaluate(0.1, True)
    dn = pipe.LookupParameter("Диаметр").AsDouble()
    #dm.create_point(p)

    p_len = lc.Length

    if p_len < 300	 * dut :
        return []

    if dn > 50 * dut :
        max_step = 5000 * dut
    else :
        max_step = 3000 * dut
        

    n_hangs = int(math.ceil(p_len / max_step))
    print(n_hangs, p_len)
    if n_hangs == 1 :
        print(p_len * dut)
    if (n_hangs < 2) and (p_len > 1000 * dut) :
        
        n_hangs = 2
        
    gap_1 = p_len / n_hangs / 2

    p_dir = lc.Direction

    if abs(XYZ.BasisZ.DotProduct(p_dir)) > 0.1 : return

    hangers = []

    with trans(doc) :
        for i_ in range(n_hangs) :	
            
            p = p0 + p_dir * gap_1 * (1 + i_*2) 
        
            new_hang = doc.Create.NewFamilyInstance(p, fam_sym, nonstr)
            param = new_hang.LookupParameter("DN").Set(dn)
            hang_conn = list(new_hang.MEPModel.ConnectorManager.Connectors)[0]
            print("Коннектор подвеса {}".format(hang_conn))
            hang_dir = XYZ(hang_conn.CoordinateSystem.BasisZ.X, hang_conn.CoordinateSystem.BasisZ.Y,0)
            print("Направление подвеса {}".format(hang_dir))
            try : 
                acos = lc.Direction.DotProduct(hang_dir)
                print("acos : {}".format(acos))
                ang = - math.acos(acos) * math.copysign(1, acos)
                
            except Exception as ex :
                print('Возникла ошибка {}'.format(ex))
            print('Угол между подвесом и трубой {}'.format(math.degrees(ang)))
            rot_line = Line.CreateBound(p, p + XYZ.BasisZ )
            try :
                ElementTransformUtils.RotateElement(doc, new_hang.Id, rot_line, ang)
            except Exception as ex :
                print("Ошибка поворота {}".format(ex))

            print("Повернули {}".format(i_))

            hangers.append(new_hang)

    return hangers


def get_pipe_ordered_connectors(p) :
    p1 = p.Location.Curve.GetEndPoint(0)
    conns = sorted([c for c in p.ConnectorManager.Connectors], key= lambda x : p1.DistanceTo(x.Origin))
def get_pipe_sizes(p) :
    return [d.NominalDiameter for d in p.PipeSegment.GetSizes()]

def get_pipe_size_next(p, d) :
    return filter(lambda x : x > d, get_pipe_sizes(p))[0]

def get_neaers_pipe_end(pipe, p) :
    lc = pipe.Location.Curve
    if lc.GetEndPoint(0).DistanceTo(p) < lc.GetEndPoint(1).DistanceTo(p) :
        return lc.GetEndPoint(0)
    else :
        return lc.GetEndPoint(1)
    

def create_sprinkler_line() :
    return 


def create_sprinkler_line_man(new_pipe_d, p_dist = 200 * dut, d_next = False) :
    import clr
    from System.Collections.Generic import IList, List
    from Autodesk.Revit.DB import SetComparisonResult, IntersectionResultArray
    import clr
    d_param = BuiltInParameter.RBS_PIPE_DIAMETER_PARAM

    new_pipe_d = pipe_d * dut

    uidoc = __revit__.ActiveUIDocument
    doc = uidoc.Document
    sprs = [doc.GetElement(r.ElementId) for r in uidoc.Selection.PickObjects(ot_elem)]
    sprs = filter(lambda x : x.Category.Id.IntegerValue == int(bic.OST_Sprinklers), sprs)
    pipe = doc.GetElement(uidoc.Selection.PickObject(ot_elem))

    pipe_d = pipe.Parameters[d_param].AsDouble()
    pipe_2d = pipe_d * 2

    

    #Отсортировать спринклеры по удалению от трубы
    lc0 = pipe.Location.Curve
    dir0 = lc0.Direction

    sprs = sorted(sprs, key = lambda x : lc0.Distance(x.Location.Point))

    s0 = sprs[-1]
    sc0 = list(s0.MEPModel.ConnectorManager.Connectors)[0]
    sp0 = sc0.Origin
    sd0 = sc0.CoordinateSystem.BasisZ
    

    p1 = sp0 + sd0* p_dist

    lc00 = Line.CreateBound(lc0.GetEndPoint(0) - lc0.Direction * 1000, lc0.GetEndPoint(0) + lc0.Direction* 1000)

    p0_ = lc00.Project(p1).XYZPoint

    d0_ =(p0_-p1)
    d0 = XYZ(d0_.X, d0_.Y, 0)

    lc1_ = Line.CreateBound(p1, p1 + d0)

    t = clr.Reference[IList[ClosestPointsPairBetweenTwoCurves]](List[ClosestPointsPairBetweenTwoCurves]())
    
    lc0.ComputeClosestPoints(lc1_, False, False, False, t)

    #проверим, выходит проекция трубы за пределы

    #Вектор до первого конца
    v01 = lc0.GetEndPoint(0) - p0_
    v02 = lc0.GetEntPoint(1) - p0_

    v01p = v01.DotProduct(dir0)
    v02p = v02.DotProduct(dir0)

    if v01p * v02p < 0 :
        #Это значит проекция попадает внутрь трубы
        inside = True
    else :
        #Это значит что проекция попадает за пределы трубы и надо делать дополнительный сегмент
        inside = False



    #если на 
    pipes = []
    dist0 = d0_.DistanceTo(d0)
    p1_ = p1 - d0 * pipe_d * 2
    if dist0 < 0.00001 :
        #трубы на одном уровне

        if inside :
            #cегмент добавлять не надо и просто создаем один сегмент
            pass
            
        else :
            #Длина сегмента будет равна большему из 
            l3 = max(new_pipe_d*2, lc0.Distance(p0_)+pipe_d)
            p2 = p0_ - d0_ * pipe_2d
            # p3 = p2 + 
            pipes.append(Line.CreateBound(p1_, p2))
            pipes.append(Line.CreateBound(p2,))


    elif d0_ < pipe_2d :
        #трубы нужно делать с переходом под тупым углом
        plane_1 = Plane.CreateByNormalAndOrigin(dir0, d0_)
        arc = Arc.Create(plane_1, pipe_2d,0,pi2)
        res1 = clr.Reference[IntersectionResultArray]()
        arc.Intersect(lc1_, res1)
        p2 = res1.item[0].XYZPoint

    else :
        #трубы надо делать под прямым углом
        pass


    # создаем трубы

    
    created_pipes = []

    with trans(doc) :
        for loc1 in pipes :
            np = ElementTransformUtils.CopyElement(doc, pipe.Id, XYZ.Zero)
            np.Location.Curve = loc1
            np.Parameters[d_param].Set(new_pipe_d)
            created_pipes.append(np)

    

    # присоединяем спринклеры

    for sp in sprs :
        pass


class dm_pipe_utils(object) :
    def __init__(self, pipe) :
        self.p = pipe
        self.doc = pipe.Document

    def get_sizes(self) :
        # return [s.NominalDiameter for s in self.p.PipeSegment.GetSizes()]
        sizes = [0.049212598425196846, 
                    0.065616797900262466, 
                    0.082020997375328086, 
                    0.10498687664041995, 
                    0.13123359580052493, 
                    0.16404199475065617, 
                    0.21325459317585302, 
                    0.26246719160104987, 
                    0.32808398950131235, 
                    0.41010498687664043, 
                    0.49212598425196852, 
                    0.65616797900262469, 
                    0.82020997375328086, 
                    0.98425196850393704, 
                    1.1482939632545932, 
                    1.3123359580052494]

        return sizes

    sizes = property(get_sizes)
    def get_next_size(self, d=0, i=1) :
        if d == 0 :
            return filter(lambda x : x >= self.diameter, self.get_sizes())[i]
        else :
            return filter(lambda x : x >= d, self.get_sizes())[i]


    def _end_connectors(self) :
        pnt = self.p.Location.Curve.GetEndPoint(0)
        return sorted([c for c in self.p.ConnectorManager.Connectors 
                                if c.ConnectorType == ConnectorType.End], 
                                        key = lambda x : pnt.DistanceTo(x.Origin))

    end_connectors = property(_end_connectors)

    def _set_location(self, l) :
        print("устанавливаем расположение")
        print(self.p, l)
        try :
            self.p.Location.Curve = l
        except Autodesk.Revit.Exceptions.ModificationOutsideTransactionException :
            with trans(self.p.Document) :
                self.p.Location.Curve = l


    def _get_location(self) :
        return self.p.Location.Curve

    loc = property(_get_location, fset = _set_location)

    def _set_size(self, d) :
        d_param = BuiltInParameter.RBS_PIPE_DIAMETER_PARAM
        try :
            self.p.Parameter[d_param].Set(d)
        except Autodesk.Revit.Exceptions.ModificationOutsideTransactionException :
            with trans(self.p.Document) :
                self.p.Parameter[d_param].Set(d)


    def _get_diameter(self) :
        return self.p.Parameter[BuiltInParameter.RBS_PIPE_DIAMETER_PARAM].AsDouble()


    diameter = property(_get_diameter, _set_size)

    def get_copy_pipe(self, d=None, lc=None, trans = False) :
        d_param = BuiltInParameter.RBS_PIPE_DIAMETER_PARAM
        if trans :
            tr = Transaction(self.doc)
            tr.Start("create pipe copy")

        
        new_pipe_id = ElementTransformUtils.CopyElement(self.doc, self.p.Id, XYZ(0,0,0))[0]
        new_pipe = self.doc.GetElement(new_pipe_id)

        if d :
            new_pipe.Parameter[d_param].Set(d)

        if lc :
            new_pipe.Location.Curve = lc 

        if trans :
            tr.Commit()

        return new_pipe

    

    

class dm_pipe_2_connect(dm_pipe_utils) :
    def __init__(self, pipe, minimum_dist_k = 2, end_dist_k = 2) :
        import clr
        from System.Collections.Generic import IList, List
        from Autodesk.Revit.DB import SetComparisonResult, IntersectionResultArray
        import clr
        d_param = BuiltInParameter.RBS_PIPE_DIAMETER_PARAM
        self.p = pipe
        self.doc = pipe.Document 
        self.d = pipe.Parameter[d_param].AsDouble()
        self.end_distance = self.d * end_dist_k
        self.minimum_dist = self.d * minimum_dist_k

        self.lc0 = pipe.Location.Curve
        if self.lc0.Length < self.end_distance :
            self.end_distance = self.lc0.Length / 2.1

        #Готовим линию, по которой будем подключать трубу.
        _p1 = self.lc0.GetEndPoint(0)
        _p2 = self.lc0.GetEndPoint(1)
        self.dir = self.lc0.Direction
        _p11 = _p1 + self.dir* self.end_distance
        _p21 = _p2 - self.dir* self.end_distance

        #Линия внутри которой допускается подключить трубу
        self.lc1 = Line.CreateBound(_p11, _p21)
        #Вычисляем условно бесконечную линию для вычисления проекции точки
        self.lc2 = Line.CreateBound(_p1 - self.dir*1000, _p1 + self.dir*1000)
       
        return


    def get_abs_project(self, pt) :
        """
        Вычисляет проекцию на прямую, на которой лежит труба
        """
        return self.lc2.Project(pt).XYZPoint
    def get_real_project(self, pt) :
        """
        Вычисляет предварительную точку присоединения. Если проекция попадает в диапазон подключения, то точка подключения будет проекцией.
        Если нет, то это будет один из концов допустимого диапазона
        """
        return self.lc1.Project(pt).XYZPoint

    def trace_from_point(self, p, make_gap_first = True, gap_size = 50 * dut) :
        """
        Вычисляет трассировку от заданной точки до трубы. Возврат - список линий, составляющих трассу - первая линия это линия у начальной точки
        последний сегмент присоединяется к трубе.
        make_gap_first - нужно ли сделать отступ.
        gap_size - размер отступа
        """
        pt0 = self.get_abs_project(p)



        pt0_1 = self.get_real_project(p)

        v = pt0_1 - p


        pt1 = pt0 - XYZ(0, 0, v.Z)

        if abs(v.Z) < self.minimum_dist :
            l1 = math.sqrt((self.minimum_dist)**2 -v.Z**2)
            pt1 = pt1 - XYZ(v.X, v.Y, 0).Normalize() * l1
            
        lines = [Line.CreateBound(p, pt1)]
            
        v1 = pt0_1-pt0
        if v1.GetLength() > 0 :
            if v1.GetLength() < 100 * dut :
                l = 100
                pt2 = pt1 + v1.Normalize() * l
            else :
                pt2 = pt1 + v1
                
            lines.append(Line.CreateBound(pt1, pt2))
        else :
            pt2 = pt1
            
        lines.append(Line.CreateBound(pt2, pt0_1))
        lines1 = []

        l1 = lines[0]
        for l2 in lines[1:]:
            if l1.Direction.IsAlmostEqualTo(l2.Direction) :
                l1 = Line.CreateBound(l1.GetEndPoint(0), l2.GetEndPoint(1))
            elif l1.Direction.DotProduct(l2.Direction) < 0 :
                p_1 = l1.Evaluate(0.8, True)
                p_2 = l2.Evaluate(0.2, True)
                l11 = Line.CreateBound(l1.GetEndPoint(0), p_1)
                l12 = Line.CreateBound(p_1, p_2)
                l21 = Line.CreateBound(p_2, l2.GetEndPoint(1))
                lines1 += [l11, l12]
                l1 = l21
                


            else :
                lines1.append(l1)
                l1 = l2
        lines1.append(l1)

        if make_gap_first :
            l0 = lines1[0]
            p0 = l0.GetEndPoint(0) - gap_size * l0.Direction
            l00 = Line.CreateBound(p0, l0.GetEndPoint(1))
            lines1 = [l00] + lines1[1:]

        return lines1

    def get_trace_from_point_direct(self, p, d, min_dist = 40 * dut) :
        """
            Вычисляет трассу прокладки трубы от точки с учетом заданного направления.
            Это удобно при вычислении подключения соединителя, т.к. необходимо, чтобы труба к соединителю 
            была направлена по нормали к плоскости соеденителя
        """

        # Проверка,  не упрется ли линия в трубу. То есть на вариант когда будет достаточно одного сегмента
        p0 = p + d * min_dist
        try :
            l0 = Line.CreateBound(p, p0)
        except Exception as ex :
            print("Не получилось get_trace_from_point_direct(self, p, d, min_dist = 40 * dut) \n{}".format(ex))



        p1 = self.get_real_project(p)
        l2 = Line.CreateBound(p, p1)
        print(l0.Direction, l2.Direction)
        if l0.Direction.IsAlmostEqualTo(l2.Direction) :
            return [l2]
        else :
            print("не равно")
            lines = self.trace_from_point(p0, make_gap_first=False)

            return [l0] + lines


    def _set_location(self, l):
        super()._set_location(l)

        self.end_distance = self.d * end_dist_k
        self.minimum_dist = self.d * minimum_dist_k

        self.lc0 = pipe.Location.Curve
        if self.lc0.Length < self.end_distance :
            self.end_distance = self.lc0.Length / 2.1

        #Готовим линию, по которой будем подключать трубу.
        _p1 = self.lc0.GetEndPoint(0)
        _p2 = self.lc0.GetEndPoint(1)
        self.dir = self.lc0.Direction
        _p11 = _p1 + self.dir* self.end_distance
        _p21 = _p2 - self.dir* self.end_distance

        #Линия внутри которой допускается подключить трубу
        self.lc1 = Line.CreateBound(_p11, _p21)
        #Вычисляем условно бесконечную линию для вычисления проекции точки
        self.lc2 = Line.CreateBound(_p1 - self.dir*1000, _p1 + self.dir*1000)
        return 

 
    def _create_pipes_from_lines(self, 
                                lines, d = 25*dut, 
                                connect_end = True,
                                transition_start = False,
                                start_size = 20 * dut
                                ) :
        doc = self.doc

        self.new_pipes = []

        if transition_start :
            l0 = lines[0]
            pt00 = l0.GetEndPoint(0)
            pt01 = l0.Evaluate(0.1, True)
            pt1 = l0.GetEndPoint(1)
            lines = [Line.CreateBound(pt00, pt01), Line.CreateBound(pt01, pt1)] + lines[1:]
        with trans(self.doc) :
            for l in lines :
                np = dm_pipe_2_connect(doc.GetElement(ElementTransformUtils.CopyElement(doc, self.p.Id, XYZ(1,1,0))[0]))
                np._set_location(l)
                np._set_size(d)
                np = dm_pipe_2_connect(np.p)
                self.new_pipes.append(np)
                

            for p1, p2 in zip(self.new_pipes[:-1], self.new_pipes[1:]) :
                try :
                    doc.Create.NewElbowFitting(p1.end_connectors[1], p2.end_connectors[0])
                except :
                    pass

            if connect_end :
                doc.Create.NewTakeoffFitting(self.new_pipes[-1].end_connectors[1], self.p)

            if transition_start :
                self.new_pipes[0].diameter = start_size
                doc.Create.NewTransitionFitting(self.new_pipes[0].end_connectors[1], self.new_pipes[1].end_connectors[0])
            
         
        return

    def get_nearest_pipe(self, pt) :
        try :
            
            pipes_ = sorted(self.new_pipes, key = lambda x : x.loc.Distance(pt))
            return pipes_[0]
        except Exception as ex :
            print("Ошибка get_nearest_pipe\n{}".format(ex))



    def create_and_connect_sprinkler_line(self, sprinklers, gap = 100 * dut) :
        """
        Создает ветку со спринклерами и подключает ее к трубе.
        sprinklers  - список подключаемых спринклеров.

        """

        # Сортируем спринклеры по удаленности от трубы.

        spr_sorted = sorted(sprinklers, key= lambda x : self.lc0.Distance(x.Location.Point))
        self.sprinklers = spr_sorted

        s1 = spr_sorted[-1]

        c0 = list(s1.MEPModel.ConnectorManager.Connectors)[0]

        p0 = c0.Origin 
        d0 = c0.CoordinateSystem.BasisZ
        size0 = c0.Radius * 2

        lines = self.get_trace_from_point_direct(p0, d0, 200 * dut)
        self._create_pipes_from_lines(lines,transition_start=True, start_size=size0)

        for s in spr_sorted[:-1] :
            c1  = list(s.MEPModel.ConnectorManager.Connectors)[0]
            p1 = c1.Origin
            d1 = c1.CoordinateSystem.BasisZ
            size1 = c1.Radius * 2

            pipe2 = self.nearest_new_pipe(p1)
            lines2 = pipe2.get_trace_from_point_direct(p1, d1, 200 *dut)

            pipe2._create_pipes_from_lines(lines2, transition_start = True, start_size = size1)



        return

    def nearest_new_pipe(self, pt) :
        if type(pt) != XYZ :
            pt = list(pt.MEPModel.ConnectorManager.Connectors)[0].Origin

        np = sorted(self.new_pipes, key= lambda x : x.loc.Distance(pt))
        return np[0]

    
        
    def connect_equipment(self, 
                    equip, next_size=1, 
                    second_size = 1, 
                    cap = True, 
                    try_to_center = True,
                    additional_gap = 0
                    ) :
        """
        Выполняет подключение оборудования к трубе
        next_size - индекс какой размер трубы используется для подключения 0 - размер трубы равен размеру коннектора, 1 - первый больший размер, 2 - второй больший размер и т.д.
        # cap - если True - тогда спринклер подсоединяем присоединением к ветке и устанавливаем заглушку на конец трубы, если False то делаем просто отводом
        second_size - это размер второго участка, число означает,на сколько шагов больше должен быть размер трубы относительно размера коннектора, если равен нулю, тогда он будет равен размеру первого сегмента
        # try_to_center - это параметр, который задает поведение, поднять трубу от оборудования до уровня трубы, если False
        """

        print("Подключение\n{}\n{}мм\nтруба{}\nспринклер\n{}".format(equip, self.d/dut, self.p.Id, equip.Id))
        c1 = list(equip.MEPModel.ConnectorManager.Connectors)[0]
        pt1 = c1.Origin
        dir1 = c1.CoordinateSystem.BasisZ
        size1 = c1.Radius * 2 # диаметр  коннектора оборудования
        
        lines1 =  [] # список линий из которых состоит первый участок
        lines2 = [] #список линий из которых состоит второй участок
        
        #размер, диаметр трубы первого сегмента
        size2 = self.get_next_size(d=size1, i = next_size) 
        size3 = self.get_next_size(size2, i= second_size)
        min_dist_1 = self.diameter
        print("size2 {} мм".format(size2/dut))
        if next_size > 0 :
            min_seg_1 = 5 * size2 # минимальная длина первого сегмента
        else :
            min_seg_1 = 3 * size2

        #pt2_ - минимальная точка для подключения (окончание первого сегмента, начало второго сегмента)
        print("mig_seg_1 {} мм".format(min_seg_1/dut))
        pt2_ = pt1 + dir1 * min_seg_1  #первое приближение длины первого сегмента.
    

        #Берем линию целевой трубы
        lc = self.p.Location.Curve

        #pt0 - вычисляем точка на трубе, куда будем присоединять
        pt0 = lc.Project(pt2_).XYZPoint

        #Вычисляем вектор от точки начала 2 сегмента к точке присоединения

        v1 = pt0 - pt1 
        #Вычисляем проекцию вектора v1 на направление соединителя.

        _l1_ = dir1.DotProduct(v1)
        _l2_ = XYZ.BasisZ.DotProduct(v1) / XYZ.BasisZ.DotProduct(dir1)

        #l_seg_1_1 = min( _l1, _l2)
        l_seg_1_1 = _l1_

        print("l_seg_1_1 {} мм\nmin_seg_1 {} мм".format(l_seg_1_1/dut, min_seg_1/dut))

        if try_to_center :
            l_seg_1 = max(l_seg_1_1, min_seg_1)
        else :
            l_seg_1 = min_seg_1

        l_seg_1 = l_seg_1 + additional_gap

        """

        if abs(l_seg_1 - l_seg_1_1) < 0.2 * self.diameter :
            l_seg_1 = l_seg_1_1 + 0.2 * self.diameter

        """
            


        print("Длина l_seg_1 {}".format(l_seg_1))

        pt2 = pt1 +  dir1 * l_seg_1

        if  next_size :
            pt10 = pt1 + dir1 * 10 * dut
            lines1.extend([Line.CreateBound(pt1, pt10), Line.CreateBound(pt10, pt2)])
        else :
            lines1.append(Line.CreateBound(pt1, pt2))

        #Вычисляем вектор от 2 точки к точке соединения. Второй сегмент должен быть по идее горизонтальным, поэтому далее будем искать проекцию на горизонтальную плоскость
        """
        pt0 - это точка куда должна быть присоединена труба
        pt1 - это точка соединителя
        pt2 -  это точка где будет находится отвод
        """
        print("{}{}".format(pt0, pt2))
        v2_ = pt0-pt2
        v20_ = XYZ(v2_.X, v2_.Y,0)
        pt3 = pt2 + v20_

        print("Длиина вектора v20_ : {}мм\nВектор {}, {}, {}".format(
                v20_.GetLength()/dut, 
                v20_.X/dut, v20_.Y/dut, v20_.Z/dut))

        print("Длиина вектора v2_ : {}мм\nВектор {}, {}, {}".format(
                v2_.GetLength()/dut, 
                v2_.X/dut, v2_.Y/dut, v2_.Z/dut))
    

        
        if v20_.GetLength() > size1/5 :

        #Второй сегмент.
            if abs(v2_.Z) < 0.005 : 
                print("втыкаем без отводов\n{}\n{}".format(min_dist_1, v2_.Z))
                l1 = Line.CreateBound(pt2, pt3)
                if cap :
                    pt20 = pt2 - l1.Direction * size2 * 2
                    l1 = Line.CreateBound(pt20, pt3) 
                lines2.append(l1)

                
            else :
                if abs(v2_.Z) > min_dist_1 : 
                    print("втыкаем вертикально")
                    try :
                        l1 = Line.CreateBound(pt2, pt3)
                        if cap :
                            pt20 = pt2 - l1.Direction * size2 * 2
                            l1 = Line.CreateBound(pt20, pt3) 
                            
                        lines2.append(l1)
                    except : pass
                    lines2.append(Line.CreateBound(pt3, pt0))
                else :
                    print("Втыкаем с отводом\n{}\n{}".format(min_dist_1, v2_.Z))
                    dl = (min_dist_1 ** 2 - v20_.Z ** 2)**0.5
                    pt3 = pt3 - v20_.Normalize() * dl

                    try :

                        l1 = Line.CreateBound(pt2, pt3)
                        if cap :
                            pt20 = pt2 - l1.Direction * size2 * 2
                            l1 = Line.CreateBound(pt20, pt3) 
                        lines2.append(l1)
                    except : pass
                    lines2.append(Line.CreateBound(pt3, pt0))

        #создаем трубы 1 участок
        pipes1 = []
        with trans(self.doc) :
            new_pipe1 = self.doc.GetElement(ElementTransformUtils.CopyElement(self.doc, self.p.Id, XYZ.BasisX)[0])
            new_pipe1 = dm_pipe_2_connect(new_pipe1)
            new_pipe1.loc = lines1[0]
            new_pipe1.diameter = size1

            if next_size > 0 :
                new_pipe2 = self.doc.GetElement(ElementTransformUtils.CopyElement(self.doc, self.p.Id, XYZ.BasisX)[0])
                new_pipe2 = dm_pipe_2_connect(new_pipe2)
                new_pipe2.loc = lines1[1]
                new_pipe2.diameter = size2

                self.doc.Create.NewTransitionFitting(new_pipe1.end_connectors[1],new_pipe2.end_connectors[0])
            else :
                new_pipe2 = new_pipe1

            c1.ConnectTo(new_pipe1.end_connectors[0])
        print("Делаем 2 сегмент")

        
        new_pipes = []
        with trans(self.doc) :
            if len(lines2) > 0 :
                new_pipes = []
                for l in lines2 :
                    new_pipe = self.doc.GetElement(
                        ElementTransformUtils.CopyElement(self.doc, self.p.Id, XYZ.BasisX)[0])
                    new_pipe = dm_pipe_2_connect(new_pipe)
                    new_pipe.loc = l
                    try :
                        new_pipe.diameter=size3
                    except Exception as ex:
                        print("Ошибка\nnew_pipe.diameter=size2\n{}".format(ex))
                    new_pipes.append(new_pipe)

                for p1, p2 in zip(new_pipes[:-1], new_pipes[1:]):
                    try :
                        self.doc.Create.NewElbowFitting(p1.end_connectors[1], p2.end_connectors[0])
                    except :
                        pass

                

                if cap :
                    try :
                        self.doc.Create.NewTakeoffFitting(new_pipe2.end_connectors[1], new_pipes[0].p)
                    except :
                        pass
                else :
                    try :
                        self.doc.Create.NewElbowFitting(new_pipe2.end_connectors[1], new_pipes[0].end_connectors[0])
                    except :
                        pass
                try :
                    self.doc.Create.NewTakeoffFitting(new_pipes[-1].end_connectors[1], self.p)
                except :
                    pass
            else :
                try :
                    self.doc.Create.NewTakeoffFitting(new_pipe2.end_connectors[1], self.p)
                except :
                    pass


        self.new_pipes = new_pipes

        #print("Готово")
        return

        




        