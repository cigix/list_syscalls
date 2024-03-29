#!/usr/bin/env python3

"""
manpages.py: Utilities around Linux man-pages.
"""

import os.path
import re

import cache
import fundecl
import syscall_tbl

MAN_PAGES_REPOSITORY="git://git.kernel.org/pub/scm/docs/man-pages/man-pages.git"

SORE = re.compile(r"\.so (man\w+/\w+\.\d\w*)\n")
FUNCREFMT = r"\.BI?\s([^;\n]+?{}\s*\((?:[^);]*|[^);]*\([^);]*\)[^);]*)\);)"
SYSCALLREFMT = r"\.BI?\s([^;\n]+syscall\s*\(SYS_{}[^);]*\);)"
BIRE = re.compile(r"^\.BI?\s", re.M)
FORMATRE = re.compile(r"\\f.")
COMMENTRE = re.compile(r"/\*.*?\*/")
SIZERE = re.compile(r"(\w+)\s*\[.*?\]", re.M)

def _get():
    return cache.get_from_git(MAN_PAGES_REPOSITORY, "master")

def warm():
    """warm(): Warm up the cache for this module."""
    _ = _get()


def _file(syscall):
    root = _get()
    def _sofile(path):
        path = os.path.join(root, path)
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            content = f.read()
        if match := SORE.match(content):
            return _sofile(match.group(1))
        return content
    return _sofile(os.path.join("man2", syscall + ".2"))

def _remove(string, filters):
    f = filters.pop(0)
    if isinstance(f, str):
        string = string.replace(f, "")
    else: # f is a re.Pattern
        string = f.sub("", string)
    if filters:
        return _remove(string, filters)
    return string

def get_decl(syscall):
    """get_decl(syscall): Get a declaration out of a man-page entry.

    Args:
      - syscall: str, the name of the syscall to find

    Return: FunDecl or None, the declaration if it was found.
    """
    content = _file(syscall)
    if content is None:
        return None

    funcre = FUNCREFMT.format(syscall)
    if m := re.search(funcre, content, re.M):
        decl = _remove(m.group(1),
                       [BIRE, '"', FORMATRE, '\n', '\\', COMMENTRE])
        decl = SIZERE.sub(r"*\1", decl)
        return fundecl.parse(decl)

    syscallre = SYSCALLREFMT.format(syscall)
    if m := re.search(syscallre, content, re.M):
        decl = _remove(m.group(1),
                       [BIRE, '"', FORMATRE, '\n', '\\', COMMENTRE])
        decl = SIZERE.sub(r"*\1", decl)
        return fundecl.parse(decl)

    return None

def _main():
    for syscall in syscall_tbl.get_list():
        if decl := get_decl(syscall.name):
            print(decl)
        else:
            print(f"no declaration found for {syscall.name}")

if __name__ == "__main__":
    _main()
