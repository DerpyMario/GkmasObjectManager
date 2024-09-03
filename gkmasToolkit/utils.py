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
