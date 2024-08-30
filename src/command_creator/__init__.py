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
from typing import Any, Callable, Mapping, TypeVar, Type, ClassVar, NoReturn, Union
from types import UnionType, NoneType
import typing

import sys
from dataclasses import Field, dataclass, MISSING, fields
from enum import Enum
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
import re

try:
  import argcomplete
  from argcomplete.completers import BaseCompleter
except ModuleNotFoundError:
  _has_argcomplete = False
else:
  _has_argcomplete = True


__all__ = [
  'version_info',
  'InvalidArgumentError',
  'SUCCESS',
  'FAILURE',
  'CmdArgument',
  'arg',
  'Command',
  'CommandT',
  'dataclass'
]


#####################################################################################
# Version Information
#####################################################################################
from command_creator._info import __version__

version_info = [int(x) if x.isdigit() else x for x in re.split(r"\.|-", __version__)]


#####################################################################################
# Error Information
#####################################################################################
class InvalidArgumentError(Exception):
  """Error raised when an invalid argument is passed to a command
  """
  pass


#####################################################################################
# Useful Constants
#####################################################################################
SUCCESS = 0
FAILURE = 1


#####################################################################################
# Typeing helpers
#####################################################################################
def _type_callable(hint: Any) -> Type | None:
  origin = typing.get_origin(hint)
  if origin is Union or origin is UnionType:
    args = typing.get_args(hint)
    if len(args) > 2:
      return None
    if len(args) == 2:
      if args[0] in (None, NoneType) and callable(args[1]):
        return args[1]
      if args[1] in (None, NoneType) and callable(args[0]):
        return args[0]
      return None
    if len(args) == 1 and callable(args[0]):
      return args[0]
  elif origin is list:
    args = typing.get_args(hint)
    if len(args) == 1 and callable(args[0]):
      return args[0]
    return None
  elif origin is not None:
    return None

  if callable(hint):
    return hint
  return None


def _is_list(hint: Any) -> bool:
  if typing.get_origin(hint) is list:
    return True
  if hint is list:
    return True
  return False


def _is_enum(hint: Any) -> bool:
  if isinstance(hint, type):
    if issubclass(hint, Enum):
      return True

  return False


