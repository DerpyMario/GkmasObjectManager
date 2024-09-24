"""
crypt.py
Manifest decryptor and object deobfuscator.
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


class GkmasDeobfuscator:
    """
    Assetbundle deobfuscator for GKMAS.
    Algorithm courtesy of github.com/MalitsPlus.
    ('maskString' is refactored to 'key' and 'maskBytes' to 'mask'.)

    Attributes:
        mask (bytes): Obfuscation mask.
        offset (int): Byte write pointer offset.
        stream_pos (int): Byte read pointer offset.
        header_len (int): Length of the obfuscated header.

    Methods:
        deobfuscate(cipher: bytes) -> bytes:
            Deobfuscates the given obfuscated bytes into plaintext.
    """

    def __init__(
        self,
        key: str,
        offset: int = 0,
        stream_pos: int = 0,
        header_len: int = 256,
    ):
        """
        Initializes a deobfuscator with given key and parameters.

        Args:
            key (str): A string key for making mask.
            offset (int) = 0: Byte write pointer offset.
            stream_pos (int) = 0: Byte read pointer offset.
            header_len (int) = 256: Length of the obfuscated header.
        """

        self.offset = offset
        self.stream_pos = stream_pos
        self.header_len = header_len
        self.mask = self._make_mask(key)

    def _make_mask(self, key: str) -> bytes:
        """
        [INTERNAL] Generates an obfuscation mask from the given key.
        """

        keysize = len(key)
        masksize = keysize * 2
        mask = bytearray(masksize)
        key = bytes(key, "utf-8")

        for i, char in enumerate(key):
            mask[i * 2] = char
            mask[masksize - 1 - i * 2] = ~char & 0xFF  # cast to unsigned

        x = 0x9B
        for b in mask:
            x = (((x & 1) << 7) | (x >> 1)) ^ b

        return bytes([b ^ x for b in mask])

    def deobfuscate(self, enc: bytes) -> bytes:
        """
        Deobfuscates the given obfuscated bytes into plaintext.

        Args:
            enc (bytes): The obfuscated bytes to deobfuscate.
        """

        buf = bytearray(enc)

        i = 0
        masksize = len(self.mask)
        while self.stream_pos + i < self.header_len:
            buf[self.offset + i] ^= self.mask[
                self.stream_pos + i - int((self.stream_pos + i) / masksize) * masksize
            ]
            i += 1

        return bytes(buf)
