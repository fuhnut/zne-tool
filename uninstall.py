from __future__ import annotations

import os
import sys
from pathlib import Path

from colorama import (
    Fore,
    Style,
    init,
)

init()


def _install_path() -> tuple[Path, Path | None]:
    if sys.platform == "win32":
        base = Path(
            os.environ.get(
                "APPDATA",
                Path.home() / "AppData" / "Roaming",
            )
        )
        d = base / "Python" / "Scripts"
        return d / "zne.py", d / "zne.cmd"
    d = Path.home() / ".local" / "bin"
    return d / "zne", None


def main() -> None:
    wrapper, cmd_wrapper = _install_path()
    removed = False

    if wrapper.exists():
        wrapper.unlink()
        print(
            f"{Fore.GREEN}✓{Style.RESET_ALL} "
            f"removed {Fore.CYAN}{wrapper}{Style.RESET_ALL}"
        )
        removed = True

    if cmd_wrapper and cmd_wrapper.exists():
        cmd_wrapper.unlink()
        print(
            f"{Fore.GREEN}✓{Style.RESET_ALL} "
            f"removed {Fore.CYAN}{cmd_wrapper}{Style.RESET_ALL}"
        )
        removed = True

    if not removed:
        print(f"{Fore.YELLOW}!{Style.RESET_ALL} zne command is not installed")


if __name__ == "__main__":
    main()
