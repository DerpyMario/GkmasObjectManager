from .utils import diclist_diff_with_ignore, Logger, ConcurrentDownloader
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
            self._parse_raw(ciphertext)
            logger.info("Manifest created from unencrypted ProtoDB")

        except:
            decryptor = AESDecryptor(GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV)
            plaintext = decryptor.decrypt(ciphertext)
            self._parse_raw(plaintext[16:])  # trim md5 hash
            logger.info("Manifest created from encrypted ProtoDB")

    def _parse_raw(self, raw: bytes):
        protodb = Database()
        protodb.ParseFromString(raw)
        self.raw = raw
        self.revision = protodb.revision
        self._parse_jdict(json.loads(MessageToJson(protodb)))

    def _parse_jdict(self, jdict: dict):
        self.jdict = jdict
        self.abs = [GkmasAssetBundle(ab) for ab in self.jdict["assetBundleList"]]
        self.reses = [GkmasResource(res) for res in self.jdict["resourceList"]]
        self._name2blob = {ab.name: ab for ab in self.abs}  # quick lookup
        self._name2blob.update({res.name: res for res in self.reses})
        logger.info(f"Found {len(self.abs)} assetbundles")
        logger.info(f"Found {len(self.reses)} resources")
        logger.info(f"Detected revision: {self.revision}")

    # ------------ Magic Methods ------------

    def __repr__(self):
        return f"<GkmasManifest revision {self.revision}>"

    def __getitem__(self, key: str):
        return self._name2blob[key]

    def __iter__(self):
        return iter(self._name2blob.values())

    def __len__(self):
        return len(self._name2blob)

    def __contains__(self, key: str):
        return key in self._name2blob

    def _make_diff_manifest(self, diffdict: dict, rev1: str, rev2: str):
        manifest = GkmasManifest()
        manifest.revision = f"{rev1}-{rev2}"
        manifest._parse_jdict(diffdict)
        logger.info("Manifest created from differentiation")
        return manifest

    def __sub__(self, other):

        return self._make_diff_manifest(
            {
                "assetBundleList": diclist_diff_with_ignore(
                    self.jdict["assetBundleList"], other.jdict["assetBundleList"]
                ),
                "resourceList": diclist_diff_with_ignore(
                    self.jdict["resourceList"], other.jdict["resourceList"]
                ),
            },
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
                        self._name2blob[file]
                        for file in self._name2blob
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
            self._export_protodb(path / f"manifest_v{self.revision}")
            self._export_json(path / f"manifest_v{self.revision}.json")
            self._export_csv(path / f"manifest_v{self.revision}.csv")

        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".json":
                self._export_json(path)
            elif path.suffix == ".csv":
                self._export_csv(path)
            else:
                self._export_protodb(path)

    def _export_protodb(self, path: Path):
        try:
            path.write_bytes(self.raw)
            logger.success(f"ProtoDB has been written into {path}")
        except:
            logger.warning(f"Failed to write ProtoDB into {path}")

    def _export_json(self, path: Path):
        try:
            path.write_text(json.dumps(self.jdict, sort_keys=True, indent=4))
            logger.success(f"JSON has been written into {path}")
        except:
            logger.warning(f"Failed to write JSON into {path}")

    def _export_csv(self, path: Path):
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
