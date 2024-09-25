"""
_initdb.py
[CLASS SPLIT] GkmasManifest protobuf initialization.
"""

from ..utils import Diclist, Logger
from ..const import (
    PATH_ARGTYPE,
    GKMAS_API_URL,
    GKMAS_API_HEADER,
    GKMAS_ONLINEPDB_KEY,
    GKMAS_OCTOCACHE_KEY,
    GKMAS_OCTOCACHE_IV,
)

from .crypt import AESCBCDecryptor
from .octodb_pb2 import Database as OctoDB
from ..object import GkmasAssetBundle, GkmasResource

import json
import requests
from google.protobuf.json_format import MessageToJson
from pathlib import Path


logger = Logger()


def _online_init(self, revision: int = 0):
    """
    [INTERNAL] Requests a manifest by the specified revision.
    Algorithm courtesy of github.com/DreamGallery/HatsuboshiToolkit
    """
    ciphertext = requests.get(
        f"{GKMAS_API_URL}/{revision}",
        headers=GKMAS_API_HEADER,
    ).content
    decryptor = AESCBCDecryptor(GKMAS_ONLINEPDB_KEY, ciphertext[:16])
    plaintext = decryptor.decrypt(ciphertext[16:])
    self._parse_raw(plaintext)
    logger.info("Manifest created from online ProtoDB")


def _offline_init(self, src: PATH_ARGTYPE):
    """
    [INTERNAL] Initializes a manifest from the given offline source.
    The protobuf referred to can be either encrypted or not.
    """
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
    protodb = OctoDB()
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
        _name2object (dict): Mapping from object name to GkmasAssetBundle/GkmasResource.

    Documentation for Diclist can be found in utils.py.
    """
    self.jdict = jdict
    self._abl = Diclist(self.jdict["assetBundleList"])
    self._resl = Diclist(self.jdict["resourceList"])
    self.abs = [GkmasAssetBundle(ab) for ab in self._abl]
    self.reses = [GkmasResource(res) for res in self._resl]
    self._name2object = {ab.name: ab for ab in self.abs}  # quick lookup
    self._name2object.update({res.name: res for res in self.reses})
    logger.info(f"Found {len(self.abs)} assetbundles")
    logger.info(f"Found {len(self.reses)} resources")
    logger.info(f"Detected revision: {self.revision}")
