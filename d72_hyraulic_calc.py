#  coding: utf-8 

import itertools
import collections
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

print("hydraulic calc")
import re

class Vertex(object) :
	def __init__(self, v, g) :
		self.name = v
		self.g = g
		pass
	def __repr__(self) :
		return "вершина {}".format(self.name)
class Edge(object) :
	def __init__(self, vv, g) :
		self.vv = vv
		self.g = g 
		pass 
class Graph(object) :
	def __init__(self) :
		self.V = {}
		self.E = {}
		self._connectors = {}
		self._new_v_num = 0

	def AddVertex(self, v) :
		self.V[v] = Vertex(v, self)
		return self.V[v]

	def AddEdge(self, e) :
		e_ = Edge()
		self.E[e[0]] = e_

	def AddConnector(self, c) :
		# Добавляем коннектор в граф как вершину 
		# print(c.ConnectorType)
		try :
			Id = c.Owner.Id.IntegerValue
			type_name =  c.Owner.Category.Name
			if not Id in self._connectors :
				# Если в словаре коннекторов не находится Id его обладателя, то такой коннектор точно отсутствует и можно создавать новый
				new_v_num = self._new_v_num
				self._new_v_num += 1
				vertex =  {"Id" : Id, 
							"type" : type_name,
							"origin" : c.Origin, 
							"Direction" : c.CoordinateSystem.BasisZ,
							"v" : new_v_num, 
							"edges" : set(), 
							"edges_in" : set()
							}
				self._connectors[Id] = {0: vertex}
			else :
				# В словаре коннекторов обладатель этого коннектора присутствует, и следовательно надо проверить, нет ли такого коннектора в списке

				found = False

				for c_i in self. _connectors[Id] :
					if self._connectors[Id][c_i]['origin'].IsAlmostEqualTo(c.Origin) :
						# Коннектор нашелся и просто возвращаем код вершины
						return self._connectors[Id][c_i]['v']
				
				new_v_num = self._new_v_num
				self._new_v_num += 1
				# Если не нашелся то надо создать новую запись:
				new_id = max(self._connectors[Id].keys()) + 1
				vertex = {"Id" : Id, 
							"type" : type_name,
						"origin" : c.Origin, 
						"Direction" : c.CoordinateSystem.BasisZ, 
						"v" : new_v_num, 
						"edges" : set(), 
						"edges_in" : set()}
				self._connectors[Id][new_id] = vertex


			self.V[new_v_num] = vertex

			return new_v_num 
		except Exception as ex:
			print("Ошибка в процедуре добавления коннектора")
			print(50*"-")
			print(ex)
			print(ex.args)
			print(50*"-")
			raise
			

	def GetConnectorVertex(self, c) :
		# Возвращает индекс вершины, которая связана с этим коннектором
		Id = c.Owner.Id
		origin = c.Origin

		for c_ in self._connectors[Id] :
			if origin.IsAlmostEqual(c_['origin']) :
				return  c_['v']

	def GetConnectorOfVertex(self, v) :
		return 



	def AddEdge(self, e) :
		#Добавляем ребро графа граф направленный

		self.V[e[0]]['edges'].add(e[1])
		self.V[e[1]]['edges_in'].add(e[0])
		self.E[e] = {}

	def GetEdges(self, v) :
		# возвращаем ребра которые выходят из вершины
		for e in self.V[v]['edges'] :
			yield (v, e)

	
	def GetEdges_in(self, v) :
		# возвращаем ребра которые входят в вершину
		for e in self.V[v]['edges_in'] :
			yield (e, v)

	def GetPredecessors(self, v) :
		return self.V[v]['edges_in'] 

	def GetSuccessors(self, v) :
		return self.V[v]['edges'] 
			


	def AddElement(self, e) :
		# добавляем коннекторы элемента в граф		
		vv = []
		сс = []
		for c1, c2 in get_connector_pairs(e) :
			try :
				v1 = self.AddConnector(c1)
				vv.append(v1)
				сс.append(c1)
			except :
				print("Ошибка при добавлении коннектора")
				raise
			if c1.IsConnected and c2.Domain == Domain.DomainPiping:		
				v2 = self.AddConnector(c2)
				self.AddEdge((v1, v2))
				self.E[(v1, v2)]["Id"] = -1
				self.E[(v1, v2)]["type"] = ""

				self.AddEdge((v2, v1))
				self.E[(v2, v1)]["Id"] =-1
				self.E[(v2, v1)]["type"] = ""
				
		if len(vv) > 1 :
			for v1, v2 in itertools.permutations(vv, 2) :
				e_ = (v1, v2)
				self.AddEdge(e_)
				self.E[e_]['Id'] = e.Id.IntegerValue
				self.E[e_]["type"] = e.Category.Name
				o1 = self.V[v1]['origin']
				o2 = self.V[v2]['origin']

				if e.Category.Name == "Трубы" :
					
					self.E[e_]['dn'] = e.Diameter / dut
					self.E[e_]['length'] = o1.DistanceTo(o2) / dut
					self.E[e_]['dh'] = (o2.Z - o1.Z) / dut

				if e.Category.Name == "Соединительные детали трубопроводов" :

					# Устанавливаем параметры для соединительных деталей
					diameter = сс[0].Radius * 2 / dut
					self.E[e_]['dn'] = diameter 
					self.E[e_]['length'] = 20 / diameter  
					self.E[e_]['dh'] = (o2.Z - o1.Z) / dut

				self.E[e_]['q'] = 1.

	def wfs(self, s) :
		# Выполнние поиска в ширину, возрврат - список  
		# s - стартовая вершина

		for v in self.V :
			self.V[v]['color'] = -1
			self.V[v]['d'] = float.PositiveInfinity
			self.V[v]['prev'] = None 

		self.V[s]['color'] = 0
		self.V[s]['d'] = 0
		self.V[s]['prev'] = None 
		q = collections.deque()
		q.append(s)
		_i=0
		while len(q) > 0 :
			print(len(q))
			
			_i += 1
			if _i > 10000 : 
				# raise
				break 

			u = q.pop()
	
			d = self.V[u]['d']


			for v in self.GetSuccessors(u) :
			

				if self.V[v]['color'] == -1 :
					self.V[v]['color'] = 0
					self.V[v]['d'] = d + 1
					self.V[v]['prev'] = u 
					q.append(v)
			self.V[u]['color'] = 1

	def initialize_single_source(self, s) :
		# выполняет процедуру инициализации для выполнения алгоритма Беллмана-Форда
		for v in self.V :
			self.V[v]["d"] = float.PositiveInfinity
			self.V[v]['prev'] = None 

		self.V[s]['d'] = 0

	def relax(self, e, w) :
		# Выполняет ослабление для заданного ребра и заданного веса ребра

		v, u = e 

		if self.V[v]['d'] > self.V[u]['d'] + w :
			self.V[v]['d'] = self.V[u]['d'] + w
			self.V[v]['prev'] = u 

	def Bellmann_Ford(self, s) :
		# Выполняет процедуру поиска кратчайших путей на графе 
		# выполнением алгоритма Беллмана-Форда
		self.initialize_single_source(s)
		for i in range(len(self.V)-1) :
			for e in self.E :
				self.relax(e, self.E[e]['dp'])

		for e in self.E :
			v, u = e 
			if self.V[v]['d'] > self.V[u]['d'] + self.E[e]['dp'] :
				return False

		return True  

				


	def edges(self) :
		for v in self.V :
			for e in self.GetEdges(v) :
				yield e
		
	def __repr__(self) :
		return "Граф"


