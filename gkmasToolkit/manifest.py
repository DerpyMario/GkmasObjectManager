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
    DIFF_IGNORE,
    CSV_COLUMNS,
)

import re
import json
import pandas as pd
from google.protobuf.json_format import MessageToJson
from pathlib import Path


# The logger would better be a global variable in the
# modular __init__.py, but Python won't allow me to
logger = Logger()


class GkmasManifest:

    def __init__(self, src: str = None):

        if not src:  # empty constructor
            self.raw = None
            self.revision = None
            return

        protodb = Database()
        ciphertext = Path(src).read_bytes()

        try:
            self.__parse_raw(ciphertext)
            logger.info("Manifest created from unencrypted ProtoDB")

        except:
            decryptor = AESDecryptor(GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV)
            plaintext = decryptor.decrypt(ciphertext)
            self.__parse_raw(plaintext[16:])  # trim md5 hash
            logger.info("Manifest created from encrypted ProtoDB")

    def __parse_raw(self, raw: bytes):
        protodb = Database()
        protodb.ParseFromString(raw)
        self.raw = raw
        self.revision = protodb.revision
        self.__parse_jdict(json.loads(MessageToJson(protodb)))

    def __parse_jdict(self, jdict: dict):
        self.jdict = jdict
        self.abs = [GkmasAssetBundle(ab) for ab in self.jdict["assetBundleList"]]
        self.reses = [GkmasResource(res) for res in self.jdict["resourceList"]]
        self.__name2blob = {ab.name: ab for ab in self.abs}  # quick lookup
        self.__name2blob.update({res.name: res for res in self.reses})
        logger.info(f"Found {len(self.abs)} assetbundles")
        logger.info(f"Found {len(self.reses)} resources")
        logger.info(f"Detected revision: {self.revision}")

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

    def __list_diff(self, a: list, b: list) -> list:
        return [item for item in a if item not in b]

    def __rip_field(self, l: list, rip: list) -> list:
        return [{k: v for k, v in ab.items() if k not in rip} for ab in l]

    def __make_diff_manifest(self, diffdict: dict, rev1: str, rev2: str):
        manifest = GkmasManifest()
        manifest.revision = f"{rev1}-{rev2}"
        manifest.__parse_jdict(diffdict)
        logger.info("Manifest created from differentiation")
        return manifest

    def __sub__(self, other):

        # rip unused fields for comparison
        abl_this = self.__rip_field(self.jdict["assetBundleList"], DIFF_IGNORE)
        abl_other = self.__rip_field(other.jdict["assetBundleList"], DIFF_IGNORE)
        abl_diff_ids = [ab["id"] for ab in self.__list_diff(abl_this, abl_other)]

        # retain complete fields for output
        abl_diff = [
            ab for ab in self.jdict["assetBundleList"] if ab["id"] in abl_diff_ids
        ]

        # turns out that resource list also does have unused fields,
        # but we haven't found a way to reduce code duplication
        resl_this = self.__rip_field(self.jdict["resourceList"], DIFF_IGNORE)
        resl_other = self.__rip_field(other.jdict["resourceList"], DIFF_IGNORE)
        resl_diff_ids = [res["id"] for res in self.__list_diff(resl_this, resl_other)]
        resl_diff = [
            res for res in self.jdict["resourceList"] if res["id"] in resl_diff_ids
        ]

        return __make_diff_manifest(
            {"assetBundleList": abl_diff, "resourceList": resl_diff},
            self.revision,
            other.revision,
        )

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
        dfa = pd.DataFrame(self.jdict["assetBundleList"], columns=CSV_COLUMNS)
        dfa["name"] = dfa["name"].apply(lambda x: x + ".unity3d")
        dfr = pd.DataFrame(self.jdict["resourceList"], columns=CSV_COLUMNS)
        df = pd.concat([dfa, dfr], ignore_index=True)
        df.sort_values("name", inplace=True)
        try:
            df.to_csv(path, index=False)
            logger.success(f"CSV has been written into {path}")
        except:
            logger.warning(f"Failed to write CSV into {path}")
