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

from __future__ import annotations

import command_creator as cc
import enum


# Set of choices to use for one of the arguments
class Choices(enum.StrEnum):
  choice1 = enum.auto()
  choice2 = enum.auto()


# Create a new command
@cc.dataclass
class CommandName(cc.Command):
  """Description of the command"""

  positional_arg: str = cc.arg(help="A positional argument")
  optional_arg: str = cc.arg(help="An optional argument", default="default value")
  flag_arg: bool = cc.arg(help="A flag argument", default=True, abrv="f")
  choice_arg: Choices = cc.arg(help="A choice argument", default=Choices.choice1, choices=Choices)

  def __post_init__(self) -> None:
    # Any additional setup can be done here
    pass

  def __call__(self) -> int:

    # The command's logic goes here
    print(self)
    return 0


if __name__ == "__main__":
  CommandName.execute()
