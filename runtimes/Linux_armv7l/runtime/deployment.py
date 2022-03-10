import os
import wasm3, base64, time, traceback, os
from multiprocessing import Process
from fastapi import FastAPI, Request
from gpiozero import LED

data_dir = f"{os.getcwd()}/../data"
wasm_process_handler = None


def update_partial(file, sha256hash, deployment_id):
    inactive_deployment = get_inactive_deployment()
    try:
        with open(f"{data_dir}/deployment_{inactive_deployment}.wasm", "wb") as f:
            f.write(file)
        with open(f"{data_dir}/deployment_{inactive_deployment}.sha256", "wb") as f:
            f.write(sha256hash)
            f.write(b" ")
            f.write(deployment_id.encode())
        switch_deployment()
        restart_wasm_process()
    except Exception as e:
        print(e)


def get_active_deployment():
    if os.path.isfile(f"{data_dir}/active_deployment"):
        with open(f"{data_dir}/active_deployment", "r") as f:
            return f.read().strip("\n")
    else:
        with open(f"{data_dir}/active_deployment", "w") as f:
            f.write("A")
        return "A"


def get_inactive_deployment():
    return "B" if get_active_deployment() == "A" else "A"


def switch_deployment():
    with open(f"{data_dir}/active_deployment", "r+") as f:
        data = f.read()
        new_data = "B" if data == "A" else "A"
        f.seek(0)
        f.write(new_data)
        f.truncate()


def env_delay(s):
    time.sleep(float(s) / 1000)
    return 0


def env_print(m3rt, *args):
    out = bytearray.fromhex(
        m3rt.get_memory(0)[args[0] : args[0] + args[1]].hex()
    ).decode()
    print(out.strip("\n"))
    return 0


def env_pinMode(pin, mode):
    """
    " This function is actually not required, because gpiozero does it automatically.
    " But the WebAssembly App expects this function to be present, so this is a dummy.
    """
    pass


LEDs = {}

gpio_pin_mapping = {}
try:
    with open("gpio_pin_mapping.txt", "rb") as f:
        raw = f.read()
        mapping = raw.decode().strip("\n").split(",")
        for m in mapping:
            gpio_pin_mapping[int(m.split(":")[0])] = int(m.split(":")[1])
        print("GPIO Pin Mapping: " + gpio_pin_mapping)
except Exception:
    print("No gpio_pin_mapping.txt found, using default mapping.")


def env_digitalWrite(pin, value):
    print(f"digitalWrite({pin}, {value})")
    if pin in gpio_pin_mapping:
        pin = gpio_pin_mapping[pin]
        print(f"Mapped pin {pin}")

    led = None
    if pin not in LEDs:
        led = LED(pin)
        LEDs[pin] = led
    else:
        led = LEDs[pin]

    if value == 1:
        led.on()
    elif value == 0:
        led.off()


def setup_wasm(file):
    env = wasm3.Environment()
    m3rt = env.new_runtime(4096)

    with open(f"{data_dir}/deployment_{get_active_deployment()}.wasm", "rb") as f:
        mod = env.parse_module(f.read())
        m3rt.load(mod)

        mod.link_function("hostbindings", "delay", "v(i)", env_delay)
        mod.link_function(
            "hostbindings", "print", "v(*i)", lambda *x: env_print(m3rt, *x)
        )
        mod.link_function(
            "hostbindings", "println", "v(*i)", lambda *x: env_print(m3rt, *x)
        )
        mod.link_function("hostbindings", "pinMode", "v(ii)", env_pinMode)
        mod.link_function("hostbindings", "digitalWrite", "v(ii)", env_digitalWrite)

        start = m3rt.find_function("_start")
        start()


def start_wasm_process():
    if not os.path.isfile(f"{data_dir}/deployment_{get_active_deployment()}.wasm"):
        print("No deployment found, idleing...")
        return

    print("Starting wasm")
    try:
        global wasm_process_handler
        wasm_process_handler = Process(
            target=setup_wasm, daemon=True, args=("app.wasm",)
        )
        wasm_process_handler.start()
    except Exception as e:
        print(e)
        print(traceback.format_exc())

        """ Fall back to previous deployment """
        switch_deployment()
        restart_wasm_process()


def restart_wasm_process():
    print("Restarting wasm process...")
    if wasm_process_handler:
        wasm_process_handler.terminate()
        wasm_process_handler.join()
    start_wasm_process()
