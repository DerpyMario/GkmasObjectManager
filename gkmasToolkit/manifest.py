"""
manifest.py
Manifest decryption and export.
"""

from .utils import Diclist, Logger, ConcurrentDownloader
from .crypt import AESCBCDecryptor
from .octodb_pb2 import Database
from .blob import GkmasAssetBundle, GkmasResource
from .const import (
    GKMAS_OCTOCACHE_KEY,
    GKMAS_OCTOCACHE_IV,
    DICLIST_IGNORED_FIELDS,
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
    """
    A GKMAS manifest, containing info about assetbundles and resources.

    Attributes:
        raw (bytes): Raw decrypted protobuf bytes.
        revision (str): Manifest revision, a number or a string (for manifest from diff).
        jdict (dict): JSON-serialized dictionary of the protobuf.
        abs (list): List of GkmasAssetBundle objects.
        reses (list): List of GkmasResource objects.

    Methods:
        download(
            *criteria: str,
            path: str = DEFAULT_DOWNLOAD_PATH,
            nworker: int = DEFAULT_DOWNLOAD_NWORKER,
        ) -> None:
            Downloads the regex-specified assetbundles/resources to the specified path.
        export(path: str) -> None:
            Exports the manifest as ProtoDB, JSON, and/or CSV to the specified path.
    """

    def __init__(self, src: str = None):
        """
        Initializes a manifest from the given source.
        Only performs decryption when necessary, and
        leaves protobuf parsing to internal backend.

        Args:
            src (str): Path to the manifest file.
                Can be the path to an encrypted octocache
                (usually named 'octocacheevai') or a decrypted protobuf.
                If None, an empty manifest is created (used for manifest from diff;
                note that _parse_jdict() must be manually called afterwards).
        """

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
            decryptor = AESCBCDecryptor(GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV)
            plaintext = decryptor.decrypt(ciphertext)
            self._parse_raw(plaintext[16:])  # trim md5 hash
            logger.info("Manifest created from encrypted ProtoDB")

    def _parse_raw(self, raw: bytes):
        """
        [INTERNAL] Records raw protobuf bytes, converts to JSON,
        and calls "secondary backend" JSON parser.
        """
        protodb = Database()
        protodb.ParseFromString(raw)
        self.raw = raw
        self.revision = protodb.revision
        self._parse_jdict(json.loads(MessageToJson(protodb)))

    def _parse_jdict(self, jdict: dict):
        """
        [INTERNAL] Parses the JSON dictionary into internal structures.
        Also *directly* called from _make_diff_manifest(),
        without handling raw protobuf in advance.

        Internal attributes:
            _abl (Diclist): List of assetbundle *info dictionaries*.
            _resl (Diclist): List of resource *info dictionaries*.
            _name2blob (dict): Mapping from blob name to GkmasAssetBundle/GkmasResource.

        Documentation for Diclist can be found in utils.py.
        """
        self.jdict = jdict
        self._abl = Diclist(self.jdict["assetBundleList"])
        self._resl = Diclist(self.jdict["resourceList"])
        self.abs = [GkmasAssetBundle(ab) for ab in self._abl]
        self.reses = [GkmasResource(res) for res in self._resl]
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
        """
        [INTERNAL] Creates a manifest from a differentiation dictionary.
        This is the only method where 'self' is not referenced.

        Args:
            diffdict (dict): A dictionary containing differentiated assetbundles and resources,
                created by utils.Diclist.diff().
            rev1 (str): Revision of the first manifest.
            rev2 (str): Revision of the second manifest.
        """
        manifest = GkmasManifest()
        manifest.revision = f"{rev1}-{rev2}"
        manifest._parse_jdict(diffdict)
        logger.info("Manifest created from differentiation")
        return manifest

    def __sub__(self, other):
        return self._make_diff_manifest(
            {
                "assetBundleList": self._abl.diff(other._abl, DICLIST_IGNORED_FIELDS),
                "resourceList": self._resl.diff(other._resl, DICLIST_IGNORED_FIELDS),
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
        """
        Downloads the regex-specified assetbundles/resources to the specified path.

        Args:
            *criteria (str): Regex patterns of assetbundle/resource names.
                Allowed special tokens are const.ALL_ASSETBUNDLES and const.ALL_RESOURCES.
            path (str) = DEFAULT_DOWNLOAD_PATH: A directory to which the blobs are downloaded.
                *WARNING: Behavior is undefined if the path points to an definite file (with extension).*
            nworker (int) = DEFAULT_DOWNLOAD_NWORKER: Number of concurrent download workers.
                Defaults to multiprocessing.cpu_count().
        """

        blobs = []

        for criterion in criteria:
            if criterion == ALL_ASSETBUNDLES:  # special tokens, enclosed in <>
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
        """
        Exports the manifest as ProtoDB, JSON, and/or CSV to the specified path.
        This is a dispatcher method.

        Args:
            path (str): A directory or a file path.
                If a directory, all three formats are exported.
                If a file path, the format is determined by the extension
                (all extensions other than .json and .csv are treated as raw binary
                and therefore exported as ProtoDB).
        """

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
        """
        [INTERNAL] Writes raw protobuf bytes into the specified path.
        """
        try:
            path.write_bytes(self.raw)
            logger.success(f"ProtoDB has been written into {path}")
        except:
            logger.warning(f"Failed to write ProtoDB into {path}")

    def _export_json(self, path: Path):
        """
        [INTERNAL] Writes JSON-serialized dictionary into the specified path.
        """
        try:
            path.write_text(json.dumps(self.jdict, sort_keys=True, indent=4))
            logger.success(f"JSON has been written into {path}")
        except:
            logger.warning(f"Failed to write JSON into {path}")

    def _export_csv(self, path: Path):
        """
        [INTERNAL] Writes CSV-serialized data into the specified path.
        Assetbundles and resources are concatenated into a single table and sorted by name.
        Assetbundles can be distinguished by their '.unity3d' suffix.
        """
        dfa = pd.DataFrame(self._abl, columns=CSV_COLUMNS)
        dfa["name"] = dfa["name"].apply(lambda x: x + ".unity3d")
        dfr = pd.DataFrame(self._resl, columns=CSV_COLUMNS)
        df = pd.concat([dfa, dfr], ignore_index=True)
        df.sort_values("name", inplace=True)
        try:
            df.to_csv(path, index=False)
            logger.success(f"CSV has been written into {path}")
        except:
            logger.warning(f"Failed to write CSV into {path}")
