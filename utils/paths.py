"""Where the large data live: `data/` in the repository, or the folder in PWPA_DATA_DIR. Git ignores both."""

import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = pathlib.Path(os.environ.get("PWPA_DATA_DIR", REPO / "data"))


def data_dir(*parts):
    """A folder under the data root, created if it does not exist."""
    path = DATA_DIR.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path
