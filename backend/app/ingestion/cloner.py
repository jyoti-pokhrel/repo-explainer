import os
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
    print(f"[CLONER] Attempting to clone repository: {url} into {temp_dir.name}")
    try:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        git.Repo.clone_from(url, temp_dir.name, env=env)
        print(f"[CLONER] Successfully cloned repository: {url}")
    except git.GitCommandError as e:
        print(f"[CLONER] GitCommandError while cloning repository: {e}")
        temp_dir.cleanup()
        raise RuntimeError(f"Failed to clone repository: {e}") from e
    except Exception as e:
        print(f"[CLONER] Unexpected error while cloning repository: {e}")
        temp_dir.cleanup()
        raise e

    return temp_dir
