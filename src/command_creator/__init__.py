#####################################################################################
# A package to simplify the creation of Python Command-Line tools
# Copyright (C) 2023  Benjamin Davis
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

from __future__ import annotations
from typing import (
    Any, Callable, Mapping, TypeVar, Type, ClassVar, NoReturn, TypedDict,
    List, Dict, Union
)
import types

import warnings

import sys
from dataclasses import Field, dataclass, MISSING, fields
from enum import Enum
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace, Action

try:
    argcomplete: types.ModuleType | None
    import argcomplete
except ImportError:
    argcomplete = None

__all__ = [
    "InvalidArgumentError",
    "Command",
    "arg",
    "CompleterList",
    "CompleterDict",
    "CompleterIter",
    "CompleterFunc",
    "Completer",
]


#####################################################################################
# Error Information
#####################################################################################
class InvalidArgumentError(Exception):
    """Error raised when an invalid argument is passed to a command
    """
    pass


#####################################################################################
# General Type-Hinting
#####################################################################################
class CompleterArgs(TypedDict):
    prefix: str
    action: Action
    parser: ArgumentParser
    parsed_args: Namespace


CompleterList = List[str]
CompleterDict = Dict[str, str]
CompleterIter = Union[CompleterList, CompleterDict]
if sys.version_info < (3, 11):
    CompleterFunc = Callable[..., CompleterIter]
else:
    from typing import Unpack
    CompleterFunc = Callable[[Unpack[CompleterArgs]], CompleterIter]

Completer = Union[CompleterFunc, CompleterDict, CompleterList]


#####################################################################################
# Command Argument
#####################################################################################
class CmdArgument(Field):
    """Class which represents a command-line argument
    """
    __slots__ = ("help", "abrv", "choices", "positional", "count", "completer", "metavar")

    def __init__(
                self,
                help: str = "",
                abrv: str | None = None,
                choices: list[Any] | type[Enum] | None = None,
                metavar: str | None = None,
                positional: bool = False,
                default: Any = MISSING,
                default_factory: Callable[[], Any] = lambda: MISSING,
                init: bool = True,
                repr: bool = True,
                hash: bool | None = None,
                compare: bool = True,
                count: bool = False,
                completer: Completer | None = None,
                metadata: Mapping[Any, Any] = dict(),
                **kwargs: Any
            ) -> None:
        if (sys.version_info >= (3, 10)):
            if "kw_only" not in kwargs:
                kwargs["kw_only"] = False

        super().__init__(default, default_factory, init, repr, hash, compare, metadata, **kwargs)

        if default_factory() is MISSING:
            self.default_factory = MISSING

        self.help = help
        """The help string used for the argument"""
        self.abrv = abrv
        self.choices = choices
        self.metavar = metavar
        self.positional = positional
        self.count = count
        self.completer = completer


def arg(
            help: str = "",
            abrv: str | None = None,
            choices: list[str] | type[Enum] | None = None,
            metavar: str | None = None,
            positional: bool = False,
            default: Any = MISSING,
            default_factory: Callable[[], Any] = lambda: MISSING,
            init: bool = True,
            repr: bool = True,
            hash: bool | None = None,
            count: bool = False,
            compare: bool = True,
            completer: Completer | None = None,
            metadata: Mapping[Any, Any] = dict(),
            **kwargs: Any
        ) -> Any:
    """Create a command-line argument

    Args:
            help (str, optional): Help message for the argument. Defaults to empty string.
            abrv (str | None, optional): Abbreviation for the argument. Defaults to None.
            choices (list[str] | Enum | None, optional): List of choices for the argument.
                Defaults to None.
            metavar (str | None) : The metavar to use when displaying argument help info.
                Defaults to None.
            positional (bool, optional): Whether the argument is positional. Defaults to False.
            default (Any, optional): Default value for the argument. Defaults to MISSING.
            default_factory (Callable[[], Any], optional): Default factory for the argument.
                Defaults to lambda: MISSING.
            init (bool, optional): Whether the argument is included in the __init__ method.
                Defaults to True.
            repr (bool, optional): Whether the argument is included in the __repr__ method.
                Defaults to True.
            hash (bool | None, optional): Whether the argument is included in the __hash__ method.
                Defaults to None.
            count (bool, optional): Whether the argument should be a count of the times it appears
                Defaults to False.
            compare (bool, optional): Whether the argument is included in the __eq__ method.
                Defaults to True.
            completer (Completer | None): A completer which can be used for argcomplete.
                Defaults to None.
            metadata (Mapping[Any, Any], optional): Metadata for the argument. Defaults to dict().
            **kwargs (Any): Additional keyword arguments for the argument.

    Returns:
            Any: The command-line argument
    """
    if sys.version_info >= (3, 10):
        if "kw_only" not in kwargs:
            kwargs["kw_only"] = False

    if 'optional' in kwargs:
        warnings.warn(
            "Using deprecated argument 'optional' in command_creator.arg",
            category=DeprecationWarning,
            stacklevel=3
        )
        positional = positional or bool(kwargs.pop('optional'))

    return CmdArgument(
        help=help,
        abrv=abrv,
        choices=choices,
        metavar=metavar,
        positional=positional,
        default=default,
        default_factory=default_factory,
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
        count=count,
        completer=completer,
        metadata=metadata,
        **kwargs
    )