#####################################################################################
# Command Argument
#####################################################################################
class CmdArgument(Field):
  """Class which represents a command-line argument
  """
  __slots__ = ("help", "abrv", "choices", "optional", "completer")

  def __init__(
        self,
        help: str = "",
        abrv: str | None = None,
        choices: list[str] | type[Enum] | None = None,
        optional: bool = False,
        completer: Any = None,
        default: Any = MISSING,
        default_factory: Callable[[], Any] = lambda: MISSING,
        init: bool = True,
        repr: bool = True,
        hash: bool | None = None,
        compare: bool = True,
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
    self.abrv = abrv
    self.choices = choices
    self.optional = optional

    if _has_argcomplete:
      self.completer = completer
    elif completer is not None:
      raise InvalidArgumentError(
        "Completer argument specified when 'argcomplete' package not installed"
      )
    else:
      self.completer = None


def arg(
      help: str = "",
      abrv: str | None = None,
      choices: list[str] | type[Enum] | None = None,
      optional: bool = False,
      completer: BaseCompleter | None = None,
      default: Any = MISSING,
      default_factory: Callable[[], Any] = lambda: MISSING,
      init: bool = True,
      repr: bool = True,
      hash: bool | None = None,
      compare: bool = True,
      metadata: Mapping[Any, Any] = dict(),
      **kwargs: Any
    ) -> Any:
  """Create a command-line argument

  Args:
      help (str, optional): Help message for the argument. Defaults to empty string.
      abrv (str | None, optional): Abbreviation for the argument. Defaults to None.
      choices (list[str] | Enum | None, optional): List of choices for the argument.
        Defaults to None.
      optional (bool, optional): Whether the argument is optional. Defaults to False.
      default (Any, optional): Default value for the argument. Defaults to MISSING.
      default_factory (Callable[[], Any], optional): Default factory for the argument.
        Defaults to lambda: MISSING.
      init (bool, optional): Whether the argument is included in the __init__ method.
        Defaults to True.
      repr (bool, optional): Whether the argument is included in the __repr__ method.
        Defaults to True.
      hash (bool | None, optional): Whether the argument is included in the __hash__ method.
        Defaults to None.
      compare (bool, optional): Whether the argument is included in the __eq__ method.
        Defaults to True.
      metadata (Mapping[Any, Any], optional): Metadata for the argument. Defaults to dict().
      **kwargs (Any): Additional keyword arguments for the argument.

  Returns:
      Any: The command-line argument
  """
  if sys.version_info >= (3, 10):
    if "kw_only" not in kwargs:
      kwargs["kw_only"] = False

  return CmdArgument(
    help=help,
    abrv=abrv,
    choices=choices,
    optional=optional,
    completer=completer,
    default=default,
    default_factory=default_factory,
    init=init,
    repr=repr,
    hash=hash,
    compare=compare,
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
  sub_command: Command | None

  @abstractmethod
  def __post_init__(self) -> None:
    """This method must be implemented by subclasses in order to setup variables or
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
  def create_parser(cls: Type[CommandT]) -> ArgumentParser:
    parser = ArgumentParser(
      prog=cls.__name__.lower(),
      description=cls.__doc__,
    )
    cls._add_args(parser)
    if _has_argcomplete:
      argcomplete.autocomplete(parser)
    cls._add_sub_commands(parser)
    return parser

  @classmethod
  def _add_args(cls, parser: ArgumentParser) -> None:
    """Add arguments to the parser

    Args:
        parser (ArgumentParser): The parser to add arguments to
    """
    types = typing.get_type_hints(cls)

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

      if _is_list(types[fld.name]):
        kwargs['nargs'] = '+'

      callable_type = _type_callable(types[fld.name])

      if callable_type is bool:
        if fld.default is MISSING or fld.default is False:
          kwargs['action'] = 'store_true'
          kwargs['default'] = False
        else:
          kwargs['action'] = 'store_false'
          kwargs['default'] = True
      elif callable_type is not None:
        kwargs['type'] = callable_type

      if fld.optional:
        if 'nargs' not in kwargs:
          kwargs['nargs'] = '?'
        else:
          kwargs['nargs'] = '*'

      if fld.choices is not None or _is_enum(types[fld.name]):
        if isinstance(fld.choices, list):
          kwargs['choices'] = fld.choices
        elif isinstance(fld.choices, Enum):
          kwargs['choices'] = [str(e).replace(fld.choices.__name__ + ".", "") for e in fld.choices]
        elif _is_enum(types[fld.name]):
          kwargs['choices'] = [
            str(e).replace(types[fld.name].__name__ + ".", "") for e in types[fld.name]
          ]
        else:
          raise ValueError(
            f"Field {fld.name} has an invalid type for choices" +
            " Did you use an Enum or a list?"
          )

      if fld.default is not MISSING:
        kwargs['default'] = fld.default

      kwargs['help'] = fld.help

      if fld.default is MISSING and fld.default_factory is MISSING:
        parser.add_argument(fld.name, **kwargs).completer = fld.completer
      elif fld.abrv is not None:
        parser.add_argument(f"--{fld.name}", f"-{fld.abrv}", **kwargs).completer = fld.completer
      else:
        parser.add_argument(f"--{fld.name}", **kwargs).completer = fld.completer

  @classmethod
  def _add_sub_commands(cls, parser: ArgumentParser) -> None:
    """Add sub-commands to the parser

    Args:
        parser (ArgumentParser): The parser to add sub-commands to
    """
    if len(cls.sub_commands) == 0:
      return

    sub_parsers = parser.add_subparsers(dest="sub_command", required=False)

    for sub_cmd_name, sub_cmd in cls.sub_commands.items():
      sub_parser = sub_parsers.add_parser(
        sub_cmd_name,
        usage=sub_cmd.__doc__,
      )
      sub_cmd._add_args(sub_parser)
      sub_cmd._add_sub_commands(sub_parser)

  @classmethod
  def from_args(cls: Type[CommandT], args: Namespace) -> CommandT:
    """Create a command from a list of arguments

    Args:
        args (list[str]): The arguments to create the command from

    Returns:
        CommandT: The created command
    """
    arg_dict = {}

    types = typing.get_type_hints(cls)

    for fld in fields(cls):
      if not isinstance(fld, CmdArgument):
        if fld.name == "sub_command":
          continue
        raise InvalidArgumentError(
          f"Field {fld.name} is not a CmdArgument" +
          " Did you use field() instead of arg()?"
        )

      arg_dict[fld.name] = getattr(args, fld.name)

      if _is_list(types[fld.name]) and fld.optional:
        if arg_dict[fld.name] is None:
          arg_dict[fld.name] = []
        elif len(arg_dict[fld.name]) == 0:
          arg_dict[fld.name] = None

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
    args = parser.parse_args()
    cmd = cls.from_args(args)
    exit(cmd())


#####################################################################################
# Type Information
#####################################################################################
CommandT = TypeVar("CommandT", bound="Command")
