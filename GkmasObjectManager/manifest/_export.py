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

    if path.suffix == "":
        # used to be path.is_dir(), but it also returns False for non-existent dirs
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
