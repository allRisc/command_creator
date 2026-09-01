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
"""Create command-line tools from :mod:`pydantic` models.

Define a command by subclassing :class:`~command_creator.command.BaseCmdModel`, declare
each argument as a pydantic field (using ``pydantic.Field`` for defaults/help and
:class:`~command_creator.command.ArgMeta` metadata for CLI-only extras), and nest
sub-commands to any depth via the ``sub_commands`` class attribute::

    from typing import ClassVar

    from command_creator import BaseCmdModel, ArgMeta, Field


    class Greet(BaseCmdModel):
        \"\"\"Greet someone.\"\"\"

        name: str = Field(description="who to greet")
        loud: bool = Field(False, description="shout", json_schema_extra=ArgMeta(abrv="l"))

        def run(self) -> None:
            message = f"Hello, {self.name}!"
            print(message.upper() if self.loud else message)


    if __name__ == "__main__":
        Greet.run_and_exit()
"""

from __future__ import annotations

from pydantic import Field

from ._info import __author__, __version__
from .command import ArgMeta, BaseCmdModel, InvalidCommandError

__all__ = [
    "ArgMeta",
    "BaseCmdModel",
    "Field",
    "InvalidCommandError",
    "__author__",
    "__version__",
]
