from .const import (
    DICLIST_DIFF_IGNORED_FIELDS,
    CHARACTER_ABBREVS,
)

import sys
from rich.console import Console
from concurrent.futures import ThreadPoolExecutor, as_completed


def diclist_rip_field(l: list, targets: list) -> list:
    return [{k: v for k, v in i.items() if k not in targets} for i in l]


def diclist_diff(a: list, b: list) -> list:
    return [item for item in a if item not in b]


def diclist_diff_with_ignore(a: list, b: list) -> list:
    # rip unused fields for comparison
    a_ = diclist_rip_field(a, DICLIST_DIFF_IGNORED_FIELDS)
    b_ = diclist_rip_field(b, DICLIST_DIFF_IGNORED_FIELDS)
    diff_ids = [i["id"] for i in diclist_diff(a_, b_)]
    # retain complete fields for output
    return [i for i in a if i["id"] in diff_ids]


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


class ConcurrentDownloader:

    def __init__(self, nworker: int):
        self.nworker = nworker

    def dispatch(self, blobs: list, path: str):
        self.executor = ThreadPoolExecutor(max_workers=self.nworker)
        futures = [self.executor.submit(blob.download, path) for blob in blobs]
        for future in as_completed(futures):
            future.result()
        self.executor.shutdown()
