from .utils import Logger, GKMAS_OBJECT_SERVER, UNITY_SIGNATURE
from .crypt import GkmasDeobfuscator

import requests
import hashlib
from pathlib import Path


logger = Logger()


class GkmasResource:

    def __init__(self, info: dict):

        self.id = info["id"]
        self.name = info["name"]
        self.size = info["size"]
        self.state = info["state"]  # unused
        self.md5 = info["md5"]
        self.objectName = info["objectName"]
        self._idname = f"[{self.id:04}] '{self.name}'"

    def __repr__(self):
        return f"<GkmasResource {self._idname}>"

    def download(self, path: str):

        path = self.__download_path(path)
        if path.exists():
            logger.info(f"{self._idname} already exists.")
            return

        plain = self.__download_bytes()
        path.write_bytes(plain)
        logger.success(f"{self._idname} has been downloaded.")

    def __download_path(self, path: str) -> Path:

        # don't expect the client to import pathlib in advance
        path = Path(path)

        if path.suffix == "":  # is directory
            path.mkdir(parents=True, exist_ok=True)
            path = path / self.name

        return path

    def __download_bytes(self) -> bytes:

        url = f"{GKMAS_OBJECT_SERVER}/{self.objectName}"
        response = requests.get(url)

        if response.status_code != 200:
            logger.error(f"{self._idname} download failed.")
            return b""

        if len(response.content) != self.size:
            logger.error(f"{self._idname} has invalid size.")
            return b""

        if hashlib.md5(response.content).hexdigest() != self.md5:
            logger.error(f"{self._idname} has invalid MD5 hash.")
            return b""

        return response.content


class GkmasAssetBundle(GkmasResource):

    def __init__(self, info: dict):

        super().__init__(info)
        self.crc = info["crc"]  # unused (for now)
        self._idname = f"[{self.id:04}] '{self.name}.unity3d'"

    def __repr__(self):
        return f"<GkmasAssetBundle {self._idname}>"

    def download(self, path: str):

        path = self.__download_path(path)
        if path.exists():
            logger.info(f"{self._idname} already exists.")
            return

        cipher = self.__download_bytes()

        if cipher[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
            path.write_bytes(cipher)
            logger.success(f"{self._idname} has been downloaded.")
        else:
            deobfuscator = GkmasDeobfuscator(self.name)
            plain = deobfuscator.decrypt(cipher)
            if plain[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
                path.write_bytes(plain)
                logger.success(f"{self._idname} has been downloaded and deobfuscated.")
            else:
                path.write_bytes(cipher)
                logger.error(f"{self._idname} has been downloaded but left obfuscated.")
