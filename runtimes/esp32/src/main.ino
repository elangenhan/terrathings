#include <WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <Ed25519.h>
#include "mbedtls/md.h"
#include "base64.hpp"
#include <Update.h>
#include "SPIFFS.h"
#include <wasm3.h>
#include <m3_env.h>
#include "ESPAsyncWebServer.h"
#include <esp_ota_ops.h>
#include <esp_system.h>
#include <nvs_flash.h>

#include "fs.h"

/* Holds data about which wasm modules are loaded */
StaticJsonDocument<200> deployment;

#define U_PART U_SPIFFS

const char *ssid = WIFI_SSID;
const char *password = WIFI_PASSWORD;

void setup()
{
    Serial.begin(115200);

    // Leave a little bit of time for a client to connect
    delay(500);
    Serial.println("== STARTING ==");

    initFS();
    initWiFi();
    initAPI();

    initDeploymentInfo();

    if (deploymentExists())
    {
        initWasmRuntime();
    }
    else
    {
        Serial.println("No WASM app found, skipping WASM runtime initialization.");
        Serial.println("Idleing until a deployment is received...");
    }

    const esp_partition_t *partition = esp_ota_get_running_partition();
    printf("🚀 Active partition: %s\r\n", partition->label);

    esp_ota_img_states_t ota_state;
    if (esp_ota_get_state_partition(partition, &ota_state) == ESP_OK)
    {
        if (ota_state == ESP_OTA_IMG_PENDING_VERIFY)
        {
            esp_ota_mark_app_valid_cancel_rollback();
        }
    }
}

void loop()
{
    if (Serial.available())
    {
        // Pressing enter or sending a newline will respond with the current status
        // used to obtain the IP address in the Terrathings controller
        Serial.readStringUntil('\n');
        Serial.println(getStatus());
    }
}

void initWiFi()
{
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.print("Connected to ");
    Serial.println(ssid);
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}
