import re
import tempfile
from pathlib import Path

import git

GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[\w\-]+/[\w\-]+(\.git)?$"
)


def validate_github_url(url: str) -> bool:
    return bool(GITHUB_URL_PATTERN.match(url))


def clone_repo(url: str) -> tempfile.TemporaryDirectory:
    if not validate_github_url(url):
        raise ValueError(f"Invalid GitHub URL: {url}")

    temp_dir = tempfile.TemporaryDirectory(prefix="codesage_")
    try:
        git.Repo.clone_from(url, temp_dir.name)
    except git.GitCommandError as e:
        temp_dir.cleanup()
        raise RuntimeError(f"Failed to clone repository: {e}") from e

    return temp_dir
