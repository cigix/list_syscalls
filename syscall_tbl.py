#!/usr/bin/env python3

"""
syscall_tbl.py: Utilities around Linux'
`arch/x86/entry/syscalls/syscall_64.tbl`.
"""

import cache

def _get():
    return cache.get_file_from_github(cache.GITHUB_LINUX_PROJECT, "master",
                                      "arch/x86/entry/syscalls/syscall_64.tbl")

def warm():
    """warm(): Warm up the cache for this module."""
    _ = _get()

class SyscallTblEntry:
    """SyscallTblEntry: An entry of `syscall_64.tbl`.

    Attributes:
      - number: int, the syscall number
      - abi: str, the syscall's ABI ("common", "64", or "x32")
      - name: str, the syscall's name (for userspace applications)
      - entrypoint: str, the syscall's entrypoint in the kernel, may be the
          empty string
    """
    def __init__(self, line):
        tokens = line.split()
        self.number = int(tokens[0])
        self.abi = tokens[1]
        self.name = tokens[2]
        self.entrypoint = tokens[3] if 3 < len(tokens) else str()

def get_list():
    """get_list(): Get all the entries of `syscall_64.tbl`.

    Return: list of SyscallTblEntry.
    """
    return [
        SyscallTblEntry(line)
        for line in _get().splitlines()
        if line and line[0] != '#'
    ]

def get_x86_64_list():
    """get_x86_64_list(): Get all the x86_64 entries of `syscall_64.tbl`.

    Similar to get_list(), but only return the entries that have ABI "common" or
    "64".

    Return: list of SyscallTblEntry.
    """
    return [
        entry
        for entry in get_list()
        if entry.abi in ("common", "64")
    ]

def _main():
    l = get_x86_64_list()
    print(f"syscall_64.tbl: {len(l)} x86_64 syscalls:")
    for entry in l:
        print(entry.name)

if __name__ == "__main__":
    _main()
