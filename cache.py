"""
cache.py: Caching utilities.
"""

import datetime
import hashlib
import os
import os.path
import shlex
import shutil
import subprocess
import urllib.parse
import urllib.request

CACHE_DIR="./.cache"
CACHE_TIMEOUT=datetime.timedelta(days=1)
CACHE_BUILD="_build"
CACHE_INSTALL="_install"

RAW_GITHUB_HOST="raw.githubusercontent.com"
RAW_GITHUB_URL="https://"+RAW_GITHUB_HOST

GIT_GITHUB_HOST="github.com"
GIT_GITHUB_URL="https://"+GIT_GITHUB_HOST

GITHUB_LINUX_PROJECT="torvalds/linux"

# Runtime file cache
FILE_CACHE = dict()

WARM_REPOS = set()

def _mkdir():
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, "CACHEDIR.TAG"), "w") as f:
            f.write("Signature: 8a477f597d28d172789f06886806bc55")

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
        _mkdir()
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
        _mkdir()
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

def configure(root, invalidate=False, configure_args=None):
    """configure(root, invalidate, configure_args): Configure a build.

    Args:
      - root: str, the root of the project to configure
      - invalidate: bool, optional (default: False), force reconfigure
      - configure_args: list of str, optional (default: []), additional
          arguments to the "configure" script
    """
    project = os.path.basename(root)
    build_dir = os.path.join(root, CACHE_BUILD)
    install_dir = os.path.join(root, CACHE_INSTALL)

    reason = None
    if not os.path.isdir(build_dir):
        reason = "not in cache"
    if reason is None and invalidate:
        reason = "forced invalidation"
    if reason is None and _is_too_old(build_dir):
        reason = "cache too old"
    if reason is None:
        return
    print(f"{project}: Configuring ({reason})")

    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    if os.path.isdir(install_dir):
        shutil.rmtree(install_dir)
    os.mkdir(build_dir)
    configure_cmd = ["../configure", "--prefix", os.path.abspath(install_dir)]
    if configure_args:
        configure_cmd.extend(configure_args)
    run(configure_cmd, build_dir)

def make(root, target=None, invalidate=False, make_args=None):
    """make(root, target, invalidate, make_args): Do a build.

    Args:
      - root: str, the root of the project to configure
      - target: str, optional, the target to make
      - invalidate: bool, optional (default: False), force rebuild
      - make_args: list of str, optional (default: []), additional arguments to
          "make"

    The target should be one that installs files.

    Return: str, the path to the install directory.
    """
    project = os.path.basename(root)
    build_dir = os.path.join(root, CACHE_BUILD)
    install_dir = os.path.join(root, CACHE_INSTALL)

    reason = None
    if not os.path.isdir(install_dir):
        reason = "not in cache"
    if reason is None and invalidate:
        reason = "forced invalidation"
    if reason is None and _is_too_old(install_dir):
        reason = "cache too old"
    if reason is None:
        return install_dir
    print(f"{project}: Making ({reason})")

    if os.path.isdir(install_dir):
        shutil.rmtree(install_dir)
    make_cmd = ["make"]
    if target:
        make_cmd.append(target)
    if make_args:
        make_cmd.extend(make_args)
    run(make_cmd, build_dir)
    return install_dir
