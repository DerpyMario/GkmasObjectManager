from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class AESDecryptor:

    def __init__(self, key: str, iv: str):

        key = bytes(key, "utf-8")
        iv = bytes(iv, "utf-8")
        key = md5(key).digest()
        iv = md5(iv).digest()
        self.cipher = AES.new(key, AES.MODE_CBC, iv)

    def decrypt(self, ciphertext: bytes) -> bytes:

        # This ensures that ciphertext is 16-byte aligned;
        # for some reason there's a single extra 0x01 byte preceding ciphertext
        clen = len(ciphertext) // 16 * 16
        ciphertext = ciphertext[-clen:]

        plaintext = self.cipher.decrypt(ciphertext)
        plaintext = unpad(plaintext, block_size=16, style="pkcs7")

        return plaintext


class GkmasDeobfuscator:

    def __init__(
        self,
        key: str,
        offset: int = 0,
        stream_pos: int = 0,
        header_len: int = 256,
    ):
        # Algorithm courtesy of github.com/MalitsPlus
        # 'maskString' is now 'key'
        # 'maskBytes' is now 'mask'

        self.offset = offset
        self.stream_pos = stream_pos
        self.header_len = header_len
        self.mask = self.__make_mask(key)

    def __make_mask(self, key: str) -> bytes:

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

    def decrypt(self, cipher: bytes) -> bytes:

        buf = bytearray(cipher)

        i = 0
        masksize = len(self.mask)
        while self.stream_pos + i < self.header_len:
            buf[self.offset + i] ^= self.mask[
                self.stream_pos + i - int((self.stream_pos + i) / masksize) * masksize
            ]
            i += 1

        return bytes(buf)
