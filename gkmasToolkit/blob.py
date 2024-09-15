"""
blob.py
Asset bundles/Resources downloading and deobfuscation.
"""

from .utils import Logger
from .crypt import GkmasDeobfuscator
from .const import (
    CHARACTER_ABBREVS,
    DEFAULT_DOWNLOAD_PATH,
    GKMAS_OBJECT_SERVER,
    GKMAS_UNITY_VERSION,
    UNITY_SIGNATURE,
    IMG_RESIZE_ARGTYPE,
)

import re
import requests
import UnityPy
from hashlib import md5
from pathlib import Path
from typing import Union, Tuple
from PIL import Image


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
            Other possible states of NONE, LATEST, and DELETE have not yet been observed.

    Methods:
        download(
            path: str = DEFAULT_DOWNLOAD_PATH,
            categorize: bool = True,
        ) -> None:
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

    def download(
        self,
        path: str = DEFAULT_DOWNLOAD_PATH,
        categorize: bool = True,
        extract_img: bool = True,
        img_format: str = "png",
        img_resize: IMG_RESIZE_ARGTYPE = None,
    ):
        """
        Downloads the resource to the specified path.

        Args:
            path (str) = DEFAULT_DOWNLOAD_PATH: A directory or a file path.
                If a directory, subdirectories are auto-determined based on the resource name.
            categorize (bool) = True: Whether to put the downloaded blob into subdirectories.
                If False, the blob is directly downloaded to the specified 'path'.
            extract_img (bool) = True:
                IGNORED. PRESERVED FOR COMPATIBILITY WITH CONCURRENT DOWNLOADER.
            img_format (str) = 'png':
                IGNORED. PRESERVED FOR COMPATIBILITY WITH CONCURRENT DOWNLOADER.
            img_resize (Union[None, str, Tuple[int, int]]) = None:
                IGNORED. PRESERVED FOR COMPATIBILITY WITH CONCURRENT DOWNLOADER.
        """

        path = self._download_path(path, categorize)
        if path.exists():
            logger.warning(f"{self._idname} already exists")
            return

        plain = self._download_bytes()
        path.write_bytes(plain)
        logger.success(f"{self._idname} downloaded")

    def _download_path(self, path: Union[str, Path], categorize: bool) -> Path:
        """
        [INTERNAL] Refines the download path based on user input.
        Appends subdirectories unless a definite file path (with suffix) is given.
        Delimiter is hardcoded as '_'.

        path is not necessarily of type Path,
        since we don't expect the client to import pathlib in advance.

        Example:
            path = 'out/' and self.name = 'type_subtype-detail.ext'
            will be refined to 'out/type/subtype/type_subtype-detail.ext'
            if categorize is True, and 'out/type_subtype-detail.ext' otherwise.
        """

        path = Path(path)

        if path.suffix == "":  # is directory
            if categorize:
                path = path / self._determine_subdir(self.name) / self.name
            else:
                path = path / self.name

        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _determine_subdir(self, filename: str) -> Path:
        """
        [INTERNAL] Automatically organize files into nested subdirectories,
        stopping at the first 'character identifier'.
        """

        filename = ".".join(filename.split(".")[:-1])  # remove extension

        # Ignore everything after the first number after '-' or '_'
        filename = re.split(r"[-_]\d", filename)[0]

        for char in CHARACTER_ABBREVS:
            if char in filename:
                # Ignore everything after 'char', and trim trailing '_' or '-'
                filename = filename.split(char)[0][:-1]
                break

        return Path(*filename.split("_"))

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
        # Note: Returning empty bytes is unnecessary, since logger.error() raises an exception.

        if response.status_code != 200:
            logger.error(f"{self._idname} download failed")

        if len(response.content) != self.size:
            logger.error(f"{self._idname} has invalid size")

        if md5(response.content).hexdigest() != self.md5:
            logger.error(f"{self._idname} has invalid MD5 hash")

        return response.content


