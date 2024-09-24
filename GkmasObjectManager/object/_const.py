"""
_const.py
[INTERNAL] Constants for GkmasAssetBundle and GkmasResource.
"""

import multiprocessing
from typing import Union, Tuple


# download
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

# deobfuscate
GKMAS_UNITY_VERSION = "2022.3.21f1"
UNITY_SIGNATURE = b"UnityFS"
IMG_RESIZE_ARGTYPE = Union[None, str, Tuple[int, int]]