#  coding: utf-8 


from Autodesk.Revit import *
from Autodesk.Revit.DB import *

import math, sys
import clr


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

class dmF(Form) :
    def OnClose(self, sender, e) :
        del(self.dEventH)
        print("Closing")

    def OnClosed(self, e) :
        print("OnClosed")

    def BtnPress1(self, *args) :
        self.exEvent.Raise()
        #self.lbl.Text = "Событие генерируем"
        Forms.MessageBox.Show("Показываем форму")
        
        
        
        pass

    def create_form(self, dEventH, exEvent) :

        btn = Forms.Button()
        btn.Size = Size(100, 30)
        btn.Location = Drawing.Point(20, 20)
        btn.Text = "Выполнить"

        btn.Click += self.BtnPress1 

        self.Controls.Add(btn)
        self.Closing += self.OnClose
        self.Closed += self.OnClosed

        self.dEventH = dEventH
        self.exEvent = exEvent

        self.Flag = "-2345"
        
        lbl = Forms.Label()
        self.lbl = lbl
        lbl.Size = Size(200, 30)
        lbl.Location = Drawing.Point(20, 50)
        lbl.Text = "Метка текст"
        self.Controls.Add(lbl)




        pass 


def create_form() :

    global f1 
    print('fdsa')

    dEventH = dmExEvent()
    exEvent = ExternalEvent.Create(dEventH)

    # dEventH = 0
    # exEvent = 0

    f1 = dmF()
    f1.create_form(dEventH=dEventH, exEvent=exEvent)

    f1.Show()

def set_time() :
    from time import localtime 
    from time import strftime
    #e = doc.GetElement(ElementId(2138933))
    param = e.LookupParameter("ADSK_Марка")
    global f1
    f1.lbl.Text = "изменение из обработчика"
    return
    with dm.trans(doc) :
        param.Set(strftime("%Y-%m-%d %H:%M:%S", localtime()) + f1.Flag)
        
create_form()





