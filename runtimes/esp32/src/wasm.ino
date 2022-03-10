/*
 * This is based on the example that can be found at
 * https://github.com/wasm3/wasm3-arduino/blob/f27a97403241da068fbc08b9362ca929ddeef0ed/examples_pio/Wasm_Advanced/wasm_vm/wasm_vm.ino
 *
 * Copyright of the original file:
 * Wasm3 - high performance WebAssembly interpreter written in C.
 * Copyright © 2020 Volodymyr Shymanskyy, Steven Massey.
 * All rights reserved.
 */

#define WASM_STACK_SLOTS 4096
#define NATIVE_STACK_SIZE (32 * 1024)

const char *gpio_pin_mapping_raw = GPIO_PIN_MAPPING;

/* This handle is used to terminate the WASM process */
TaskHandle_t wasmTaskHandle = NULL;

/*
 * A Raspberry Pi has 26 usable GPIO pins.
 * Therefore we chose this arbitrary limit.
 */
uint32_t virtual_gpio_pins[26] = {};

/*
 * API bindings
 *
 * Note: each RawFunction should complete with one of these calls:
 *   m3ApiReturn(val)   - Returns a value
 *   m3ApiSuccess()     - Returns void (and no traps)
 *   m3ApiTrap(trap)    - Returns a trap
 */

m3ApiRawFunction(m3_hostbindings_millis)
{
    m3ApiReturnType(uint32_t)

        m3ApiReturn(millis());
}

m3ApiRawFunction(m3_hostbindings_delay)
{
    m3ApiGetArg(uint32_t, ms)

        // You can also trace API calls
        // Serial.print("api: delay "); Serial.println(ms);

        delay(ms);

    m3ApiSuccess();
}

uint8_t mapPinMode(uint8_t mode)
{
    switch (mode)
    {
    case 0:
        return INPUT;
    case 1:
        return OUTPUT;
    case 2:
        return INPUT_PULLUP;
    }
    return INPUT;
}

m3ApiRawFunction(m3_hostbindings_pinMode)
{
    m3ApiGetArg(uint32_t, pin)
        m3ApiGetArg(uint32_t, mode)

#if !defined(PARTICLE)
            typedef uint8_t PinMode;
#endif
    pinMode(virtual_gpio_pins[pin - 1], (PinMode)mapPinMode(mode));

    m3ApiSuccess();
}

m3ApiRawFunction(m3_hostbindings_digitalWrite)
{
    m3ApiGetArg(uint32_t, pin)
        m3ApiGetArg(uint32_t, value)
            digitalWrite(virtual_gpio_pins[pin - 1], value);

    m3ApiSuccess();
}

m3ApiRawFunction(m3_hostbindings_getPinLED)
{
    m3ApiGetArg(uint32_t, value)
        m3ApiReturnType(uint32_t)
            m3ApiReturn(0);
}

m3ApiRawFunction(m3_hostbindings_print)
{
    m3ApiGetArgMem(const uint8_t *, buf)
        m3ApiGetArg(uint32_t, len)

        // printf("api: print %p %d\n", buf, len);
        Serial.write(buf, len);

    m3ApiSuccess();
}

m3ApiRawFunction(m3_hostbindings_getGreeting)
{
    m3ApiGetArgMem(uint8_t *, out)
        m3ApiGetArg(uint32_t, out_len)

            const char buff[] = "Hello WASM world! 😊";
    memcpy(out, buff, min(sizeof(buff), out_len));

    m3ApiSuccess();
}

M3Result LinkHostbindings(IM3Runtime runtime)
{
    IM3Module module = runtime->modules;
    const char *hostbindings = "hostbindings";

    m3_LinkRawFunction(module, hostbindings, "millis", "i()", &m3_hostbindings_millis);
    m3_LinkRawFunction(module, hostbindings, "delay", "v(i)", &m3_hostbindings_delay);
    m3_LinkRawFunction(module, hostbindings, "pinMode", "v(ii)", &m3_hostbindings_pinMode);
    m3_LinkRawFunction(module, hostbindings, "digitalWrite", "v(ii)", &m3_hostbindings_digitalWrite);
    m3_LinkRawFunction(module, hostbindings, "getPinLED", "i(i)", &m3_hostbindings_getPinLED);
    m3_LinkRawFunction(module, hostbindings, "getGreeting", "v(*i)", &m3_hostbindings_getGreeting);
    m3_LinkRawFunction(module, hostbindings, "print", "v(*i)", &m3_hostbindings_print);

    return m3Err_none;
}

