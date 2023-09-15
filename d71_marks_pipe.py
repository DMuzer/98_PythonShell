#  coding: utf-8 




from Autodesk.Revit import *
from Autodesk.Revit.DB import *

import Autodesk.Revit.UI as UI

import math, sys
import clr



clr.AddReferenceToFileAndPath(r"C:\Users\Дмитрий\NetTopologySuite.2.4.0\lib\netstandard2.0\NetTopologySuite.dll")
import NetTopologySuite as nts
import NetTopologySuite.Geometries as nts_geom


clr.AddReferenceByPartialName("System.Windows.Forms")
clr.AddReferenceByPartialName("System.Drawing")
clr.AddReferenceByPartialName("IronPython")
clr.AddReferenceByPartialName("Microsoft.Scripting")

from System import Drawing
from System.Windows import Forms



lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
	sys.path.append(lib_path)


pi2 = math.pi * 2

dut = 0.0032808398950131233

	
bic = BuiltInCategory
bip = DB.Structure.StructuralType
nonstr = bip.NonStructural
ot = UI.Selection.ObjectType

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

	
import dm_connect_2 as dm
import dm_nearest_geometry as dm1

reload(dm)	
reload(dm1)

def CreateTag(self, pipe) :
    try : 
        print("т.1.")

        lc = pipe.Location.Curve
        p0 = lc.Evaluate(0.5, True)

        tr1 = Transaction(doc)
        tr1.Start("Adding pipe tags")
        print("---")

        try :
            pipe_ref = Reference(pipe)

            tag = IndependentTag.Create(doc, 
                                        self.ActiveTagType.Id, 
                                        uidoc.ActiveView.Id, 
                                        pipe_ref, 
                                        True,
                                        TagOrientation.Horizontal,
                                        p0
                                        )

            tr1.Commit()
        except Exception as ex:
            print(ex)

            tr1.RollBack()
    except  Exception as ex :
        print(ex)



class dmForm(Forms.Form) :
    def init_form(self) :
        self.add_combo1()
        self.add_button_take()
        pass 

    def on_ComboBox1Select(self, cb, e) :
        print(type(self))
        print(type(cb))
        print(type(e))
        self.ActiveTagType = self.tag_types[cb.SelectedIndex]
        print(Element.Name.GetValue(self.ActiveTagType))

    def add_combo1(self) :
        cb = Forms.ComboBox()
        cb.Size = Drawing.Size(300, 30)
        cb.Location = Drawing.Point(20,20)
        self.Controls.Add(cb)

        fc = list(FilteredElementCollector(doc).OfCategory(bic.OST_PipeTags).WhereElementIsElementType().ToElements())
        self.tag_types = fc

        for e in fc:
            cb.Items.Add("{} -> {}".format(e.FamilyName, Element.Name.GetValue(e)))
        cb.SelectedIndex = 0

        cb.SelectedIndexChanged += self.on_ComboBox1Select


    

    def on_Button_take(self, btn, e) :
        print("Выбираем")
        Forms.MessageBox.Show("Нажата кнопка")

        e_ids = uidoc.Selection.GetElementIds()
        if len(e_ids) > 0 :
            self.pipes = [doc.GetElement(eid) for eid in e_ids]

        else :
            pipes_ref = uidoc.Selection.PickObjects(ot.Element)
            self.pipes = [doc.GetElement(eid) for eid in pipes_ref] 
        print("вызываем функцию создания")
        self.CreateTag(self, self.pipes[0])

        

    def add_button_take(self) :
        button = Forms.Button()
        button.Text = "Выбрать"
        button.Size = Drawing.Size(100, 30)
        button.Location = Drawing.Point(350, 20)
        self.Controls.Add(button)
        button.Click += self.on_Button_take



def create_form() :
    f = dmForm()
    f.init_form()
    f.Size = Drawing.Size(500,500)
    f.Text = "Добавление марок на трубы"
    f.ShowDialog()

    f.a = ""



    return f

print("d71_marks_pipe")

f=create_form()



