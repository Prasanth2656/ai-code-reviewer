import os
import stat
import shutil
from git import Repo

TEMP_DIR = "temp_repo"


def _remove_readonly(func, path, _):
    """Error handler for shutil.rmtree on Windows.
    Git pack files are marked read-only; this clears that flag and retries."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_repository(repo_url: str):
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, onerror=_remove_readonly)

    Repo.clone_from(repo_url, TEMP_DIR)
    return TEMP_DIR