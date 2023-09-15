#  coding: utf-8 


import heapq
from xml.dom.minidom import Element
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
import itertools
import System



class dmHeapQ(object) :
    def __init__(self) :
        self.pq = []
        self.entry_finder = {}
        self.counter = itertools.count()

    def add(self, v, d) :
        if v in self.entry_finder :
            self.remove_task(v)
        entry = [d, v]
        self.entry_finder[v] = entry
        heapq.heappush(self.pq, entry)

    def remove_task(self,v) :
        entry = self.entry_finder.pop(v)
        entry[-1] = None 
    def pop_task(self) :
        while self.pq :
            d, v = heapq.heappop(self.pq)
            if not v is None :
                del self.entry_finder[v]
                return v 
        raise KeyError("Попытка вытащить из пустой кучи")





class dmElement(object) :
    def __init__(self, e) :
        if isinstance(e, int) :
            e = doc.GetElement(ElementId(e))
        self.e = e
        self.doc = e.Document
    def __repr__(self) :
        return "Элемент {}".format(self.e.Id)

    def _get_connector_by_id(self, conn_id) :
        if hasattr(self.e, "ConnectorManager") :
            conns = self.e.ConnectorManager.Connectors
        elif hasattr(self.e, "MEPModel") :
            conns = self.e.MEPModel.ConnectorManager.Connectors
        else :
            return 

        res = {c.Id : c for c in conns}
        return res[conn_id]

    def GetParameterValue(self, name) :
        param = self.e.LookupParameter(name) 
        if not param :
            t = self.doc.GetElement(self.e.GetTypeId())
            param = t.LookupParameter(name) 

        if not param : return

        if param.StorageType == StorageType.String :
            return param.AsString()
        elif param.StorageType == StorageType.Double :
            return param.AsDouble()
        elif param.StorageType == StorageType.Integer :
            return param.AsInteger()
        elif param.StorageType == StorageType.ElementId :
            return param.AsElementId()

    def SetParameterValue(self, name, v) :
        param = self.e.LookupParameter(name) 
        if not param :
            t = self.doc.GetElement(self.e.GetTypeId())
            param = t.LookupParameter(name) 
        if not param : return
        try :
            param.Set(v)
        except :
            try :
                with dm.trans(self.doc) :
                    param.Set(v)
            except :
                raise 

    def GetConduitConnectors(self) :
        if hasattr(self.e, "ConnectorManager") :
            conns = self.e.ConnectorManager.Connectors
        elif hasattr(self.e, "MEPModel") :
            conns = self.e.MEPModel.ConnectorManager.Connectors
        else :
            return 

        res = [c for c in conns if c.Domain == Domain.DomainCableTrayConduit]
        return res 
    conduitConnectors = property(GetConduitConnectors)
    
    def GetConnectedConduitPartsId(self) :
        # Возвращает подключенные элементы в виде кортежей: (с.Id, c1.Owner.Id, c1.Id)
        # Где с.Id - это идентификатор коннектора объекта к которому подключен внешний объект
        # c1.Owner.Id - ElementId подключенного объекта
        # с1.
        res = []
        sid = self.e.Id
        for c in self.conduitConnectors :
            if c.IsConnected :
                for c1 in c.AllRefs :
                    if c1.Owner.Id != sid :
                        res.append((c.Id, c1.Owner.Id.IntegerValue, c1.Id))
        return res

    # def GetConnected

    def get_used_connector_vertexes(self) :
        sid = self.e.Id.IntegerValue
        for c in self.conduitConnectors :
            yield (sid, c.Id)

    def get_all_conduit_edges(self) :
        # Возвращает все ребра для элемента

        res = []

        vs = []
        sid = self.e.Id.IntegerValue

        for c in self.conduitConnectors :
            if not c.IsConnected : continue
            vs.append((sid, c.Id))

        for v1, v2 in itertools.combinations(vs,2) :
            res.append((v1, v2))
            res.append((v2, v1))

        for v in self.GetConnectedConduitPartsId() :
            v1 = (sid, v[0])
            v2 = (v[1], v[2])
            res.append((v1, v2))
            res.append((v2, v1))

        
            

        return res 




