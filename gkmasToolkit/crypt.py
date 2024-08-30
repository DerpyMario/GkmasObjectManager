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
        self, key: str, offset: int = 0, stream_pos: int = 0, header_len: int = 256
    ):
        # 'maskString' is now 'key'
        # 'maskBytes' is now 'mask'

        self.offset = offset
        self.stream_pos = stream_pos
        self.header_len = header_len
        self.mask = self._makemask(key)

    def _makemask(key: str) -> bytes:
        # Algorithm courtesy of github.com/MalitsPlus

        masksize = len(key) << 1
        mask = bytearray(masksize)

        if len(key) >= 1:
            i = 0
            j = 0
            k = masksize - 1
            while j != len(key):
                charJ = key[j]
                charJ = int.from_bytes(
                    charJ.encode("ascii"), byteorder="little", signed=False
                )  # Must be casted as Int in python
                j += 1
                mask[i] = charJ
                i += 2
                charJ = ~charJ & 0xFF  # Must AND 0xFF to get an unsigned integer
                mask[k] = charJ
                k -= 2

        if masksize >= 1:
            l = masksize
            m = masksize
            n = 0x9B
            ptr = 0
            while m:
                v16 = mask[ptr]
                ptr += 1
                m -= 1
                n = (((n & 1) << 7) | (n >> 1)) ^ v16
            b = 0
            while l:
                l -= 1
                mask[b] ^= n
                b += 1

        return bytes(mask)

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
