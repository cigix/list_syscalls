"""
cache.py: Caching utilities.
"""

import datetime
import hashlib
import os
import os.path
import shlex
import subprocess
import urllib.parse
import urllib.request

CACHE_DIR="./.cache"
CACHE_TIMEOUT=datetime.timedelta(days=1)

RAW_GITHUB_HOST="raw.githubusercontent.com"
RAW_GITHUB_URL="https://"+RAW_GITHUB_HOST

GIT_GITHUB_HOST="github.com"
GIT_GITHUB_URL="https://"+GIT_GITHUB_HOST

GITHUB_LINUX_PROJECT="torvalds/linux"

# Runtime file cache
FILE_CACHE = dict()

WARM_REPOS = set()

def _is_too_old(path):
    mtimestamp = os.path.getmtime(path)
    mtime = datetime.datetime.fromtimestamp(mtimestamp)
    age = datetime.datetime.now() - mtime
    return CACHE_TIMEOUT < age

def get_file_from_github(project, branch, path, invalidate=False, binary=False):
    """get_file_from_github(project, branch, path, invalidate=False,
      binary=False): Fetch a file from GitHub or cache.

    Args:
      project: str, the name of the GitHub project
      branch: str, the branch to fetch from
      path: str, the file to fetch
      invalidate: bool, optional (default: False), force cache invalidation
      binary: bool, optional (default: False), get file as bytes

    Return: str or bytes depending on `binary` parameter, the contents of the
    file.
    """
    h = hashlib.md5(path.encode()).hexdigest()
    if h in FILE_CACHE and binary in FILE_CACHE[h]:
        return FILE_CACHE[h][binary]
    cached_path = os.path.join(CACHE_DIR, h)

    reason = None
    if not os.path.isfile(cached_path):
        reason = "not in cache"
    if reason is None and invalidate:
        reason = "forced invalidation"
    if reason is None and _is_too_old(cached_path):
        reason = "cache too old"

    if reason is None:
        print(f"{path}: Using cache")
        mode = "rb" if binary else "rt"
        with open(cached_path, mode) as f:
            data = f.read()
    else:
        print(f"{path}: Downloading ({reason})")
        url = urllib.parse.urljoin(RAW_GITHUB_URL,
                                   project + '/' + branch + '/' + path)
        with urllib.request.urlopen(url) as response:
            data = response.read()
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cached_path, "wb") as f:
            f.write(data)
        if not binary:
            data = data.decode()

    if h not in FILE_CACHE:
        FILE_CACHE[h] = dict()
    FILE_CACHE[h][binary] = data
    return data

def run(cmd, cwd, *args, **kwargs):
    print(f"{cwd}$ {shlex.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True, *args, **kwargs)

def get_from_git(url, branch, invalidate=False):
    """get_from_git(url, branch, invalidate=False): Clone a Git repository.

    Args:
      - url: str, the URL of the repository
      - branch: str, the branch to fetch from
      - invalidate: bool, optional (default: False), force pull

    Warning: A `git reset --hard` is done first to avoid conflicts. This may
    lose data.

    Return: str, a path to the root of the repository.
    """
    basename = os.path.basename(url)
    if basename.endswith(".git"):
        basename = basename[:-4]
    cached_path = os.path.join(CACHE_DIR, basename)
    if basename in WARM_REPOS:
        return cached_path
    reason = None
    clone_or_pull = None
    if not os.path.isdir(cached_path):
        reason = "not in cache"
        clone_or_pull = "clone"

    if clone_or_pull is None and invalidate:
        reason = "forced invalidation"
        clone_or_pull = "pull"
    if (clone_or_pull is None
        and _is_too_old(os.path.join(cached_path, ".git", "FETCH_HEAD"))):
        reason = "cache too old"
        clone_or_pull = "pull"

    if clone_or_pull == "clone":
        print(f"{basename}.git: Cloning ({reason})")
        os.makedirs(CACHE_DIR, exist_ok=True)
        run(["git", "clone",
             "--branch", branch,
             "--depth", "1",
             url], CACHE_DIR)
        run(["git", "pull", "--depth", "1"], cached_path) # create FETCH_HEAD
    elif clone_or_pull == "pull":
        print(f"{basename}.git: Pulling ({reason})")
        run(["git", "reset", "--hard"], cached_path)
        run(["git", "switch", "--force", branch], cached_path)
        run(["git", "pull", "--depth", "1"], cached_path)
    else:
        print(f"{basename}.git: Using cache")
        #run(["git", "reset", "--hard"], cached_path)
        #run(["git", "switch", "--force", branch], cached_path)
    WARM_REPOS.add(basename)
    return cached_path

def get_from_github(project, branch, invalidate=False):
    """get_from_github(project, branch, invalidate=False): Clone a Git
      repository.

    Args:
      - project: str, the name of the GitHub project
      - branch: str, the branch to fetch from
      - invalidate: bool, optional (default: False), force pull

    Warning: A `git reset --hard` is done first to avoid conflicts. This may
    lose data.

    Return: str, a path to the root of the repository.
    """
    url = urllib.parse.urljoin(GIT_GITHUB_URL, project + ".git")
    return get_from_git(url, branch, invalidate)
