from __future__ import annotations

import asyncio
import os
import stat
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


def _self_install() -> None:
    wrapper, cmd_wrapper = _install_path()
    if wrapper.exists():
        return

    print(
        f"{Fore.MAGENTA}?{Style.RESET_ALL} "
        f"install {Fore.CYAN}zne{Style.RESET_ALL} command to PATH? "
        f"{Fore.WHITE}[y/n]{Style.RESET_ALL} ",
        end="",
        flush=True,
    )

    try:
        ans = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if ans not in ("y", "yes"):
        print(f"{Fore.YELLOW}skipped{Style.RESET_ALL}")
        return

    wrapper.parent.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    this = Path(__file__).resolve()

    if sys.platform == "win32":
        wrapper.write_text(f'@"{python}" "{this}" %*\n')
        cmd_wrapper.write_text(f'@"{python}" "{this}" %*\n')
    else:
        wrapper.write_text(f'#!/usr/bin/env sh\nexec "{python}" "{this}" "$@"\n')
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

    print(
        f"{Fore.GREEN}✓{Style.RESET_ALL} "
        f"installed -> {Fore.CYAN}{wrapper}{Style.RESET_ALL}"
    )

    path_env = os.environ.get("PATH", "")
    if str(wrapper.parent) not in path_env:
        if sys.platform == "win32":
            print(
                f"{Fore.YELLOW}!{Style.RESET_ALL} add this folder to your system PATH:"
            )
            print(f"  {Fore.WHITE}{wrapper.parent}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}!{Style.RESET_ALL} add this to your shell config:")
            print(
                f'  {Fore.WHITE}export PATH="{wrapper.parent}:$PATH"{Style.RESET_ALL}'
            )


def _install_uvloop() -> None:
    if sys.platform == "win32":
        return
    try:
        from uvloop import EventLoopPolicy

        asyncio.set_event_loop_policy(EventLoopPolicy())
    except ImportError:
        pass


def main() -> None:
    _self_install()
    _install_uvloop()

    from ui.app import zneapp

    zneapp().run()


if __name__ == "__main__":
    main()
