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
"""Tests for the optional shtab-backed completion sub-command and per-arg completers."""

# NOTE: intentionally *no* ``from __future__ import annotations`` -- pydantic must be able
# to resolve the annotations of models defined inside test functions.

import sys

import pytest

from command_creator import BaseCmdModel, CmdConfig, InvalidCommandError, arg, option


def _action(parser, dest):
    for action in parser._actions:
        if action.dest == dest:
            return action
    raise AssertionError(f"no action with dest {dest!r}")


def _subparser_map(parser):
    """Return the {verb: sub-parser} map of a parser's subparsers action (or {})."""
    for action in parser._actions:
        mapping = getattr(action, "_name_parser_map", None)
        if mapping is not None:
            return mapping
    return {}


# --- The completion verb -----------------------------------------------------------
def test_completion_absent_by_default() -> None:
    class Sub(BaseCmdModel):
        model_config = CmdConfig(cmd_name="sub")

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,))

    assert "completion" not in _subparser_map(Root.get_parser())


def test_completion_verb_present_when_opted_in() -> None:
    shtab = pytest.importorskip("shtab")

    class Sub(BaseCmdModel):
        model_config = CmdConfig(cmd_name="sub")

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,), completion=True)

    verbs = _subparser_map(Root.get_parser())
    assert "completion" in verbs
    shell = _action(verbs["completion"], "shell")
    # Guards against a hard-coded shell list drifting from shtab's own.
    assert list(shell.choices) == list(shtab.SUPPORTED_SHELLS)


def test_completion_prints_script_and_exits(capsys) -> None:
    shtab = pytest.importorskip("shtab")

    class Root(BaseCmdModel):
        model_config = CmdConfig(completion=True)
        opt: str = option(default="")

    with pytest.raises(SystemExit) as excinfo:
        Root.run_and_exit(["completion", "bash"])
    assert excinfo.value.code == 0

    out = capsys.readouterr().out
    expected = shtab.complete(Root.get_parser(prog="root"), "bash")
    assert out.startswith(expected.rstrip("\n"))
    assert out.endswith("\n") and not out.endswith("\n\n")


def test_completion_stdout_purity(capsys) -> None:
    # The load-bearing guarantee: the root command's run() must NOT run (its output would
    # corrupt the script piped into `eval "$(tool completion bash)"`).
    pytest.importorskip("shtab")

    class Root(BaseCmdModel):
        model_config = CmdConfig(completion=True)
        opt: str = option(default="")

        def run(self) -> None:
            print("POLLUTION_SENTINEL")

    with pytest.raises(SystemExit):
        Root.run_and_exit(["completion", "zsh"])

    out = capsys.readouterr().out
    assert "POLLUTION_SENTINEL" not in out  # run() must not fire
    assert out.strip()  # ...but the script itself must still be written


def test_completion_on_flat_tool() -> None:
    # A command with only options (no sub_commands) still grows the completion verb.
    pytest.importorskip("shtab")

    class Root(BaseCmdModel):
        model_config = CmdConfig(completion=True)
        opt: str = option(default="")

    verbs = _subparser_map(Root.get_parser())
    assert set(verbs) == {"completion"}
    # The normal (no-verb) invocation still parses.
    assert Root.parse(["--opt", "x"]).opt == "x"


def test_completion_custom_name() -> None:
    pytest.importorskip("shtab")

    class Root(BaseCmdModel):
        model_config = CmdConfig(completion=True, completion_name="complete")
        opt: str = option(default="")

    verbs = _subparser_map(Root.get_parser())
    assert "complete" in verbs and "completion" not in verbs


@pytest.mark.parametrize("shell", ["bash", "zsh", "tcsh", "fish", "powershell"])
def test_completion_generates_for_undocumented_subcommands(capsys, shell) -> None:
    # Regression: shtab's zsh/fish generators dereference a sub-parser's help/description;
    # an undocumented sub-command would crash `completion <shell>` without a fallback.
    pytest.importorskip("shtab")

    class Leaf(BaseCmdModel):  # deliberately NO docstring
        model_config = CmdConfig(cmd_name="leaf")
        val: str = arg(description="v")

    class Mid(BaseCmdModel):  # deliberately NO docstring, and has a child
        model_config = CmdConfig(cmd_name="mid", sub_commands=(Leaf,))

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Mid,), completion=True)

    with pytest.raises(SystemExit) as excinfo:
        Root.run_and_exit(["completion", shell])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip()  # a real script, not a crash


