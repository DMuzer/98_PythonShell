public static void CreateViewFilter(Document doc, View view)
{
    List<ElementId> categories = new List<ElementId>();
    categories.Add(new ElementId(BuiltInCategory.OST_Walls));
    List<ElementFilter> elementFilterList = new List<ElementFilter>();

    using (Transaction t = new Transaction(doc, "Add view filter"))
    {
        t.Start();

        // Criterion 1 - wall type Function is "Exterior"
        ElementId exteriorParamId = new ElementId(BuiltInParameter.FUNCTION_PARAM);
        elementFilterList.Add(new ElementParameterFilter(ParameterFilterRuleFactory.CreateEqualsRule(exteriorParamId, (int)WallFunction.Exterior)));

        // Criterion 2 - wall length > = 28 or < = 14
        ElementId lengthId = new ElementId(BuiltInParameter.CURVE_ELEM_LENGTH);
        LogicalOrFilter wallHeightFilter = new LogicalOrFilter(
            new ElementParameterFilter(ParameterFilterRuleFactory.CreateGreaterOrEqualRule(lengthId, 28.0, 0.00001)),
            new ElementParameterFilter(ParameterFilterRuleFactory.CreateLessOrEqualRule(lengthId, 14.0, 0.00001)));
        elementFilterList.Add(wallHeightFilter);

        // Criterion 3 - custom shared parameter value matches string pattern
        // Get the id for the shared parameter - the ElementId is not hardcoded, so we need to get an instance of this type to find it
        Guid spGuid = new Guid("96b00b61-7f5a-4f36-a828-5cd07890a02a");
        FilteredElementCollector collector = new FilteredElementCollector(doc);
        collector.OfClass(typeof(Wall));
        Wall wall = collector.FirstElement() as Wall;

        if (wall != null)
        {
            Parameter sharedParam = wall.get_Parameter(spGuid);
            ElementId sharedParamId = sharedParam.Id;

            elementFilterList.Add(new ElementParameterFilter(ParameterFilterRuleFactory.CreateBeginsWithRule(sharedParamId, "15.", true)));
        }

        // Create filter element associated to the input categories
        LogicalAndFilter andFilter = new LogicalAndFilter(elementFilterList);
        if (ParameterFilterElement.ElementFilterIsAcceptableForParameterFilterElement(doc, new HashSet<ElementId>(categories), andFilter))
        {
            ParameterFilterElement parameterFilterElement = ParameterFilterElement.Create(doc, "Example view filter", categories, andFilter);

            // Apply filter to view
            view.AddFilter(parameterFilterElement.Id);
            view.SetFilterVisibility(parameterFilterElement.Id, false);
        }
        else
        {
            TaskDialog.Show("Error", "Filter cannot be used");
        }
        t.Commit();
    }
}