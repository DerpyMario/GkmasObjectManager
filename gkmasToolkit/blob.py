"""
blob.py
Asset bundles/Resources downloading and deobfuscation.
"""

from .utils import Logger, determine_subdir
from .crypt import GkmasDeobfuscator
from .const import (
    DEFAULT_DOWNLOAD_PATH,
    GKMAS_OBJECT_SERVER,
    GKMAS_UNITY_VERSION,
    UNITY_SIGNATURE,
)

import UnityPy
import requests
from io import BytesIO
from hashlib import md5
from pathlib import Path


logger = Logger()
UnityPy.config.FALLBACK_UNITY_VERSION = GKMAS_UNITY_VERSION


class GkmasResource:
    """
    A general-purpose binary resource, presumably multimedia instead of an assetbundle.

    Attributes:
        id (int): Resource ID, unique across manifests.
        name (str): Human-readable name, unique across manifests.
        objectName (str): Object name on server, 6-character alphanumeric.
        size (int): Resource size in bytes, used for integrity check.
        md5 (str): MD5 hash of the resource, used for integrity check.
        state (str): Resource state in manifest (ADD/UPDATE), unused for now.

    Methods:
        download(path: str = DEFAULT_DOWNLOAD_PATH) -> None:
            Downloads the resource to the specified path.
    """

    def __init__(self, info: dict):
        """
        Initializes a resource with the given information.
        Usually called from GkmasManifest.

        Args:
            info (dict): An info dictionary, extracted from protobuf.
                Must contain the following keys: id, name, objectName, size, md5, state.
        """

        self.id = info["id"]
        self.name = info["name"]
        self.size = info["size"]
        self.state = info["state"]  # unused
        self.md5 = info["md5"]
        self.objectName = info["objectName"]
        self._idname = f"RS[{self.id:05}] '{self.name}'"

    def __repr__(self):
        return f"<GkmasResource {self._idname}>"

    def download(self, path: str = DEFAULT_DOWNLOAD_PATH):
        """
        Downloads the resource to the specified path.

        Args:
            path (str) = DEFAULT_DOWNLOAD_PATH: A directory or a file path.
                If a directory, subdirectories are auto-determined based on the resource name.
        """

        path = self._download_path(path)
        if path.exists():
            logger.warning(f"{self._idname} already exists")
            return

        plain = self._download_bytes()
        path.write_bytes(plain)
        logger.success(f"{self._idname} downloaded")

    def _download_path(self, path: str) -> Path:
        """
        [INTERNAL] Refines the download path based on user input.
        Appends subdirectories unless a definite file path (with suffix) is given.
        Delimiter is hardcoded as '_'.

        Example:
            path = 'out/' and self.name = 'type_subtype-detail.ext'
            will be refined to 'out/type/subtype/type_subtype-detail.ext'
        """

        # don't expect the client to import pathlib in advance
        path = Path(path)

        if path.suffix == "":  # is directory
            path = path / determine_subdir(self.name) / self.name

        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _download_bytes(self) -> bytes:
        """
        [INTERNAL] Downloads the resource from the server and performs sanity checks
        on HTTP status code, size, and MD5 hash. Returns the resource as raw bytes.
        """

        url = f"{GKMAS_OBJECT_SERVER}/{self.objectName}"
        response = requests.get(url)

        # We're being strict here by aborting the download process
        # if any of the sanity checks fail, in order to avoid corrupted output.
        # The client can always retry (just ignore the "file already exists" warnings).

        if response.status_code != 200:
            logger.error(f"{self._idname} download failed")
            return b""

        if len(response.content) != self.size:
            logger.error(f"{self._idname} has invalid size")
            return b""

        if md5(response.content).hexdigest() != self.md5:
            logger.error(f"{self._idname} has invalid MD5 hash")
            return b""

        return response.content


class GkmasAssetBundle(GkmasResource):
    """
    An assetbundle. Class inherits from GkmasResource.

    Attributes:
        All attributes from GkmasResource, plus
        name (str): Human-readable name, appended with '.unity3d'.
        crc (int): CRC checksum, unused for now (since scheme is unknown).

    Methods:
        download(path: str = DEFAULT_DOWNLOAD_PATH) -> None:
            Downloads and deobfuscates the assetbundle to the specified path.
            Also extracts a single image from each bundle with type 'img'.
    """

    def __init__(self, info: dict):
        """
        Initializes an assetbundle with the given information.
        Usually called from GkmasManifest.

        Args:
            info (dict): An info dictionary, extracted from protobuf.
                Must contain the following keys: id, name, objectName, size, md5, state, crc.
        """

        super().__init__(info)
        self.name = info["name"] + ".unity3d"
        self.crc = info["crc"]  # unused (for now)
        self._idname = f"AB[{self.id:05}] '{self.name}'"

    def __repr__(self):
        return f"<GkmasAssetBundle {self._idname}>"

    def download(self, path: str = DEFAULT_DOWNLOAD_PATH):
        """
        Downloads and deobfuscates the assetbundle to the specified path.

        Args:
            path (str) = DEFAULT_DOWNLOAD_PATH: A directory or a file path.
                If a directory, subdirectories are auto-determined based on the assetbundle name.
        """

        path = self._download_path(path)
        if path.exists():
            logger.warning(f"{self._idname} already exists")
            return

        cipher = self._download_bytes()

        if cipher[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
            self._write_bytes(path, cipher)
            logger.success(f"{self._idname} downloaded")
        else:
            deobfuscator = GkmasDeobfuscator(self.name.replace(".unity3d", ""))
            plain = deobfuscator.deobfuscate(cipher)
            if plain[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
                self._write_bytes(path, plain)
                logger.success(f"{self._idname} downloaded and deobfuscated")
            else:
                self._write_bytes(path, cipher)
                logger.warning(f"{self._idname} downloaded but LEFT OBFUSCATED")
                # Unexpected things may happen...
                # So unlike _download_bytes() in the parent class,
                # here we don't raise an error and abort.

    def _write_bytes(self, path: Path, data: bytes):
        """
        [INTERNAL] Writes the data (in raw bytes) to the specified path.
        An extra layer that integrates with image extraction
        (triggered only when the assetbundle name starts with 'img_').
        """
        if self.name.split("_")[0] == "img":
            path.with_suffix(".png").write_bytes(self._extract_image(data))
        else:
            path.write_bytes(data)

    def _extract_image(self, bundle: bytes) -> bytes:
        """
        [INTERNAL] Extracts a single image from the assetbundle's container.
        Raises a warning if the bundle contains multiple objects.

        Note: This method accepts an assetbundle in raw bytes and returns an image
        in raw bytes, for a more straightforward interface.
        """
        env = UnityPy.load(bundle)
        values = list(env.container.values())
        if len(values) != 1:
            logger.warning(f"{self._idname} contains {len(values)} objects")
            return b""
        img = values[0].read().image
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
