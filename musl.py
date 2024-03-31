#!/usr/bin/env python3

"""
libc.py: Utilities around libCs.
"""

import os.path
import re

import cache
import fundecl
import manpages
import syscall_tbl

LIBC_REPOSITORY="git://git.musl-libc.org/musl"

BACKSLASHLFRE = re.compile(r"\\\n")
PREPROCRE = re.compile(r"^\s*#.*$", re.M)
FUNCREFMT = r"[^;{{]+(?:\s|\*){}\s*\(.*?\)\s*;"

def _get():
    return cache.get_from_git(LIBC_REPOSITORY, "master")

def warm():
    """warm(): Warm up the cache for this module."""
    _ = _get()

# Runtime "preprocessed" file cache
_filecache = dict()
def _file(header):
    if header in _filecache:
        return _filecache[header]

    root = _get()
    path = os.path.join(root, "include", header)
    if not os.path.isfile(path):
        _filecache[header] = None
        return None

    with open(path) as f:
        content = f.read()
    content = BACKSLASHLFRE.sub("", content)
    content = PREPROCRE.sub("", content)

    _filecache[header] = content
    return content

def find_decls(syscall, header):
    """find_decls(syscall, header): Get syscall wrapper declarations from libC.

    Args:
      - syscall: str, the name of the wrapper
      - header: str, the name of the libC header (e.g. "sys/stat.h")

    Return: set of FunDecl, the found declarations, possibly empty.
    """
    content = _file(header)
    if content is None:
        return set()

    funcre = FUNCREFMT.format(syscall)
    ret = set()
    for decl in re.findall(funcre, content):
        decl = manpages.SIZERE.sub(r"\1*", decl).strip()
        try:
            ret.add(fundecl.parse(decl))
        except ValueError as e:
            # Some declarations cannot be parsed by our simple parser, like
            # clone(2)
            pass
    return ret

def _main():
    for syscall in syscall_tbl.get_list():
        for header in manpages.get_headers(syscall.name):
            for decl in find_decls(syscall.name, header):
                print(decl)

if __name__ == "__main__":
    _main()
