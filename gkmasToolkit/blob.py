from .utils import Logger, GKMAS_OBJECT_SERVER

import requests
from pathlib import Path


logger = Logger()


class GkmasResource:

    def __init__(self, info: dict):

        self.id = info["id"]
        self.name = info["name"]
        self.size = info["size"]
        self.state = info["state"]
        self.md5 = info["md5"]
        self.objectName = info["objectName"]

    def __repr__(self):
        return f"<GkmasResource {self.name}>"

    def download(self, path: str):

        # don't expect the client to import pathlib in advance
        path = Path(path)

        if path.suffix == "":  # is directory
            path.mkdir(parents=True, exist_ok=True)
            path = path / self.name

        if path.exists():
            logger.info(f"'{self.name}' exists, skipping download.")
            return

        url = f"{GKMAS_OBJECT_SERVER}/{self.objectName}"
        response = requests.get(url)
        if response.status_code == 200:
            Path(path).write_bytes(response.content)
            logger.success(f"'{self.name}' has been downloaded.")
        else:
            logger.error(f"'{self.name}' download failed.")


class GkmasAssetBundle(GkmasResource):

    def __init__(self, info: dict):

        super().__init__(info)
        self.name = info["name"] + ".unity3d"
        self.crc = info["crc"]

    def __repr__(self):
        return f"<GkmasAssetBundle {self.name}>"

    def download(self, path: str):

        super().download(path)
        _unobfuscate(path, self.crc)
