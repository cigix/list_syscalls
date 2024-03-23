#!/usr/bin/env python3

"""
syscalls_h.py: Utilities around Linux' `include/linux/syscalls.h` and
`include/asm-generic/syscalls.h`.
"""

import re
import sys

import cache
import syscall_tbl

ENTRYPOINTREFMT = r"asmlinkage[^;]+{}\s*\([^);]*\);"
SPACERE = re.compile(r"\s+", re.S)
COMMARE = re.compile(r"\s*,\s*")

def _get():
    return (cache.get_file_from_github(cache.GITHUB_LINUX_PROJECT, "master",
                                       "include/linux/syscalls.h")
            + cache.get_file_from_github(cache.GITHUB_LINUX_PROJECT, "master",
                                         "include/asm-generic/syscalls.h"))

def warm():
    """warm(): Warm up the cache for this module."""
    _ = _get()

def find_decls(entrypoint):
    """find_decls(entrypoint): Get the declarations of an entrypoint.

    Args:
      - entrypoint: str, the name of the entrypoint (usually sys_...)

    Return: list of str, the found declarations for the entrypoint. May be
    empty.
    """
    header = _get()
    entrypointre = re.compile(ENTRYPOINTREFMT.format(entrypoint), re.S)
    return [
        SPACERE.sub(" ", decl)
        for decl in entrypointre.findall(header)
    ]

def _main():
    syscall_tbl_entries = syscall_tbl.get_x86_64_list()
    entrypoints = [e.entrypoint for e in syscall_tbl_entries if e.entrypoint]
    decls = list()
    for entrypoint in entrypoints:
        d = find_decls(entrypoint)
        if len(d) == 0:
            print("No declaration found for", entrypoint, file=sys.stderr)
        elif 1 < len(d):
            print(f"{len(d)} declarations found for {entrypoint}, keeping "
                  "the last one", file=sys.stderr)
            decls.append(d[-1])
        else:
            decls.append(d[0])
    print(f"syscalls.h: {len(decls)}/{len(entrypoints)} declarations found:")
    for decl in decls:
        print(decl)

if __name__ == "__main__":
    _main()
