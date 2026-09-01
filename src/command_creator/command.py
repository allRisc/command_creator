#####################################################################################
# A package to simplify the creation of Python Command-Line tools
# Copyright (C) 2026 Benjamin Davis
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
"""Pydantic-based command model.

A command is a :class:`pydantic.BaseModel` subclass of :class:`BaseCmdModel`.  Each
model field becomes a command-line argument, driven entirely by native pydantic
constructs:

* the field's type annotation drives argument type, list handling and choices
  (``Enum`` / ``Literal``),
* ``pydantic.Field(default=..., description=...)`` supplies the default value and
  the ``--help`` text,
* anything that pydantic's ``Field`` has no native concept of (an abbreviation, a
  forced-positional, a count flag, a custom metavar) is passed through the field's
  ``json_schema_extra`` metadata, typed by the :class:`ArgMeta` ``TypedDict``.

Sub-commands are declared with class-owned identity: every command class knows its
own :attr:`~BaseCmdModel.cmd_name` (defaulting to the lower-cased class name) and
:attr:`~BaseCmdModel.cmd_aliases`, and a parent lists its children in
:attr:`~BaseCmdModel.sub_commands`.  Because every sub-command is itself a
``BaseCmdModel`` this nests to an arbitrary depth.
"""

from __future__ import annotations

