"""Ausführbarer Einstiegspunkt des Pakets.

Ermöglicht den Start über ``python -m avor_smart_attribute_manager``. Die
eigentliche Startlogik liegt in :func:`avor_smart_attribute_manager.app.run`,
damit der Einstiegspunkt schlank bleibt und testbar ist.
"""

from __future__ import annotations

import sys

from avor_smart_attribute_manager.app import run


def main() -> None:
    """Delegiert an :func:`avor_smart_attribute_manager.app.run`."""
    sys.exit(run())


if __name__ == "__main__":
    main()
