# Developer README

- [Developer README](#developer-readme)
  - [Releasing](#releasing)


## Releasing

Releases are published automatically when a tag is pushed to GitHub.

```bash
  # Set next version number
  export RELEASE=x.x.x
  export RELEASE=$(python -c "import command_creator._version as _version; print(_version.__version__)")

  # Ensure committing everything (optional)
  git add -A

  # Create tags
  git commit --allow-empty -m "Release $RELEASE"
  git tag -a $RELEASE -m "Version $RELEASE"

  # Push
  git push --follow-tags
```