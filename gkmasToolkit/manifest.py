import hashlib
import octodb_pb2
import json

from utils import Logger
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from google.protobuf.json_format import MessageToJson
from pathlib import Path


# Input cache file and output directory strings
__inputPathString = "./EncryptedCache/octocacheevai"
__outputPathString = "./DecryptedCache"


# Initialization
logger = Logger()


def __decryptCache(key=KEY, iv=IV) -> octodb_pb2.Database:
    """
    Decrypts a cache file (usually named 'octocacheevai') and deserializes it to a protobuf object

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
        logger.error(
            f"Failed to load encrypted cache file at '{encryptCachePath}'.", fatal=True
        )

    try:
        # For some reason there's a single extra 0x01 byte at the start of the encrypted file
        decryptedBytes = unpad(
            cipher.decrypt(encryptedBytes[1:]), block_size=16, style="pkcs7"
        )
    except:
        logger.error("Failed to decrypt cache file.", fatal=True)

    # The first 16 bytes are an md5 hash of the database that follows it, which is skipped because it's useless for this purpose
    decryptedBytes = decryptedBytes[16:]
    # Read the decrypted bytes to a protobuf object
    protoDatabase = octodb_pb2.Database()
    protoDatabase.ParseFromString(decryptedBytes)
    # Revision number should probably change with every update..?
    logger.info(f"Current revision: {protoDatabase.revision}")
    # Get output dir and append it to the filename
    outputPath = Path(f"{__outputPathString}\manifest_v{protoDatabase.revision}")
    # Write the decrypted cache to a local file
    try:
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        outputPath.write_bytes(decryptedBytes)
        logger.success(f"Decrypted cache has been written into {outputPath}.")
    except:
        logger.error(f"Failed to write decrypted file into {outputPath}.", fatal=True)

    return protoDatabase


def __protoDb2Json(protoDb: octodb_pb2.Database) -> dict:

    return json.loads(MessageToJson(protoDb))


def __writeJsonFile(d: dict, path: Path):

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(d, sort_keys=True, indent=4))
        logger.success(f"JSON has been written into {path}.")
    except:
        logger.error(f"Failed to write JSON into {path}.", fatal=True)


def doDecrypt() -> dict:
    protoDb = __decryptCache()
    jDict = __protoDb2Json(protoDb)
    outputPath = Path(f"{__outputPathString}\manifest_v{protoDb.revision}.json")
    __writeJsonFile(jDict, outputPath)
