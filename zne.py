import asyncio
import sys

from colorama import init

init()

from ui.app import zneapp


def install_uvloop() -> None:
    if sys.platform != "win32":
        try:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass


def main() -> None:
    install_uvloop()
    zneapp().run()


if __name__ == "__main__":
    main()
