from .utils import Logger, GKMAS_OBJECT_SERVER
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

    def __repr__(self):
        return f"<GkmasResource [{self.id:04}] '{self.name}'>"

    def download(self, path: str):

        path = self._download_path(path)
        if path.exists():
            logger.info(f"[{self.id:04}] '{self.name}' already exists.")
            return

        plain = self._download_bytes()
        path.write_bytes(plain)
        logger.success(f"[{self.id:04}] '{self.name}' has been downloaded.")

    def _download_path(self, path: str) -> Path:

        # don't expect the client to import pathlib in advance
        path = Path(path)

        if path.suffix == "":  # is directory
            path.mkdir(parents=True, exist_ok=True)
            path = path / self.name

        return path

    def _download_bytes(self) -> bytes:

        url = f"{GKMAS_OBJECT_SERVER}/{self.objectName}"
        response = requests.get(url)

        if response.status_code != 200:
            logger.error(f"[{self.id:04}] '{self.name}' download failed.")
            return b""

        if len(response.content) != self.size:
            logger.error(f"[{self.id:04}] '{self.name}' has invalid size.")
            return b""

        md5_hash = hashlib.md5(response.content).hexdigest()
        if md5_hash != self.md5:
            logger.error(f"[{self.id:04}] '{self.name}' has invalid MD5 hash.")
            return b""

        return response.content


class GkmasAssetBundle(GkmasResource):

    def __init__(self, info: dict):

        super().__init__(info)
        self.name = info["name"] + ".unity3d"
        self.crc = info["crc"]

    def __repr__(self):
        return f"<GkmasAssetBundle '{self.name}'>"

    def download(self, path: str):

        path = self._download_path(path)
        if path.exists():
            logger.info(f"'{self.name}' already exists.")
            return

        cipher = self._download_bytes()
        deobfuscator = GkmasDeobfuscator(self.md5)
        plain = deobfuscator.decrypt(cipher)
        path.write_bytes(plain)
        logger.success(f"'{self.name}' has been downloaded.")
