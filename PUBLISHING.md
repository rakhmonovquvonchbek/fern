# Publishing fern-audit to PyPI

## Prerequisites

- PyPI account at https://pypi.org
- `pip install build twine`

## Build

```bash
cd ~/fern
python -m build
```

This creates `dist/fern_audit-0.2.0-*.whl` and `.tar.gz`.

## Test on TestPyPI (recommended first)

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ fern-audit
```

## Publish to PyPI

```bash
twine upload dist/*
```

## Verify

```bash
pip install fern-audit
cd /tmp && fern --help
```

## Version bumps

1. Update `version` in `pyproject.toml` and `src/fern/__init__.py`
2. Rebuild and upload

## Notes

- Package name: `fern-audit`
- Console script: `fern`
- User data lives in `~/.fern/` (not bundled)
