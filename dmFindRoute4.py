#  coding: utf-8
import Autodesk.Revit
from Autodesk.Revit import  DB, UI 
from Autodesk.Revit.DB import *
from contextlib import contextmanager
import System

bic = BuiltInCategory
dut = 0.0032808398950131233
import clr
import json
import sys 
import os 

buffersPath = r"C:\Users\Дмитрий\System.Buffers.4.4.0\lib\netstandard2.0\System.Buffers.dll"
NTSPath = r"C:\Users\Дмитрий\nettopologysuite.2.5.0\lib\netstandard2.0\NetTopologySuite.dll"
SQLPath = r"C:\Users\Дмитрий\AppData\Roaming\Autodesk\Revit\Addins\2023\RevitPythonShell\IronPython.SQLite.dll"
currentReferences = [assembly.Location for assembly in clr.References]

stopModelNameStr = ["(ТХ)"]
pipeGap = 12.5 * dut

if buffersPath not in currentReferences :
    clr.AddReferenceToFileAndPath(buffersPath)
if NTSPath not in currentReferences :
    clr.AddReferenceToFileAndPath(NTSPath)
if SQLPath not in currentReferences :
    clr.AddReferenceToFileAndPath(SQLPath)
    clr.AddReference("IronPython.SQLite, Version=3.4.0.0, Culture=neutral, PublicKeyToken=7f709c5b713576e1" )
#clr.AddReferenceToFileAndPath(SQLPath) 
print()  
import NetTopologySuite as nts
from NetTopologySuite.Geometries import *
import NetTopologySuite.Geometries as geoms
import sqlite3 as sql

class dmNotFoundSectionInDataBaseError(Exception) :
    pass 
class dmNotFoundLevelInDataBaseError(Exception) :
    pass 
class dmNotFoundPlanInDataBaseError(Exception) :
    pass
class dmNoLevelsOfPlan(Exception) :
    pass 
class dmNotFoundLevelOfPlan(Exception) :
    pass 

from types import FunctionType
from System.Diagnostics import Stopwatch
timer = Stopwatch()
times = {}

 

def profiler_(fnc) :
    return fnc
def profiler(fnc) :
    def wrapped(*args, **keywargs) :
        global times
        if not timer.IsRunning :
            timer.Start()
        start 		= timer.ElapsedMilliseconds
        retVal 		= fnc(*args, **keywargs)
        timeTaken 	= timer.ElapsedMilliseconds - start
        
        name            = fnc.__name__
        function_times 	= times.setdefault(name, [])
        function_times.append(timeTaken)
        return retVal
    return wrapped

def printProfiling(t) :
    for name, calls in sorted(times.items(), key = lambda x : sum(x[1]), reverse= True):
        print(f"Функция : {name}")
        print(f"Вызывалась {len(calls)} раз")
        print(f"Общее время вызовов {float(sum(calls)):.1f}")
        avg = (sum(calls) / float(len(calls)))
        print(f"Макс: {float(max(calls)):.1f}, Мин: {float(min(calls)):.1f}, Среднее: {avg:.1f}")
        print()

        


class ProfilingMetaclass(type) :
    def __new__(meta, classname, bases, classDict) :
        #print(0)
        for name, item in classDict.items() :
            if isinstance(item, FunctionType) :
                #print(f"Формируется {name}")
                classDict[name] = profiler(item)
        return type.__new__(meta, classname, bases, classDict)
    
_ProfilingMetaclass = type