#define FATAL(func, msg)                  \
    {                                     \
        Serial.print("Fatal: " func " "); \
        Serial.println(msg);              \
        return;                           \
    }

void run_deployment()
{
    M3Result result = m3Err_none;

    IM3Environment env = m3_NewEnvironment();
    if (!env)
        FATAL("NewEnvironment", "failed");

    IM3Runtime runtime = m3_NewRuntime(env, WASM_STACK_SLOTS, NULL);
    if (!runtime)
        FATAL("NewRuntime", "failed");

#ifdef WASM_MEMORY_LIMIT
    runtime->memoryLimit = WASM_MEMORY_LIMIT;
#endif

    String filename = getActiveDeploymentFilename();
    Serial.println("Loading file " + filename);
    File file = SPIFFS.open(getActiveDeploymentFilename(), "r");
    auto fileSize = file.size();
    unsigned char wasm_buffer[fileSize];
    auto i = 0;
    while (file.available())
    {
        wasm_buffer[i] = file.read();
        i++;
    }
    file.close();

    IM3Module module;
    result = m3_ParseModule(env, &module, wasm_buffer, fileSize);
    if (result)
        FATAL("ParseModule", result);

    result = m3_LoadModule(runtime, module);
    if (result)
        FATAL("LoadModule", result);

    result = LinkHostbindings(runtime);
    if (result)
        FATAL("LinkHostbindings", result);

    IM3Function f;
    result = m3_FindFunction(&f, runtime, "_start");
    if (result)
        FATAL("FindFunction", result);

    Serial.println("Running WebAssembly...");

    result = m3_CallV(f);

    if (result)
    {
        M3ErrorInfo info;
        m3_GetErrorInfo(runtime, &info);
        Serial.print("Error: ");
        Serial.print(result);
        Serial.print(" (");
        Serial.print(info.message);
        Serial.println(")");
        if (info.file && strlen(info.file) && info.line)
        {
            Serial.print("At ");
            Serial.print(info.file);
            Serial.print(":");
            Serial.println(info.line);
        }
    }

    vTaskDelete(NULL);
}

void run_wasm(void *)
{
    Serial.println("Running active Deployment");
    run_deployment();
    Serial.println("Failed to run active Deployment");

    // arriving here means that the startup of the deployment failed
    // try again with other deployment
    Serial.println("Fall back to previous Deployment");
    switchActiveDeployment();
    run_deployment();
}

/**
 * This maps the GPIO pins from the wasm app to the hardware ones
 */
void mapGpioPins()
{
    char mapping[strlen(gpio_pin_mapping_raw)];
    strcpy(mapping, gpio_pin_mapping_raw);
    char *end_str;
    char *group = strtok_r(mapping, ",", &end_str);

    while (group != NULL)
    {
        char *end_token;
        char *pin = strtok_r(group, ":", &end_token);
        char *virtualPin = pin;
        char *realPin = strtok_r(NULL, ":", &end_token);
        virtual_gpio_pins[atoi(virtualPin) - 1] = atoi(realPin);
        group = strtok_r(NULL, ",", &end_str);
    }
}

void initWasmRuntime()
{
    mapGpioPins();

    if (wasmTaskHandle)
    {
        vTaskDelete(wasmTaskHandle);
        wasmTaskHandle = NULL;
    }

    Serial.println("\nWasm3 v" M3_VERSION " (" M3_ARCH "), build " __DATE__ " " __TIME__);

    // On ESP32 we can launch in a separate thread
#ifdef ESP32
    xTaskCreate(&run_wasm, "wasm3", NATIVE_STACK_SIZE, NULL, 5, &wasmTaskHandle);
#else
    run_wasm(NULL);
#endif
}
