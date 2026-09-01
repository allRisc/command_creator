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
"""Tests for individual command-line argument features."""

# NOTE: intentionally *no* ``from __future__ import annotations`` -- pydantic must be
# able to resolve the annotations of models defined inside test functions, and string
# annotations referencing function-local types cannot be resolved.

import pytest

from command_creator import ArgMeta, BaseCmdModel, Field, InvalidCommandError


def _action(parser, dest):
    for action in parser._actions:
        if action.dest == dest:
            return action
    raise AssertionError(f"no action with dest {dest!r}")


def test_help_from_description() -> None:
    class Cmd(BaseCmdModel):
        opt: str = Field("", description="the opt help")

    assert _action(Cmd.get_parser(), "opt").help == "the opt help"


def test_positional_inference() -> None:
    # A required field (no default) is positional; a field with a default is an option.
    class Cmd(BaseCmdModel):
        src: str = Field(description="required -> positional")
        dst: str = Field("out", description="default -> option")

    parser = Cmd.get_parser()
    assert _action(parser, "src").option_strings == []
    assert "--dst" in _action(parser, "dst").option_strings

    cmd = Cmd.parse(["in"])
    assert cmd.src == "in"
    assert cmd.dst == "out"

    cmd = Cmd.parse(["in", "--dst", "here"])
    assert cmd.dst == "here"


def test_abrv() -> None:
    class Cmd(BaseCmdModel):
        opt1: str = Field("", json_schema_extra=ArgMeta(abrv="o"))
        opt2: str = Field("", json_schema_extra=ArgMeta(abrv="pp"))

    parser = Cmd.get_parser()
    assert "-o" in _action(parser, "opt1").option_strings
    assert "--opt1" in _action(parser, "opt1").option_strings
    assert "-pp" in _action(parser, "opt2").option_strings

    assert Cmd.parse(["-o", "x"]).opt1 == "x"


def test_metavar() -> None:
    class Cmd(BaseCmdModel):
        opt: str = Field("", json_schema_extra=ArgMeta(metavar="SOME_META"))

    assert _action(Cmd.get_parser(), "opt").metavar == "SOME_META"


def test_underscores_become_hyphens() -> None:
    class Cmd(BaseCmdModel):
        output_file: str = Field("")

    parser = Cmd.get_parser()
    assert "--output-file" in _action(parser, "output_file").option_strings
    assert Cmd.parse(["--output-file", "f"]).output_file == "f"


def test_int_and_float_coercion() -> None:
    class Cmd(BaseCmdModel):
        count: int = Field(0)
        ratio: float = Field(0.0)

    cmd = Cmd.parse(["--count", "7", "--ratio", "1.5"])
    assert cmd.count == 7 and isinstance(cmd.count, int)
    assert cmd.ratio == 1.5 and isinstance(cmd.ratio, float)


def test_bool_flag_store_true() -> None:
    class Cmd(BaseCmdModel):
        debug: bool = Field(False)

    assert Cmd.parse([]).debug is False
    assert Cmd.parse(["--debug"]).debug is True


def test_bool_flag_store_false() -> None:
    # A bool defaulting to True becomes a "turn it off" flag.
    class Cmd(BaseCmdModel):
        color: bool = Field(True)

    assert Cmd.parse([]).color is True
    assert Cmd.parse(["--color"]).color is False


def test_count() -> None:
    class Cmd(BaseCmdModel):
        verbose: int = Field(0, json_schema_extra=ArgMeta(count=True, abrv="v"))

    assert Cmd.parse([]).verbose == 0
    assert Cmd.parse(["-vvv"]).verbose == 3
    assert Cmd.parse(["--verbose"] * 5).verbose == 5


def test_optional_value_option() -> None:
    class Cmd(BaseCmdModel):
        out: str | None = Field("default_out", json_schema_extra=ArgMeta(optional=True))

    assert Cmd.parse([]).out == "default_out"        # absent -> default
    assert Cmd.parse(["--out"]).out is None          # flag given, no value -> None
    assert Cmd.parse(["--out", "v"]).out == "v"      # value given


def test_forced_positional_with_default() -> None:
    class Cmd(BaseCmdModel):
        name: str = Field("anon", json_schema_extra=ArgMeta(positional=True))

    parser = Cmd.get_parser()
    assert _action(parser, "name").option_strings == []
    assert Cmd.parse([]).name == "anon"
    assert Cmd.parse(["bob"]).name == "bob"


def test_forced_option_when_required() -> None:
    class Cmd(BaseCmdModel):
        token: str = Field(json_schema_extra=ArgMeta(positional=False))

    parser = Cmd.get_parser()
    assert "--token" in _action(parser, "token").option_strings
    with pytest.raises(SystemExit):
        Cmd.parse([])
    assert Cmd.parse(["--token", "abc"]).token == "abc"


def test_count_requires_int() -> None:
    class Cmd(BaseCmdModel):
        bad: str = Field("", json_schema_extra=ArgMeta(count=True))

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_required_bool_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        flag: bool = Field(description="a bare required bool is contradictory")

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_optional_option_without_none_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        x: int = Field(5, json_schema_extra=ArgMeta(optional=True))

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_numeric_abrv_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        n: int = Field(0, json_schema_extra=ArgMeta(abrv="2"))

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_abrv_collision_is_rejected() -> None:
    # '-h' collides with the auto-added help option.
    class Cmd(BaseCmdModel):
        height: int = Field(0, json_schema_extra=ArgMeta(abrv="h"))

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_field_alias_populates_by_name() -> None:
    class Cmd(BaseCmdModel):
        output_file: str = Field("default", alias="out")

    assert Cmd.parse(["--output-file", "y"]).output_file == "y"
    assert Cmd.parse([]).output_file == "default"


@pytest.mark.filterwarnings("ignore::UserWarning")  # pydantic warns on shadowing a method
def test_reserved_field_name_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        run: str = Field("")  # collides with BaseCmdModel.run

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()
