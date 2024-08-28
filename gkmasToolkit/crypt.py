from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from .utils import *


class GkmasManifestDecryptor:

    def __init__(self, key: str = GKMAS_OCTOCACHE_KEY, iv: str = GKMAS_OCTOCACHE_IV):

        key = bytes(key, "utf-8")
        iv = bytes(iv, "utf-8")
        key = md5(key).digest()
        iv = md5(iv).digest()
        self.cipher = AES.new(key, AES.MODE_CBC, iv)

    def decrypt(self, ciphertext: bytes) -> bytes:

        # for some reason there's a single extra 0x01 byte preceding ciphertext
        clen = len(ciphertext) // 16 * 16
        ciphertext = ciphertext[-clen:]

        plaintext = self.cipher.decrypt(ciphertext)
        plaintext = unpad(plaintext, block_size=16, style="pkcs7")

        return plaintext[16:]  # skip md5 hash