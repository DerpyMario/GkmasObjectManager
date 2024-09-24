"""
manifest.py
Manifest decryption and export.
"""

from .crypt import AESCBCDecryptor
from .octodb_pb2 import Database as OctoDB
from ..object import GkmasAssetBundle, GkmasResource
from ..utils import Diclist, Logger, ConcurrentDownloader
from ..const import (
    GKMAS_OCTOCACHE_KEY,
    GKMAS_OCTOCACHE_IV,
    DICLIST_IGNORED_FIELDS,
    DEFAULT_DOWNLOAD_NWORKER,
    DEFAULT_DOWNLOAD_PATH,
    IMG_RESIZE_ARGTYPE,
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
            nworker: int = DEFAULT_DOWNLOAD_NWORKER,
            path: str = DEFAULT_DOWNLOAD_PATH,
            categorize: bool = True,
            extract_img: bool = True,
            img_format: str = "png",
            img_resize: Union[None, str, Tuple[int, int]] = None,
        ) -> None:
            Downloads the regex-specified assetbundles/resources to the specified path.
        export(path: str) -> None:
            Exports the manifest as ProtoDB, JSON, and/or CSV to the specified path.
    """

    from ._offline_init import _parse_raw, _parse_jdict
    from ._download import download
    from ._export import export, _export_protodb, _export_json, _export_csv

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

        ciphertext = Path(src).read_bytes()

        try:
            self._parse_raw(ciphertext)
            logger.info("Manifest created from unencrypted ProtoDB")

        except:
            decryptor = AESCBCDecryptor(GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV)
            plaintext = decryptor.decrypt(ciphertext)
            self._parse_raw(plaintext[16:])  # trim md5 hash
            logger.info("Manifest created from encrypted ProtoDB")

    # ------------ Magic Methods ------------

    def __repr__(self):
        return f"<GkmasManifest revision {self.revision}>"

    def __getitem__(self, key: str):
        return self._name2object[key]

    def __iter__(self):
        return iter(self._name2object.values())

    def __len__(self):
        return len(self._name2object)

    def __contains__(self, key: str):
        return key in self._name2object

    def __sub__(self, other):
        """
        [INTERNAL] Creates a manifest from a differentiation dictionary.
        The diffdict refers to a dictionary containing differentiated
        assetbundles and resources, created by utils.Diclist.diff().
        """
        manifest = GkmasManifest()
        manifest.revision = f"{self.revision}-{other.revision}"
        manifest._parse_jdict(
            {
                "assetBundleList": self._abl.diff(other._abl, DICLIST_IGNORED_FIELDS),
                "resourceList": self._resl.diff(other._resl, DICLIST_IGNORED_FIELDS),
            }
        )
        logger.info("Manifest created from differentiation")
        return manifest