import argparse
import enum
import itertools
import sys
import types
from collections.abc import Sequence
from typing import (
    Any,
    ClassVar,
    Literal,
    NoReturn,
    Self,
    TypedDict,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict, PrivateAttr

__all__ = [
    "ArgMeta",
    "BaseCmdModel",
    "InvalidCommandError",
]

# Field names that would collide with the command API and break dispatch/identity.
_RESERVED_NAMES = frozenset(
    {
        "run",
        "run_path",
        "run_and_exit",
        "command_chain",
        "sub_command",
        "sub_commands",
        "cmd_name",
        "cmd_aliases",
        "get_cmd_name",
        "get_cmd_aliases",
        "get_parser",
        "parse",
    }
)


#####################################################################################
# Errors
#####################################################################################
class InvalidCommandError(Exception):
    """Raised when a command or one of its fields is defined in a way that cannot be
    turned into a command-line interface.
    """


#####################################################################################
# Argument metadata
#####################################################################################
class ArgMeta(TypedDict, total=False):
    """Command-line metadata for a field, supplied via ``Field(json_schema_extra=...)``.

    Everything here is intentionally *not* something pydantic's ``Field`` already
    models.  :class:`ArgMeta` is a ``TypedDict`` (all keys optional), so it names and
    types the accepted options for editors and type-checkers while remaining a plain
    ``dict`` at runtime::

        from pydantic import Field
        from command_creator import ArgMeta

        class Cmd(BaseCmdModel):
            verbose: bool = Field(False, description="be loud",
                                  json_schema_extra=ArgMeta(abrv="v"))

    Pass only the options you need; omitted keys are simply absent.

    Keys:
        abrv: A single short-option abbreviation, e.g. ``"v"`` exposes ``-v`` alongside
            the long ``--<name>`` option.  Ignored for positional arguments.
        positional: Force the argument to be positional (``True``) or an option
            (``False``).  When omitted the argument is positional if the field is
            required and an option otherwise.
        optional: Allow the argument's value to be omitted (argparse ``nargs="?"``).
            For an option this means ``--opt`` may be given with no following value,
            in which case the value becomes ``None`` (declare the field as ``T | None``).
        count: Treat the argument as a repeat-counter (argparse ``action="count"``),
            e.g. ``-vvv`` -> ``3``.  Only valid on ``int`` fields and mutually
            exclusive with ``positional``.
        metavar: Override the placeholder shown for the argument's value in ``--help``.
    """

    abrv: str
    positional: bool
    optional: bool
    count: bool
    metavar: str


#####################################################################################
# Type-introspection helpers
#####################################################################################
def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Strip a single ``None`` from an ``Optional``/union annotation.

    Args:
        annotation: The field annotation to inspect.

    Returns:
        A ``(inner_type, is_optional)`` pair.  ``inner_type`` is the annotation with a
        lone ``NoneType`` removed (unchanged for non-optional annotations) and
        ``is_optional`` reports whether ``None`` was one of the union members.
    """
    if get_origin(annotation) in (types.UnionType, Union):
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        is_optional = type(None) in args
        if len(non_none) == 1:
            return non_none[0], is_optional
        return annotation, is_optional
    return annotation, False


def _is_enum(tp: Any) -> bool:
    """Return whether *tp* is an ``enum.Enum`` subclass."""
    return isinstance(tp, type) and issubclass(tp, enum.Enum)


def _enum_choices(tp: type[enum.Enum]) -> tuple[list[Any], type]:
    """Derive argparse ``choices`` and a value-converter for an ``Enum`` type.

    Choices are the member *values* (pydantic coerces a value back to the member),
    and the converter matches the value type so argparse can validate before pydantic
    ever sees it.

    Args:
        tp: The enum type.

    Returns:
        A ``(choices, converter)`` pair.
    """
    values = [member.value for member in tp]
    if issubclass(tp, int) and not issubclass(tp, str):
        return values, int
    if issubclass(tp, str):
        return values, str
    converter = type(values[0]) if values else str
    return values, converter


def _scalar_converter(tp: Any) -> Any | None:
    """Return the argparse ``type=`` callable for a scalar annotation.

    Args:
        tp: The (already optional-unwrapped) scalar annotation.

    Returns:
        A callable suitable for argparse's ``type=`` argument, or ``None`` when the
        value should be left as a raw string for pydantic to coerce.
    """
    if _is_enum(tp):
        return _enum_choices(tp)[1]
    if get_origin(tp) is Literal:
        # Match the argparse-side type to the literal values so string input is
        # converted before it is compared against the (possibly non-string) choices.
        values = get_args(tp)
        return type(values[0]) if values else None
    if tp in (int, float, str):
        return tp
    return None


def _choices_for(tp: Any) -> list[Any] | None:
    """Return argparse ``choices`` for ``Enum`` / ``Literal`` annotations, else ``None``."""
    if _is_enum(tp):
        return _enum_choices(tp)[0]
    if get_origin(tp) is Literal:
        return list(get_args(tp))
    return None


#####################################################################################
# Command model
#####################################################################################
class BaseCmdModel(BaseModel):
    """Base class for a command-line command.

    Subclass it, declare each argument as a pydantic field and implement :meth:`run`.
    Nest commands by listing child classes in :attr:`sub_commands`.
    """

    # Arguments are always populated by field name (never by a pydantic alias), so a
    # field that declares an ``alias`` still constructs correctly from parsed values.
    model_config = ConfigDict(populate_by_name=True)

    # --- Class-level command identity (not pydantic fields) --------------------------
    cmd_name: ClassVar[str | None] = None
    """Explicit name for the (sub)command; defaults to the lower-cased class name."""
    cmd_aliases: ClassVar[Sequence[str]] = ()
    """Alternate names the (sub)command may be invoked by."""
    sub_commands: ClassVar[Sequence[type[BaseCmdModel]]] = ()
    """Child command classes.  Each may declare its own ``sub_commands`` (any depth)."""

    # --- Runtime state ---------------------------------------------------------------
    _sub_command: BaseCmdModel | None = PrivateAttr(default=None)
    """The selected child command instance, populated during :meth:`parse`."""

    # --- Identity helpers ------------------------------------------------------------
    @classmethod
    def get_cmd_name(cls) -> str:
        """Return the command name, defaulting to the lower-cased class name."""
        return cls.cmd_name if cls.cmd_name is not None else cls.__name__.lower()

    @classmethod
    def get_cmd_aliases(cls) -> tuple[str, ...]:
        """Return the command's aliases as a tuple."""
        return tuple(cls.cmd_aliases)

    # --- User hooks ------------------------------------------------------------------
    def run(self) -> None:
        """Execute this command's logic.

        Override in subclasses.  When a sub-command is selected, every command along
        the invoked path runs :meth:`run` in order from root to leaf (see
        :meth:`run_path`).  Raise an exception (or ``SystemExit``) to signal failure.
        """

    # --- Selected-command access -----------------------------------------------------
    @property
    def sub_command(self) -> BaseCmdModel | None:
        """The child command selected on the command line, or ``None``."""
        return self._sub_command

    def command_chain(self) -> list[BaseCmdModel]:
        """Return the invoked commands from this one down to the selected leaf.

        The list always starts with ``self`` and follows :attr:`sub_command` links.
        """
        chain: list[BaseCmdModel] = [self]
        node: BaseCmdModel | None = self._sub_command
        while node is not None:
            chain.append(node)
            node = node._sub_command
        return chain

    def run_path(self) -> None:
        """Run :meth:`run` for every command on the invoked path, root first."""
        for command in self.command_chain():
            command.run()

    #####################################################################################
    # Parser construction
    #####################################################################################
    @classmethod
    def get_parser(cls, prog: str | None = None) -> argparse.ArgumentParser:
        """Build the :class:`argparse.ArgumentParser` for this command and its children.

        Args:
            prog: The program name shown in usage.  Defaults to :meth:`get_cmd_name`.

        Returns:
            The fully-populated argument parser.
        """
        parser = argparse.ArgumentParser(prog=prog or cls.get_cmd_name(), description=cls.__doc__)
        cls._build(parser, prefix="", depth=0, counter=itertools.count())
        return parser

    @classmethod
    def _build(
        cls,
        parser: argparse.ArgumentParser,
        prefix: str,
        depth: int,
        counter: itertools.count,
    ) -> None:
        """Recursively add this command's arguments and sub-commands to *parser*.

        Args:
            parser: The parser (or sub-parser) representing this command.
            prefix: Unique dest prefix keeping this command's fields distinct from
                same-named fields at other depths.
            depth: The current nesting depth (0 at the root).
            counter: Shared counter used to mint unique per-command prefixes.
        """
        has_positional = cls._add_arguments(parser, prefix)

        if not cls.sub_commands:
            return

        if has_positional:
            raise InvalidCommandError(
                f"{cls.__name__}: a command that declares sub_commands cannot also have "
                f"positional arguments (a positional would consume the sub-command token); "
                f"expose them as options via ArgMeta(positional=False)"
            )

        sub_parsers = parser.add_subparsers(
            dest=f"_cc_lvl{depth}",
            metavar="COMMAND",
            help="Sub-command to run; pass --help to any for details.",
        )

        seen: dict[str, type[BaseCmdModel]] = {}
        for sub in cls.sub_commands:
            names = (sub.get_cmd_name(), *sub.get_cmd_aliases())
            for name in names:
                if name in seen:
                    if seen[name] is sub:
                        raise InvalidCommandError(
                            f"{cls.__name__}: command {sub.__name__} lists name/alias "
                            f"{name!r} more than once"
                        )
                    raise InvalidCommandError(
                        f"{cls.__name__}: sub-command name/alias {name!r} is used by both "
                        f"{seen[name].__name__} and {sub.__name__}"
                    )
                seen[name] = sub

            sub_prefix = f"_c{next(counter)}_"
            sub_parser = sub_parsers.add_parser(
                sub.get_cmd_name(),
                aliases=list(sub.get_cmd_aliases()),
                help=_first_line(sub.__doc__),
                description=sub.__doc__,
            )
            # Record which class (and its dest prefix) was chosen at this depth so the
            # exact invoked chain can be rebuilt regardless of which alias was typed.
            sub_parser.set_defaults(**{f"_cc_cls{depth}": sub, f"_cc_pfx{depth}": sub_prefix})
            sub._build(sub_parser, prefix=sub_prefix, depth=depth + 1, counter=counter)

    @classmethod
    def _add_arguments(cls, parser: argparse.ArgumentParser, prefix: str) -> bool:
        """Add every field of this command to *parser* as a CLI argument.

        Args:
            parser: The parser representing this command.
            prefix: Dest prefix isolating this command's fields.

        Returns:
            Whether any positional argument was added (parents that also declare
            sub-commands may not have positionals -- they would swallow the token).
        """
        has_positional = False
        for name, field in cls.model_fields.items():
            if name in _RESERVED_NAMES:
                raise InvalidCommandError(
                    f"{cls.__name__}.{name}: field name {name!r} is reserved by the command API; "
                    f"rename the field, or annotate class-owned attributes as ClassVar"
                )

            extra = field.json_schema_extra
            meta: dict[str, Any] = extra if isinstance(extra, dict) else {}

            abrv = meta.get("abrv")
            force_positional = meta.get("positional")
            value_optional = bool(meta.get("optional", False))
            is_count = bool(meta.get("count", False))
            metavar = meta.get("metavar")

            inner, is_optional = _unwrap_optional(field.annotation)
            origin = get_origin(inner)
            type_args = get_args(inner)
            is_variadic_tuple = origin is tuple and len(type_args) == 2 and type_args[1] is Ellipsis
            is_fixed_tuple = origin is tuple and not is_variadic_tuple and bool(type_args)
            is_list = origin in (list, set, frozenset) or is_variadic_tuple
            is_bool = inner is bool
            required = field.is_required()

            if is_count and inner is not int:
                raise InvalidCommandError(
                    f"{cls.__name__}.{name}: count=True requires an int field"
                )
            if is_count and force_positional:
                raise InvalidCommandError(
                    f"{cls.__name__}.{name}: count and positional are mutually exclusive"
                )
            if abrv is not None and str(abrv).isdigit():
                raise InvalidCommandError(
                    f"{cls.__name__}.{name}: numeric abbreviation {abrv!r} would disable "
                    f"negative-number parsing; use a non-numeric abbreviation"
                )

            # Positional unless it is a flag/count/option; an explicit meta wins.
            if force_positional is None:
                positional = required and not is_bool and not is_count
            else:
                positional = bool(force_positional)

            dest = f"{prefix}{name}"
            kwargs: dict[str, Any] = {"default": argparse.SUPPRESS}
            if field.description:
                kwargs["help"] = field.description

            if is_bool and not is_count:
                # Booleans are always flags; a bare required bool is contradictory since
                # an absent flag must resolve to a concrete value.
                if required:
                    raise InvalidCommandError(
                        f"{cls.__name__}.{name}: a boolean flag must have a default "
                        f"(e.g. `{name}: bool = Field(False)`)"
                    )
                # Direction (and the absent value) follow the default.
                store_false = field.default is True
                kwargs["action"] = "store_false" if store_false else "store_true"
                kwargs["default"] = store_false
                positional = False
            elif is_count:
                # A counter's natural absent value is 0 (or the field default).
                kwargs["action"] = "count"
                kwargs["default"] = field.default if isinstance(field.default, int) else 0
                positional = False
            elif is_fixed_tuple:
                # A heterogeneous fixed-length tuple: enforce exact arity and let pydantic
                # coerce each position, since a single argparse type= cannot span them.
                kwargs["nargs"] = len(type_args)
            else:
                element = type_args[0] if is_list and type_args else inner
                converter = _scalar_converter(element)
                if converter is not None:
                    kwargs["type"] = converter
                choices = _choices_for(element)
                if choices is not None:
                    kwargs["choices"] = choices

                if is_list:
                    # A required list needs at least one value regardless of whether it
                    # renders as a positional or an option.
                    at_least_one = required and not value_optional
                    kwargs["nargs"] = "+" if at_least_one else "*"
                elif value_optional or (positional and not required):
                    # A value that may be omitted: an explicit optional value, or a
                    # positional carrying a default (positionals are otherwise required).
                    kwargs["nargs"] = "?"
                    if value_optional and not positional:
                        if not is_optional:
                            raise InvalidCommandError(
                                f"{cls.__name__}.{name}: optional=True on an option requires "
                                f"the field to be declared `T | None`"
                            )
                        kwargs["const"] = None

            cls._set_metavar(kwargs, name, metavar, positional, is_bool or is_count)

            try:
                if positional:
                    # For a positional the name *is* the dest; a metavar (set above) keeps
                    # the prefixed dest out of the help text.
                    has_positional = True
                    parser.add_argument(dest, **kwargs)
                else:
                    option = f"--{name.replace('_', '-')}"
                    if required and not is_bool and not is_count:
                        kwargs["required"] = True
                    flags = [option, f"-{abrv}"] if abrv else [option]
                    parser.add_argument(*flags, dest=dest, **kwargs)
            except argparse.ArgumentError as err:
                raise InvalidCommandError(f"{cls.__name__}.{name}: {err}") from err

        return has_positional

    @staticmethod
    def _set_metavar(
        kwargs: dict[str, Any],
        name: str,
        metavar: str | None,
        positional: bool,
        no_value: bool,
    ) -> None:
        """Choose a display metavar that never leaks the internal dest prefix.

        Args:
            kwargs: The argparse keyword arguments being assembled (mutated in place).
            name: The field name.
            metavar: A user-supplied metavar override, if any.
            positional: Whether the argument is positional.
            no_value: Whether the argument takes no value (a flag or a counter).
        """
        if no_value:
            return
        if metavar is not None:
            kwargs["metavar"] = metavar
        elif positional:
            # Positional dest is prefixed, so a metavar is required to show a clean name.
            kwargs["metavar"] = name
        elif "choices" not in kwargs:
            # Options otherwise default their metavar to the prefixed dest; override it.
            kwargs["metavar"] = name.upper()

    #####################################################################################
    # Parsing
    #####################################################################################
    @classmethod
    def parse(cls, argv: Sequence[str] | None = None) -> Self:
        """Parse command-line arguments into a fully-populated command instance.

        Args:
            argv: Arguments to parse.  Defaults to ``sys.argv[1:]`` (argparse's default).

        Returns:
            The root command instance, with any selected sub-commands linked through
            :attr:`sub_command`.
        """
        namespace = cls.get_parser().parse_args(argv)

        root = cls._from_namespace(namespace)
        parent: BaseCmdModel = root
        depth = 0
        while True:
            sub_cls: type[BaseCmdModel] | None = getattr(namespace, f"_cc_cls{depth}", None)
            sub_pfx: str | None = getattr(namespace, f"_cc_pfx{depth}", None)
            if sub_cls is None or sub_pfx is None:
                break
            child = sub_cls._from_namespace(namespace, sub_pfx)
            parent._sub_command = child
            parent = child
            depth += 1

        return root

    @classmethod
    def _from_namespace(cls, namespace: argparse.Namespace, prefix: str = "") -> Self:
        """Build a single command instance from the parsed *namespace*.

        Only this command's own (prefix-scoped) fields are read; pydantic supplies
        defaults and performs validation/coercion for anything the user omitted.

        Args:
            namespace: The parsed argparse namespace.
            prefix: The dest prefix for this command's fields.

        Returns:
            The constructed command instance.
        """
        kwargs: dict[str, Any] = {}
        for name in cls.model_fields:
            dest = f"{prefix}{name}"
            if hasattr(namespace, dest):
                kwargs[name] = getattr(namespace, dest)
        return cls(**kwargs)

    #####################################################################################
    # Execution
    #####################################################################################
    @classmethod
    def run_and_exit(cls, argv: Sequence[str] | None = None) -> NoReturn:
        """Parse arguments, run the full invoked command path, then exit ``0``.

        Args:
            argv: Arguments to parse.  Defaults to ``sys.argv[1:]``.

        An uncaught exception raised by :meth:`run` propagates (yielding a non-zero
        exit via the interpreter); raise ``SystemExit`` for an explicit exit code.
        """
        cls.parse(argv).run_path()
        sys.exit(0)


#####################################################################################
# Helpers
#####################################################################################
def _first_line(doc: str | None) -> str | None:
    """Return the first non-empty line of a docstring, for sub-command help listings."""
    if not doc:
        return None
    for line in doc.strip().splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None
