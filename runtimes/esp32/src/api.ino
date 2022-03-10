
AsyncWebServer server(80);

void updateHandler(AsyncWebServerRequest *request, String uploadFilename, size_t index, uint8_t *data, size_t len, bool final)
{
    String type = request->getParam("type")->value();

    if (type == "partial")
    {
        updatePartial(request, uploadFilename, index, data, len, final);
    }
    else if (type == "full")
    {
        updateFull(request, uploadFilename, index, data, len, final);
    }
    else
    {
        request->send(400, "text/plain", "Invalid update type");
    }
}

void updatePartial(AsyncWebServerRequest *request, String uploadFilename, size_t index, uint8_t *data, size_t len, bool final)
{
    String signature_base64 = request->getParam("signature")->value();
    String deployment_id = request->getParam("deployment_id")->value();

    if (!index)
    {
        Serial.printf("UploadStart: %s\n", uploadFilename.c_str());
        if (SPIFFS.exists(getInactiveDeploymentFilename()))
        {
            SPIFFS.remove(getInactiveDeploymentFilename());
        }
    }
    /* Overwriting the currently inactive file */
    File file = SPIFFS.open(getInactiveDeploymentFilename(), "a");
    for (size_t i = 0; i < len; i++)
    {
        file.write(data[i]);
    }
    file.close();
    if (final)
    {
        /* Calculating the sha256 hash of the uploaded file */
        File file = SPIFFS.open(getInactiveDeploymentFilename(), "r");
        auto fileSize = file.size();
        unsigned char wasm_buffer[fileSize];
        auto i = 0;
        while (file.available())
        {
            wasm_buffer[i] = file.read();
            i++;
        }
        file.close();

        byte shaResult[32];

        mbedtls_md_context_t ctx;
        mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

        mbedtls_md_init(&ctx);
        mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 0);
        mbedtls_md_starts(&ctx);
        mbedtls_md_update(&ctx, (const unsigned char *)wasm_buffer, fileSize);
        mbedtls_md_finish(&ctx, shaResult);
        mbedtls_md_free(&ctx);

        /* Logging the hash for debugging */
        Serial.print("Hash: ");
        for (int i = 0; i < sizeof(shaResult); i++)
        {
            char str[3];

            sprintf(str, "%02x", (int)shaResult[i]);
            Serial.print(str);
        }
        Serial.println();

        /* Public Key gets hardcoded during compile time for now */
        unsigned char pubkey_base64[] = VERIFICATION_KEY;
        unsigned char pubkey[32];
        decode_base64(pubkey_base64, pubkey);

        /**
         * The Ed25519 Library expects the signature to be in non-uri-safe form.
         * Therefore we need to convert the signature from uri-safe to non-uri-safe form.
         */
        std::string s = (std::string)signature_base64.c_str();
        std::replace(s.begin(), s.end(), '_', '/');
        std::replace(s.begin(), s.end(), '-', '+');

        /* Decoding Base64 encoded signature into byte format */
        char signature_buf[64];
        strcpy(signature_buf, (const char *)(s.c_str()));
        unsigned char signature[64];
        unsigned int signature_len = decode_base64((unsigned char *)signature_buf, signature);

        /* Validate signature */
        if (!Ed25519::verify(signature, pubkey, shaResult, 32))
        {
            Serial.println("Signature verification failed");
            request->send(400, "text/plain", "Signature verification failed");
            SPIFFS.remove(getInactiveDeploymentFilename());
            return;
        }

        /* Writing the new deployment id and checksum */
        loadDeploymentInfo();
        unsigned char sha256_str[24];
        encode_base64(shaResult, 32, sha256_str);
        String sha_b64 = String((const char *)sha256_str);

        writeFile(getInactiveDeploymentFilename() + ".sha256", sha_b64);
        writeFile(getInactiveDeploymentFilename() + ".id", deployment_id);

        /* Successful Signature Check -- Switch deployment and reboot to activate */
        Serial.println("Signature verification succeeded");
        switchActiveDeployment();

        request->send(200);
        Serial.printf("UploadEnd: %s, %u B\n", uploadFilename.c_str(), index + len);
        delay(200);

        /* Restarting the current wasm process does not yet work for some reason */
        // Serial.print("Restarting WASM file...");
        // initWasmRuntime();

        /* Restarting the device as a workaround instead */
        Serial.println("Restarting...");
        ESP.restart();
    }
}

esp_ota_handle_t ota_handle;
const esp_partition_t *ota_partition;
byte full_update_sha[32];
mbedtls_md_context_t ctx;
mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

