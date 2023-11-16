# Developer README

- [Releasing](#releasing)


## Releasing

Releases are published automatically when a tag is pushed to GitHub.

```bash
  # Set next version number
  export RELEASE=x.x.x

  # Create tags
  git commit --allow-empty -m "Release $RELEASE"
  git tag -a $RELEASE -m "Version $RELEASE"

  # Push
  git push --tags
```