class dmSQLConnection(metaclass = ProfilingMetaclass) :
    connection  = None 
    dbPath      = None
    def createDb(dbPath) :
        dmSQLConnection.connection = sql.connect(dbPath)

        qt1 = """
        CREATE TABLE PLANS (
            Plan_code    INTEGER     PRIMARY KEY
                                    UNIQUE,
            Plan_name TEXT (255),
            Level_name   TEXT (1000) 
        );
        """

        qt2 = """
            CREATE TABLE Eshelons (
                Elevation_code     INTEGER PRIMARY KEY,
                centerElevation    NUMERIC,
                levelElevation     INTEGER,
                Height             NUMERIC,
                Plan_code          INTEGER REFERENCES PLANS (Plan_code),
                wallsPolygonB      BLOB,
                archPolygonB       BLOB,
                ductPolygonB       BLOB,
                pipePolygonB       BLOB,
                electricalPolygonB BLOB
            );


        """

        dmSQLConnection.connection.execute(qt1)
        dmSQLConnection.connection.execute(qt2)
        dmSQLConnection.connection.commit()
        dmSQLConnection.connection.row_factory = sql.Row
        return dmSQLConnection.connection

    def __new__(cls) :
        if dmSQLConnection.connection : 
            print("курсор определен")
            try :
                print("проверяем, открыто ли соединение")
                dmSQLConnection.connection.cursor()
                print("соединение открыто, возвращаем существующее")
                return dmSQLConnection.connection
            except :
                print("соединение закрыто, надо создать")
                pass 
        docPath = __revit__.ActiveUIDocument.Document.PathName
        fld = "\\".join(docPath.split("\\")[:-1])
        name = docPath.split("\\")[-1]
        stem = ".".join(name.split(".")[:-1])

        dmSQLConnection.dbPath = fld + "\\" + stem + ".tracing1.sqlite"
        
        if not os.path.exists(dmSQLConnection.dbPath) :
            print("Файл не найден, Создаем новую базу данные")
            dmSQLConnection.connection = dmSQLConnection.createDb(dmSQLConnection.dbPath)
        else :
            print("создаем новое соединение с существующей базой")
            dmSQLConnection.connection = sql.connect(dmSQLConnection.dbPath)
            dmSQLConnection.connection.row_factory = sql.Row
        return dmSQLConnection.connection 
    
class dmLinkedElement(metaclass = ProfilingMetaclass) :
    def __init__(self, link, element) :
        self.link   = link
        self.e      = element
    
    def __repr__(self) :
        return "{} :".format(self.e.Category.Name, self.e.Id, self.link)

class dmLinkInstance(metaclass = ProfilingMetaclass) :
    def __init__(self, linkInstance) :
        self.linkInstance = linkInstance
        self.linkDocument = linkInstance.GetLinkDocument()
        self.Transform = linkInstance.GetTotalTransform

    def getFilteredElements(self, bb, flt) :
        if bb :
            pmin_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Min))
            pmax_= self.InvTransform.OfPoint(bb.Transform.OfPoint(bb.Max))

            pmin = XYZ(min(pmin_.X, pmax_.X), min(pmin_.Y, pmax_.Y), min(pmin_.Z, pmax_.Z))
            pmax = XYZ(max(pmin_.X, pmax_.X), max(pmin_.Y, pmax_.Y), max(pmin_.Z, pmax_.Z))


            outline = Outline(pmin, pmax)
            bbFlt = BoundingBoxIntersectsFilter (outline)
        fc = FilteredElementCollector(self.linkDocument)\
            .WherePasses(flt)\
                .ToElements()
        
        return list(fc)
    def getElements(self, bb) :
        flt =  ElementMulticategoryFilter(System.Array[bic]([
                bic.OST_PipeCurves, bic.OST_PipeFitting, bic.OST_PipeAccessory,
                bic.OST_MechanicalEquipment, 
                bic.OST_PipeInsulations
        ]))

        pass




    
    def __repr__(self)  :
        return "Вставленная модель {}".format(self.linkInstance.Name)


class dmDocument(metaclass = ProfilingMetaclass) :
    def __init__(self, doc) :
        self.doc = doc
    
    def _getLinkInstances(self) :
        for li in FilteredElementCollector(self.doc).OfClass(RevitLinkInstance).ToElements() :
            yield dmLinkInstance(li)
    linkInstances = property(_getLinkInstances)

    def __repr__(self) :
        return "Ссылка на модель : {}".format(self.doc.PathName)

class dmEshelon(metaclass = ProfilingMetaclass) :
    def __init__(self) :
        pass 
    def createBlank(self, centerElevation, height, view) :
        return
    def loadFromDataBase(self, levelElevation, view) :
        return 

    pass

class dmPlan(metaclass = ProfilingMetaclass) :
    def __init__(self, view) :
        self.view = view

        return 
    def __repr__(self):
        return "Рабочий план {}".format(self.view.Name)
    
    
    def createEshelons(self, startElevation, endElevation, height) :
        pass


    pass
    