class dmCircuit(dmElement) :
    def __repr__(self) :
        return "Цепь {}".format(self.e.Name)

    def _get_elements(self) :
        return [dmElement(e) for e in self.e.Elements]

    elements = property(_get_elements)

    def _get_panel(self) :
        return dmElement(self.e.BaseEquipment)

    panel = property(_get_panel)

    def get_conduit_graph(self) :

        self.equipment_set = set([e.e.Id.IntegerValue for e in self.elements])
        to_visit = set()
        visited = set()
        to_visit.add(self.panel.e.Id.IntegerValue)
        g = dmGraph()
        # проходим

        while len(to_visit) > 0 :
            current_id = to_visit.pop()
            # если он уже посещен, то пропускаем
            if current_id in visited : continue

            visited.add(current_id)
            e = doc.GetElement(ElementId(current_id))
            current = dmElement(e)

            for v in current.get_all_conduit_edges() :
                g.add_edge(v)

            for ce in current.GetConnectedConduitPartsId() :
                to_visit.add(ce[1])
        return g

    def _get_loadName(self) :
        try :
            return self.e.LoadName
            #return self.e.GetParameterValue("Имя нагрузки").AsString()
        except :
            return 
    loadName = property(_get_loadName)

    def find_fartherst_element(self) :
        # Находит наиболее удаленный элемент в сети графа.
        self.g = self.get_conduit_graph()
        self.g.calc_edges_length()
        panel_vert = self.g.get_element_nearest_vertex(self.panel)

        print(self.g.Ids[self.panel.e.Id.IntegerValue])
        print(50*"*")
        print("Вершина панели : {}".format(panel_vert))
        self.g.calc_edges_length()
        self.g.initialize_single_source(panel_vert)
        self.g.dijkstra(panel_vert)

        elems = {}
        for e in self.elements :
            try :
                u = self.g.get_element_nearest_vertex(e)
                if u is None : continue
                ud = self.g.V[u]
                elems[u] = ud
            except :
                pass 
        fartherst = max(elems, key = lambda x : elems[x]['d'])
        return fartherst

    def get_fartherst_element_path(self) :
        farthest = self.find_fartherst_element()
        res = self.g.get_shortest_path(farthest)
        return res

    def get_fartherst_element_path_elems(self) :
        fp = self.get_fartherst_element_path()
        res =[ fp[-1][0]]

        for u in fp[::-1] :
            if res[-1] == u[0] :
                continue
            res.append(u[0])
        return res
    def get_path_and_branches(self) :
        # Вычисляет путь до самого дальнего устройства
        # и вычисляет начала ответвлений от пути
        # Возвращает кортеж (fp_res, map1)
        # fp_res - путь от панели к наиболее удаленному устройству (путь в виде вершин)
        # map1 - это словарь с ответвлениями, где ключи - это Id элементов основного пути, а 
        # значения - вершины графа с которых начинаются ответвления.

        # Находим путь от самого удаленного элемента
        # к панели
        fp = self.get_fartherst_element_path()
    
        

        base_path_set = set([i for i in fp[:-1]])
        base_path_id_set = set([i[0] for i in base_path_set])



        # Находим все элементы prev которых указывает
        # на любой элемент из основного пути
        # и формируем словарь для определения ссылки на 
        # обход ветки

        map1 = {}

        for u in self.g.V :
            ud = self.g.V[u]
            if ud['prev'] is None :
                continue 
            if (ud['prev'][0] in base_path_id_set) :
                if not u[0] in base_path_id_set :
                    map1[ud['prev']] = u 

        fp_res = fp[::-1]

        return fp_res, map1

    def _reset_color(self, g = None) :
        # Сбрасываем настройки графики для элемента
        view = uidoc.ActiveView
        parts = set()
        if g is None :
            g = self.g 
        # print(g)
        for v in g.V :
            # print(v)
            try :
                parts.add(v[0])
            except :
                pass
        # print("сбрасываем цвета элементов цепи")
        ogs = OverrideGraphicSettings()
        color = Color.InvalidColorValue
        ogs.SetProjectionLineColor(color)
        ogs.SetProjectionLineWeight(-1)
        with dm.trans(doc) :
            for eid in parts :
                view.SetElementOverrides(ElementId(eid), ogs)

    def _show_elements(self, lst, color=None) :
        # Раскрашивает список элементов заданным цветом
        #  lst - список Id в целочисленном значении
        if color is None :
            color = Color(0,255,0)
        view = uidoc.ActiveView
        ogs = OverrideGraphicSettings()
        ogs.SetProjectionLineColor(color)
        ogs.SetProjectionLineWeight(5)

        with dm.trans(doc) :
            for eid in lst :
                view.SetElementOverrides(ElementId(eid), ogs)

    def walk_branch(self, b) :
        # Выполняет обход ветки при этом не заходя на основной путь
        # b - которая начинает ветку
        # 


        print("Обход ветки")
        print(b)
        bd = self.g.V[b]
        if bd['visited'] > 0 :
            print("Тут уже были, пропускаем")
        to_visit = collections.deque([b])
        branch_sequence = []
        it = 0 
        while to_visit :
            it += 1
            if it > 80 : break 
            u = to_visit.popleft()
            ud = self.g.V[u]
            # Если текущая вершина на основном пути то пропускаем
            if ud['main'] : continue
            if ud['visited'] > 0 : continue
            branch_sequence.append(u)
            to_visit.extend(ud['edges_out'])
            ud['visited'] = 1
            print(to_visit)
            
        print("branch_sequence")
        print(branch_sequence)
        return branch_sequence
            

    def reset_graph(self, path, branches) :
        # Подготовка графа к обходу для определения последовательности элементов
        # path - путь к наиболее удаленному элементу - последовательность вершин (кортежи (Id, cId))
        # branches - словарь ветвлений keys - элементы основной последовталеьности - values - начало веток
        print(50*"-")
        print("сброс")
        for u in self.g.V :
            ud = self.g.V[u]
            ud['main'] = False 
            ud['branch'] = False 
            ud['visited'] = 0

        for u in path :
            ud = self.g.V[u]
            ud['main'] = True 
        for u in branches :
            ud = self.g.V[u]
            ud['branch'] = True 

        for u in self.g.V :
            ud = self.g.V[u]
            if ud['branch'] and ud['main'] :
                print("Основной с ответвлением")

        print(path)
        print(branches)

        count1 = 0 
        for u in branches :
            if u in path :
                count1 += 1

        print("Количество веток в основном пути {}".format(count1))



    def show_path_and_branches(self) :
        from collections import deque
        path, branches = self.get_path_and_branches()
        branches1 = {k[0] : branches[k] for k in branches} 
        path = deque(path)


        self._reset_color()

        green_elements = set([i[0] for i in path])
        green_color = Color(0,255,0)
        #self._show_elements(green_elements, green_color)

        red_elements  = set([i[0] for i in branches.values()])
        red_color = Color(255,0,0)
        #self._show_elements(red_elements, red_color)

        self.reset_graph(path, branches)

        sequence = []

        it1 = 0

        while path :
            current = path.popleft()
            sequence.append(current)
            current_d = self.g.V[current]
            current_d['visited'] = 1
            if not current[0] in branches1.keys() : continue
            print("Нужен обход ветки")
            
            # Нужно сделать обход ветки
            branch = branches1[current[0]]
            print(branch)
            branch_sequence = self.walk_branch(branch)
            sequence.extend(branch_sequence)
            it1 += 1
            if it1 > 200 :  break 

        
        blue_elements =  [i[0] for i in  sequence]
        blue_color = Color(0,0,255)
        #self._show_elements(blue_elements, blue_color)

        element_set = set([e.e.Id.IntegerValue for e in self.elements])
        print(element_set)

        added = set()
        el_sequence = []

        for e in sequence :
            if e[0] in element_set :
                el_sequence.append(e[0])
                element_set.discard(e[0])

        tr = Transaction(doc)



        

        yelow_color = Color(255, 255,0)
        #self._show_elements(el_sequence, yelow_color)

        

        tr.Start("1")

        for num, e in enumerate(el_sequence, 1) :
            # print(num, e)
            el = doc.GetElement(ElementId(e))
            try :
                old = el.LookupParameter("Марка").AsString()
                parts = old.split(".")
                parts[-1] = str(num)
                new_mark= ".".join(parts)
                el.LookupParameter("Марка").Set(new_mark)
                el.LookupParameter("ADSK_Номер в шлейфе").Set(num)
            except :
                pass 
        tr.Commit()

        # Вычисляем последовательность соединения приборов


        el_sequence = [self.panel.e.Id.IntegerValue] + el_sequence

        print()

        vertex_sequence = []

        dev_sequence = [(e1, e2) for e1, e2 in zip(el_sequence[:-1], el_sequence[1:])]
        for pair in dev_sequence :
            print(pair)
            e1, e2 = pair

            self.g.dijkstra(e1)
            e2_vert = self.g.get_element_nearest_vertex(e2)
            s_path_1 = self.g.get_shortest_path(e2_vert)
            vertex_sequence.extend(s_path_1)

        points_path = []
        print("Вычисляем путь")

        for u in vertex_sequence :
        
            
            el = dmElement(u[0])
 
            c1 = el._get_connector_by_id(u[1])
            points_path.append(c1.Origin)

        print(points_path)
        print(len(points_path))

        circuit_path = self.e.GetCircuitPath()
        print(100*'-')
        print("circuit path")
        print(circuit_path)
        p0 = circuit_path.Item[0]
        print(type(p0))

        points_path = [p0] + points_path

        print("points path")
        print(points_path)

        
        p1 = points_path[0]
        points_path_res = [p1]
        i = 0
        while i < len(points_path)-1 :
            i += 1
            print(i)
            p2 = points_path[i]

            d = p2 - p1 
            print(d, p1, p2)

            if abs(d.X) > 0.003 :
                p2_ = p1 + XYZ(d.X,0,0)
                points_path_res.append(p2_)
                p1 = p2_
            if abs(d.Y) > 0.003 :
                p2_ = p1 + XYZ(0,d.Y,0)
                points_path_res.append(p2_)
                p1 = p2_ 
            if abs(d.Z) > 0.003 :
                p2_ = p1 + XYZ(0,0,d.Z)
                points_path_res.append(p2_)
                p1= p2_
            
            

    
        new_path = System.Array[XYZ](points_path_res)
        print('Количество точе траектории')
        print(len(points_path_res))

        print(50*"-")
        print(new_path)
        
        print(self.loadName)

        tr.Start("Modyfy circut Path")
        self.e.SetCircuitPath(new_path)
        tr.Commit()




            


            

        





        return sequence


        

        




