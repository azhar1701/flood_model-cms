"""
Utility script to fix Jupyter notebooks that have incomplete widget
metadata.  Some notebook previewers will fail to render notebooks when
they encounter a ``metadata.widgets`` entry that does not include a
``state`` key.  Running this script on a notebook will add an
empty ``state`` dict if it is missing or, if you prefer, remove the
entire ``widgets`` entry.  The default behaviour adds an empty
``state`` to preserve any existing widget metadata.

Usage examples::

    # Add a missing ``state`` key to ``metadata.widgets`` in-place
    python fix_notebook_widgets.py path/to/notebook.ipynb

    # Remove the entire widgets metadata instead
    python fix_notebook_widgets.py --remove-widgets path/to/notebook.ipynb

    # Recursively scan a directory for notebooks and fix them
    python fix_notebook_widgets.py --recursive path/to/dir

The script makes a backup of each notebook before overwriting it by
appending ``.bak`` to the filename.  This allows you to revert the
changes if necessary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


def fix_widgets_metadata(
    nb_data: dict, *, remove_widgets: bool = False
) -> bool:
    """Fix the ``metadata.widgets`` section of a notebook.

    Args:
        nb_data: Parsed notebook JSON.
        remove_widgets: If true, delete ``metadata.widgets`` entirely
            instead of adding a missing ``state`` key.

    Returns:
        bool: True if any modifications were made, False otherwise.
    """
    changed = False
    meta = nb_data.get("metadata", {})
    widgets = meta.get("widgets")
    if widgets is not None:
        if remove_widgets:
            # Drop the entire widgets entry
            del meta["widgets"]
            changed = True
        elif isinstance(widgets, dict) and "state" not in widgets:
            # Add an empty state dictionary
            widgets["state"] = {}
            changed = True

    # Widgets metadata can also appear on individual cell metadata
    for cell in nb_data.get("cells", []):
        cmeta = cell.get("metadata", {})
        widgets = cmeta.get("widgets")
        if widgets is not None:
            if remove_widgets:
                del cmeta["widgets"]
                changed = True
            elif isinstance(widgets, dict) and "state" not in widgets:
                widgets["state"] = {}
                changed = True
    return changed


def process_notebooks(paths: Iterable[Path], *, remove_widgets: bool) -> None:
    for nb_path in paths:
        if nb_path.suffix != ".ipynb":
            continue
        try:
            text = nb_path.read_text(encoding="utf-8")
            nb_data = json.loads(text)
        except Exception as exc:
            print(f"Error reading {nb_path}: {exc}")
            continue
        changed = fix_widgets_metadata(nb_data, remove_widgets=remove_widgets)
        if changed:
            backup_path = nb_path.with_suffix(nb_path.suffix + ".bak")
            nb_path.replace(backup_path)
            nb_path.write_text(json.dumps(nb_data, indent=2), encoding="utf-8")
            print(
                f"Fixed widgets metadata in {nb_path}, backup saved to {backup_path}")


def iterate_notebooks(base_dir: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        yield from base_dir.rglob("*.ipynb")
    else:
        yield from base_dir.glob("*.ipynb")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fix the 'state' key in metadata.widgets for Jupyter notebooks."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Notebook file(s) or directory(ies) to process.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search directories for notebooks.",
    )
    parser.add_argument(
        "--remove-widgets",
        action="store_true",
        help="Remove the widgets metadata entirely instead of adding an empty state.",
    )
    args = parser.parse_args()
    for path_str in args.paths:
        p = Path(path_str)
        if p.is_file():
            process_notebooks([p], remove_widgets=args.remove_widgets)
        elif p.is_dir():
            notebooks = list(iterate_notebooks(p, recursive=args.recursive))
            if not notebooks:
                print(f"No notebooks found in directory {p}")
            process_notebooks(notebooks, remove_widgets=args.remove_widgets)
        else:
            print(f"Path not found: {p}")


if __name__ == "__main__":
    main()