def calc_edge_pressure_drop(g, e) :
	# Расчет потери давления на ребре графа, т.е. на участке трубопроводной сети

	K = {
		15. : 0.18,
		20. : 0.926,
		25 : 3.65,
		32 : 16.5,
		40 : 34.5,
		50 : 135, 
		65 : 517,
		80 : 1262,
		90 : 2725,
		100 : 5205,
		125 : 16940,
		150 : 43000,
	}

	try :
		ed = g.E[e]
		e_type = ed['type']
		dn = ed['dn']
		dh = ed['dh']
		q = ed['q']
		l = ed['length'] /1000
		v, u = e
	except :
		ed['dp'] = 0.00001
		return 0.00001
	
	dpl = q ** 2 * l / K[dn] / 100
	dp = dh / 1000 * 0.00980665012 + dpl 
	ed['dp'] = dp 

	return dp 




def get_connector_pairs(e) :
	# возвращает коннекторы элемента в парах с присоединенным коннектором
	Id = e.Id
	for c1 in get_connectors(e) :
		for c2 in c1.AllRefs :
			if c2.Owner.Id != Id :
				yield (c1, c2)


def get_connectors(e) :
	if hasattr(e, "ConnectorManager") :
		cc = e.ConnectorManager.Connectors 
	elif hasattr(e, "MEPModel") :
		cc = e.MEPModel.ConnectorManager.Connectors
	for c in cc :
			yield c

