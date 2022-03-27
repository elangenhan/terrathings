
String listFilesInDir(File dir, int numTabs = 1);
String listFilesInDir(File dir, int numTabs);
String readFile(String filename);
void writeFile(String filename, String content);
void initFS();
void loadDeploymentInfo();
void updateDeploymentInfo();
void initDeploymentInfo();
void switchActiveDeployment();
String getActiveDeploymentFilename();
String getInactiveDeploymentFilename();
bool deploymentExists();
