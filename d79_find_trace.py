#  coding: utf-8 


from Autodesk.Revit import *
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import math, sys
import clr
import System
from System.Collections.Generic import IList, List

from dm_connect_2 import *



lib_path = r"D:\18_проектирование\98_PythonShell"
if not lib_path in sys.path :
	sys.path.append(lib_path)


uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document



class dmFindTrace :
    def __init__(self) :
        pass

    def createPossibleSolid(self) :
        self.possibleSolid = None 
        self.roomRef = uidoc.Selection.PickObject(UI.Selection.ObjectType.LinkedElement)
        self.linkInstance = doc.GetElement(self.roomRef)
        self.linkDoc = self.linkInstance.GetLinkDocument()
        self.room = self.linkDoc.GetElement(self.roomRef.LinkedElementId)
        opt = Options()
        geometry = [s for s in self.room.Geometry[opt] if type(s) == Solid]
        
        self.ds = create_ds(geometry)

        


    def execute(self) :
        print("исполнение начинаем поиск трассы")
        self.createPossibleSolid()