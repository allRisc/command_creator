#####################################################################################
# A package to simplify the creation of Python Command-Line tools
# Copyright (C) 2026  Benjamin Davis
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; If not, see <https://www.gnu.org/licenses/>.
#####################################################################################
"""Example command-line tool built with ``command_creator``.

Try it out::

    python example.py --help
    python example.py greet Ada --loud
    python example.py remote add https://example.com --name origin
    python example.py rm add https://example.com   # 'rm' is an alias of 'remote'
"""

from enum import StrEnum
from typing import ClassVar

from command_creator import BaseCmdModel, arg, option


class Casing(StrEnum):
    """How to render greeting text."""

    plain = "plain"
    caps = "caps"
    titled = "titled"


class Greet(BaseCmdModel):
    """Greet someone by name."""

    # Aliases let the sub-command be invoked as `greet`, `hi` or `hello`.
    cmd_aliases: ClassVar = ("hi", "hello")

    # arg() -> a positional argument (no default -> required).
    name: str = arg(description="who to greet")
    # option() -> a `--loud`/`-l` option.
    loud: bool = option(default=False, abrv="l", description="SHOUT the greeting")
    # An Enum field becomes a `--casing {plain,caps,titled}` choice for free.
    casing: Casing = option(default=Casing.titled, description="how to case the greeting")

    def run(self) -> None:
        message = f"Hello, {self.name}!"
        if self.casing is Casing.caps:
            message = message.upper()
        elif self.casing is Casing.titled:
            message = message.title()
        print(message.upper() if self.loud else message)


class RemoteAdd(BaseCmdModel):
    """Add a remote."""

    cmd_name: ClassVar = "add"

    url: str = arg(description="remote URL")
    name: str = option(default="origin", description="local name for the remote")

    def run(self) -> None:
        print(f"Added remote {self.name!r} -> {self.url}")


class Remote(BaseCmdModel):
    """Manage remotes (has its own sub-commands, nested to any depth)."""

    cmd_aliases: ClassVar = ("rmt",)
    sub_commands: ClassVar = (RemoteAdd,)

    def run(self) -> None:
        # Runs before the selected child (whole-path dispatch); nothing to do here.
        pass


class Tool(BaseCmdModel):
    """A small example tool.  Its sub-commands do the real work."""

    # A repeat-counter: `-vvv` -> verbose == 3.
    verbose: int = option(default=0, count=True, abrv="v", description="increase verbosity")
    sub_commands: ClassVar = (Greet, Remote)

    def run(self) -> None:
        if self.verbose:
            print(f"[verbosity: {self.verbose}]")


if __name__ == "__main__":
    Tool.run_and_exit()
