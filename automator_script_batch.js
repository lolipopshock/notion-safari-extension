function run(input, parameters) {
    var app = Application.currentApplication()
    app.includeStandardAdditions = true

    var returnVals = ["--page_selection"];

    // Obtain the Notion information to construct the Selection Pannel 
    function readFile(file) {
        return app.read(Path(file))
    }
    jsonFile = readFile(Path('<your/notion/config/file/path>'))
    var notonInfo = JSON.parse(jsonFile)
    let functionChoices = Object.keys(notonInfo["pages"]).concat(["Custom"])

    // Fetch user selection 
    var pageSelection = app.chooseFromList(functionChoices, {
        withPrompt: "Which page do you want to add to?",
        defaultItems: functionChoices[0]
    })

    // Parse the user selection
    if (pageSelection[0] == "Custom") {
        // Allow user input
        var response = app.displayDialog("Please paste the link to the Notion Page", {
            defaultAnswer: "",
            withIcon: "note",
            buttons: ["Cancel", "Continue"],
            defaultButton: "Continue"
        })
        returnVals.push(response.textReturned)
    } else if (pageSelection[0] != undefined) {
        returnVals.push(pageSelection[0])
    } else (
        returnVals.push(false)
    )

    // Fetch the data from the given application
    titleVals = ["--titles"]
    urlVals = ["--urls"]
    var Safari = Application('Safari');
    Safari.includeStandardAdditions = true;
    Safari.windows[0].tabs().forEach(function (tab) {
        // console.log(tab.url())
        urlVals.push(tab.url())
        titleVals.push(tab.name())
    })

    // Return the values 
    returnVals = returnVals.concat(titleVals).concat(urlVals)
    return returnVals
}