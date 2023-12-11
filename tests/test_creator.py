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

import io
from enum import Enum
from command_creator import Command, arg
from dataclasses import dataclass
import sys


class OptionsDemo(Enum):
  """Enum to demonstrate the use of an Enum for the choices of an argument
  """
  A = "A"
  B = "B"
  C = "C"


@dataclass
class DemoCommand(Command):
  """Create a demo command
  """
  test: str = arg(help="A test argument")
  choose: OptionsDemo = arg(choices=OptionsDemo, help="Choose an option", default=OptionsDemo.A)
  debug: bool = arg(abrv="d", help="Enable debug mode", default=False)

  def __post_init__(self) -> None:
    pass

  def __call__(self) -> int:
    return 0


def test_creator():
  parser = DemoCommand.create_parser()
  str_io = io.StringIO()
  parser.print_help(str_io)

  opt_str = "options:" if sys.version_info >= (3, 10) else "optional arguments:"

  assert str_io.getvalue() == (
                               "usage: democommand [-h] [--choose {A,B,C}] [--debug] test\n"
                               "\n"
                               "Create a demo command\n"
                               "\n"
                               "positional arguments:\n"
                               "  test              A test argument\n"
                               "\n"
                               f"{opt_str}\n"
                               "  -h, --help        show this help message and exit\n"
                               "  --choose {A,B,C}  Choose an option\n"
                               "  --debug, -d       Enable debug mode\n"
                              )


if __name__ == "__main__":
  parser = DemoCommand.create_parser()
  str_io = io.StringIO()
  parser.print_help(str_io)

  print(str_io.getvalue())
