from .utils import Logger, GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV
from .crypt import AESDecryptor
from .octodb_pb2 import Database
from .blob import GkmasAssetBundle, GkmasResource

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
            logger.info("ProtoDB is not encrypted.")
        except:
            decryptor = AESDecryptor(key, iv)
            plaintext = decryptor.decrypt(ciphertext)
            self.raw = plaintext[16:]  # trim md5 hash
            protodb.ParseFromString(self.raw)
            logger.info("ProtoDB has been decrypted.")

        self.revision = protodb.revision
        logger.info(f"Manifest revision: {self.revision}")

        self.jdict = json.loads(MessageToJson(protodb))
        self.abs = [GkmasAssetBundle(ab) for ab in self.jdict["assetBundleList"]]
        self.resources = [GkmasResource(res) for res in self.jdict["resourceList"]]

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
            if path.suffix == ".json":
                self.__export_json(path)
            elif path.suffix == ".csv":
                self.__export_csv(path)
            else:
                self.__export_protodb(path)

    def __export_protodb(self, path: Path):
        try:
            path.write_bytes(self.raw)
            logger.success(f"ProtoDB has been written into {path}.")
        except:
            logger.error(f"Failed to write ProtoDB into {path}.")

    def __export_json(self, path: Path):
        try:
            path.write_text(json.dumps(self.jdict, sort_keys=True, indent=4))
            logger.success(f"JSON has been written into {path}.")
        except:
            logger.error(f"Failed to write JSON into {path}.")

    def __export_csv(self, path: Path):
        dfa = DataFrame(
            self.jdict["assetBundleList"],
            columns=[
                "objectName",
                "md5",
                "name",
                "size",
                "state",
                "crc",
            ],
        )
        dfr = DataFrame(
            self.jdict["resourceList"],
            columns=[
                "objectName",
                "md5",
                "name",
                "size",
                "state",
            ],
        )
        dfa.sort_values("name", inplace=True)
        dfr.sort_values("name", inplace=True)
        try:
            spath = str(path.parent) + "/" + str(path.stem)  # string form
            dfa.to_csv(spath + "_ab.csv", index=False)
            dfr.to_csv(spath + "_res.csv", index=False)
            logger.success(f"CSV has been written into {path}.")
        except:
            logger.error(f"Failed to write CSV into {path}.")