#####################################################################################
# Command Class
#####################################################################################
@dataclass
class Command(ABC):
    """Class which represents a command-line command
    """

    sub_commands: ClassVar[dict[str, Type[Command]]] = dict()
    """A dictionary mapping the sub-command name to the respective sub-command"""
    sub_command: Command | None
    """The sub-command found during argument parsing. None if one not found"""

    def __post_init__(self) -> None:
        """This method may be implemented by subclasses in order to setup variables or
        post-process any user inputs
        """
        pass

    @abstractmethod
    def __call__(self) -> int:
        """This method must be implemented by subclasses, it is the method which is called
        to execute the command
        """
        pass

    @classmethod
    def create_parser(cls: Type[CommandT], doc_mode: bool = False) -> ArgumentParser:
        """Create the argument parser for the Command using argparser library

        Args:
            doc_mode (bool, optional): Whether to force meta-data use for prettier documentation.
                Defaults to False.

        Returns:
            ArgumentParser: The argument-parser derived from the class definition
        """
        parser = ArgumentParser(
            prog=cls.__name__.lower(),
            description=cls.__doc__,
        )
        cls._add_args(parser, doc_mode)
        cls._add_sub_commands(parser, doc_mode)
        return parser

    @classmethod
    def _add_args(cls, parser: ArgumentParser, doc_mode: bool = False) -> None:
        """Add arguments to the parser

        Args:
            parser (ArgumentParser): The parser to add arguments to
            doc_mode (bool): Force the args to use metavars instead of options
        """
        for fld in fields(cls):
            if "ClassVar" in str(fld.type):
                continue
            if fld.name == "sub_command":
                continue
            if not isinstance(fld, CmdArgument):
                raise InvalidArgumentError(
                    f"Field {fld.name} is not a CmdArgument" +
                    " Did you use field() instead of arg()?"
                )

            kwargs: dict[str, Any] = dict()

            if fld.count and fld.type != 'int':
                raise ValueError(f"Field ({fld.name}) with count=True has type {fld.type}!=int")

            if argcomplete is None and fld.completer is not None:
                raise ValueError("Completer provided without argcomplete package installed...")

            if 'list' in fld.type:
                kwargs['nargs'] = '+'
            elif 'bool' in fld.type:
                if fld.default is MISSING or fld.default is False:
                    kwargs['action'] = 'store_true'
                    kwargs['default'] = False
                else:
                    kwargs['action'] = 'store_false'
                    kwargs['default'] = True
            elif 'str' in fld.type:
                kwargs['type'] = str
            elif 'int' in fld.type:
                kwargs['type'] = int
            elif 'float' in fld.type:
                kwargs['type'] = float

            if fld.count:
                if 'type' in kwargs:
                    kwargs.pop('type')
                kwargs['action'] = 'count'

            if fld.positional:
                if 'nargs' not in kwargs:
                    kwargs['nargs'] = '?'
                else:
                    kwargs['nargs'] = '*'

            if fld.choices is not None:
                if isinstance(fld.choices, list):
                    kwargs['choices'] = fld.choices
                elif issubclass(fld.choices, Enum):
                    kwargs['choices'] = [
                        str(e).replace(fld.choices.__name__ + ".", "") for e in fld.choices
                    ]
                else:
                    raise ValueError(
                        f"Field {fld.name} has an invalid type for choices" +
                        " Did you use an Enum or a list?"
                    )
            elif isinstance(fld.completer, list):
                kwargs['choices'] = fld.completer
                kwargs['metavar'] = fld.name.upper()
            elif fld.completer is not None:
                kwargs['metavar'] = fld.name.upper()

            if fld.metavar is not None:
                kwargs['metavar'] = fld.metavar

            if fld.default is not MISSING:
                kwargs['default'] = fld.default

            kwargs['help'] = fld.help

            if doc_mode:
                if 'choices' in kwargs:
                    kwargs.pop('choices')
                    kwargs['metavar'] = fld.name.upper()

            # Determine whether the argument is positional
            positional = False
            if fld.positional:
                positional = True
            if fld.default is MISSING and fld.default_factory is MISSING:
                positional = True
            if fld.count:
                positional = False

            if positional:
                action = parser.add_argument(fld.name, **kwargs)
            else:
                name = fld.name if '_' not in fld.name else fld.name.replace('_', '-')
                kwargs['dest'] = fld.name
                if fld.abrv is not None:
                    action = parser.add_argument(f"--{name}", f"-{fld.abrv}", **kwargs)
                else:
                    action = parser.add_argument(f"--{name}", **kwargs)

            if fld.completer is not None and isinstance(fld.completer, dict):
                def _completer(**kwargs):
                    return fld.completer
                action.completer = _completer  # type: ignore[attr-defined]
            elif fld.completer is not None and callable(fld.completer):
                action.completer = fld.completer  # type: ignore[attr-defined]

    @classmethod
    def _add_sub_commands(cls, parser: ArgumentParser, doc_mode: bool = False) -> None:
        """Add sub-commands to the parser

        Args:
            parser (ArgumentParser): The parser to add sub-commands to
        """
        if len(cls.sub_commands) == 0:
            return

        sub_parsers = parser.add_subparsers(
            dest="sub_command",
            description="Get help for subcommands with the --help flag"
        )

        for sub_cmd_name, sub_cmd in cls.sub_commands.items():
            sub_parser = sub_parsers.add_parser(
                sub_cmd_name,
                description=sub_cmd.__doc__,
            )
            sub_cmd._add_args(sub_parser, doc_mode)
            sub_cmd._add_sub_commands(sub_parser, doc_mode)

    @classmethod
    def from_args(cls: Type[CommandT], args: Namespace) -> CommandT:
        """Create a command from a list of arguments

        Args:
            args (list[str]): The arguments to create the command from

        Returns:
            CommandT: The created command
        """
        arg_dict = {}

        for fld in fields(cls):
            if not isinstance(fld, CmdArgument):
                if fld.name == "sub_command":
                    continue
                raise InvalidArgumentError(
                    f"Field {fld.name} is not a CmdArgument" +
                    " Did you use field() instead of arg()?"
                )

            arg_dict[fld.name] = getattr(args, fld.name)

            if 'list' in fld.type and fld.positional:
                if arg_dict[fld.name] is None:
                    arg_dict[fld.name] = []
                elif len(arg_dict[fld.name]) == 0:
                    arg_dict[fld.name] = None
            else:
                if fld.choices is not None and not isinstance(fld.choices, list):
                    if issubclass(fld.choices, Enum) and arg_dict[fld.name] is not None:
                        try:
                            arg_dict[fld.name] = fld.choices(arg_dict[fld.name])
                        except ValueError:
                            arg_dict[fld.name] = fld.choices[arg_dict[fld.name]]

        if len(cls.sub_commands) != 0 and args.sub_command is not None:
            arg_dict["sub_command"] = cls.sub_commands[args.sub_command].from_args(args)
        else:
            arg_dict["sub_command"] = None

        return cls(**arg_dict)

    @classmethod
    def execute(cls: Type[CommandT]) -> NoReturn:
        """Execute the command and exit with the return code
        """
        parser = cls.create_parser()
        if argcomplete is not None:
            argcomplete.autocomplete(parser)
        args = parser.parse_args()
        cmd = cls.from_args(args)
        exit(cmd())


#####################################################################################
# Type Information
#####################################################################################
CommandT = TypeVar("CommandT", bound="Command")
