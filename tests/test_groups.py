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
"""Tests for argument groups: the ``group=`` title on args/options and nested-model
groups declared with :func:`group`.
"""

# NOTE: no ``from __future__ import annotations`` -- pydantic must resolve the
# annotations of models defined inside test functions (see test_basics.py).

from typing import ClassVar

import pytest

from command_creator import BaseCmdModel, CmdConfig, InvalidCommandError, arg, group, option


def _group_title_of(parser, dest):
    """Return the title of the argparse group holding *dest*, or ``None``."""
    for grp in parser._action_groups:
        for action in grp._group_actions:
            if action.dest == dest:
                return grp.title
    raise AssertionError(f"no action with dest {dest!r}")


def _titles(parser):
    return [grp.title for grp in parser._action_groups]


#####################################################################################
# Mechanism B: group= string title on arg()/option()
#####################################################################################
def test_group_string_places_option_in_named_group() -> None:
    class Cmd(BaseCmdModel):
        host: str = option(default="localhost", group="Network")
        port: int = option(default=8080, group="Network")
        name: str = option(default="app")

    parser = Cmd.get_parser()
    assert "Network" in _titles(parser)
    assert _group_title_of(parser, "host") == "Network"
    assert _group_title_of(parser, "port") == "Network"
    # Ungrouped options stay in the default section.
    assert _group_title_of(parser, "name") != "Network"


def test_group_string_shares_one_group_object() -> None:
    class Cmd(BaseCmdModel):
        a: str = option(default="", group="G")
        b: str = option(default="", group="G")

    parser = Cmd.get_parser()
    # Exactly one group named "G" is created, not one per option.
    assert _titles(parser).count("G") == 1


def test_group_string_is_display_only() -> None:
    class Cmd(BaseCmdModel):
        host: str = option(default="localhost", group="Network")

    # Grouping changes nothing about parsing / field access.
    assert Cmd.parse([]).host == "localhost"
    assert Cmd.parse(["--host", "db"]).host == "db"


def test_group_string_on_positional() -> None:
    class Cmd(BaseCmdModel):
        src: str = arg(description="source", group="Inputs")

    parser = Cmd.get_parser()
    assert _group_title_of(parser, "src") == "Inputs"
    assert Cmd.parse(["in"]).src == "in"


#####################################################################################
# Mechanism A: nested-model groups via group()
#####################################################################################
class ConnOpts(BaseCmdModel):
    """Connection options."""

    model_config = CmdConfig(cmd_name="Connection")
    host: str = option(default="localhost", description="server host")
    port: int = option(default=5432, description="server port")


def test_nested_group_flattens_with_flat_flag_names() -> None:
    class Serve(BaseCmdModel):
        conn: ConnOpts = group()
        debug: bool = option(default=False)

    parser = Serve.get_parser()
    # Flat names -- no field-name prefix.
    assert "--host" in {s for a in parser._actions for s in a.option_strings}
    assert "--port" in {s for a in parser._actions for s in a.option_strings}
    # Both nested fields render under the child's title.
    assert _group_title_of(parser, "host") == "Connection"
    assert _group_title_of(parser, "port") == "Connection"


def test_nested_group_reconstructs_child_instance() -> None:
    class Serve(BaseCmdModel):
        conn: ConnOpts = group()
        debug: bool = option(default=False)

    cmd = Serve.parse(["--host", "db1", "--port", "6000", "--debug"])
    assert isinstance(cmd.conn, ConnOpts)
    assert cmd.conn.host == "db1"
    assert cmd.conn.port == 6000
    assert cmd.debug is True
    # Omitted values fall back to the child's own defaults.
    assert Serve.parse([]).conn.host == "localhost"


def test_nested_group_title_precedence() -> None:
    # 1. Explicit group(title=...) wins.
    class ServeOverride(BaseCmdModel):
        conn: ConnOpts = group(title="Connection Settings")

    assert "Connection Settings" in _titles(ServeOverride.get_parser())

    # 2. Else the child's cmd_name (verbatim).
    class ServeCmdName(BaseCmdModel):
        conn: ConnOpts = group()

    assert "Connection" in _titles(ServeCmdName.get_parser())

    # 3. Else the child class __name__ (as-is).
    class Plain(BaseCmdModel):
        value: str = option(default="x")

    class ServeClassName(BaseCmdModel):
        plain: Plain = group()

    assert "Plain" in _titles(ServeClassName.get_parser())


def test_bare_basemodel_field_is_auto_detected_as_group() -> None:
    # No group() wrapper needed -- a BaseCmdModel-typed field is flattened automatically.
    class Extra(BaseCmdModel):
        flag: bool = option(default=False)

    class Cmd(BaseCmdModel):
        extra: Extra

    parser = Cmd.get_parser()
    assert "Extra" in _titles(parser)
    assert Cmd.parse(["--flag"]).extra.flag is True