void updateFull(AsyncWebServerRequest *request, const String &filename, size_t index, uint8_t *data, size_t len, bool final)
{
    size_t content_len = request->contentLength();
    String signature_base64 = request->getParam("signature")->value();

    if (!index)
    {
        Serial.println("Starting Update Full");
        Serial.println("Signature: " + signature_base64);

        ota_partition = esp_ota_get_next_update_partition(NULL);
        esp_ota_begin(ota_partition, OTA_SIZE_UNKNOWN, &ota_handle);

        mbedtls_md_init(&ctx);
        mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 0);
        mbedtls_md_starts(&ctx);
    }

    Serial.println("Writing to flash: " + String(index) + " / " + String(content_len));
    esp_ota_write(ota_handle, (const void *)data, len);
    mbedtls_md_update(&ctx, (const unsigned char *)data, len);

    if (final)
    {
        mbedtls_md_finish(&ctx, full_update_sha);
        mbedtls_md_free(&ctx);

        /* Logging the hash for debugging */
        Serial.print("Hash: ");
        for (int i = 0; i < sizeof(full_update_sha); i++)
        {
            char str[3];

            sprintf(str, "%02x", (int)full_update_sha[i]);
            Serial.print(str);
        }
        Serial.println();

        /* Public Key gets hardcoded during compile time for now */
        unsigned char pubkey_base64[] = VERIFICATION_KEY;
        unsigned char pubkey[32];
        decode_base64(pubkey_base64, pubkey);

        /**
         * The Ed25519 Library expects the signature to be in non-uri-safe form.
         * Therefore we need to convert the signature from uri-safe to non-uri-safe form.
         */
        std::string s = (std::string)signature_base64.c_str();
        std::replace(s.begin(), s.end(), '_', '/');
        std::replace(s.begin(), s.end(), '-', '+');

        /* Decoding Base64 encoded signature into byte format */
        char signature_buf[64];
        strcpy(signature_buf, (const char *)(s.c_str()));
        unsigned char signature[64];
        unsigned int signature_len = decode_base64((unsigned char *)signature_buf, signature);

        /* Validate signature */
        if (!Ed25519::verify(signature, pubkey, full_update_sha, 32))
        {
            Serial.println("Signature verification failed");
            request->send(400, "text/plain", "Signature verification failed");
            return;
        }

        if (esp_ota_end(ota_handle) != ESP_OK || esp_ota_set_boot_partition(ota_partition) != ESP_OK)
        {
            request->send(500, "text/plain", "Update failed");
            delay(500);
            return;
        }

        /* Writing the new deployment id and checksum */
        loadDeploymentInfo();
        unsigned char sha256_str[24];
        encode_base64(full_update_sha, 32, sha256_str);
        String sha_b64 = String((const char *)sha256_str);

        const esp_partition_t *partition = esp_ota_get_running_partition();
        writeFile("/" + String(partition->label) + ".sha256", sha_b64);

        Serial.println("...done");
        request->send(200, "text/plain", "OK");
        Serial.println("Rebooting...");
        delay(500);
        esp_restart();
    }
}

void initAPI()
{
    server.on("/status", HTTP_GET, [](AsyncWebServerRequest *request)
              { request->send_P(200, "text/plain", getStatus().c_str()); });
    server.on(
        "/update", HTTP_POST, [](AsyncWebServerRequest *request)
        {
            AsyncWebServerResponse *response = request->beginResponse(200, "text/plain", "OK");
            response->addHeader("Connection", "close");
            request->send(response); },
        updateHandler);
    server.begin();
    Serial.println("started webserver on :80");
}

/*
 * Returns the current version of the active deployment
 * and the active runtime.
 */
String getStatus()
{
    String response;
    StaticJsonDocument<2000> doc;

    loadDeploymentInfo();

    doc["ip"] = WiFi.localIP().toString();

    JsonObject runtime = doc.createNestedObject("runtime");
    runtime["id"] = "esp32";

    const esp_partition_t *partition = esp_ota_get_running_partition();
    runtime["sha256"] = readFile("/" + String(partition->label) + ".sha256");

    // Embedding deployment data
    JsonObject deployment_response = doc.createNestedObject("deployment");
    deployment_response["id"] = readFile(getActiveDeploymentFilename() + ".id");
    deployment_response["sha256"] = readFile(getActiveDeploymentFilename() + ".sha256");

    serializeJson(doc, response);
    return response + "\n";
}