def test_completion_verb_not_in_get_sub_commands() -> None:
    pytest.importorskip("shtab")

    class Sub(BaseCmdModel):
        model_config = CmdConfig(cmd_name="sub")

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Sub,), completion=True)

    # The verb is a parser-level token only; introspection is unaffected.
    assert Root.get_sub_commands() == (Sub,)


# --- Error cases -------------------------------------------------------------------
def test_completion_positional_conflict_is_rejected() -> None:
    pytest.importorskip("shtab")

    class Root(BaseCmdModel):
        model_config = CmdConfig(completion=True)
        target: str = arg(description="a positional")

    with pytest.raises(InvalidCommandError, match="positional"):
        Root.get_parser()


def test_completion_name_collision_is_rejected() -> None:
    pytest.importorskip("shtab")

    class Completion(BaseCmdModel):
        model_config = CmdConfig(cmd_name="completion")

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Completion,), completion=True)

    with pytest.raises(InvalidCommandError, match="clashes"):
        Root.get_parser()


def test_completion_missing_shtab_is_rejected(monkeypatch) -> None:
    # Simulate shtab being absent: a sentinel of None makes `import shtab` raise ImportError.
    monkeypatch.setitem(sys.modules, "shtab", None)

    class Root(BaseCmdModel):
        model_config = CmdConfig(completion=True)
        opt: str = option(default="")

    with pytest.raises(InvalidCommandError, match="shtab"):
        Root.get_parser()


def test_completion_enabled_ignored_on_nested_command() -> None:
    # completion=True only matters at the root (depth 0); a nested command ignores it.
    pytest.importorskip("shtab")

    class Child(BaseCmdModel):
        model_config = CmdConfig(cmd_name="child", completion=True)
        opt: str = option(default="")

    class Root(BaseCmdModel):
        model_config = CmdConfig(sub_commands=(Child,))

    verbs = _subparser_map(Root.get_parser())
    assert "child" in verbs
    assert "completion" not in _subparser_map(verbs["child"])


# --- Per-argument completers -------------------------------------------------------
def test_completer_dict_sets_action_complete() -> None:
    pytest.importorskip("shtab")
    custom = {"bash": "_my_fn", "zsh": "_my_fn"}

    class Cmd(BaseCmdModel):
        host: str = option(default="", completer=custom)

    assert _action(Cmd.get_parser(), "host").complete == custom


def test_completer_file_shorthand_resolves_to_preset() -> None:
    shtab = pytest.importorskip("shtab")

    class Cmd(BaseCmdModel):
        path: str = option(default="", completer="file")
        out: str = option(default="", completer="dir")

    parser = Cmd.get_parser()
    assert _action(parser, "path").complete == shtab.FILE
    assert _action(parser, "out").complete == shtab.DIRECTORY


def test_completer_on_positional() -> None:
    shtab = pytest.importorskip("shtab")

    class Cmd(BaseCmdModel):
        path: str = arg(description="file", completer="file")

    assert _action(Cmd.get_parser(), "path").complete == shtab.FILE


def test_unknown_completer_shorthand_is_rejected() -> None:
    pytest.importorskip("shtab")

    class Cmd(BaseCmdModel):
        path: str = option(default="", completer="nope")

    with pytest.raises(InvalidCommandError, match="unknown completer shorthand"):
        Cmd.get_parser()


def test_completer_inert_without_shtab(monkeypatch) -> None:
    # Without shtab a completer is simply not applied -- no error, parsing unaffected.
    monkeypatch.setitem(sys.modules, "shtab", None)

    class Cmd(BaseCmdModel):
        path: str = option(default="x", completer="file")

    action = _action(Cmd.get_parser(), "path")
    assert not hasattr(action, "complete")
    assert Cmd.parse(["--path", "y"]).path == "y"


def test_unknown_completer_shorthand_rejected_without_shtab(monkeypatch) -> None:
    # A shorthand typo fails loudly even when shtab is absent (validation is env-independent).
    monkeypatch.setitem(sys.modules, "shtab", None)

    class Cmd(BaseCmdModel):
        path: str = option(default="", completer="nope")

    with pytest.raises(InvalidCommandError, match="unknown completer shorthand"):
        Cmd.get_parser()


def test_completer_on_flag_is_rejected() -> None:
    # A completer on a valueless flag/count can never fire -> fail loud, like other misuse.
    class BoolCmd(BaseCmdModel):
        flag: bool = option(default=False, completer="file")

    with pytest.raises(InvalidCommandError, match="takes no value"):
        BoolCmd.get_parser()

    class CountCmd(BaseCmdModel):
        verbose: int = option(default=0, count=True, completer="dir")

    with pytest.raises(InvalidCommandError, match="takes no value"):
        CountCmd.get_parser()
