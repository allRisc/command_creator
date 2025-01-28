#####################################################################################
# A package to simplify the creation of Python Command-Line tools
# Copyright (C) 2025  Benjamin Davis
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

from command_creator import Command, arg
from dataclasses import dataclass

import pytest


def test_list_arg() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt1: list[str] = arg(default_factory=list)

        def __call__(self) -> int:
            return 0

    tmp = _TmpCmd.parse_args("--opt1 val1".split())
    assert isinstance(tmp.opt1, list)
    assert set(tmp.opt1) == {"val1"}

    tmp = _TmpCmd.parse_args("--opt1 val1 val2".split())
    assert isinstance(tmp.opt1, list)
    assert set(tmp.opt1) == {"val1", "val2"}

    tmp = _TmpCmd.parse_args("".split())
    assert isinstance(tmp.opt1, list)
    assert len(tmp.opt1) == 0


def test_list_arg_positional() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt1: list[str] | None = arg(positional=True, optional=True)

        def __call__(self) -> int:
            return 0

    tmp = _TmpCmd.parse_args("val1".split())
    assert isinstance(tmp.opt1, list)
    assert set(tmp.opt1) == {"val1"}

    tmp = _TmpCmd.parse_args("val1 val2".split())
    assert isinstance(tmp.opt1, list)
    assert set(tmp.opt1) == {"val1", "val2"}

    tmp = _TmpCmd.parse_args("".split())
    assert tmp.opt1 is None


def test_list_arg_positional_default() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt1: list[str] | None = arg(positional=True, optional=True, default_factory=list)

        def __call__(self) -> int:
            return 0

    tmp = _TmpCmd.parse_args("val1".split())
    assert isinstance(tmp.opt1, list)
    assert set(tmp.opt1) == {"val1"}

    tmp = _TmpCmd.parse_args("val1 val2".split())
    assert isinstance(tmp.opt1, list)
    assert set(tmp.opt1) == {"val1", "val2"}

    tmp = _TmpCmd.parse_args("".split())
    assert isinstance(tmp.opt1, list)
    assert len(tmp.opt1) == 0
