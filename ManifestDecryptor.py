import hashlib
import json
import octodb_pb2
import sqlite3
import sys
import re
from rich.console import Console
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from pathlib import Path
from google.protobuf.json_format import MessageToJson

# Currently known magic strings
__KEY = "1nuv9td1bw1udefk"
__IV = "LvAUtf+tnz"

# Input cache file and output directory strings
__inputPathString = "./EncryptedCache/octocacheevai"
__outputPathString = "./DecryptedCache"

# Initialization
console = Console()


def __decryptCache(key=__KEY, iv=__IV) -> octodb_pb2.Database:
    """Decrypts a cache file (usually named 'octocacheevai') and deserializes it to a protobuf object

    Args:
        key (string): A byte-string. Currently 16 characters long and appears to be alpha-numeric.
        iv (string): A byte-string. Currently 10 characters long and appears to be base64-ish.

    Returns:
        octodb_pb2.Database: A protobuf object representing the deserialized cache.
    """
    key = bytes(key, "utf-8")
    iv = bytes(iv, "utf-8")

    key = hashlib.md5(key).digest()
    iv = hashlib.md5(iv).digest()

    cipher = AES.new(key, AES.MODE_CBC, iv)
    encryptCachePath = Path(__inputPathString)

    try:
        encryptedBytes = encryptCachePath.read_bytes()
    except:
        console.print(
            f"[bold red]>>> [Error][/bold red] Failed to load encrypted cache file at '{encryptCachePath}'.\n{sys.exc_info()}\n"
        )
        raise

    try:
        # For some reason there's a single extra 0x01 byte at the start of the encrypted file
        decryptedBytes = unpad(
            cipher.decrypt(encryptedBytes[1:]), block_size=16, style="pkcs7"
        )
    except:
        console.print(
            f"[bold red]>>> [Error][/bold red] Failed to decrypt cache file.\n{sys.exc_info()}\n"
        )
        raise

    # The first 16 bytes are an md5 hash of the database that follows it, which is skipped because it's useless for this purpose
    decryptedBytes = decryptedBytes[16:]
    # Read the decrypted bytes to a protobuf object
    protoDatabase = octodb_pb2.Database()
    protoDatabase.ParseFromString(decryptedBytes)
    # Revision number should probably change with every update..?
    console.print(
        f"[bold]>>> [Info][/bold] Current revision : {protoDatabase.revision}\n"
    )
    # Get output dir and append it to the filename
    outputPath = Path(f"{__outputPathString}\manifest_v{protoDatabase.revision}")
    # Write the decrypted cache to a local file
    try:
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        outputPath.write_bytes(decryptedBytes)
        console.print(
            f"[bold green]>>> [Succeed][/bold green] Decrypted cache has been written into {outputPath}.\n"
        )
    except:
        console.print(
            f"[bold red]>>> [Error][/bold red] Failed to write decrypted file into {outputPath}.\n{sys.exc_info()}\n"
        )
        raise

    return protoDatabase


def __protoDb2Json(protoDb: octodb_pb2.Database) -> str:
    """Converts a protobuf serialized object to JSON string then return the string."""
    jsonDb = MessageToJson(protoDb)
    return jsonDb


def __writeJsonFile(d: dict, path: Path):
    # Write the string to a json file
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(d, sort_keys=True, indent=4))
        console.print(
            f"[bold green]>>> [Succeed][/bold green] JSON has been written into {path}.\n"
        )
    except:
        console.print(
            f"[bold red]>>> [Error][/bold red] Failed to write JSON into {path}.\n{sys.exc_info()}\n"
        )
        raise


def __appendType(d: dict) -> dict:
    for it in d["assetBundleList"]:
        m = re.match(r"(.+?)_.*$", it["name"])  # Matches first _ in name
        if m:
            typeStr = m.group(1)
        else:
            typeStr = "others"
        it["type"] = typeStr
    for it in d["resourceList"]:
        m = re.match(r"(.+?)_.*$", it["name"])  # Matches first _ in name
        if m:
            typeStr = m.group(1)
        else:
            typeStr = "others"
        it["type"] = typeStr
    return d


def doDecrypt() -> dict:
    protoDb = __decryptCache()
    jsonString = __protoDb2Json(protoDb)
    jDict = json.loads(jsonString)
    jDict = __appendType(jDict)
    outputPath = Path(f"{__outputPathString}\manifest_v{protoDb.revision}.json")
    __writeJsonFile(jDict, outputPath)
