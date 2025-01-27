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
import sys

from enum import Enum
from command_creator import Command, arg
from dataclasses import dataclass
import argparse

import pytest


def test_arg_help() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt1: str = arg(help="Test opt1 help")
        opt2: int = arg(default=1, help="Test opt2 help")

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "opt1":
            assert action.help == "Test opt1 help"
        if action.dest == "opt2":
            assert action.help == "Test opt2 help"


def test_arg_abrv() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt1: str = arg(default="", abrv="o")
        opt2: str = arg(default="", abrv="pp")

    for action in _TmpCmd.create_parser()._actions:
        assert f"--{action.dest}" in action.option_strings
        if action.dest == "opt1":
            assert "-o" in action.option_strings
        if action.dest == "opt2":
            assert "-pp" in action.option_strings


def test_arg_choices_list() -> None:
    options = ["choice1", "choice2", "choice3"]
    @dataclass
    class _TmpCmd(Command):
        opt: str = arg(choices=options)

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "opt":
            assert action.choices is not None
            assert set(options) == set(action.choices)


def test_arg_choices_enum() -> None:
    class _TmpEnum(Enum):
        A = "a"
        B = "b"
        C = "c"

    @dataclass
    class _TmpCmd(Command):
        opt: _TmpEnum = arg(choices=_TmpEnum)

        def __call__(self) -> int:
            return 0

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "opt":
            assert action.choices is not None
            assert set(action.choices) == {"A", "B", "C"}

    args = _TmpCmd.create_parser().parse_args("B".split())
    assert args.opt == 'B'

    cmd = _TmpCmd.from_args(args)
    assert cmd.opt == _TmpEnum.B

    with pytest.raises(SystemExit):
        args = _TmpCmd.create_parser().parse_args("D".split())


def test_arg_positional() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt1: str | None = arg(positional=True)
        opt2: str = arg(positional=True, default="default_opt2")

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "help":
            continue
        assert len(action.option_strings) == 0

    args = _TmpCmd.create_parser().parse_args("".split())
    assert args.opt1 is None
    assert args.opt2 == "default_opt2"


def test_arg_count() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt: int = arg(count=True)

    _TmpCmd.create_parser().print_help()
    args = _TmpCmd.create_parser().parse_args(["--opt"] * 5)
    assert args.opt == 5
    args = _TmpCmd.create_parser().parse_args(["--opt"] * 7)
    assert args.opt == 7


def test_arg_completer_list() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt: int = arg(completer=[0, 1, 2, 3])

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "opt":
            assert action.choices is not None
            assert set(action.choices) == {0, 1, 2, 3}
            assert action.metavar == "OPT"


def test_arg_completer_dict() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt: int = arg(completer={0: "Zero", 1: "One"})

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "opt":
            assert action.completer(  # type:ignore[attr-defined]
                prefix="",
                action=action,
                parser=_TmpCmd.create_parser(),
                parsed_args=argparse.Namespace()
            ) == {0: "Zero", 1: "One"}
            assert action.metavar == "OPT"


def test_arg_completer_callable() -> None:
    if sys.version_info > (3, 10):
        from typing import Unpack
        from command_creator import CompleterArgs
        def _tmp_completer(**kwargs: Unpack[CompleterArgs]) -> dict[str, str]:
            return {f"c{i}": f"Choice {i}" for i in range(10)}
    else:
        def _tmp_completer(**kwargs) -> dict[str, str]:
            return {f"c{i}": f"Choice {i}" for i in range(10)}

    @dataclass
    class _TmpCmd(Command):
        opt: str = arg(completer=_tmp_completer)

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "opt":
            assert action.completer(  # type:ignore[attr-defined]
                prefix="",
                action=action,
                parser=_TmpCmd.create_parser(),
                parsed_args=argparse.Namespace()
            ) == {f"c{i}": f"Choice {i}" for i in range(10)}
            assert action.metavar == "OPT"


def test_arg_completer_callable() -> None:
    @dataclass
    class _TmpCmd(Command):
        opt: str = arg(metavar="SOME_META")

    for action in _TmpCmd.create_parser()._actions:
        if action.dest == "opt":
            assert action.metavar == "SOME_META"