def test_required_option_inside_group_is_enforced() -> None:
    class Auth(BaseCmdModel):
        token: str = option()  # required

    class Cmd(BaseCmdModel):
        auth: Auth = group()

    with pytest.raises(SystemExit):
        Cmd.parse([])
    assert Cmd.parse(["--token", "abc"]).auth.token == "abc"


def test_nested_group_within_group() -> None:
    class Inner(BaseCmdModel):
        deep: str = option(default="d")

    class Mid(BaseCmdModel):
        mid_val: str = option(default="m")
        inner: Inner = group()

    class Cmd(BaseCmdModel):
        mid: Mid = group()

    cmd = Cmd.parse(["--mid-val", "MM", "--deep", "DD"])
    assert cmd.mid.mid_val == "MM"
    assert isinstance(cmd.mid.inner, Inner)
    assert cmd.mid.inner.deep == "DD"


def test_group_run_is_not_invoked() -> None:
    log: list[str] = []

    class Cfg(BaseCmdModel):
        value: str = option(default="v")

        def run(self) -> None:  # must never fire -- a group is config, not a verb
            log.append("cfg")

    class Cmd(BaseCmdModel):
        cfg: Cfg = group()

        def run(self) -> None:
            log.append("cmd")

    Cmd.parse([]).run_path()
    assert log == ["cmd"]


#####################################################################################
# Validation
#####################################################################################
def test_flat_namespace_collision_is_rejected() -> None:
    class Grp(BaseCmdModel):
        host: str = option(default="h")

    class Cmd(BaseCmdModel):
        grp: Grp = group()
        host: str = option(default="x")  # clashes with Grp.host

    with pytest.raises(InvalidCommandError, match="duplicate"):
        Cmd.get_parser()


def test_group_child_with_sub_commands_is_rejected() -> None:
    class Leaf(BaseCmdModel):
        pass

    class Grp(BaseCmdModel):
        sub_commands: ClassVar = (Leaf,)
        x: str = option(default="x")

    class Cmd(BaseCmdModel):
        grp: Grp = group()

    with pytest.raises(InvalidCommandError, match="sub_commands"):
        Cmd.get_parser()


def test_positional_group_field_with_sibling_sub_commands_is_rejected() -> None:
    # A group that contributes a positional would swallow the sub-command token.
    class NeedsPos(BaseCmdModel):
        target: str = arg(description="a positional")

    class Child(BaseCmdModel):
        pass

    class Cmd(BaseCmdModel):
        grp: NeedsPos = group()
        sub_commands: ClassVar = (Child,)

    with pytest.raises(InvalidCommandError, match="positional"):
        Cmd.get_parser()


@pytest.mark.filterwarnings("ignore::UserWarning")  # pydantic warns on shadowing a method
def test_reserved_group_field_name_is_rejected() -> None:
    # A group field named `run` would shadow BaseCmdModel.run and break dispatch; the
    # reserved-name guard must fire even though a group field is never emitted directly.
    class Sub(BaseCmdModel):
        x: str = option(default="x")

    class Cmd(BaseCmdModel):
        run: Sub = group()  # type: ignore[assignment]

    with pytest.raises(InvalidCommandError, match="reserved"):
        Cmd.get_parser()


def test_optional_group_field_is_rejected() -> None:
    class Sub(BaseCmdModel):
        x: str = option(default="x")

    class Cmd(BaseCmdModel):
        sub: Sub | None = group()

    with pytest.raises(InvalidCommandError, match="optional"):
        Cmd.get_parser()


def test_group_string_titles_a_nested_group_field() -> None:
    # A group= string on a nested-model field titles the group (below an explicit
    # group(title=...) but above the child's cmd_name).
    class Conn(BaseCmdModel):
        model_config = CmdConfig(cmd_name="Connection")
        host: str = option(default="localhost")

    class Cmd(BaseCmdModel):
        conn: Conn = option(group="MyNet")  # type: ignore[assignment]

    parser = Cmd.get_parser()
    assert "MyNet" in _titles(parser)
    assert "Connection" not in _titles(parser)
    assert _group_title_of(parser, "host") == "MyNet"


def test_duplicate_collision_error_names_declaring_owner() -> None:
    class Endpoint(BaseCmdModel):
        host: str = option(default="h")

    class Cmd(BaseCmdModel):
        src: Endpoint = group(title="Source")
        dst: Endpoint = group(title="Dest")  # same flat 'host' dest -> collision

    with pytest.raises(InvalidCommandError, match=r"Endpoint\.host"):
        Cmd.get_parser()


def test_group_and_string_group_titles_merge() -> None:
    # A nested group and a group= string sharing a title land in one display group.
    class Net(BaseCmdModel):
        model_config = CmdConfig(cmd_name="Network")
        host: str = option(default="h")

    class Cmd(BaseCmdModel):
        net: Net = group()
        retries: int = option(default=3, group="Network")

    parser = Cmd.get_parser()
    assert _titles(parser).count("Network") == 1
    assert _group_title_of(parser, "host") == "Network"
    assert _group_title_of(parser, "retries") == "Network"
