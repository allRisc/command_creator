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
"""Tests for how field types map onto command-line arguments."""

import enum
from typing import Literal

import pytest

from command_creator import BaseCmdModel, Field


class Color(enum.StrEnum):
    RED = enum.auto()
    GREEN = enum.auto()
    BLUE = enum.auto()


class Level(enum.IntEnum):
    LOW = 1
    HIGH = 10


def _action(parser, dest):
    for action in parser._actions:
        if action.dest == dest:
            return action
    raise AssertionError(f"no action with dest {dest!r}")


def test_list_option() -> None:
    class Cmd(BaseCmdModel):
        opt: list[str] = Field(default_factory=list)

    assert Cmd.parse([]).opt == []
    assert Cmd.parse(["--opt", "a"]).opt == ["a"]
    assert Cmd.parse(["--opt", "a", "b", "c"]).opt == ["a", "b", "c"]


def test_list_positional_required() -> None:
    class Cmd(BaseCmdModel):
        paths: list[str] = Field(description="one or more paths")

    parser = Cmd.get_parser()
    assert _action(parser, "paths").option_strings == []
    assert _action(parser, "paths").nargs == "+"
    assert Cmd.parse(["a", "b"]).paths == ["a", "b"]
    with pytest.raises(SystemExit):
        Cmd.parse([])


def test_list_of_ints_coerced() -> None:
    class Cmd(BaseCmdModel):
        nums: list[int] = Field(default_factory=list)

    assert Cmd.parse(["--nums", "1", "2", "3"]).nums == [1, 2, 3]


def test_str_enum_choices() -> None:
    class Cmd(BaseCmdModel):
        color: Color = Field(Color.RED)

    action = _action(Cmd.get_parser(), "color")
    assert action.choices is not None and set(action.choices) == {"red", "green", "blue"}

    assert Cmd.parse(["--color", "blue"]).color is Color.BLUE
    assert Cmd.parse([]).color is Color.RED
    with pytest.raises(SystemExit):
        Cmd.parse(["--color", "purple"])


def test_int_enum_choices() -> None:
    class Cmd(BaseCmdModel):
        level: Level = Field(Level.LOW)

    action = _action(Cmd.get_parser(), "level")
    assert action.choices is not None and set(action.choices) == {1, 10}

    assert Cmd.parse(["--level", "10"]).level is Level.HIGH


def test_literal_choices() -> None:
    class Cmd(BaseCmdModel):
        mode: Literal["fast", "slow"] = Field("fast")

    action = _action(Cmd.get_parser(), "mode")
    assert action.choices is not None and set(action.choices) == {"fast", "slow"}

    assert Cmd.parse(["--mode", "slow"]).mode == "slow"
    with pytest.raises(SystemExit):
        Cmd.parse(["--mode", "medium"])


def test_int_literal_choices() -> None:
    # Integer literals must be converted before comparison against int choices.
    class Cmd(BaseCmdModel):
        lvl: Literal[1, 2, 3] = Field(1)

    action = _action(Cmd.get_parser(), "lvl")
    assert action.choices is not None and set(action.choices) == {1, 2, 3}

    assert Cmd.parse(["--lvl", "2"]).lvl == 2
    with pytest.raises(SystemExit):
        Cmd.parse(["--lvl", "5"])


def test_fixed_length_tuple() -> None:
    class Cmd(BaseCmdModel):
        pair: tuple[int, str] = Field((0, "x"))

    action = _action(Cmd.get_parser(), "pair")
    assert action.nargs == 2

    assert Cmd.parse(["--pair", "1", "hello"]).pair == (1, "hello")
    with pytest.raises(SystemExit):  # wrong arity rejected by argparse
        Cmd.parse(["--pair", "1"])


def test_variadic_tuple() -> None:
    class Cmd(BaseCmdModel):
        xs: tuple[int, ...] = Field(default_factory=tuple)

    assert Cmd.parse(["--xs", "1", "2", "3"]).xs == (1, 2, 3)
    assert Cmd.parse([]).xs == ()


def test_optional_scalar_defaults_none() -> None:
    class Cmd(BaseCmdModel):
        out: str | None = Field(None)

    assert Cmd.parse([]).out is None
    assert Cmd.parse(["--out", "x"]).out == "x"


def test_pydantic_validation_still_applies() -> None:
    # Constraints declared on the pydantic Field are enforced on the parsed value.
    from pydantic import ValidationError

    class Cmd(BaseCmdModel):
        port: int = Field(8080, ge=1, le=65535)

    assert Cmd.parse(["--port", "9000"]).port == 9000
    with pytest.raises(ValidationError):
        Cmd.parse(["--port", "70000"])
