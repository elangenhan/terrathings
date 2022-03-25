#!/bin/bash

# fetch dependencies if missing
[ ! -d "./node_modules" ] && npm i

npm run build

rm -rf build
mkdir -p build

mv app.wasm build/

