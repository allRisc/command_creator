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

from command_creator import BaseCmdModel, Field, InvalidCommandError, arg, arg_meta, option


def _action(parser, dest):
    for action in parser._actions:
        if action.dest == dest:
            return action
    raise AssertionError(f"no action with dest {dest!r}")


def test_help_from_description() -> None:
    class Cmd(BaseCmdModel):
        opt: str = option(default="", description="the opt help")

    assert _action(Cmd.get_parser(), "opt").help == "the opt help"


def test_arg_is_positional_option_is_optional() -> None:
    class Cmd(BaseCmdModel):
        src: str = arg(description="a positional")
        dst: str = option(default="out", description="an option")

    parser = Cmd.get_parser()
    assert _action(parser, "src").option_strings == []
    assert "--dst" in _action(parser, "dst").option_strings

    cmd = Cmd.parse(["in"])
    assert cmd.src == "in"
    assert cmd.dst == "out"
    assert Cmd.parse(["in", "--dst", "here"]).dst == "here"


def test_raw_field_positional_inference() -> None:
    # The escape hatch: a plain Field still works -- required -> positional, default -> option.
    class Cmd(BaseCmdModel):
        src: str = Field(description="required -> positional")
        dst: str = Field("out", description="default -> option")

    parser = Cmd.get_parser()
    assert _action(parser, "src").option_strings == []
    assert "--dst" in _action(parser, "dst").option_strings


def test_abrv() -> None:
    class Cmd(BaseCmdModel):
        opt1: str = option(default="", abrv="o")
        opt2: str = option(default="", abrv="pp")

    parser = Cmd.get_parser()
    assert "-o" in _action(parser, "opt1").option_strings
    assert "--opt1" in _action(parser, "opt1").option_strings
    assert "-pp" in _action(parser, "opt2").option_strings

    assert Cmd.parse(["-o", "x"]).opt1 == "x"


def test_metavar() -> None:
    class Cmd(BaseCmdModel):
        opt: str = option(default="", metavar="SOME_META")

    assert _action(Cmd.get_parser(), "opt").metavar == "SOME_META"


def test_underscores_become_hyphens() -> None:
    class Cmd(BaseCmdModel):
        output_file: str = option(default="")

    parser = Cmd.get_parser()
    assert "--output-file" in _action(parser, "output_file").option_strings
    assert Cmd.parse(["--output-file", "f"]).output_file == "f"


def test_int_and_float_coercion() -> None:
    class Cmd(BaseCmdModel):
        count: int = option(default=0)
        ratio: float = option(default=0.0)

    cmd = Cmd.parse(["--count", "7", "--ratio", "1.5"])
    assert cmd.count == 7 and isinstance(cmd.count, int)
    assert cmd.ratio == 1.5 and isinstance(cmd.ratio, float)


def test_bool_flag_store_true() -> None:
    class Cmd(BaseCmdModel):
        debug: bool = option(default=False)

    assert Cmd.parse([]).debug is False
    assert Cmd.parse(["--debug"]).debug is True


def test_bool_flag_store_false() -> None:
    # A bool defaulting to True becomes a "turn it off" flag.
    class Cmd(BaseCmdModel):
        color: bool = option(default=True)

    assert Cmd.parse([]).color is True
    assert Cmd.parse(["--color"]).color is False


def test_count() -> None:
    class Cmd(BaseCmdModel):
        verbose: int = option(default=0, count=True, abrv="v")

    assert Cmd.parse([]).verbose == 0
    assert Cmd.parse(["-vvv"]).verbose == 3
    assert Cmd.parse(["--verbose"] * 5).verbose == 5


def test_optional_value_option() -> None:
    class Cmd(BaseCmdModel):
        out: str | None = option(default="default_out", optional=True)

    assert Cmd.parse([]).out == "default_out"        # absent -> default
    assert Cmd.parse(["--out"]).out is None          # flag given, no value -> None
    assert Cmd.parse(["--out", "v"]).out == "v"      # value given


def test_arg_with_default_is_optional_positional() -> None:
    class Cmd(BaseCmdModel):
        name: str = arg(default="anon")

    parser = Cmd.get_parser()
    assert _action(parser, "name").option_strings == []
    assert Cmd.parse([]).name == "anon"
    assert Cmd.parse(["bob"]).name == "bob"


def test_option_without_default_is_required() -> None:
    class Cmd(BaseCmdModel):
        token: str = option()

    assert "--token" in _action(Cmd.get_parser(), "token").option_strings
    with pytest.raises(SystemExit):
        Cmd.parse([])
    assert Cmd.parse(["--token", "abc"]).token == "abc"


def test_option_forwards_pydantic_constraints() -> None:
    from pydantic import ValidationError

    class Cmd(BaseCmdModel):
        port: int = option(default=8080, ge=1, le=65535)

    assert Cmd.parse(["--port", "9000"]).port == 9000
    with pytest.raises(ValidationError):
        Cmd.parse(["--port", "70000"])


def test_option_forwards_arbitrary_field_kwargs() -> None:
    # Any pydantic Field option (here title/examples) is forwarded to the FieldInfo.
    class Cmd(BaseCmdModel):
        port: int = option(default=8080, title="Port", examples=[80, 443])

    info = Cmd.model_fields["port"]
    assert info.title == "Port"
    assert info.examples == [80, 443]


def test_count_requires_int() -> None:
    class Cmd(BaseCmdModel):
        bad: str = option(default="", count=True)

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_required_bool_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        flag: bool = option()  # a bare required bool is contradictory

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_optional_option_without_none_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        x: int = option(default=5, optional=True)

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_numeric_abrv_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        n: int = option(default=0, abrv="2")

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_abrv_collision_is_rejected() -> None:
    # '-h' collides with the auto-added help option.
    class Cmd(BaseCmdModel):
        height: int = option(default=0, abrv="h")

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()


def test_field_alias_populates_by_name() -> None:
    class Cmd(BaseCmdModel):
        output_file: str = Field("default", alias="out")

    assert Cmd.parse(["--output-file", "y"]).output_file == "y"
    assert Cmd.parse([]).output_file == "default"


def test_arg_meta_escape_hatch_with_extra_keys() -> None:
    # arg_meta() feeds a raw Field; recognised keys plus arbitrary extras pass through.
    class Cmd(BaseCmdModel):
        opt: str = Field("", json_schema_extra=arg_meta(abrv="o", my_tag="io", weight=3))

    assert Cmd.model_fields["opt"].json_schema_extra == {"abrv": "o", "my_tag": "io", "weight": 3}
    assert "-o" in _action(Cmd.get_parser(), "opt").option_strings


def test_arg_meta_omits_unset_but_keeps_explicit_none_extra() -> None:
    assert arg_meta(abrv="v") == {"abrv": "v"}
    assert arg_meta(abrv="v", note=None) == {"abrv": "v", "note": None}


@pytest.mark.filterwarnings("ignore::UserWarning")  # pydantic warns on shadowing a method
def test_reserved_field_name_is_rejected() -> None:
    class Cmd(BaseCmdModel):
        run: str = option(default="")  # collides with BaseCmdModel.run

    with pytest.raises(InvalidCommandError):
        Cmd.get_parser()
