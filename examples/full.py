#!/usr/bin/env python
#####################################################################################
# A package to simplify the creation of Python Command-Line tools
# Copyright (C) 2023  Benjamin Davis
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

# Optional:
# from __future__ import annotations

import command_creator as cc

import enum
import pathlib

from argcomplete.completers import ChoicesCompleter


class Choices(enum.StrEnum):
    CHOICE1 = enum.auto()
    CHOICE2 = enum.auto()
    CHOICE3 = enum.auto()


@cc.dataclass
class Full(cc.Command):

    filename: str = cc.arg(
        help="The filename to select"
    )
    debug: bool = cc.arg(
        help="Set the command into debug mode",
        default=True
    )
    choices: Choices = cc.arg(
        help="Some choice to make",
        default=Choices.CHOICE1
    )
    iterations: int = cc.arg(
        help="The number of iterataions",
        default=10
    )
    args: list[str] = cc.arg(default_factory=list)
    seed: int | None = cc.arg(default=None)
    test: str | None = cc.arg(
        default=None,
        completer=ChoicesCompleter(["test_base", "test_spi", "test_i2c"])
    )

    def __post_init__(self) -> None:
        pass

    def __call__(self) -> int:
        if not pathlib.Path(self.filename).resolve().exists():
            print("Invalid path")
            return cc.FAILURE

        print(self)


if __name__ == "__main__":
    Full.execute()
