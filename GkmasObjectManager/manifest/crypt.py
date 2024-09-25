"""
crypt.py
[INTERNAL] GkmasManifest decryptor.
"""

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

    def __init__(self, key: bytes, iv: bytes):
        """
        Initializes the decryptor with the given key and IV.

        Args:
            key (bytes): The AES key.
            iv (bytes): The AES initialization vector.
        """

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