def connectors(e, s=None) :
	connectors = [c for c in get_connectors(e) if c.Domain == Domain.DomainPiping]
	if s : 
		connectors = [c for c in connectors if c.MEPSystem]
		connectors = [c for c in connectors if c.MEPSystem.Id == s.Id]

	return connectors

def get_connected_elements(e) :
	conns = get_connectors(e) 
	for c1 in conns :
		if not c1.IsConnected : continue
		for c2 in c1.AllRefs :
			if c2.Owner.Id != e.Id :
				if c2.Domain == Domain.DomainPiping :
					yield c2.Owner

def connected_elements(e) :
	return list(get_connected_elements(e))


def create_graph(start) :
	to_insert = [start.Id]
	inserted = []
	g = Graph()

	i = 0

	while len(to_insert) > 0 :
		i += 1
		if i > 500 : break 
		e = doc.GetElement(to_insert.pop())
		try :
			g.AddElement(e)
		except Exception as ex:
			print("ошибка при добавлении элемента {} Id : {}".format(i, e.Id))
			print(ex)
		inserted.append(e.Id)

		for e1 in get_connected_elements(e) :
			if e1.Id in inserted :				
				continue
			if e1.Id in to_insert :
				continue

			to_insert.append(e1.Id)

	return  g


def get_sprinklers(g) :
	"""
	***************************************************************
	* Вычисляет вершины которые соответствуют спринклерам
	* 
	* 
	***************************************************************
	"""
	res = []
	for v in g.V :
		if g.V[v]['type'] == "Спринклеры" :
			res.append(v)

	return res

def get_calc_results(g, sprinkler_list, k=0.27, p = 0.1, ) :
	"""
	***************************************************************
	* Выполнение гидравлического расчета 
	* на входе 
	* g - граф
	* sprinkler_list - список спринклеров которые будут рассчитываться (список Id )
	* k - коэффициент расхода спринклеров
	* P - минимальное давление на диктующем спринклере
	***************************************************************
	"""

	return 

def get_opposite_connector(c) :
	for c1 in c.AllRefs :
		if (c1.Owner != c.Owner) and (c1.Domain == Domain.DomainPiping) :
			return c1


def put_text(text = "test text", p = None) :
	av = uidoc.ActiveView

	if p is None :
		text_loc = uidoc.Selection.PickPoint("Покажи точку вставки текста")
	else :
		text_loc = p 

	def_text_type_id = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)
	opts = TextNoteOptions(def_text_type_id)

	with dm.trans(doc) :
		text_note = TextNote.Create(doc, av.Id, text_loc, 50 * dut, text, opts)

def show_graph_data(g) :
	for eid in g._connectors :
		try :
			e = doc.GetElement(ElementId(eid))
			c = g._connectors[eid][0]
			origin = c['origin']
			v = c['v']

			d = g.V[v]['d']
			#p = g.V[v]['dp']

			text = "Вершина {}\n d : {}\n dp".format(v, d,)
			put_text(text, origin)
		except :
			raise
			pass

