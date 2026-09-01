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
"""Tests for sub-commands: aliases, arbitrary nesting depth and dispatch."""

from typing import ClassVar

import pytest

from command_creator import BaseCmdModel, InvalidCommandError, arg, option

# Records the order in which run() methods fire, for the dispatch tests.
RUN_LOG: list[str] = []


class Deep(BaseCmdModel):
    """A third-level (leaf) command."""

    cmd_aliases: ClassVar = ("dd",)
    target: str = arg(description="what to go deep on")  # positional (leaf, no sub-commands)
    factor: int = option(default=1, abrv="f")

    def run(self) -> None:
        RUN_LOG.append(f"deep:{self.target}:{self.factor}")


class Add(BaseCmdModel):
    """Add an item."""

    # An intermediate command that groups sub-commands uses options, not positionals.
    cmd_aliases: ClassVar = ("a", "insert")
    sub_commands: ClassVar = (Deep,)
    label: str = option(default="none", abrv="l")

    def run(self) -> None:
        RUN_LOG.append(f"add:{self.label}")


class Remove(BaseCmdModel):
    """Remove an item."""

    cmd_name: ClassVar = "remove"
    cmd_aliases: ClassVar = ("rm", "del")
    name: str = arg(description="item name")  # positional (leaf, no sub-commands)

    def run(self) -> None:
        RUN_LOG.append(f"remove:{self.name}")


class Root(BaseCmdModel):
    """Top-level command."""

    sub_commands: ClassVar = (Add, Remove)
    verbose: bool = option(default=False, abrv="v")

    def run(self) -> None:
        RUN_LOG.append("root")


def setup_function() -> None:
    RUN_LOG.clear()


def test_cmd_name_defaults_to_lowercased_class_name() -> None:
    assert Add.get_cmd_name() == "add"
    assert Deep.get_cmd_name() == "deep"


def test_cmd_name_explicit_override() -> None:
    assert Remove.get_cmd_name() == "remove"


def test_no_subcommand_selected() -> None:
    root = Root.parse([])
    assert root.sub_command is None
    assert root.command_chain() == [root]


def test_select_subcommand_by_canonical_name() -> None:
    root = Root.parse(["add", "-l", "widget"])
    assert isinstance(root.sub_command, Add)
    assert root.sub_command.label == "widget"


def test_select_subcommand_by_alias() -> None:
    for alias in ("a", "insert"):
        root = Root.parse([alias])
        assert isinstance(root.sub_command, Add)
        assert root.sub_command.label == "none"


def test_remove_aliases() -> None:
    for alias in ("remove", "rm", "del"):
        root = Root.parse([alias, "gadget"])
        assert isinstance(root.sub_command, Remove)
        assert root.sub_command.name == "gadget"


def test_arbitrary_depth() -> None:
    root = Root.parse(["add", "deep", "widget", "-f", "9"])
    chain = root.command_chain()
    assert [type(c).__name__ for c in chain] == ["Root", "Add", "Deep"]
    assert chain[2].target == "widget"
    assert chain[2].factor == 9


def test_arbitrary_depth_via_aliases() -> None:
    root = Root.parse(["a", "dd", "gizmo", "-f", "3"])
    chain = root.command_chain()
    assert [type(c).__name__ for c in chain] == ["Root", "Add", "Deep"]
    assert chain[2].target == "gizmo"
    assert chain[2].factor == 3


def test_whole_path_dispatch_order() -> None:
    root = Root.parse(["-v", "add", "-l", "x", "deep", "widget", "-f", "2"])
    root.run_path()
    assert RUN_LOG == ["root", "add:x", "deep:widget:2"]


def test_run_path_stops_at_selected_leaf() -> None:
    root = Root.parse(["add"])
    root.run_path()
    assert RUN_LOG == ["root", "add:none"]


def test_parent_args_isolated_from_child_args() -> None:
    # Prefixed dests keep each level's fields separate; Root.verbose must not bleed in.
    root = Root.parse(["-v", "add"])
    assert root.verbose is True
    assert isinstance(root.sub_command, Add)


def test_alias_collision_is_rejected() -> None:
    class A(BaseCmdModel):
        cmd_name: ClassVar = "dup"

    class B(BaseCmdModel):
        cmd_aliases: ClassVar = ("dup",)

    class Parent(BaseCmdModel):
        sub_commands: ClassVar = (A, B)

    with pytest.raises(InvalidCommandError):
        Parent.get_parser()


def test_self_duplicate_alias_is_rejected() -> None:
    class SelfDup(BaseCmdModel):
        cmd_name: ClassVar = "x"
        cmd_aliases: ClassVar = ("x",)

    class Parent(BaseCmdModel):
        sub_commands: ClassVar = (SelfDup,)

    with pytest.raises(InvalidCommandError, match="more than once"):
        Parent.get_parser()


def test_positional_with_subcommands_is_rejected() -> None:
    class Child(BaseCmdModel):
        pass

    class Parent(BaseCmdModel):
        target: str = arg(description="a positional")
        sub_commands: ClassVar = (Child,)

    with pytest.raises(InvalidCommandError, match="positional"):
        Parent.get_parser()


def test_run_and_exit_exits_zero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        Root.run_and_exit(["remove", "widget"])
    assert excinfo.value.code == 0
    assert RUN_LOG == ["root", "remove:widget"]
