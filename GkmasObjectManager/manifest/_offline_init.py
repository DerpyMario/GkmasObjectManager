from ._crypt import AESCBCDecryptor
from ._octodb_pb2 import Database as OctoDB
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


logger = Logger()


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
