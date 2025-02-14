import json
from typing import Any, ClassVar

from colorama import Fore, Style, just_fix_windows_console

just_fix_windows_console()


class Log:
    debug_mode: ClassVar[bool] = False

    def __init__(self, logger_name: str):
        self.logger_name = logger_name

    def info(self, message: str):
        print(f"{Fore.GREEN}{Style.BRIGHT}[+{self.logger_name}+] {message}{Style.RESET_ALL}")

    def debug(self, message: str):
        if not self.debug_mode:
            return

        print(f"{Fore.BLUE}{Style.BRIGHT}[*{self.logger_name}*] {message}{Style.RESET_ALL}")

    def verbose(self, message: str):
        print(f"{Fore.CYAN}{Style.BRIGHT}[~{self.logger_name}~] {message}{Style.RESET_ALL}")

    def warning(self, message: str):
        print(f"{Fore.YELLOW}{Style.BRIGHT}[!{self.logger_name}!] {message}{Style.RESET_ALL}")

    def error(self, message: str):
        print(f"{Fore.RED}{Style.BRIGHT}[-{self.logger_name}-] {message}{Style.RESET_ALL}")


_config = None
def get_config(key: str) -> Any:
    global _config  # noqa: PLW0603 shhhhh :)

    if _config is None:
        with open("config.json") as f:
            _config = json.load(f)
    return _config[key]
