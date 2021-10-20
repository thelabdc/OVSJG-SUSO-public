from pathlib import Path
from typing import List, Optional, Union

ROOT_MARKERS = (
    ".git",
    "pyproject.toml",
    "poetry.lock",
)


# There are a few users who are on Python 3.7 which doesn't support
# Python 3.8's HIGHEST_PROTOCOL (5), and so we need to specify that
# we are using PICKLE_PROTOCOL = 4
PICKLE_PROTOCOL = 4


def here(
    *name: List[str], root_markers: Optional[Union[str, List[str]]] = None
) -> Path:
    """
    Acts like R's `here` package and let's you find a directory
    relative to the project root (denoted by the presence of a file with a name in
    `root_markers`)
    """

    root_markers = root_markers or ROOT_MARKERS
    if isinstance(root_markers, str):
        root_markers = [root_markers]

    endpath = Path(*name)

    path = Path.cwd()
    while True:
        if any((path / root_marker).exists() for root_marker in root_markers):
            break

        new_path = path.parent
        if new_path == path:
            raise ValueError("No project root found")

        path = new_path

    return path / endpath
