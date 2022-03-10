# Terrathings
This is a proof-of-concept that helps to install and update applications on IoT devices. This demo includes a WebAssembly application that gets deployed to a Raspberry Pi and an ESP32 microcontroller using Wasm3.

## Setup
Make sure to install the dependencies for the controller with:
```bash
pip install -r requirements.txt
```
and also to install dependencies for every deployment/device runtime.

## Configuration
The configuration consists of the following:
* Applications
	* ID
	* Commands to create or fetch them
* Devices
	* ID
	* Commands to create or fetch them
	* Connections: one for initialization and one for updating later on
	* reference to applications to deploy

## Usage
```bash
# Basic structure of the cli
./tt --config config.yaml <cmd> [<device_ids>]

./tt --config config.yaml build # compiles all applications and runtimes
./tt --config config.yaml init # initializes all devices
./tt --config config.yaml update # updates the deployments on all devices
./tt --config config.yaml apply # combines all the above

# The actions can also be limited to certain devices
./tt --config config.yaml init esp # initializes a device with ID esp

# Or only certain deployments
./tt --config config.yaml --deployment blink update # updates the deployment with the ID blink on all devices it is referenced

```


