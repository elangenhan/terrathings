#!/bin/bash

~/.platformio/penv/bin/pio run

rm -rf build
mkdir -p build && cp .pio/build/ESP32/firmware.bin build/