class dmCircuits(object) :
    def __init__(self, doc = None) :
        self.doc = doc 
        if not self.doc :
            self.doc = uidoc.Application.ActiveUIDocument.Document
        
        self._c_list = [dmCircuit(e) for e in FilteredElementCollector(self.doc).OfClass(Electrical.ElectricalSystem).ToElements()]

        self.circuits_by_loads = collections.defaultdict(list)
        for c in self._c_list :
            self.circuits_by_loads[c.loadName].append(c)


    def __getitem__(self, index) :
        return self._c_list[index]

    def getByLoadName(self, name) :
        return self.circuits_by_loads[name]
        





class dmGraph(object) :
    def __init__(self, to_copy = None) :
        import copy 
        if to_copy is None:
            self.V = collections.defaultdict(dict)
            self.E = collections.defaultdict(dict)
            self.Ids = collections.defaultdict(set)
        else :
            self.V = copy.deepcopy(to_copy.V)
            self.E = copy.deepcopy(to_copy.E)
            self.Ids = copy.deepcopy(to_copy.Ids)

        self.Q = dmHeapQ()

    def get_copy(self) :
        return dmGraph(to_copy=self)

    def add_edge(self, e) :
        # Добавляем ребро, и если необходимо вершины также будут добавлены

        v1, v2 = e

        v1d = self.V[v1]
        self.Ids[v1[0]].add(v1)
        if not "edges_out" in v1d :
            v1d['edges_out'] = set([v2])
        else :
            v1d['edges_out'].add(v2)

        v2d = self.V[v2]
        self.Ids[v2[0]].add(v2)
        if not "edges_in" in v2d :
            v2d['edges_in'] = set([v1])
        else :
            v2d['edges_in'].add(v1)
        self.E[e]

    def delete_edge(self, e) :
        # Удаление ребра графа
        u, v = e 
        ud = self.V[u]
        vd = self.V[v]
        # Сначала удалим вхождение в исходящих ребер из вершины начала
        ud['edges_out'].discard(vd)
        # Удалим вхождение ребра из множества входящих ребер конца ребра
        vd['edges_in'].discard(ud)
        # Удаляем ребро из словаря ребер
        del self.E[e]


    def delete_vertex(self, u) :
        # Удаление вершины графа
        # Сначала удалим исходящие ребра
        ud = self.V[u]

        for v in ud['edges_out'] :
            self.delete_edge((u, v))         

        # Далее удалим входящие ребра
        for u in ud['edges_in'] :
            self.delete_edge((v, u))

        # Далее удалим вершину из словаря
        del self.V[u]

        # Далее удалим вершину из множества вершин в словаре ссылок Ids
        self.Ids.discard(u)

    def delete_element_vertexes(self, eid) :
        # Удаляет все вершины, которые относятся к элементу с заданным
        # id 

        uu = self.Ids[eid]
        print("Найдены вершины {}".format(uu))
        for u in uu :
            self.delete_vertex(u)
        

    def get_vertex_position(self, v) :
        # Возращает положение вершины в пространстве в виде XYZ()
        vid, vcid = v
        ve = dmElement(vid)
        # print(ve)
        c = ve._get_connector_by_id(vcid)
        return c.Origin 

    def calc_edges_length(self) :
        # Расчет длинн ребер графа.
        # Длина графа определяется как расстояние между местоположениями вершин
        # которые определяются как точка соответствующего коннектора

        for e in self.E :
            ed = self.E[e]
            u, v = e
            ou = self.get_vertex_position(u)
            ov = self.get_vertex_position(v)
            e_len = ou.DistanceTo(ov)
            if e_len < 0.001 :
                e_len = 0.001

            ed['length'] = e_len 


    def initialize_single_source(self, s) :
        for v in self.V.values() :
            v['d'] = float.PositiveInfinity
            v['prev'] = None 
            v['color'] = 0
        self.V[s]['d'] = 0
        self.Q = dmHeapQ()


    def relax(self, u, v, w='length') :
        # Функция ослабления в соответствии с учебником
        ud = self.V[u]
        vd = self.V[v]
        ed = self.E[(u, v)]

        if vd['d'] > ud['d'] + ed[w] :
            vd['d'] = ud['d'] + ed[w]
            vd['prev'] = u 
            self.Q.add(v, vd['d'])

    def relax_condition(self, u, v, w='length', cond_name = "color") :
        # Функция ослабления в соответствии с учебником, но с добавлением условия
        # наличия цвета, то есть вершина будет ослабляться при случае, если
        # ее цвет (или другой атрибут) будет равен или меньше 0
        # Это дает возможность в графе закрыть пути

        ud = self.V[u]
        vd = self.V[v]
        if vd[cond_name] > 0 : return 
        ed = self.E[(u, v)]

        if vd['d'] > ud['d'] + ed[w] :
            vd['d'] = ud['d'] + ed[w]
            vd['prev'] = u 
            self.Q.add(v, vd['d'])

    def dijkstra(self, s) :
        if type(s) != tuple :
            s = self.get_element_nearest_vertex(s)
            
        self.initialize_single_source(s)

        S = set()
        self.Q.add(s, 0)
        # print(self.Q.pq)
        i = 0

        while self.Q.pq :
            i += 1
            try :
                u = self.Q.pop_task()
            except :
                print("Количество итераций {}".format(i))
                return
            S.add(u)

            try :
                for v in self.V[u]['edges_out'] :
                    self.relax(u, v, "length")
            except Exception as ex:
                print('ошибка при ослаблении вершины')
                print(ex)

    def check_branch(self, u) :
        # Выполняет обход ответвления
        # При этом не заходит на основную трассу 
        # возвращает элементы в последовательности

        pass



    def get_element_nearest_vertex(self, eid) :
        # Возвращает ближайшую вершину элемента после выполнения алгоритма
        # поиска минимального пути.
        # 
        #   
        if isinstance(eid, ElementId) :
            eid = eid.IntegerValue
        elif isinstance(eid, dmElement) :
            eid = eid.e.Id.IntegerValue
        
        vs = list(self.Ids[eid])
        # print(eid)
        # print(self.Ids[eid])
        if not vs : return None 
        # print(vs)
        try :
            res = min(vs, key = lambda x : self.V[x]['d'])
        except :
            res = next(iter(vs))
        return res 
        

    def get_shortest_path(self, u, name = 'prev', color_name = "color") :
        # возвращает последовательность вершин кратчайшего пути
        # после выполнения алгоритма поиска кратчайшего пути
        # кратчайший путь определяется по атрибуту name по умолчаюнию - prev

        for ud in self.V.values() :
            ud[color_name] = -1
        res = [u]

        
        while u :
            ud = self.V[u]
            if ud[color_name] == 0 : break 
            ud[color_name] = 0 
            v = ud['prev']
            if v is None : return res
            u = v 
            res.append(u)

        return res 






        

