"""
const.py
Module-wide constants (macro equivalents).
"""

import multiprocessing
from typing import Union, Tuple


# manifest decrypt
GKMAS_OCTOCACHE_KEY = "1nuv9td1bw1udefk"
GKMAS_OCTOCACHE_IV = "LvAUtf+tnz"

# manifest export
DICLIST_IGNORED_FIELDS = ["dependencies", "uploadVersionId"]
CSV_COLUMNS = ["objectName", "md5", "name", "size", "state"]

# manifest download dispatcher, "token" style
ALL_ASSETBUNDLES = "<ALL_ASSETBUNDLES>"
ALL_RESOURCES = "<ALL_RESOURCES>"

# object download
GKMAS_OBJECT_SERVER = "https://object.asset.game-gakuen-idolmaster.jp/"
DEFAULT_DOWNLOAD_PATH = "objects/"
DEFAULT_DOWNLOAD_NWORKER = multiprocessing.cpu_count()
CHARACTER_ABBREVS = [
    "hski",  # Hanami SaKI
    "ttmr",  # Tsukimura TeMaRi
    "fktn",  # Fujita KoToNe
    "hrnm",  # Himesaki RiNaMi
    "ssmk",  # Shiun SuMiKa
    "shro",  # Shinosawa HiRO
    "kllj",  # Katsuragi LiLJa
    "kcna",  # Kuramoto ChiNA
    "amao",  # Arimura MAO
    "hume",  # Hanami UME
    "hmsz",  # Hataya MiSuZu
    "jsna",  # Juo SeNA
    "nasr",  # Neo ASaRi
    "trvo",  # VOcal TRainer
    "trda",  # DAnce TRainer
    "trvi",  # VIsual TRainer
]

# object deobfuscate
GKMAS_UNITY_VERSION = "2022.3.21f1"
UNITY_SIGNATURE = b"UnityFS"
IMG_RESIZE_ARGTYPE = Union[None, str, Tuple[int, int]]
