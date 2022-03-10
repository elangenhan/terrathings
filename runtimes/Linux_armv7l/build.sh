#!/bin/bash

echo "Creating runtime.tar.gz"

rm -rf build && mkdir -p build
echo $gpio_pin_mapping > runtime/gpio_pin_mapping.txt
echo $VERIFICATION_KEY > runtime/verification_key
tar --sort=name --mtime='1970-01-01' --exclude='./build' --exclude='./build.sh' -zcvf runtime.tar.gz * > /dev/null 2>&1
mv runtime.tar.gz build/