def show_shortest_path_data(g, s) :
	v = s
	_i=0
	path = []
	
	while not v is None :
		
		_i += 1
		if _i > 1500 : break 
		sd = g.V[v]
		d = sd['d']
		p = sd['origin']
		u = sd['prev']

		
		if u is None : break
		e = (u, v)
		ed = g.E[e]
		try :
			dp = ed['dp']
			
		except : 
			dp = 0
			dh = 0
		try :
			dh = ed['dh']
		except :
			dh =0 
		text = "Вершина {} d : {}, ребро dp = {} dh = {}".format(v, d, dp, dh)
		path.append(text)
		put_text(text, p)

		v = u

		

	t = "\n".join(path)

	put_text(t, p)



class dmCalcGraph(object) :
	def __init__(self, system) :
		# Граф представляется словарям 

		"""
		***************************************************************
		* вершина - это словарь в словаре. вершины  индексируются в словаре
		* может быть любое значение но подразумевается что это целое число
		* которым нумеруют коннекторы
		* вершина  это словарь, который может иметь любые поля но  обязательные :
		* связь со словарем коннекторов:
		* Id - номер элемента
		* conn_num - номер коннектора
		* origin - XYZ - точка расположение коннектора
		* Информация о точке
		* q  - поток в точке
		* p - давление в точке
		* k -  коэффициент расхода, для вычисления количества выходящей воды - это для вершин, которые являются спринклерами. 
		* 		спринклера будут листьями в дереве и расход в точке спринклера будет формироваться для счет  вычисления по формуле q=10*K*SQRT(p)
		* dn - диаметр коннектора
		* Информация по графу:
		* edges - исходящие ребра - множество соседних вершин, к которым направлены  ребра в эту вершину
		* edges_in - входящие ребра - множество соседних вершин, от которых направлены ребра в эту вершину
		* поля для работы при расчетах
		* right - следующая вершина при движении от узла управления к спринклеру  основной поток, 
		* left - следующая вершина при движении воды от узла управления к спринклеру - ответвление, второстепенная ветка, если вершина соединяется с одной 
				последующим узлом, то left = None

		* prev - это указатель на  предыдущуу вершину при работе алгоритмов построения деревьев и расчетов
		* d - расстояние при работе алгоритмов поиска в ширину и глубину
		* f - время закрытия вершины для алгоритмов поиска в глубину

		{
			"Id: : ,
			"conn_num" : ,
			"origin" : ,
			"q" : 1.0,
			"p" : float.PositiveInfinity,
			"dn" : 0,
			"k" : 0,
			"edges" : set(),
			"edges_id" : set(),
			"right" : None,
			"left" : None,
			"prev" : None,
			"d" : 0,
			"f" : 0,
		}


		***************************************************************
		"""
		self.V = {}
		"""
		***************************************************************
		* Ребра хранятся в поле self.E - словарь. ключами являеются крртежи (v, u)
		* ребро представленно как словарь  значения:
		* dn - диаметр
		* length - длина эквивалентная длина фитинга или трубы
		* q - поток по ребру
		* dh - перепад высоты по ребру и
		* dph - перепад гидрастатического давления
		* dp - потеря давления ребре
		* 
		***************************************************************
		"""
		self.E = {}
		# Словарь для хранения информации о коннекторах в графе
		"""
		***************************************************************
		* структура хранения информации о коннекторах
		* словарь - индексируется по Id элемента
		* в словаре хранятся словари, которые индексируются целым числом начинаяс 0.
		* каждый элемент словаря также является словарем который в себе содержит информацию о 
		* коннекторе: 
		* owner_id - Id элемента, 
		* origin - коннектора и 
		* basisZ коннектора - для ориентации в пространстве а также номер вершины, которой 
		* коннектор представлен в графе. для нумерации вершин есть поле 
		* v - номер вершины  которая представляет коннектор
		* next_vertex_num - номер последующей вершины, который будет присвоен вершине и 
		***************************************************************
		"""
		self._connectors = {}
		self.system = system
		self._get_main_gate()
		self._get_sprinklers()
		self.next_vertex_num = 0

	def _get_main_gate(self) :
		# Поиск узла управления системы

		accessories = []
		self.main_gate = None

		for e in self.system.PipingNetwork :
			if e.Category.Name == 'Арматура трубопроводов' :
				print(e.Category.Name)
				accessories.append(e)
			if e.Category.Name == "Оборудование" :
				accessories.append(e)

		for e in accessories :
			if e.LookupParameter("DM_Узел управления ПТ").AsInteger() :
				self.main_gate = e 
				print("Id узла управления = Id({})".format(e.Id.IntegerValue))
				return e

	def _get_sprinklers(self) :
		self.sprinklers = []
		self.sprinkler_critical = None 

		for e in self.system.PipingNetwork :
			if e.Category.Name == "Спринклеры" :
				if e.LookupParameter("DM_Спринклер_учитывать").AsInteger() :
					self.sprinklers.append(e) 

				if e.LookupParameter("DM_Спринклер_диктующий").AsInteger() :
					print("Найден диктующий спринклер")
					self.sprinkler_critical = e 

	def _add_connector_as_vertex(self, c) :
		# Ищет коннектор в словаре коннекторов и если не находи , то 
		# Создает запись в словаре коннекторов 
		# возвращает номер вершины которая представляет коннектор

		if c is None :
			return -1

		owner_id = c.Owner.Id.IntegerValue
		v_found = False 

		if not owner_id in self._connectors :
			# если в словаре нет элемента с таким Id то создаем запись
			v = self.next_vertex_num
			self.next_vertex_num += 1

			con_data = {
				"owner_id" : owner_id,
				"v" : v,
				"origin" : c.Origin,
				"basisz" : c.CoordinateSystem.BasisZ,
				'connector' : c
			}
			self._connectors[owner_id] = {
				0 : con_data
				}
			i = 0

			 

		else :
			# Если такой элемент уже существует, пытаемся найти коннектор
			e_conns = self._connectors[owner_id]
			
			for i  in e_conns :
				con_data = e_conns[i]

				if c.Origin.IsAlmostEqualTo(con_data['origin']) :
					# Коннектор найден берем номер вершины
					v = con_data['v']
					v_found = True 
			
			if not v_found :
				# если вершину найти не удалось то создаем новую вершину
				i += 1
				v = self.next_vertex_num
				self.next_vertex_num += 1

				e_conns[i] = {
					"owner_id" : owner_id,
					"v" : v,
					"origin" : c.Origin,
					"basisz" : c.CoordinateSystem.BasisZ,
					'connector' : c
				}


		if not v_found :
			self.V[v] = {
				"Id": owner_id ,
				"conn_num" : i,
				"origin" : c.Origin,
				"q" : 1.0,
				"p" : float.PositiveInfinity,
				"dn" : c.Radius * 2 / dut,
				"k" : 0,
				"edges" : set(),
				"edges_in" : set(),
				"right" : None,
				"left" : None,
				"prev" : None,
				"d" : 0,
				"f" : 0,
				'v' : v,
				'connector' : c 

			}

		return v
			

	def _add_edge(self, e) :
		# Добавляем ребро в граф

		# Проверяем нет ли этого ребра в графе:

		if e in self.E : return 

		v, u = e
		# Проверяем есть ли вершины
		if not v in self.V or not u in self.V : return 

		self.V[v]['edges'].add(u)
		self.V[u]['edges_in'].add(v)

		# Такого ребра нет.
		# Добавляем ребро в словарь

		e_data = {
			"dn" : 0,
			"length" : 0,
			"dh" : 0,
			"pdh" : 0,
			'dp' : 0,
		}

		self.E[e] = e_data
		# добавляем в вершины информацию о входящих и исходящих ребрах

		return e_data

	def AddElement(self, e) :
		# Добавляет элемент в качестве участка графа: добавляет каждый коннектор элемента как вершину
		# и создает связци в виде ребер со своими с сопредельными коннекторами

		# берем коннекторы в элементе
		# создаем вершины графа для коннекторов, если для коннектора вершины не было, если была, то не создаем и используем существующую
		# определяем для н

		if  True : #e.Category.Name == "Спринклеры" :
			# Коннекторы

			conns1 = connectors(e, self.system)
			
			vv1 = [(self._add_connector_as_vertex(c), c) for c in conns1]
			vv1_ = [c1[0] for c1 in vv1]
			conns2 = [get_opposite_connector(c) for c in conns1]
			vv2 = [(self._add_connector_as_vertex(c), c) for c in conns2]
			
			for ((v, c1), (u, c2)) in zip(vv1, vv2) :
				self._add_edge((v,u))
				self._add_edge((u,v))
			
			for e in itertools.permutations(vv1_, 2) :
				# print(e)
				self._add_edge(e)

		
		if  False : # e.Category.Name == "Арматура трубопроводов" :
			# Коннекторы
			print("Арматура")

			conns1 = connectors(e)
			print(1)
			vv1 = [(self._add_connector_as_vertex(c), c) for c in conns1]
			print(2)
			conns2 = [get_opposite_connector(c) for c in conns1]
			print(3)
			vv2 = [(self._add_connector_as_vertex(c), c) for c in conns2]
			print(4)

			
			for ((v, c1), (u, c2)) in zip(vv1, vv2) :
				self._add_edge((v,u))
				self._add_edge((u,v))

	
	def wfs(self, s) :
		# выполнение поиска в ширину
		print("wfs {}".format(s))

		q = collections.deque()

		for v in self.V.values() :
			v['color'] = -1
			v['d'] = float.PositiveInfinity
			v['prev'] = None 

		v = self.V[s]
		v['color'] = 0
		v['d'] = 0
		q.append(s)

		while len(q) > 0 :
			u = q.popleft()
			# print(u)
			u_data = self.V[u]
			for v in self.V[u]['edges'] :
				v_data = self.V[v]
				if v_data['color'] == -1 :
					v_data['color'] = 0
					v_data['d'] = u_data['d'] + 1
					v_data['prev'] = u
					q.append(v)
					

	def _find_leaves(self) :
		# Находит листья графа - то есть вершины которые являются конечными
		# Листом назовем вершину, из которой можно уйти только в ту же вершину, из которой пришел, либо вообще никуда
		# то есть вершина будет листом если у нее только один сосед

		leaves = []

		for v in self.V :
			# print(self.V[v]['edges'], self.V[v]['edges_in'])
			if len(self.V[v]['edges']) == 1 and self.V[v]['edges'].issubset(self.V[v]['edges_in']) :
				# print("добавляем")
				leaves.append(v)
			
		return leaves

	leaves = property(_find_leaves)

	def _find_main_gate_leaf(self) :
		
		# Найдем вершины узла управления

		vv = [c['v'] for c in self._connectors[self.main_gate.Id.IntegerValue].values()]

		res = list(set(self.leaves).intersection(set(vv)))[0]

		return res

	main_gate_leaf = property(_find_main_gate_leaf)

	def _find_sprinkler_leaves(self) :
		# Находим вершины спринклеров, 0 позиция - это диктующий спринклер
		c_v = self.get_vertexes(self.sprinkler_critical)[0]

		res = []
		for s in self.sprinklers :
			v = self.get_vertexes(s)
			res.extend(v)

		res.remove(c_v)
		res = [c_v] + res 
		return res


	sprinkler_vertexes = property(_find_sprinkler_leaves)

	
	def get_vertexes(self, e) :
		# Возвращает вершины которые принадлежат элементу

		conns = self._connectors[e.Id.IntegerValue]

		res = [c['v'] for c in conns.values()]
		return res

	def get_path_prev(self, main_gate, v) :
		# Выполняет проход по дереву prev
		# print(50*"*")
		# print("печать пути начало")

		# Строим дерево предшествования от main_gate
		self.wfs(main_gate)

		# Выполняем проход от вершины к корню

		if v == 0 :

			print("Печатаем путь к {} от {}".format(main_gate, v))
		i = 0 
		
		path = [v]
		while not v is None :
			
			v = self.V[v]['prev']
			if v is None :
				print("v none") 
				break
			
			path.append(self.V[v]['v'])

		return path


	def show_vertex_num(self) :
		# выводим на экран номер вершин

		for v in self.V.values() :
			print(v['v'], v['origin'])
			put_text(str(v['v']), v['origin'])

	def show_sprinkler_num (self) :
		for vn in self.sprinkler_vertexes :
			v = self.V[vn]
			# print(v['v'], v['origin'])
			s = "{}\n".format(v['v']) + "q = {} л/с\np = {} МПа".format(v['q'], v['p'])
			put_text(s, v['origin'])


	def set_precalc_data(self) :
		# Устанавливаем инициирующией данные для расчета и вычисления последовательности расчетов
		# 
		# 

		# Устанавливаем данные в ребрах.

		def set_edges() :
			for e in self.E :
				de = self.E[e]

				v,u = e

				dv = self.V[v]
				du = self.V[u]
				

				if dv['Id'] == du['Id'] :
					# случай когда ребро соединяет точки внутри одного элемента
					elem = doc.GetElement(ElementId(dv['Id']))
					try :
						parttype = elem.MEPModel.PartType

					except :
						parttype = "труба"

					print(" {} Ребро внутри элемента {} {} {} {}".format(e, dv['Id'], du['Id'], elem.Category.Name, parttype))

					
					if elem.Category.Name == "Трубы" :
						de['length'] = dv['origin'].DistanceTo(du['origin'])
						de['dn'] = elem.Diameter / dut
						de['dh'] = (du['origin'].Z - dv['origin'].Z) / dut / 1000
						de['pdh'] = de['dh'] * 0.009806

					elif elem.Category.Name == "Соединительные детали трубопроводов" :
						print("Соединительные делаем {}".format(elem.MEPModel.PartType))
						if elem.MEPModel.PartType == PartType.Elbow:
							print("отвод")
							de['length'] = 30 / dv['dn']
							de['dn'] = dv['dn']
							de['dh'] = (du['origin'].Z - dv['origin'].Z) / dut / 1000
							de['pdh'] = de['dh'] * 0.009806 if de['dh'] > 0.001 else 0
						elif elem.MEPModel.PartType == PartType.Tee :
							print("тройник")
							de['length'] = 30 / dv['dn']
							de['dn'] = dv['dn']
							de['dh'] = (du['origin'].Z - dv['origin'].Z) / dut / 1000
							de['pdh'] = de['dh'] * 0.009806 if de['dh'] > 0.001 else 0
				else :
					print("{} Ребро соединяет элементы {} {}".format(e, dv['Id'], du['Id']))

					pass
				print(de)

			
		def set_nodes() :
			for s in self.sprinkler_vertexes :
				v_data = self.V[s]
				Id = v_data['Id']

				try :
					elem = doc.GetElement(ElementId(Id))
					v_data['k'] = elem.LookupParameter("DM_Коэффициент расхода").AsDouble()
				except :
					v_data['k'] = 0.07
		set_edges()
		set_nodes()


		# Устанавливаем данные в вершинах


	def calc_edge(self, e) :
		v, u = e 
		K = {
		
		15. : 0.18,
		20. : 0.926,
		25. : 3.65,
		32. : 16.5,
		40. : 34.5,
		50. : 135, 
		65. : 517,
		80. : 1262,
		90. : 2725,
		100. : 5205,
		125. : 16940,
		150. : 43000,
	}

		e_data = self.E[e]



		e_data['q'] = self.V[u]['q']
	
		if e_data['dn'] != 0 :
			e_data['dpl'] = e_data['q'] ** 2 * e_data['length'] / (100 * K[e_data['dn']])
		else :
			e_data ['dpl'] = 0
	
		e_data['dp'] = -e_data['pdh'] - e_data['dpl']
	

	def prepare_calc(self, base_node) :
		self.wfs(base_node)

		for v in self.V.values() :
			v['sequence_start'] = -1
			v['next_left'] = None
			v['next_right'] = None 
			v['k'] = 0

		for s in self.sprinkler_vertexes :
			v = s 
			v_prev = None 
			

			while v != None :
				v_data = self.V[v]
				if v_data['sequence_start'] != -1 :
					v_data['next_right'] = v_prev 
					break 
				v_data['sequence_start'] = s 
				v_data['next_left'] = v_prev
				v_prev = v 
				if v == base_node : break 
				v = v_data['prev']

	def calc_sequence(self, base_node, sequence_start, p0) :
		"""
		***************************************************************
		* Выполнение расчета последовательности узлов
		* p0 - давление которое задается в начальной точке последовательности
		* 
		***************************************************************
		"""

		v = sequence_start 
		self.V[v]['p'] = p0 

		max_delta_p = 0.001

		print(58*"-")
		print("начинаем расчет")


		while not v is None :
			print(v)
			dv = self.V[v]
			u = dv['next_left']
			o = dv['next_right']
			q1 = 0
			lq = 0
			q0 = 0
			
			if dv['sequence_start'] == sequence_start :
				print("{} : dv['sequence_start'] == sequence_start = {}".format(v, dv['sequence_start']))

				print("u = {}".format(u))
				if not u is None :
					du = self.V[u]
					e = (v, u)
					lq = du['q']
					try : 
						self.calc_edge(e)
					except :
						print("calc_edge")
						print(e)
						print(self.E[e])
						raise
					try :
						de = self.E[e]
						lq = du['q'] 
						dv['p'] = du['p'] - de['dp']
					except :
						print("ошибка 1")
						raise
				
				if not o is None :
					print('not o is None')
					# Если точка узловая
					do = self.V[o]
					e1 = (v, o)
					de1 = self.E[e1]
					cnt1 = 0
					right_sequence_start = do['sequence_start']
					rsp = self.V[right_sequence_start]
					dp1 = float.PositiveInfinity
					self.calc_sequence(o, right_sequence_start, 0.1)
				
					while dp1 > max_delta_p :
						cnt1 += 1
						if cnt1 > 10 :
							print("Не удалось выполнить увязку, разница в давлении {}".format(11))
							break
						self.calc_edge(e1)
						print(do)
						q1 = do['q']
						p1 = do['p'] - de1['dp']
						dp1 = p1 - dv['p']
						print("p1 = {}, dv[p] = {} dp1={}".format(p1, dv['p'], dp1))
						
						print("dp1 = {} max_delta_p = {}".format(dp1, max_delta_p))
						if abs(dp1) > max_delta_p :
							upd_p = rsp['p'] - dp1
							if upd_p < 0 :
								upd_p = 0.01
							print("Перед вызовом расчета ветки. upd_p = {}".format(upd_p)) 
							self.calc_sequence(o, right_sequence_start, upd_p)

					print('not o is None выполнен')
					

				print('1')
				try :
					if dv['k'] > 0 :
						q0 = 10 * dv['k'] * dv['p'] ** 0.5
				except :
					print("dv[k] = {}, dv[p] = {} ".format(dv['k'], dv['p']))
					print('не найден k')
					raise

				print("{} : lq = {}, q0 = {}, q1 = {}".format(v, lq, q0, q1))



				dv['q'] = lq + q0 + q1 
				print("dv = {}".format(dv))

				if v == base_node : 
					break 
				try :
					v = dv['prev']
				except :
					print("ошибка v = dv['prev']")
					raise
			else :
				break 



	def calculation(self) :
		# Выполнение гидравлического расчета
		self.wfs(self.main_gate_leaf)

		"""
		***************************************************************
		* Выполняем предварительный обход графов от спринклера до узла управления
		* массив sprinkler_vertexes - содержит номера вершин каждого спринклер
		* при предварительном обходе выполняем действия 
		* устанавливаем атрибут left - указатель на вершину предыдущую расчету
		***************************************************************
		"""

		# Необходимо пометить пути обхода дерева при расчете
		# для каждого спринклера
		# рабочие поля 
		# 
		pass 

	def __repr__(self) :
		s = ""
		try :
			s = "Граф гидравлического расчета системы : {}".format(self.system.Name)
		except : pass 

		try :
			s += "\nКоличество спринклеров : {}".format(len(self.sprinklers))
		except : pass
		try :
			s += "\nДиктующий ороситель Id {}".format(self.sprinkler_critical.Id)
		except : pass 
		return s 
def create_graph_2(pipe) :
	p_system = pipe.MEPSystem

	g = dmCalcGraph(p_system)
	return g




	



