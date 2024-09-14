"""
utils.py
Typing, logging, downloading, and miscellaneous utilities.
"""

from .const import CHARACTER_ABBREVS

import sys
from rich.console import Console
from concurrent.futures import ThreadPoolExecutor, as_completed


def determine_subdir(filename: str) -> str:
    """
    Automatically organize files into nested subdirectories,
    stopping at the first 'character identifier'.
    """

    filename = ".".join(filename.split(".")[:-1])  # remove extension

    for char in CHARACTER_ABBREVS:
        if char in filename:
            filename = filename.split(char)[0]  # ignore everything after 'char'
            break

    return filename[:-1].replace("_", "/")  # trim trailing '_' or '-'


class Diclist(list):
    """
    A list of dictionaries, optimized for comparison.

    Methods:
        __sub__(other: Diclist) -> Diclist:
            Subtracts another Diclist from this Diclist.
            Returns the list of elements unique to 'self'.
        rip_field(targets: list) -> Diclist:
            Removes selected fields from all dictionaries.
        diff(other: Diclist, ignored_fields: list) -> Diclist:
            Compares two Diclists while ignoring selected fields,
            but **retains all fields** in the reconstructed output.
    """

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
        return Diclist([self[self_rip.index(entry)] for entry in self_rip - other_rip])


class Logger(Console):
    """
    A rich console logger with custom log levels.

    Methods:
        info(message: str): Logs an informational message in white text.
        success(message: str): Logs a success message in green text.
        warning(message: str): Logs a warning message in yellow text.
        error(message: str): Logs an error message in red text
            followed by traceback, and raises an error.
    """

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
    """
    A multithreaded downloader for objects on server.

    Methods:
        dispatch(blobs: list, path: str):
            Downloads a list of blobs to a specified path.
            Executor implicitly calls blob.GkmasResource.download().
    """

    def __init__(self, nworker: int):
        self.nworker = nworker

    def dispatch(self, blobs: list, path: str):

        # not initialized in __init__ to avoid memory leak
        self.executor = ThreadPoolExecutor(max_workers=self.nworker)

        futures = [self.executor.submit(blob.download, path) for blob in blobs]
        for future in as_completed(futures):
            future.result()

        self.executor.shutdown()
