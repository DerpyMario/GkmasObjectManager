from .const import CHARACTER_ABBREVS

import sys
from rich.console import Console
from concurrent.futures import ThreadPoolExecutor, as_completed


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


class Diclist(list):

    def __init__(self, diclist: list):
        super().__init__(diclist)

    def __sub__(self, other: "Diclist") -> "Diclist":
        return Diclist([item for item in self if item not in other])

    def rip_field(self, targets: list) -> "Diclist":
        return Diclist(
            [{k: v for k, v in entry.items() if k not in targets} for entry in self]
        )

    def diff(self, other: "Diclist", ignored_fields: list = []) -> "Diclist":

        if not ignored_fields:
            return self - other

        # rip unused fields for comparison
        self_rip = self.rip_field(ignored_fields)
        other_rip = other.rip_field(ignored_fields)

        # retain complete fields for output
        raw_lookup = {i: entry for i, entry in enumerate(self)}
        return Diclist(
            [raw_lookup[self_rip.index(entry)] for entry in self_rip - other_rip]
        )


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


class ConcurrentDownloader:

    def __init__(self, nworker: int):
        self.nworker = nworker

    def dispatch(self, blobs: list, path: str):
        self.executor = ThreadPoolExecutor(max_workers=self.nworker)
        futures = [self.executor.submit(blob.download, path) for blob in blobs]
        for future in as_completed(futures):
            future.result()
        self.executor.shutdown()
