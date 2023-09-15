public void EditFamilyTypes(Document document, FamilyInstance familyInstance)
{
    // example works best when familyInstance is a rectangular concrete element

    if ((null == document) || (null == familyInstance.Symbol))
    {
        return;   // invalid arguments
    }

    // Get family associated with this
    Family family = familyInstance.Symbol.Family;
    if (null == family)
    {
        return;    // could not get the family
    }

    // Get Family document for family
    Document familyDoc = document.EditFamily(family);
    if (null == familyDoc)
    {
        return;    // could not open a family for edit
    }

    FamilyManager familyManager = familyDoc.FamilyManager;
    if (null == familyManager)
    {
        return;  // cuould not get a family manager
    }

    // Start transaction for the family document
    using (Transaction newFamilyTypeTransaction = new Transaction(familyDoc, "Add Type to Family"))
    {
        int changesMade = 0;
        newFamilyTypeTransaction.Start();

        // add a new type and edit its parameters
        FamilyType newFamilyType = familyManager.NewType("2X2");

        if (newFamilyType != null)
        {
            // look for 'b' and 'h' parameters and set them to 2 feet
            FamilyParameter familyParam = familyManager.get_Parameter("b");
            if (null != familyParam)
            {
                familyManager.Set(familyParam, 2.0);
                changesMade += 1;
            }

            familyParam = familyManager.get_Parameter("h");
            if (null != familyParam)
            {
                familyManager.Set(familyParam, 2.0);
                changesMade += 1;
            }
        }

        if (2 == changesMade)   // set both paramaters?
        {
            newFamilyTypeTransaction.Commit();
        }
        else   // could not make the change -> should roll back 
        {
            newFamilyTypeTransaction.RollBack();
        }

        // if could not make the change or could not commit it, we return
        if (newFamilyTypeTransaction.GetStatus() != TransactionStatus.Committed)
        {
            return;
        }
    }

    // now update the Revit project with Family which has a new type
    LoadOpts loadOptions = new LoadOpts();

    // This overload is necessary for reloading an edited family
    // back into the source document from which it was extracted
    family = familyDoc.LoadFamily(document, loadOptions);
    if (null != family)
    {
        // find the new type and assign it to FamilyInstance
        ISet familySymbolIds = family.GetFamilySymbolIds();
        foreach (ElementId id in familySymbolIds)
        {
            FamilySymbol familySymbol = family.Document.GetElement(id) as FamilySymbol;
            if ((null != familySymbol) && familySymbol.Name == "2X2")
            {
                using (Transaction changeSymbol = new Transaction(document, "Change Symbol Assignment"))
                {
                    changeSymbol.Start();
                    familyInstance.Symbol = familySymbol;
                    changeSymbol.Commit();
                }
                break;
            }
        }
    }
}

class LoadOpts : IFamilyLoadOptions
{
    public bool OnFamilyFound(bool familyInUse, out bool overwriteParameterValues)
    {
        overwriteParameterValues = true;
        return true;
    }

    public bool OnSharedFamilyFound(Family sharedFamily, bool familyInUse, out FamilySource source, out bool overwriteParameterValues)
    {
        source = FamilySource.Family;
        overwriteParameterValues = true;
        return true;
    }
}