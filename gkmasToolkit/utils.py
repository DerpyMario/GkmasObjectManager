import sys
from rich.console import Console


### Macro equivalents

# manifest decrypt
GKMAS_OCTOCACHE_KEY = "1nuv9td1bw1udefk"
GKMAS_OCTOCACHE_IV = "LvAUtf+tnz"

# manifest export
CSV_COLUMNS_ASSETBUNDLE = ["objectName", "md5", "name", "size", "state", "crc"]
CSV_COLUMNS_RESOURCE = ["objectName", "md5", "name", "size", "state"]

# manifest download dispatcher
ASSETBUNDLES = ALL_ASSETBUNDLES = "<ALL_ASSETBUNDLES>"  # alias for compatibility
RESOURCES = ALL_RESOURCES = "<ALL_RESOURCES>"

# blob download
GKMAS_OBJECT_SERVER = "https://object.asset.game-gakuen-idolmaster.jp/"
DEFAULT_DOWNLOAD_PATH = "blob/"
CHARACTER_ABBREVS = [
    "hski",
    "ttmr",
    "fktn",
    "hrnm",
    "ssmk",
    "shro",
    "kllj",
    "kcna",
    "amao",
    "hume",
    "hmsz",
    "isna",
    "nasr",
    "trvo",
    "trda",
    "trvi",
]

# blob deobfuscate
UNITY_SIGNATURE = b"UnityFS"


def determine_subdir(filename: str) -> str:
    # Auto organize files into nested subdirectories,
    # stop at the first "character identifier"

    filename = ".".join(filename.split(".")[:-1])  # remove extension
    filename = filename.split("-")[0]  # remove suffix
    segments = filename.split("_")
    for i, segment in enumerate(segments):
        if segment in CHARACTER_ABBREVS:
            break

    return "/".join(segments[: i + 1])


class Logger(Console):

    def __init__(self):
        super().__init__()

    def info(self, message: str):
        self.print(f"[bold white][Info][/bold white] {message}")

    def success(self, message: str):
        self.print(f"[bold green][Success][/bold green] {message}")

    def warning(self, message: str):
        self.print(f"[bold yellow][Warning][/bold yellow] {message}")

    def error(self, message: str):
        self.print(f"[bold red][Error][/bold red] {message}\n{sys.exc_info()}")
        raise