class dmCreateGraph(object) :
    def create_graph(self, p=None) :
        self.g = self.circuit.get_conduit_graph()
        self.g1 = dmGraph(self.g)
        print('граф составлен')

    def get_sequence(self) :
        #  Вычисляем последовательность включенного оборудования


        return




    def execute(self, LoadName = "ДПЛС 3") :
        print("Выполняем")
        # self.circuit = dmCircuit()
        self.circuit = dmCircuits().getByLoadName(LoadName)[0]

        # fe = self.circuit.find_fartherst_element()
        # print(fe)
        panel = self.circuit.panel 
        print('1')
        # sp = self.circuit.get_fartherst_element_path_elems()
   
        print(2)
        sequence = self.circuit.show_path_and_branches()



        print(3)
        
        self.g = self.circuit.g




            


        return 


    def reset_color(self, g = None) :
        # Сбрасываем настройки графики для элемента
        view = uidoc.ActiveView
        parts = set()
        if g is None :
            g = self.g 
        print(g)
        for v in g.V :
            print(v)
            try :
                parts.add(v[0])
            except :
                pass
        print("приступаем к раскраске")
        ogs = OverrideGraphicSettings()
        color = Color.InvalidColorValue
        ogs.SetProjectionLineColor(color)
        ogs.SetProjectionLineWeight(-1)
        with dm.trans(doc) :
            for eid in parts :
                view.SetElementOverrides(ElementId(eid), ogs)

    def show_elements(self, lst, color = None) :
        if color is None :
            color = Color(0,255,0)
        view = uidoc.ActiveView

        ogs = OverrideGraphicSettings()
        # color = Color.InvalidColorValue
        ogs.SetProjectionLineColor(color)
        ogs.SetProjectionLineWeight(5)

        with dm.trans(doc) :
            for eid in lst :
                view.SetElementOverrides(ElementId(eid), ogs)



    def show_shortest_path(self, g=None) :
        # Выведем на печать кратчайший путь к самому удаленному элементу
        elems = {}
        for e in self.circuit.elements :
            try :
                u = self.g.get_element_nearest_vertex(e.e.Id)
                if u is None : continue
                ud = self.g.V[u]
                elems[u] = ud
                print(u)
                print(ud)
            except :
                pass
        
        
        farthest = max(elems, key = lambda x : elems[x]['d'])
        print("Самый дальний эллемента {}".format(farthest))
        f_path = self.g.get_shortest_path(farthest)

        print("Наиболее удаленный элемент {}".format(farthest))
        parts = set()
        for u in f_path :
            print("{} : {}".format(u, self.g.V[u]['d']))
            parts.add(u[0])

        el_path = [f_path[-1][0]]
        for v in f_path[::-1] :
            if v[0] == el_path[-1] : continue
            el_path.append(v[0])
            print(v[0])


        

        # Составляем список элементов входящих в кратчайший путь
        # список элементов
        print("выводим путь")
        color = Color(0, 255, 0)
        self.show_elements(el_path, color)


    def _show_elements(self, lst, color=None) :
        # Раскрашивает список элементов заданным цветом
        #  lst - список Id в целочисленном значении
        if color is None :
            color = Color(0,255,0)
        view = uidoc.ActiveView
        ogs = OverrideGraphicSettings()
        ogs.SetProjectionLineColor(color)
        ogs.SetProjectionLineWeight(5)

        with dm.trans(doc) :
            for eid in lst :
                view.SetElementOverrides(ElementId(eid), ogs)


    def show_circuit_element_distance(self) :
        res = []

        for e in self.circuit.elements :
            eid = e.e.Id
            try :
                v = self.g.get_element_nearest_vertex(eid)
                if not v : continue
                
                d = self.g.V[v]['d']
                res.append((v,d))
            except :
                print("ошибка в элементе {}".format(e))
        res = sorted(res, key=lambda x : x[1])

        for u, d in res :
            print("{} : {}".format(u, d/dut))

        

    def show_infinite_vertex(self) :
        # Найдем и выведем вершины графа до которых далеко

        res = []

        for v in self.g.V :
            vd = self.g.V[v]
            if vd['d'] == float.PositiveInfinity :
                res.append((v, vd))
        print("Количество вершин с inf расстоянием: {}".format(len(res)))
        for vd in res :
            print("{} : {}".format(vd[0], vd[1]['d']))

    def show_zero_vertexes(self) :
        res = []

        for v in self.g.V :
            vd = self.g.V[v]
            if vd['d'] == 0 :
                res.append((v, vd))
        print("Количество вершин с 0 расстоянием: {}".format(len(res)))
        for vd in res :
            print("{} : {}".format(vd[0], vd[1]['d']))

            

        

    def show_vertexes (self) :
        for k in self.g.V :
            print(50*'-')
            print(k)
            v = self.g.V[k]
            for vv in v :
                print("{} : {}".format(vv, v[vv]))

    def show_edges(self) :
        for k in self.g.E :
            print(50 * '-')
            print(k)
            e = self.g.E[k]
            for ee in e :
                print("{} : {}".format(ee, e))

g = None 