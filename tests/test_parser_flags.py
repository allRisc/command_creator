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
"""Tests for the argparse ``suggest_on_error`` / ``color`` pass-through flags."""

from command_creator import BaseCmdModel, CmdConfig, option


class _Sub(BaseCmdModel):
    model_config = CmdConfig(cmd_name="sub")
    x: int = option(default=0)


class _Root(BaseCmdModel):
    model_config = CmdConfig(sub_commands=(_Sub,))
    v: int = option(default=0, count=True, abrv="v")


def _subparser(parser):
    for action in parser._actions:
        mapping = getattr(action, "_name_parser_map", None)
        if mapping is not None:
            return mapping["sub"]
    raise AssertionError("no sub-parser found")


def test_defaults_match_argparse() -> None:
    parser = _Root.get_parser()
    assert parser.suggest_on_error is False
    assert parser.color is True


def test_flags_forwarded_to_root() -> None:
    parser = _Root.get_parser(suggest_on_error=True, color=False)
    assert parser.suggest_on_error is True
    assert parser.color is False


def test_flags_propagate_to_subparsers() -> None:
    parser = _Root.get_parser(suggest_on_error=True, color=False)
    sub = _subparser(parser)
    assert sub.suggest_on_error is True
    assert sub.color is False


def test_parse_still_works_with_flags() -> None:
    root = _Root.parse(["sub", "--x", "5"], suggest_on_error=True, color=False)
    assert isinstance(root.sub_command, _Sub)
    assert root.sub_command.x == 5
