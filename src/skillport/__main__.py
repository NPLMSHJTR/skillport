"""Allow `python -m skillport`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())