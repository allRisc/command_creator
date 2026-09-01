Changelog
====================================================================================================

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

3.0.0 (In-progress)
----------------------------------------------------------------------

### Changed

- **BREAKING**: Commands are now built on top of [pydantic](https://docs.pydantic.dev/).
  Subclass `command_creator.BaseCmdModel` instead of the previous dataclass-based
  `Command`, and implement `run()` (with `run_and_exit()` as the CLI entry point).
- **BREAKING**: Arguments are declared with the typed `arg()` (positional) and `option()`
  wrappers, which are thin wrappers over `pydantic.Field` and forward every field argument.
- Updated `pyproject.toml` to the current packaging layout and dependency-group format.

### Added

- Argument groups for organising `--help` output. Pass `group="Title"` to `arg()` /
  `option()` to list arguments under a shared heading, or declare a field whose type is a
  `BaseCmdModel` subclass to flatten that nested model's fields into a titled group. The
  new `group()` wrapper sets a nested group's title (defaulting to the child's `cmd_name`,
  then its class name) and is exported from the package root.
- `arg_meta()` helper that produces the CLI metadata for a hand-built `pydantic.Field`
  (via its `json_schema_extra`).
- `InvalidCommandError` is exported from the package root.

### Removed

- **BREAKING**: The dataclass-based `Command` base class and its `@dataclass`/`__call__`
  usage pattern. See the documentation for the migration path to `BaseCmdModel`.

3.0.0a1
----------------------------------------------------------------------

### Added

- Initial pre-release of the pydantic-based command model.

2.3.1
----------------------------------------------------------------------

### Changed

- Documentation updates.

2.3.0
----------------------------------------------------------------------

### Added

- Ability to rename a command independently of its class name.

### Changed

- Updated GitHub Actions CI workflows.

2.2.0
----------------------------------------------------------------------

### Added

- Reintroduced `optional` so it can be used alongside `positional`.

2.1.3
----------------------------------------------------------------------

### Fixed

- Corrected how enum choices are parsed.
- Backwards-compatibility fixes for argument handling.

### Added

- Support for both plain `Enum` and `str`-based enums as `choices`.

2.1.0
----------------------------------------------------------------------

### Added

- Dictionary completer support.
- Ability to create optional arguments with a default other than `None`.
- Python 3.8 and 3.9 support.

### Changed

- `argcomplete` is now an optional dependency.
- `count` no longer forces a default to be set.

### Fixed

- Enum choice handling.
- Usage message for sub-commands.

2.0.0
----------------------------------------------------------------------

### Changed

- Major rewrite of the command-creation flow and backend.

1.2.0
----------------------------------------------------------------------

### Added

- Earlier releases of `command_creator`. See the Git history for details.
