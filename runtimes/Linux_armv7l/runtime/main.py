import time, traceback, os, base64
from multiprocessing import Process
from fastapi import FastAPI, Request
from nacl.encoding import HexEncoder, URLSafeBase64Encoder, Base64Encoder
from nacl.signing import VerifyKey
import hashlib
import deployment

app = FastAPI()
data_dir = f"{os.getcwd()}/../data"
verification_key = None
with open("verification_key", "r") as f:
    verification_key = f.read().strip("\n")


@app.get("/status")
def get_status():
    def read_file(file):
        if not os.path.exists(file):
            return False
        with open(file, "r") as f:
            return f.read().strip("\n")

    status = {}

    active_runtime = read_file(f"{data_dir}/active_runtime")
    if active_runtime:
        status["runtime"] = {}
        runtime_data = read_file(f"{data_dir}/runtime_{active_runtime}.sha256")
        if runtime_data:
            active_runtime_hash, runtime_id = runtime_data.split(" ")
            status["runtime"]["id"] = runtime_id
            status["runtime"]["sha256"] = active_runtime_hash

    active_deployment = read_file(f"{data_dir}/active_deployment")
    if active_deployment:
        status["deployment"] = {}
        deployment_data = read_file(f"{data_dir}/deployment_{active_deployment}.sha256")
        if deployment_data:
            active_deployment_hash, deployment_id = deployment_data.split(" ")
            status["deployment"]["id"] = deployment_id
            status["deployment"]["sha256"] = active_deployment_hash

    return status


@app.post("/update")
async def update(request: Request):
    form = await request.form()
    file = await next(iter(form.values())).read()

    params = request.query_params
    if "type" not in params:
        return {"error": "No type specified: please specify if partial or full update"}

    if "signature" not in params:
        return {
            "error": "No hash specified: please provide the signature of the update file"
        }

    sha256hash = get_sha256(file)
    if not verify_file(sha256hash, params["signature"]):
        return {"error": "Invalid signature"}

    if params["type"] == "partial":
        deployment.update_partial(file, sha256hash, params["deployment_id"])
    elif params["type"] == "full":
        update_full(file, sha256hash, params["runtime_id"])

    return 200


def get_active_runtime():
    if os.path.isfile(f"{data_dir}/active_runtime"):
        with open(f"{data_dir}/active_runtime", "rb") as f:
            return f.read().decode("utf-8").strip("\n")
    else:
        with open(f"{data_dir}/active_runtime", "w") as f:
            f.write("A")
        return "A"


def get_inactive_runtime():
    if get_active_runtime() == "A":
        return "B"
    else:
        return "A"


def switch_runtime():
    inactive = get_inactive_runtime()
    with open(f"{data_dir}/active_runtime", "w") as f:
        f.write(inactive)

    os.system("sudo systemctl restart terrathings")


def update_full(file, sha256hash, runtime_id):
    inactive_runtime = get_inactive_runtime()
    try:
        with open(f"{data_dir}/runtime_{inactive_runtime}.tar.gz", "wb") as f:
            f.write(file)
        with open(f"{data_dir}/runtime_{inactive_runtime}.sha256", "wb") as f:
            f.write(sha256hash)
            f.write(b" ")
            f.write(runtime_id.encode() + b"\n")

        os.system(
            f"rm -rf {data_dir}/../runtime_{inactive_runtime} && tar -xzf {data_dir}/runtime_{inactive_runtime}.tar.gz -C /opt/terrathings/ && mv {data_dir}/../runtime {data_dir}/../runtime_{inactive_runtime}"
        )
        switch_runtime()
    except Exception as e:
        print(e)


def verify_file(content, signature):
    verify_key = VerifyKey(verification_key, encoder=Base64Encoder)
    signature = Base64Encoder.decode(signature.replace("-", "+").replace("_", "/"))
    return verify_key.verify(content, signature, encoder=Base64Encoder)


def get_sha256(bytes):
    sha256hash = hashlib.sha256()
    sha256hash.update(bytes)
    return base64.b64encode(sha256hash.digest())


deployment.start_wasm_process()
