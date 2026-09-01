# Command Creator

[![Tests Status](https://github.com/allRisc/command_creator/actions/workflows/test.yml/badge.svg)](https://github.com/allRisc/command_creator/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/command_creator.svg)](https://badge.fury.io/py/command_creator)
[![Documentation Status](https://readthedocs.org/projects/command-creator/badge/?version=latest)](https://command-creator.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/pypi/l/command_creator.svg)](https://pypi.org/project/command_creator/)
[![Python Version](https://img.shields.io/pypi/pyversions/command_creator.svg)](https://pypi.org/project/command_creator/)

Command Creator is a Python package that simplifies the creation of command-line interfaces (CLIs) using Python's `dataclasses`.
It allows you to define commands as dataclass objects, making it easy to create, manage, and execute commands with various options and arguments.
This package is particularly useful for developers who want to quickly set up CLIs without having to write extensive boilerplate code.

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Simple Usage](#simple-usage)
- [CLI Argument Features](#cli-argument-features)
  - [Positional Arguments and Options](#positional-arguments-and-options)
  - [help](#help)
  - [abrv](#abrv)
  - [choices](#choices)
  - [metavar](#metavar)
  - [optional](#optional)
  - [positional](#positional)
  - [default and default\_factory](#default-and-default_factory)
  - [count](#count)
  - [completer](#completer)
- [Argument Groups](#argument-groups)
- [Sub-commands](#sub-commands)
- [Using with Sphinx-Autoprogram](#using-with-sphinx-autoprogram)
- [Shell Completion](#shell-completion)

## Simple Usage

The `command_creator` package can be used to automatically create CLIs from dataclass objects.
This is done using the `@dataclass` decorator, `command_creator.arg` method, and the `command_creator.Command` class.

```python
    from dataclasses import dataclass
    from command_creator import arg, Command


    # A command is a class which extends command_creator.Command and is a dataclass
    @dataclass
    class SimpleCommand(Command):
        """This doc-string is used as the command description in the help message"""

        positional: str = arg(
            help="This is a positional argument, since it has no default"
        )
        extra_positional: str = arg(
            default="Not-Given",
            positional=True,
            help="This is an extra positional argument, since it has 'positional=True'"
        )
        option: bool = arg(
            default=False,
            help="This is the --option argument which when given sets self.option to true"
        )
        output_file: str | None = arg(
            default=None,
            help="This is the '--output-file OUTPUT_FILE' argument"
        )
        args: list[str] | None = arg(
            default=None,
            help="This is the '--args ARGS [ARGS ...]' argument"
        )

        # The __post_init__ method is called after creation of the object, but before running the command
        #   It is optional
        def __post_init__(self) -> None:
            pass

        # The __call__ method is required. This is the entry point for the command
        def __call__(self) -> int:
            print("Doing something")
            return 0


    # The execute class method can be used to parse command-line arguments and run the command
    if __name__ == "__main__":
        SimpleCommand.execute()
```

## CLI Argument Features

Each dataclass field represents a command-line argument.
In order to add functionality, these *must* use `command_creator.arg` to instantiate rather than `dataclasses.field`.
This section outlines how this method can be used to create a wide-range of arguments.

### Positional Arguments and Options

In unix-style CLI there are two main ways data can be passed to the underlying command: as a positional argument or as an option.
Positional arguments are interpreted based soley on their position.
However, options use `-` characters and a name to denote their intended use.
For example `--debug` is an option which might tell the underlying command to run in debug mode regardless of where it provided.

Command Creator uses 3-indicators to determine whether an arugment should be interpreted as a Positional Arugment or an Option:

1. `positional`

    - Arguments which have `positional=True` are always treats as Positional Arguments
    - See positional_ for more details

2. `default` and `default_factory`

    - Arguments with a default are treated as options *unless* they are explicitly positional.
    - See `default and default_factory`_ for more details

3. `count`

    - Arguments which have `count=True` are treated as Options even if they don't have a default, because there is no command-line concept of counting positional arguments.
    - `count=True` is mutually exclusive with `positional`
    - See count_ for more details

### help

The `help` argument takes a string which is used for the help message of the command

### abrv

The `abrv` argument takes a string which is used as the `-[abrv]` abreviated option.

### choices

The `choices` argument takes a list or enum type which sets the valid inputs to the option/positional argument.
If the provided argument is a subclass of the paython standard `Enum` then the options are the uppercase names of the enumerated values.

### metavar

The `metavar` argument takes a string which is used as the `METAVAR` in the help string.

### optional

The `optional` argument takes a boolean and determines the following based on the argument:

- If the argument is *positional*

  - Then the positional argument can be excluded in the command line
  - If the argument is excluded and a default is given then the field gets set to the default
  - If the argument is excluded and no default is given then the field gets set to `None`

- If the argument is an *option*

  - Then the optional option can be provided without an argument after it
  - If the option is excluded from the command-line then the field gets set to the default
  - If the option is provided w/o an argument then the field gets set to `None`
  - If the option is provided w/ an argument then the field gets set to the provided argument

### positional

The `positional` argument takes a boolean.
When true it forces the argument to be positional rather than an option.

### default and default_factory

Provides defaults to the underlying argument if it is not specified on the command-line.
`default_factory` is a callable that can be used to create new objects at run-time.
See the Python `dataclasses` module documentation for more details.

### count

A boolean which indicates that the argument is a counting option.
This means that the argument can be provided multiple times and the value of the field will be the number of times the argument was provided.
For example, if the argument is `--verbose` and it is provided 3 times, then the field will be set to `3`.
This is useful for options that can be repeated to increase their effect, such as `--verbose` or `--debug`.
It is mutually exclusive with `positional`, meaning that an argument cannot be both positional and a counting option.

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

```python
    @dataclass
    class ReusableSubCommand(Command):
        opt1: str = arg()

        def __call__(self) -> int:
            print("A sub-command which can be used across a variety of contexts")
            return 0

    @dataclass
    class ParentCommand(Command):

        @dataclass
        class SpecificSubCommand(Command):
            opt2: str = arg()

            def __call__(self) -> int:
                print("A sub-command for use only in this parent command")
                return 0

        sub_commands = {
            "specific": SpecificSubCommand,
            "reusable": ReusableSubCommand,
        }

        def __call__(self) -> int:
            if self.sub_command is not None:
                self.sub_command()
```

## Using with Sphinx-Autoprogram

```rst
    .. autoprogram:: pkg_name.module:CommandClass.create_parser(True)
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
