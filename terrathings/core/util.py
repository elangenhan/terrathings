import os
from nacl.encoding import Base64Encoder, HexEncoder, URLSafeBase64Encoder
from nacl.signing import SigningKey

key_length = 32
private_key_signature = b"\x00\x00\x00\x40"
public_key_signature = b"\x00\x00\x00\x20"

device_ip_cache_filename = ".device_ip.cache"


def read_device_ip_from_cache(device_id: str):
    """
    Reads the cache file and looks if it has seen the device before

    :param str device_id: ID of the device to look for

    :returns: IP of the device, None otherwise
    :rtype: str or None
    """

    print("Reading ip from cache: " + device_id)
    with open(device_ip_cache_filename, "r") as f:
        for line in reversed(f.readlines()):
            if line.startswith(device_id):
                return line.split()[1]


def write_device_ip_to_cache(device_id: str, ip: str):
    """
    Writes the IP of the device to the cache file

    :param str device_id: ID of the device
    :param str ip: IP of the device
    """

    if not os.path.exists(device_ip_cache_filename):
        with open(device_ip_cache_filename, "w") as f:
            f.write("")

    current = read_device_ip_from_cache(device_id)
    if current is None or current != ip:
        with open(device_ip_cache_filename, "a+") as f:
            f.write(f"{device_id} {ip}\n")


def sign_file(file_path: str, sign_key: str):
    """
    Sign a file with the given key

    :param str file_path: path to the file to sign
    :param str sign_key: private key to sign the file with. Expects it to be in Base64 format.
    """

    signing_key = extract_curve_private_key(sign_key)
    signed = signing_key.sign(get_sha256_hash(file_path), encoder=Base64Encoder)
    signature = signed.signature

    """ Replacing padding characters for uri encoding. """
    signature = signature.decode("utf-8").replace("+", "-").replace("/", "_")

    with open(file_path + ".sha256.signed", "wb") as f:
        f.write(signature.encode("utf-8"))


def get_pubkey(sign_key):
    """
    Get the public key from the given private key

    :param str sign_key: private key to get the public key from. Expects it to be in Base64 format.

    :return: public key in Hex format
    :rtype: str
    """
    signing_key = extract_curve_private_key(sign_key)
    return signing_key.verify_key.encode(encoder=HexEncoder)


def get_sha256_hash(file_path):
    """
    Get the sha256 hash of the given file

    :param str file_path: path to the file to get the hash of

    :return: sha256 hash of the file in byte format
    :rtype: bytes
    """
    import hashlib

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.digest()


def bytes_from_file(file_path, chunksize=8192):
    """
    Reads the given file and returns the contents as a byte array

    :param str file_path: path to the file to read
    :param int chunksize: size of the chunks to read

    :returns: the contents of the file as a byte array
    :rtype: bytearray
    """
    with open(file_path, "rb") as f:
        while True:
            if chunk := f.read(chunksize):
                yield from chunk
            else:
                break


def bytes_after(signature, length, bytestr):
    """
    Returns the bytes after the given signature

    :param bytes signature: the signature to find the bytes after
    :param int length: the length of the bytes to return
    :param bytes bytestr: the bytes to search in

    :returns: the bytes after the signature
    :rtype: bytes
    """
    start = bytestr.find(signature) + len(signature)
    return bytestr[start : start + length]


def extract_curve_private_key(openssh_priv_key):
    """
    Returns the curve private key from the openssh private key

    :param str openssh_priv_key: openssh private key

    :returns: the curve private key
    """
    return SigningKey(seed=openssh_priv_key, encoder=URLSafeBase64Encoder)
