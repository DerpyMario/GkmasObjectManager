"""
_crypt.py
[INTERNAL] GkmasManifest decryptor.
"""

from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class AESCBCDecryptor:
    """
    General-purpose AES decryptor (CBC mode).

    Attributes:
        cipher (Crypto.Cipher.AES): AES cipher object.

    Methods:
        decrypt(enc: bytes) -> bytes:
            Decrypts the given ciphertext into plaintext.
    """

    def __init__(self, key: str, iv: str):
        """
        Initializes the decryptor with the given key and IV.

        Args:
            key (str): An UTF-8 encoded string whose MD5 hash is the AES key.
            iv (str): An UTF-8 encoded string whose MD5 hash is the AES initialization vector.
        """

        key = bytes(key, "utf-8")
        iv = bytes(iv, "utf-8")
        key = md5(key).digest()
        iv = md5(iv).digest()
        self.cipher = AES.new(key, AES.MODE_CBC, iv)

    def decrypt(self, enc: bytes) -> bytes:
        """
        Decrypts the given ciphertext into plaintext.

        Args:
            enc (bytes): The encrypted bytes to decrypt.
                For some reason there's a single extra 0x01 byte preceding ciphertext
                downloaded from the server, so the method also ensures that
                ciphertext is 16-byte aligned by trimming these leading bytes.
        """

        clen = len(enc) // 16 * 16
        enc = enc[-clen:]

        dec = self.cipher.decrypt(enc)
        dec = unpad(dec, block_size=16, style="pkcs7")

        return dec
