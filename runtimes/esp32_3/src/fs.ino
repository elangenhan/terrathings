
String listFilesInDir(File dir, int numTabs)
{
    String list = "";
    while (true)
    {

        File entry = dir.openNextFile();
        if (!entry)
        {
            // no more files in the folder
            break;
        }
        list += entry.name();
        if (entry.isDirectory())
        {
            list += "/\n";
            listFilesInDir(entry, numTabs + 1);
        }
        else
        {
            // display zise for file, nothing for directory
            list += "\t\t" + String(entry.size()) + " bytes\n";
        }
        entry.close();
    }
    return list;
}

String readFile(String filename)
{
    File file = SPIFFS.open(filename, "r");
    if (!file)
    {
        return "";
    }
    String content = "";
    while (file.available())
    {
        content += (char)file.read();
    }
    file.close();
    return content;
}

void writeFile(String filename, String content)
{
    File file = SPIFFS.open(filename, "w");
    if (!file)
    {
        return;
    }
    file.print(content);
    file.close();
}

void initFS()
{
    if (SPIFFS.begin(true))
    {
        Serial.println(F("SPIFFS mounted correctly."));
    }
    else
    {
        Serial.println(F("!An error occurred during SPIFFS mounting"));
    }

    unsigned int totalBytes = SPIFFS.totalBytes();
    unsigned int usedBytes = SPIFFS.usedBytes();
    Serial.println("===== File system info =====");

    Serial.print("Total space:      ");
    Serial.print(totalBytes);
    Serial.println("byte");

    Serial.print("Total space used: ");
    Serial.print(usedBytes);
    Serial.println("byte");

    Serial.println();

    // List files in SPIFFS - for DEBUG
    File dir = SPIFFS.open("/");
    Serial.print(listFilesInDir(dir));
}

bool deploymentExists()
{
    return SPIFFS.exists("/A/app.wasm") || SPIFFS.exists("/B/app.wasm");
}

void loadDeploymentInfo()
{
    File file = SPIFFS.open("/deployment.json", "r");
    if (!file)
    {
        Serial.println("Failed to open deployment.json");
        return;
    }
    size_t size = file.size();
    std::unique_ptr<char[]> buf(new char[size]);
    file.readBytes(buf.get(), size);

    DeserializationError error = deserializeJson(deployment, buf.get());

    if (error)
    {
        Serial.print(F("deserialize deployment.json failed: "));
        Serial.println(error.f_str());
        return;
    }
}

void updateDeploymentInfo()
{
    Serial.println("Updating deployment.json");
    File file = SPIFFS.open("/deployment.json", "w");
    if (!file)
    {
        Serial.println("Failed to open deployment.json for writing");
        return;
    }
    serializeJson(deployment, file);
    file.close();
}

void initDeploymentInfo()
{
    if (SPIFFS.exists("/deployment.json"))
    {
        loadDeploymentInfo();
    }
    else
    {
        Serial.println("No deployment.json found, creating...");
        File file = SPIFFS.open("/deployment.json", "w");
        if (!file)
        {
            Serial.println("Failed to create deployment.json");
            return;
        }

        file.close();

        deployment["active"] = "A";
        updateDeploymentInfo();
    }
}

void switchActiveDeployment()
{
    Serial.println("== Switching active deployment ==");
    loadDeploymentInfo();
    String active = deployment["active"];
    Serial.println("active previous: " + active);
    if (active == "A")
    {
        deployment["active"] = "B";
    }
    else
    {
        deployment["active"] = "A";
    }
    updateDeploymentInfo();
}

String getActiveDeploymentFilename()
{
    loadDeploymentInfo();
    auto active = deployment["active"];

    String filename = "app.wasm";
    if (active == "A")
    {
        return "/A/" + filename;
    }
    else if (active == "B")
    {
        return "/B/" + filename;
    }
    else
    {
        return "/A/" + filename;
    }
}

String getInactiveDeploymentFilename()
{

    loadDeploymentInfo();
    auto active = deployment["active"];

    String filename = "app.wasm";
    if (active == "A")
    {
        return "/B/" + filename;
    }
    else if (active == "B")
    {
        return "/A/" + filename;
    }
    else
    {
        return "/A/" + filename;
    }
}
