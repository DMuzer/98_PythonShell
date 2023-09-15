#  coding: utf-8 


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

print('структурная схема')

clr.AddReferenceByPartialName("System.Windows.Forms")
clr.AddReferenceByPartialName("System.Drawing")
clr.AddReferenceByPartialName("IronPython")
clr.AddReferenceByPartialName("Microsoft.Scripting")

from Autodesk.Revit.UI import ExternalEvent, IExternalEventHandler

from System.Drawing import Size
from System.Windows.Forms import Form, Application

import IronPython
import System.Drawing as Drawing
import System.Windows.Forms as Forms 


f1 = None

class dmExEvent(IExternalEventHandler) :
    def Execute(self, app) :
       
        print("Вызов")
        set_time()

    def GetName(self) :
		return "Обработка внешнего события"


class dmPanel(object) :
	def __init__(self, e) :
		self.e = e 

	def _get_ugo_type(self) :
		try :
			eid = self.e.LookupParameter("DM_Семейство УГО").AsElementId()
		except :
			eid = ElementId(-1)
			
		return eid 

	udo_type = property(_get_ugo_type)

	def __repr__(self) :
		return "Панель {} Id {}".format(self.e.Name, self.e.Id)

class dmUpdateAnnotationLink(IExternalEventHandler) :
    def Execute(self, app) :
		global update_link_data
		while len(update_link_data) > 0 :
			e = update_link_data.pop()
			e.update()
    def GetName(self) :
		return "Обновление значений меток"

# Переменная для вызова и обновления атрибутов
update_link_data = []

class dmCreateCircuitLabelHandler(IExternalEventHandler) :
    def Execute(self, app) :
		print("Обработчик создания новой метки")

		uidoc.ActiveView = f1.ActiveView
		if not f1.circuit_annotation_type :
			return 

		try :
			circuit_id = f1.circuits[f1.system_box.SelectedNode.Text].Id.IntegerValue
			print("Id цепи".format(circuit_id))
		except :
			try :
				circuit_id = f1.devices[f1.system_box.SelectedNode.Text].Id.IntegerValue
				print("Id оборудования".format(circuit_id))

			except Exception as ex:
				print("Не найдено оборудование")
				print(ex)
				return 

		

		print(f1.circuit_annotation_type)
		print(f1.ActiveView)

		
		while True :
			try :
				pnt = uidoc.Selection.PickPoint()
			except :
				break 

			with dm.trans(doc) :
				ansym = doc.Create.NewFamilyInstance(pnt, f1.circuit_annotation_type, uidoc.ActiveView)
				ansym.LookupParameter('DM_Связанный_элемент_ID').Set(circuit_id)

			ansym_ = dmAnnotationTag(ansym)
			ansym_.update()
			
    def GetName(self) :
		return "Создание метки для цепи"


class dmAnnotationTag(object) :
	def __init__(self, e) :
		self.element = e

	def _check_link(self) :
		# Проверяем наличие атрибута DM_Связанный_элемент_ID

	
		link_param = self.element.LookupParameter("DM_Связанный_элемент_ID")
		if link_param :
			return True 

		return False

	def _get_linked_element(self) :
		linked_param = self.element.LookupParameter("DM_Связанный_элемент_ID")
		return doc.GetElement(ElementId(linked_param.AsInteger()))
	linked_element = property(_get_linked_element)

	def update(self) :
		from time import localtime, strftime
		le = self.linked_element
		print('Обновление')

		with dm.trans(doc) :
			mark_param = self.element.LookupParameter("ADSK_Марка")

			if type(le) == Electrical.ElectricalSystem :
				# Еслии электрическая система
				print("обновление цепи")
				cable_type = le.LookupParameter("Марка проводника_Электрические цепи").AsString()
				cable_len = le.LookupParameter("Длина").AsDouble()/dut / 1000
				coef_spare = le.LookupParameter("Запас проводника_Электрические цепи").AsInteger() 
				additional_spare = le.LookupParameter("Запас на разделку проводника_Электрические цепи").AsDouble() / dut / 1000
				cable_len = cable_len * (1 + coef_spare/100) + additional_spare * len(list(le.Elements))
				panel_name = le.LookupParameter("ADSK_Имя панели").AsString()
				line_num = str(le.LookupParameter("ADSK_Номер линии").AsInteger())

				mark_str = "{}.{}\n{} - {:.0f} м".format(panel_name, line_num, cable_type, cable_len)
				print(mark_str)

				print("coef_spare : {}, additional_spare : {} количество устройство в цепи {}".format(coef_spare, additional_spare, len(list(le.Elements))))

				print(50*"-")

				if mark_param :
					mark_param.Set(mark_str)
			elif type(le) == FamilyInstance :
				if le.Category.Name == "Электрооборудование" :
					print("Электрооборудование")

					dev_mark = le.LookupParameter("Марка").AsString()


					mark_str = "{}".format(dev_mark)

					if mark_param :
						mark_param.Set(mark_str)


				





	hasLink = property (_check_link)