class GkmasAssetBundle(GkmasResource):
    """
    An assetbundle. Class inherits from GkmasResource.

    Attributes:
        All attributes from GkmasResource, plus
        name (str): Human-readable name, appended with '.unity3d'.
        crc (int): CRC checksum, unused for now (since scheme is unknown).

    Methods:
        download(
            path: str = DEFAULT_DOWNLOAD_PATH,
            categorize: bool = True,
            extract_img: bool = True,
            img_format: str = "png",
            img_resize: Union[None, str, Tuple[int, int]] = None,
        ) -> None:
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

    def download(
        self,
        path: str = DEFAULT_DOWNLOAD_PATH,
        categorize: bool = True,
        extract_img: bool = True,
        img_format: str = "png",
        img_resize: IMG_RESIZE_ARGTYPE = None,
    ):
        """
        Downloads and deobfuscates the assetbundle to the specified path.

        Args:
            path (str) = DEFAULT_DOWNLOAD_PATH: A directory or a file path.
                If a directory, subdirectories are auto-determined based on the assetbundle name.
            categorize (bool) = True: Whether to put the downloaded blob into subdirectories.
                If False, the blob is directly downloaded to the specified 'path'.
            extract_img (bool) = True: Whether to extract a single image from assetbundles of type 'img'.
                If False, 'img_.*\\.unity3d' is downloaded as is.
            img_format (str) = 'png': Image format for extraction. Case-insensitive.
                Effective only when 'extract_img' is True.
                Valid options are checked by PIL.Image.save() and are not enumerated.
            img_resize (Union[None, str, Tuple[int, int]]) = None: Image resizing argument.
                If None, image is downloaded as is.
                If str, string must contain exactly one ':' and image is resized to the specified ratio.
                If Tuple[int, int], image is resized to the specified exact dimensions.
        """

        path = self._download_path(path, categorize)
        if path.exists():
            logger.warning(f"{self._idname} already exists")
            return

        cipher = self._download_bytes()

        if cipher[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
            self._export_img(path, cipher, extract_img, img_format, img_resize)
            logger.success(f"{self._idname} downloaded")
        else:
            deobfuscator = GkmasDeobfuscator(self.name.replace(".unity3d", ""))
            plain = deobfuscator.deobfuscate(cipher)
            if plain[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
                self._export_img(path, plain, extract_img, img_format, img_resize)
                logger.success(f"{self._idname} downloaded and deobfuscated")
            else:
                path.write_bytes(cipher)
                logger.warning(f"{self._idname} downloaded but LEFT OBFUSCATED")
                # Unexpected things may happen...
                # So unlike _download_bytes() in the parent class,
                # here we don't raise an error and abort.

    def _export_img(
        self,
        path: Path,
        data: bytes,
        extract_img: bool,
        img_format: str,
        img_resize: IMG_RESIZE_ARGTYPE,
    ):
        """
        [INTERNAL] Attempts to extract a single image from the assetbundle's container.
        Triggered only when the assetbundle name starts with 'img_' AND extract_img is True.
        Raises a warning and falls back to raw dump if the bundle contains multiple objects.
        """

        if self.name.split("_")[0] != "img" or not extract_img:
            path.write_bytes(data)
            return

        env = UnityPy.load(data)
        values = list(env.container.values())
        if len(values) != 1:
            logger.warning(f"{self._idname} contains {len(values)} objects")
            path.write_bytes(data)
            return

        img = values[0].read().image
        if img_resize:
            if type(img_resize) == str:
                img_resize = self._determine_new_size(img.size, ratio=img_resize)
            img = img.resize(img_resize, Image.LANCZOS)

        img.save(path.with_suffix(f".{img_format.lower()}"), quality=100)
        logger.success(f"{self._idname} extracted as {img_format.upper()}")

    def _determine_new_size(
        self,
        size: Tuple[int, int],
        ratio: str,
        mode: Union["maximize", "ensure_fit", "preserve_npixel"] = "maximize",
    ) -> Tuple[int, int]:
        """
        [INTERNAL] Determines the new size of an image based on a given ratio.

        mode can be one of (terms borrowed from PowerPoint):
        - 'maximize': Enlarges the image to fit the ratio.
        - 'ensure_fit': Shrinks the image to fit the ratio.
        - 'preserve_npixel': Maintains approximately the same pixel count.

        Example: Given ratio = '4:3', an image of size (1920, 1080) is resized to:
        - (1920, 1440) in 'maximize' mode,
        - (1440, 1080) in 'ensure_fit' mode, and
        - (1663, 1247) in 'preserve_npixel' mode.
        """

        ratio = ratio.split(":")
        if len(ratio) != 2:
            raise ValueError("Invalid ratio format. Use 'width:height'.")

        ratio = (float(ratio[0]), float(ratio[1]))
        if ratio[0] <= 0 or ratio[1] <= 0:
            raise ValueError("Invalid ratio values. Must be positive.")

        ratio = ratio[0] / ratio[1]
        w, h = size
        ratio_old = w / h
        if ratio_old == ratio:
            return size

        w_new, h_new = w, h
        if mode == "preserve_npixel":
            pixel_count = w * h
            h_new = (pixel_count / ratio) ** 0.5
            w_new = h_new * ratio
        elif (mode == "maximize" and ratio_old > ratio) or (
            mode == "ensure_fit" and ratio_old < ratio
        ):
            h_new = w / ratio
        else:
            w_new = h * ratio

        round = lambda x: int(x + 0.5)  # round to the nearest integer
        return round(w_new), round(h_new)
