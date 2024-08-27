from rich.console import Console


class Logger(Console):

    def __init__(self):
        super().__init__()

    def info(self, message: str):
        self.print(f"[bold white]>>> [Info][/bold white] {message}\n")

    def success(self, message: str):
        self.print(f"[bold green]>>> [Success][/bold green] {message}\n")

    def error(self, message: str, fatal: bool = False):
        if fatal:
            self.print(
                f"[bold red]>>> [Error][/bold red] {message}\n{sys.exc_info()}\n"
            )
            raise
        else:
            self.print(f"[bold red]>>> [Error][/bold red] {message}\n")