def get_panels()  :
	fc = FilteredElementCollector(doc).OfClass(Electrical.ElectricalSystem).ToElements()

	for e in fc :
		yield dmPanel(e)

class dmForm(Forms.Form) :
	def Btn1Click(self, *args) :
		print("Вставка обозначения")
		self.createNewCircuitTagEvent.Raise()

		

	def SelectSchemeView(self, s, e) :

		self.ActiveView = self.view_list[s.SelectedItem]
		print("Выбор вида схемы")
		print(self.ActiveView.Name)

	def _create_view_list(self) :
		self.comboBox1 = Forms.ComboBox()
		self.comboBox1.Size = Drawing.Size(300, 30)
		self.comboBox1.Location = Drawing.Point(20, 50)
		self.Controls.Add(self.comboBox1)

		fc = FilteredElementCollector(doc).OfClass(ViewDrafting).ToElements()
		self.view_list = {e.Name : e for e in fc}
		for item in self.view_list :
			self.comboBox1.Items.Add(item)

		

		self.comboBox1.SelectedIndexChanged += self.SelectSchemeView
		self.comboBox1.SelectedItem = list(self.view_list.keys())[-1]


		self.label1 = Forms.Label()
		self.label1.Size = Drawing.Size(300, 20)
		self.label1.Location = Drawing.Point(20, 20)
		self.label1.Text = "Для вставки используеется вид"
		self.Controls.Add(self.label1)
		

	def _circuit_select(self, sender, e) :

		sel_node = sender.SelectedNode.Text
		print(sel_node)

		if sel_node in self.circuits :
			circuit = self.circuits[sel_node]
			
			self.Label_Circuit_Name.Text = sel_node + " : " +  str(circuit.Id)

		else :
			self.Label_Circuit_Name.Text = "-------"
		pass 


	def _create_system_list(self) :
		# Создание бокса с системами и оборудованием
		self.system_box = Forms.TreeView()
		self.system_box.Location = Drawing.Point(30, 80)
		self.system_box.Size = Drawing.Size(300, 500)
		self.Controls.Add(self.system_box)
		self.system_box.AfterSelect += self._circuit_select

		self.Label_Circuit_Name = Forms.Label()
		self.Label_Circuit_Name.Location = Drawing.Point(400, 50)
		self.Label_Circuit_Name.Size = Drawing.Size(300, 30)
		self.Label_Circuit_Name.Text = "Название цепи"
		self.Controls.Add(self.Label_Circuit_Name)


		fc = FilteredElementCollector(doc).OfClass(Electrical.ElectricalSystem).ToElements()
		self.circuits = {}
		self.devices = {}

		
		


		for e in fc :

			if not e.SystemType in self.circuits.keys() :
				self.circuits[e.SystemType] = {}
			
			syst_dict = self.circuits[e.SystemType]
			if not e.PanelName in syst_dict :
				syst_dict[e.PanelName] = [e]
			else :
				syst_dict[e.PanelName].append(e)
			self.devices[e.PanelName] = e

			
		for st in sorted(self.circuits) :
			node1 = self.system_box.Nodes.Add(str(st))

			for pn in sorted(self.circuits[st]) :
				node2 = node1.Nodes.Add(str(pn))
				for c in self.circuits[st][pn] :				
					pn = c.LookupParameter("ADSK_Имя панели").AsString()
					nl = c.LookupParameter("ADSK_Номер линии").AsInteger()
					
					c_pos = ""
					if pn :
						c_pos += pn 

					if nl :
						c_pos += "." + str(nl	)

					circ_node = node2.Nodes.Add(c_pos)
					self.circuits[c_pos] = c

					for el in c.Elements :
						el_M = el.LookupParameter("Марка").AsString()
						circ_node.Nodes.Add(el_M)
						self.devices[el_M] = el 
						



			#self.system_box.Nodes.Add(c_pos)

	def btn2Click(self, *args) :
		print("Выполнение обновления ЦБК")
		global update_link_data

		fc = FilteredElementCollector(doc, self.ActiveView.Id).OfCategory(bic.OST_GenericAnnotation).WhereElementIsNotElementType().ToElements()

		update_link_data = []
		for e in fc :
			e1 = dmAnnotationTag(e)
			
			if e1.hasLink :
				update_link_data.append(e1)

		self.UpdateEvent.Raise()
		

	def _create_buttons(self) :
		btn1 = Forms.Button()
		btn1.Size = Drawing.Size(80, 30)
		btn1.Location = Drawing.Point(50, 720)
		btn1.Text = 'Разместить\nЦБК'
		btn1.Click += self.Btn1Click
		self.Controls.Add(btn1)


		btn2 = Forms.Button()
		btn2.Size = Drawing.Size(80, 30)
		btn2.Location = Drawing.Point(150, 720)
		btn2.Text = 'Обновить\nЦБК'
		btn2.Click += self.btn2Click
		self.Controls.Add(btn2)

	def _select_circuit_annotation_type(self, *args) :
		self.circuit_annotation_type = self._circuit_annotation_types[self.listBox_annotation_type.SelectedItem]
		print(self.listBox_annotation_type.SelectedItem)
		pass 


	def _create_annotation_type_list(self) :
		self.listBox_annotation_type = Forms.ComboBox()
		self.listBox_annotation_type.Size = Drawing.Size(300, 20)
		self.listBox_annotation_type.Location = Drawing.Point(370,100)
		

		fc = FilteredElementCollector(doc).OfCategory(bic.OST_GenericAnnotation).WhereElementIsElementType().ToElements()
		self._circuit_annotation_types = {}
		for e in fc :
			self.listBox_annotation_type.Items.Add(Element.Name.GetValue(e))
			self._circuit_annotation_types[Element.Name.GetValue(e)] = e

		self.listBox_annotation_type.SelectedIndexChanged += self._select_circuit_annotation_type
		self.Controls.Add(self.listBox_annotation_type)
		

		lb2 = Forms.Label()
		lb2.Text = "Семейство для создания меток с цепями"
		lb2.Location = Drawing.Point(370, 80)
		lb2.Size = Drawing.Size(300, 20)
		self.Controls.Add(lb2)
		

	
	def create_form(self) :
		self.Size = Drawing.Size(800, 800)

		# Создаем обработчик события для обновления меток

		self.AnnUpdatningEventHandler = dmUpdateAnnotationLink()
		self.UpdateEvent = ExternalEvent.Create(self.AnnUpdatningEventHandler)

		self.CreateNewCircuitTagHandler = dmCreateCircuitLabelHandler()
		self.createNewCircuitTagEvent = ExternalEvent.Create(self.CreateNewCircuitTagHandler)



		self._create_view_list()
		self._create_system_list()
		self._create_buttons()
		self._create_annotation_type_list()




f1 = None 

def create_form() :
	global f1 
	f1 = dmForm()
	f1.create_form()
	

	f1.Show()

	return f1 

create_form()
