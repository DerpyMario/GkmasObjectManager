from .utils import Logger, ConcurrentDownloader
from .crypt import AESDecryptor
from .octodb_pb2 import Database
from .blob import GkmasAssetBundle, GkmasResource
from .const import (
    GKMAS_OCTOCACHE_KEY,
    GKMAS_OCTOCACHE_IV,
    DEFAULT_DOWNLOAD_PATH,
    DEFAULT_DOWNLOAD_NWORKER,
    ALL_ASSETBUNDLES,
    ALL_RESOURCES,
    CSV_COLUMNS,
)

import re
import json
from google.protobuf.json_format import MessageToJson
from pandas import DataFrame
from pathlib import Path
from typing import Union, Tuple


# The logger would better be a global variable in the
# modular __init__.py, but Python won't allow me to
logger = Logger()


class GkmasManifest:

    def __init__(self, src: Union[str, Tuple[dict, int, int]]):
        # src can be a path to a ProtoDB file,
        # or a (diff-dict, rev1, rev2) tuple [INTERNAL USE ONLY]

        if isinstance(src, tuple):
            diffdict, rev1, rev2 = src
            self.raw = None
            self.__parse_jdict(diffdict)
            self.revision = f"{rev1}-{rev2}"
            logger.info("Manifest created from differentiation")
            logger.info(f"Manifest revision: {self.revision}")
            return

        protodb = Database()
        ciphertext = Path(src).read_bytes()

        try:
            self.raw = ciphertext
            protodb.ParseFromString(self.raw)
            self.__parse_jdict(json.loads(MessageToJson(protodb)))
            logger.info("Manifest created from unencrypted ProtoDB")

        except:
            decryptor = AESDecryptor(GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV)
            plaintext = decryptor.decrypt(ciphertext)
            self.raw = plaintext[16:]  # trim md5 hash
            protodb.ParseFromString(self.raw)
            self.__parse_jdict(json.loads(MessageToJson(protodb)))
            logger.info("Manifest created from encrypted ProtoDB")

        self.revision = protodb.revision
        logger.info(f"Manifest revision: {self.revision}")

    def __parse_jdict(self, jdict: dict):

        self.jdict = jdict
        self.abs = [GkmasAssetBundle(ab) for ab in self.jdict["assetBundleList"]]
        self.reses = [GkmasResource(res) for res in self.jdict["resourceList"]]
        self.__name2blob = {ab.name: ab for ab in self.abs}  # quick lookup
        self.__name2blob.update({res.name: res for res in self.reses})

        logger.info(f"Found {len(self.abs)} assetbundles")
        logger.info(f"Found {len(self.reses)} resources")

    # ------------ Magic Methods ------------

    def __repr__(self):
        return f"<GkmasManifest revision {self.revision}>"

    def __getitem__(self, key: str):
        return self.__name2blob[key]

    def __iter__(self):
        return iter(self.__name2blob.values())

    def __len__(self):
        return len(self.__name2blob)

    def __contains__(self, key: str):
        return key in self.__name2blob

    def __listdiff(self, a, b):
        return [item for item in a if item not in b]

    def __sub__(self, other):

        # rip 'dependencies' field for comparison
        abl_this = [
            {k: v for k, v in ab.items() if k != "dependencies"}
            for ab in self.jdict["assetBundleList"]
        ]
        abl_other = [
            {k: v for k, v in ab.items() if k != "dependencies"}
            for ab in other.jdict["assetBundleList"]
        ]
        abl_diff_ids = [ab["id"] for ab in self.__listdiff(abl_this, abl_other)]

        # retain complete fields for output
        abl_diff = [
            ab for ab in self.jdict["assetBundleList"] if ab["id"] in abl_diff_ids
        ]

        # resource list doesn't have 'dependencies' field
        resl_this = self.jdict["resourceList"]
        resl_other = other.jdict["resourceList"]
        resl_diff = self.__listdiff(resl_this, resl_other)

        return {"assetBundleList": abl_diff, "resourceList": resl_diff}

    # ------------ Download ------------

    def download(
        self,
        *criteria: str,
        path: str = DEFAULT_DOWNLOAD_PATH,
        nworker: int = DEFAULT_DOWNLOAD_NWORKER,
    ):

        blobs = []

        for criterion in criteria:
            if criterion == ALL_ASSETBUNDLES:  # similar to 'tokens' in NLP
                blobs.extend(self.abs)
            elif criterion == ALL_RESOURCES:
                blobs.extend(self.reses)
            else:
                blobs.extend(
                    [
                        self.__name2blob[file]
                        for file in self.__name2blob
                        if re.match(criterion, file)
                    ]
                )

        ConcurrentDownloader(nworker).dispatch(blobs, path)

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
