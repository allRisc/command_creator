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
"""Tests for ``propagate=True``: options/groups made available on descendant
sub-commands so they may be given anywhere in the argument list.
"""

# NOTE: no ``from __future__ import annotations`` -- pydantic must resolve the
# annotations of models defined inside test functions (see test_groups.py).

import pytest
from pydantic import Field

from command_creator import (
    BaseCmdModel,
    CmdConfig,
    InvalidCommandError,
    arg_meta,
    group,
    option,
)


#####################################################################################
# A three-level tree with propagated options declared on the root.
#####################################################################################
class _Leaf(BaseCmdModel):
    """Leaf command with its own positional."""

    model_config = CmdConfig(cmd_name="leaf")
    target: str = Field(json_schema_extra={"positional": True, "metavar": "target"})

    def run(self) -> None: ...


class _Mid(BaseCmdModel):
    """Intermediate command grouping a sub-command."""

    model_config = CmdConfig(cmd_name="mid", sub_commands=(_Leaf,))
    label: str = option(default="none", abrv="l")

    def run(self) -> None: ...


class _Root(BaseCmdModel):
    """Top-level command with propagated globals."""

    model_config = CmdConfig(sub_commands=(_Mid,))
    verbose: int = option(default=0, count=True, abrv="v", propagate=True)
    config: str | None = option(default=None, propagate=True)
    quiet: bool = option(default=False, propagate=True)

    def run(self) -> None: ...


def test_propagated_option_before_or_after_subcommand() -> None:
    # Given before the sub-command (classic argparse position) ...
    assert _Root.parse(["--config", "a.cfg", "mid"]).config == "a.cfg"
    # ... or after it: same field on the same (root) instance.
    assert _Root.parse(["mid", "--config", "a.cfg"]).config == "a.cfg"


def test_propagated_option_reaches_grandchild() -> None:
    root = _Root.parse(["mid", "leaf", "widget", "--config", "deep.cfg"])
    assert root.config == "deep.cfg"
    # The positional still lands on the leaf.
    assert root.sub_command.sub_command.target == "widget"


def test_propagated_count_flag_after_subcommand() -> None:
    assert _Root.parse(["mid", "leaf", "w", "-vvv"]).verbose == 3
    assert _Root.parse(["-vv", "mid"]).verbose == 2


def test_propagated_bool_flag_after_subcommand() -> None:
    assert _Root.parse(["mid", "leaf", "w", "--quiet"]).quiet is True


def test_propagated_negatable_flag_after_subcommand() -> None:
    class Sub(BaseCmdModel):
        model_config = CmdConfig(cmd_name="sub")

        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        color: bool = option(default=True, negatable=True, propagate=True)

        def run(self) -> None: ...

    # The negated form is accepted after the sub-command token ...
    assert Root.parse(["sub", "--no-color"]).color is False
    # ... and the positive form too; both land on the root owner.
    assert Root.parse(["sub", "--color"]).color is True
    # Absent everywhere -> owner default.
    assert Root.parse(["sub"]).color is True


def test_absent_propagated_options_keep_owner_default() -> None:
    root = _Root.parse(["mid", "leaf", "w"])
    assert root.verbose == 0
    assert root.config is None
    assert root.quiet is False


def test_deepest_level_wins_on_override() -> None:
    # -v at the root then -vv at the leaf: deepest (leaf) value replaces the shallower.
    assert _Root.parse(["-v", "mid", "leaf", "w", "-vv"]).verbose == 2


def test_non_propagated_option_rejected_after_subcommand() -> None:
    class Sub(BaseCmdModel):
        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        plain: str = option(default="p")  # not propagated

        def run(self) -> None: ...

    assert Root.parse(["--plain", "x", "sub"]).plain == "x"
    with pytest.raises(SystemExit):
        Root.parse(["sub", "--plain", "x"])


#####################################################################################
# Propagated groups
#####################################################################################
def test_propagated_group_flattens_onto_descendants() -> None:
    class Net(BaseCmdModel):
        host: str = option(default="localhost")
        port: int = option(default=80)

    class Sub(BaseCmdModel):
        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        net: Net = group(propagate=True)

        def run(self) -> None: ...

    root = Root.parse(["sub", "--host", "db", "--port", "90"])
    assert root.net.host == "db"
    assert root.net.port == 90
    # And still usable before the sub-command.
    assert Root.parse(["--host", "db", "sub"]).net.host == "db"


#####################################################################################
# --help / display
#####################################################################################
def test_inherited_option_listed_on_subcommand_parser() -> None:
    parser = _Root.get_parser()
    sub_action = next(a for a in parser._actions if a.dest.startswith("_cc_lvl"))
    mid_parser = sub_action.choices["mid"]
    option_strings = {s for a in mid_parser._actions for s in a.option_strings}
    assert "--config" in option_strings
    assert "-v" in option_strings


def test_inherited_option_renders_under_shared_group_title() -> None:
    class Sub(BaseCmdModel):
        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        token: str = option(default="t", group="Auth", propagate=True)

        def run(self) -> None: ...

    parser = Root.get_parser()
    sub_action = next(a for a in parser._actions if a.dest.startswith("_cc_lvl"))
    sub_parser = sub_action.choices["sub"]
    titles = [grp.title for grp in sub_parser._action_groups if grp.title == "Auth"]
    assert titles == ["Auth"]


#####################################################################################
# Validation
#####################################################################################
def test_propagate_on_required_field_is_rejected() -> None:
    class Sub(BaseCmdModel):
        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        token: str = option(propagate=True)  # required (no default)

        def run(self) -> None: ...

    with pytest.raises(InvalidCommandError, match="requires a default"):
        Root.get_parser()


def test_propagate_on_positional_is_rejected() -> None:
    class Sub(BaseCmdModel):
        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        p: str = Field(
            default="d", json_schema_extra=arg_meta(positional=True, propagate=True)
        )

        def run(self) -> None: ...

    with pytest.raises(InvalidCommandError, match="not positional"):
        Root.get_parser()


def test_propagated_name_clash_with_subcommand_is_rejected() -> None:
    class Sub(BaseCmdModel):
        config: str = option(default="s")

        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        config: str = option(default="r", propagate=True)

        def run(self) -> None: ...

    with pytest.raises(InvalidCommandError, match="conflicting option string"):
        Root.get_parser()


def test_propagate_in_group_with_required_subfield_is_rejected() -> None:
    class Net(BaseCmdModel):
        host: str = option()  # required

    class Sub(BaseCmdModel):
        def run(self) -> None: ...

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))
        net: Net = group(propagate=True)

        def run(self) -> None: ...

    with pytest.raises(InvalidCommandError, match="requires a default"):
        Root.get_parser()
