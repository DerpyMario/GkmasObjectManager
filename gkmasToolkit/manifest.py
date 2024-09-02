from .utils import Logger
from .crypt import AESDecryptor
from .octodb_pb2 import Database
from .blob import GkmasAssetBundle, GkmasResource
from .const import (
    GKMAS_OCTOCACHE_KEY,
    GKMAS_OCTOCACHE_IV,
    DEFAULT_DOWNLOAD_PATH,
    ALL_ASSETBUNDLES,
    ALL_RESOURCES,
    CSV_COLUMNS,
)

import re
import json
from google.protobuf.json_format import MessageToJson
from pandas import DataFrame
from pathlib import Path


# The logger would better be a global variable in the
# modular __init__.py, but Python won't allow me to
logger = Logger()


class GkmasManifest:

    def __init__(
        self,
        path: str,
        key: str = GKMAS_OCTOCACHE_KEY,
        iv: str = GKMAS_OCTOCACHE_IV,
    ):

        protodb = Database()
        ciphertext = Path(path).read_bytes()

        try:
            self.raw = ciphertext
            protodb.ParseFromString(self.raw)
            logger.info("ProtoDB is not encrypted")
        except:
            decryptor = AESDecryptor(key, iv)
            plaintext = decryptor.decrypt(ciphertext)
            self.raw = plaintext[16:]  # trim md5 hash
            protodb.ParseFromString(self.raw)
            logger.info("ProtoDB has been decrypted")

        self.revision = protodb.revision
        logger.info(f"Manifest revision: {self.revision}")

        self.jdict = json.loads(MessageToJson(protodb))
        self.abs = [GkmasAssetBundle(ab) for ab in self.jdict["assetBundleList"]]
        self.reses = [GkmasResource(res) for res in self.jdict["resourceList"]]
        self.__name2blob = {ab.name: ab for ab in self.abs}  # quick lookup
        self.__name2blob.update({res.name: res for res in self.reses})
        logger.info(f"Number of assetbundles: {len(self.abs)}")
        logger.info(f"Number of resources: {len(self.reses)}")

    # ------------ Download ------------

    def download(
        self,
        *criteria: str,
        path: str = DEFAULT_DOWNLOAD_PATH,
    ):
        # dispatcher

        for criterion in criteria:
            if criterion == ALL_ASSETBUNDLES:  # similar to 'tokens' in NLP
                for ab in self.abs:
                    ab.download(path)
            elif criterion == ALL_RESOURCES:
                for res in self.reses:
                    res.download(path)
            else:
                for file in filter(re.compile(criterion).match, self.__name2blob):
                    self.__name2blob[file].download(path)

    # ------------ Export ------------

    def export(self, path: str):
        # dispatcher

        path = Path(path)

        if path.suffix == "":  # used to be path.is_dir()
            path.mkdir(parents=True, exist_ok=True)
            self.__export_protodb(path / f"manifest_v{self.revision}")
            self.__export_json(path / f"manifest_v{self.revision}.json")
            self.__export_csv(path / f"manifest_v{self.revision}.csv")

        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".json":
                self.__export_json(path)
            elif path.suffix == ".csv":
                self.__export_csv(path)
            else:
                self.__export_protodb(path)

    def __export_protodb(self, path: Path):
        try:
            path.write_bytes(self.raw)
            logger.success(f"ProtoDB has been written into {path}")
        except:
            logger.warning(f"Failed to write ProtoDB into {path}")

    def __export_json(self, path: Path):
        try:
            path.write_text(json.dumps(self.jdict, sort_keys=True, indent=4))
            logger.success(f"JSON has been written into {path}")
        except:
            logger.warning(f"Failed to write JSON into {path}")

    def __export_csv(self, path: Path):
        bloblist = self.jdict["assetBundleList"]
        for blob in bloblist:
            blob["name"] += ".unity3d"
        bloblist.extend(self.jdict["resourceList"])
        df = DataFrame(bloblist, columns=CSV_COLUMNS)
        df.sort_values("name", inplace=True)
        try:
            df.to_csv(path, index=False)
            logger.success(f"CSV has been written into {path}")
        except:
            logger.warning(f"Failed to write CSV into {path}")
