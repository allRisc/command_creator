# Command Creator

[![Tests Status](https://github.com/allRisc/command_creator/actions/workflows/test.yml/badge.svg)](https://github.com/allRisc/command_creator/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/command_creator.svg)](https://badge.fury.io/py/command_creator)
[![Documentation Status](https://readthedocs.org/projects/command-creator/badge/?version=latest)](https://command-creator.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/pypi/l/command_creator.svg)](https://pypi.org/project/command_creator/)
[![Python Version](https://img.shields.io/pypi/pyversions/command_creator.svg)](https://pypi.org/project/command_creator/)

Command Creator is a Python package that simplifies the creation of command-line interfaces (CLIs) from [pydantic](https://docs.pydantic.dev/) models.
You define a command by subclassing `BaseCmdModel`, declaring each argument as a model field, and implementing `run()`.
Field type annotations drive argument parsing, validation and coercion, so you get a fully-featured CLI without writing argparse boilerplate.

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Installation](#installation)
- [Simple Usage](#simple-usage)
- [CLI Argument Features](#cli-argument-features)
  - [Positional Arguments and Options](#positional-arguments-and-options)
  - [description](#description)
  - [abrv](#abrv)
  - [choices](#choices)
  - [metavar](#metavar)
  - [optional](#optional)
  - [default and default\_factory](#default-and-default_factory)
  - [count](#count)
  - [Lists and tuples](#lists-and-tuples)
  - [completer](#completer)
- [Argument Groups](#argument-groups)
- [Sub-commands](#sub-commands)
- [Using with Sphinx-Autoprogram](#using-with-sphinx-autoprogram)
- [Shell Completion](#shell-completion)

## Installation

```bash
pip install command_creator
```

Command Creator requires Python 3.14+ and pydantic 2.13+.  Shell completion is available
through an optional extra (see [Shell Completion](#shell-completion)):

```bash
pip install command_creator[shtab]
```

## Simple Usage

A command is a subclass of `command_creator.BaseCmdModel` (itself a `pydantic.BaseModel`).
Declare each argument as a field using `arg()` for a positional argument or `option()` for
an option (`--name`), implement `run()`, and call `run_and_exit()` as the entry point.

```python
    from command_creator import BaseCmdModel, arg, option


    class SimpleCommand(BaseCmdModel):
        """This doc-string is used as the command description in the help message."""

        # arg() -> a positional argument. With no default it is required.
        positional: str = arg(description="a required positional argument")
        # A positional with a default becomes optional on the command line.
        extra_positional: str = arg(default="Not-Given", description="an optional positional")
        # option() -> an option (--flag). A bool field is always a flag.
        flag: bool = option(default=False, description="sets self.flag to True when given")
        # `--output-file OUTPUT_FILE`; None until provided.
        output_file: str | None = option(default=None, description="where to write output")
        # `--args ARGS [ARGS ...]`; a list field accepts multiple values.
        args: list[str] | None = option(default=None, description="extra arguments")

        # run() holds the command's logic. Override it in every command.
        def run(self) -> None:
            print("Doing something")


    # run_and_exit() parses sys.argv, runs the command, and exits.
    if __name__ == "__main__":
        SimpleCommand.run_and_exit()
```

`arg()` and `option()` are thin wrappers over `pydantic.Field`: any `Field` keyword
(`default`, `default_factory`, `description`, and validation constraints such as `ge` or
`max_length`) is forwarded unchanged and fully type-checked.  If you build a `Field`
yourself, `arg_meta()` produces the equivalent CLI metadata for its `json_schema_extra`.

To parse without running, use `SimpleCommand.parse(argv)` (returns a populated instance) or
`SimpleCommand.get_parser()` (returns the underlying `argparse.ArgumentParser`).

## CLI Argument Features

Each model field represents a command-line argument.
To add CLI behaviour, declare the field with `command_creator.arg` (positional) or
`command_creator.option` (option) rather than a bare `pydantic.Field`.
This section outlines the keywords those helpers accept.

### Positional Arguments and Options

In unix-style CLIs there are two main ways data can be passed to a command: as a positional
argument or as an option.
Positional arguments are interpreted based solely on their position.
Options use `-`/`--` characters and a name, so `--debug` tells the command to run in debug
mode regardless of where it is provided.

The distinction is explicit in Command Creator:

- `arg()` declares a **positional** argument.
- `option()` declares an **option** (`--name`).

Two field kinds are always options regardless of which helper is used, because there is no
command-line concept for them as positionals:

- `bool` fields, which become flags (`--flag` / `store_true`, or `store_false` when the
  default is `True`).  A boolean must have a default.
- `count=True` options (see [count](#count)), which are mutually exclusive with a positional.

A positional argument with a default (or `optional=True`) may be omitted on the command line;
a required option (an `option()` with no default) must be provided.

### description

`arg()` / `option()` forward `description=` to `pydantic.Field`; it is used as the
argument's help text in `--help`.

### abrv

The `abrv` keyword (options only) takes a single character used as the short `-[abrv]` form
alongside the long `--name` option, e.g. `option(abrv="v")` exposes `-v`.  A numeric
abbreviation is rejected because it would disable negative-number parsing.

### choices

Choices are derived from the field's **type annotation** - there is no `choices` keyword.
Annotate the field as an `enum.Enum` subclass or a `typing.Literal[...]` and its members
become the argument's valid values automatically:

```python
from enum import StrEnum
from typing import Literal
from command_creator import BaseCmdModel, option


class Casing(StrEnum):
    plain = "plain"
    caps = "caps"


class Cmd(BaseCmdModel):
    casing: Casing = option(default=Casing.plain)          # --casing {plain,caps}
    level: Literal["low", "high"] = option(default="low")  # --level {low,high}

    def run(self) -> None: ...
```

### metavar

The `metavar` keyword takes a string used as the value placeholder shown in `--help`.

### optional

The `optional` keyword takes a boolean:

- On a **positional** argument it makes the value omittable (argparse `nargs="?"`); when
  omitted the field takes its default.
- On an **option** it allows `--opt` to be given with no following value, in which case the
  field is set to `None`.  The field must be declared as `T | None` for this to be valid.

### default and default_factory

`default` and `default_factory` are forwarded to `pydantic.Field`.
A field with no default is required; giving it a default makes it optional.
`default_factory` is a callable that builds a fresh default at run time (use it for mutable
defaults such as lists).
See the pydantic documentation for details.

### count

`count=True` (options only) makes a repeat-counter: the option may be provided multiple
times and the field is set to the number of occurrences.
For example a `--verbose`/`-v` option provided three times sets the field to `3`.
It requires an `int` field and is mutually exclusive with a positional argument.

```python
verbose: int = option(default=0, count=True, abrv="v", description="increase verbosity")
```

### Lists and tuples

A field annotated as `list[T]` (or `set[T]` / `frozenset[T]`, or a variadic
`tuple[T, ...]`) accepts multiple values on the command line.
A required list requires at least one value (`nargs="+"`); a list with a default accepts
zero or more (`nargs="*"`).
A fixed-length `tuple[A, B, ...]` requires exactly that many values.

### completer

The `completer` argument attaches a shell-completion hint to an argument's value, consumed
by [`shtab`](https://github.com/iterative/shtab) when it generates a completion script (see
[Shell Completion](#shell-completion)). It accepts:

- an `shtab` preset - `shtab.FILE` or `shtab.DIRECTORY`;
- the string shorthands `"file"`, `"dir"` / `"directory"` (resolved to those presets);
- a `{shell: snippet}` mapping for a custom completer per shell.

```python
import shtab
from command_creator import BaseCmdModel, arg, option


class Convert(BaseCmdModel):
    """Convert a file."""

    src: str = arg(description="input file", completer="file")           # shorthand
    out_dir: str = option(default=".", completer=shtab.DIRECTORY)         # shtab preset
    fmt: str = option(                                                    # custom snippet
        default="png", completer={"bash": "compgen -W 'png jpg webp'", "zsh": "(png jpg webp)"}
    )

    def run(self) -> None: ...
```

`completer` requires the optional `shtab` dependency; without it the hint is stored but
never applied (it only matters at script-generation time, which itself needs `shtab`).

## Argument Groups

Arguments can be organised into titled groups in the `--help` output.
There are two ways to do this.

**1. The `group` keyword on `arg()` / `option()`**

Pass `group="Title"` and the argument is listed under that heading.
Same-level arguments sharing a title are displayed together.
Grouping is display-only: it does not change parsing, dests or the field name.

```python
from command_creator import BaseCmdModel, option


class Serve(BaseCmdModel):
    """Run the server."""

    host: str = option(default="localhost", group="Network")
    port: int = option(default=8080, group="Network")
    debug: bool = option(default=False)  # ungrouped

    def run(self) -> None: ...
```

**2. A nested command as a field**

A field whose type is itself a `BaseCmdModel` subclass is *flattened*: the child model's
fields become command-line arguments on the parent, listed together under one group.
The child does not become a sub-command and its `run()` is never called - the parsed child
instance is simply stored on the field, giving you structured access
(`self.connection.host`).

Because the group's arguments share the parent's flat namespace, every flattened field
name must be unique across the command (a clash raises `InvalidCommandError`).

```python
from command_creator import BaseCmdModel, group, option


class Connection(BaseCmdModel):
    """Connection settings."""

    host: str = option(default="localhost", description="server host")
    port: int = option(default=5432, description="server port")


class Serve(BaseCmdModel):
    """Run the server."""

    # A BaseCmdModel-typed field is auto-detected as a group; use group() to
    # override the title or forward pydantic Field arguments.
    connection: Connection = group(title="Connection Settings")
    debug: bool = option(default=False)

    def run(self) -> None:
        print(f"serving on {self.connection.host}:{self.connection.port}")
```

The group title defaults to the child's `cmd_name` (if set), then the child class name;
`group(title=...)` overrides it. Groups nest to any depth.

## Sub-commands

A command becomes a parent of others by listing child command classes in the
`sub_commands` key of its `model_config` (a `CmdConfig`).  Each child is itself a
`BaseCmdModel`, so sub-commands nest to any depth.  Give a command a custom name or
alternate names with `cmd_name` / `cmd_aliases`.

When a sub-command is selected, `run_and_exit()` runs `run()` for **every** command along
the invoked path, from root to leaf (whole-path dispatch).  A parent that declares
`sub_commands` cannot also have positional arguments, since a positional would consume the
sub-command token - expose those as options instead.

```python
from command_creator import BaseCmdModel, CmdConfig, arg, option


class Add(BaseCmdModel):
    """Add a remote."""

    # cmd_name overrides the default (lower-cased class name).
    model_config = CmdConfig(cmd_name="add", cmd_aliases=("a",))

    url: str = arg(description="remote URL")
    name: str = option(default="origin", description="local name for the remote")

    def run(self) -> None:
        print(f"Added remote {self.name!r} -> {self.url}")


class Remote(BaseCmdModel):
    """Manage remotes."""

    model_config = CmdConfig(sub_commands=(Add,))

    def run(self) -> None:
        # Runs before the selected child; nothing to do here.
        pass


class Tool(BaseCmdModel):
    """Top-level tool: `tool remote add <url> --name origin`."""

    model_config = CmdConfig(sub_commands=(Remote,))
    verbose: int = option(default=0, count=True, abrv="v", description="increase verbosity")

    def run(self) -> None: ...


if __name__ == "__main__":
    Tool.run_and_exit()
```

Sub-commands can also be registered imperatively with `add_sub_command`, either as a class
decorator or by passing the class directly - handy for reusing a command across several
parents:

```python
@Remote.add_sub_command
class Remove(BaseCmdModel):
    """Remove a remote."""

    name: str = arg(description="remote to remove")

    def run(self) -> None:
        print(f"Removed {self.name!r}")


Tool.add_sub_command(Remote)  # equivalent to listing it in sub_commands
```

The selected child is reachable at `self.sub_command`, and `self.command_chain()` returns
the full invoked path from this command down to the selected leaf.

## Using with Sphinx-Autoprogram

`get_parser()` returns the underlying `argparse.ArgumentParser`, so the tool documents
cleanly with [`sphinxcontrib-autoprogram`](https://sphinxcontrib-autoprogram.readthedocs.io/):

```rst
    .. autoprogram:: pkg_name.module:CommandClass.get_parser()
```

## Shell Completion

Command Creator can generate completion scripts for `bash`, `zsh`, `tcsh`, `fish` and
`powershell` via the optional [`shtab`](https://github.com/iterative/shtab) dependency:

```bash
pip install command_creator[shtab]
```

Set `completion=True` in your **root** command's `model_config` (see `CmdConfig`) and the
tool automatically grows a `completion <shell>` sub-command:

```python
from command_creator import BaseCmdModel, CmdConfig, arg, option


class Greet(BaseCmdModel):
    """Greet someone."""

    name: str = arg(description="who to greet")

    def run(self) -> None:
        print(f"Hello, {self.name}!")


class Tool(BaseCmdModel):
    """Example tool."""

    # completion=True -> a `completion <shell>` verb; completion_name renames it.
    model_config = CmdConfig(sub_commands=(Greet,), completion=True)

    def run(self) -> None: ...


if __name__ == "__main__":
    Tool.run_and_exit()
```

Users then source the script for their shell (once, or from their shell rc file):

```bash
eval "$(mytool completion bash)"        # bash
eval "$(mytool completion zsh)"         # zsh
mytool completion fish | source         # fish
```

Notes:

- The script is emitted at parse time, so a command's `run()` output can never pollute it.
- Rename the verb with `CmdConfig(completion=True, completion_name="complete")`.
- Enabling `completion=True` without `shtab` installed raises `InvalidCommandError`.
- Per-argument completers (file paths, directories, custom snippets) are configured with
  the [`completer`](#completer) keyword on `arg()` / `option()`.
