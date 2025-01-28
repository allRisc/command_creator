User's Guide
====================================================================================================

.. contents::
    :local:

Simple Usage
---------------------------------------------------------------------------

The ``command_creator`` package can be used to automatically create CLIs from dataclass objects.
This is done using the ``@dataclass`` decorator, ``command_creator.arg`` method, and the ``command_creator.Command`` class.

.. code-block:: python
    :caption: Simple Example

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


CLI Argument Features
---------------------------------------------------------------------------

Each dataclass field represents a command-line argument.
In order to add functionality, these *must* use ``command_creator.arg`` to instantiate rather than ``dataclasses.field``.
This section outlines how this method can be used to create a wide-range of arguments.

Positional Arguments and Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In unix-style CLI there are two main ways data can be passed to the underlying command: as a positional argument or as an option.
Positional arguments are interpreted based soley on their position.
However, options use ``-`` characters and a name to denote their intended use.
For example ``--debug`` is an option which might tell the underlying command to run in debug mode regardless of where it provided.

Command Creator uses 3-indicators to determine whether an arugment should be interpreted as a Positional Arugment or an Option:

1. ``positional``

    - Arguments which have ``positional=True`` are always treats as Positional Arguments
    - See positional_ for more details

2. ``default`` and ``default_factory``

    - Arguments with a default are treated as options *unless* they are explicitly positional.
    - See `default and default_factory`_ for more details

3. ``count``

    - Arguments which have ``count=True`` are treated as Options even if they don't have a default, because there is no command-line concept of counting positional arguments.
    - ``count=True`` is mutually exclusive with ``positional``
    - See count_ for more details



help
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``help`` argument takes a string which is used for the help message of the command

abrv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``abrv`` argument takes a string which is used as the ``-[abrv]`` abreviated option.

choices
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``choices`` argument takes a list or enum type which sets the valid inputs to the option/positional argument.
If the provided argument is a subclass of the paython standard ``Enum`` then the options are the uppercase names of the enumerated values.

metavar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``metavar`` argument takes a string which is used as the ``METAVAR`` in the help string.

optional
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``optional`` argument takes a boolean and determines the following based on the argument:

- If the argument is *positional*

    - Then the positional argument can be excluded in the command line
    - If the argument is excluded and a default is given then the field gets set to the default
    - If the argument is excluded and no default is given then the field gets set to ``None``

- If the argument is an *option*

    - Then the optional option can be provided without an argument after it
    - If the option is excluded from the command-line then the field gets set to the default
    - If the option is provided w/o an argument then the field gets set to ``None``
    - If the option is provided w/ an argument then the field gets set to the provided argument

positional
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``positional`` argument takes a boolean.
When true it forces the argument to be positional rather than an option.

default and default_factory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Provides defaults to the underlying argument if it is not specified on the command-line.
``default_factory`` is a callable that can be used to create new objects at run-time.
See the Python ``dataclasses`` module documentation for more details.

count
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



completer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sub-commands
---------------------------------------------------------------------------

.. code-block:: python

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


Using with Sphinx-Autoprogram
---------------------------------------------------------------------------

.. code-block:: RST

    .. autoprogram:: pkg_name.module:CommandClass.create_parser(True)


BASH and ZSH Auto-complete
---------------------------------------------------------------------------

.. code-block:: python

    # PYTHON_ARGCOMPLETE_OK