#!/usr/bin/env python3

import collections
import sys

import c_output
import fundecl
import manpages
import syscall_tbl
import syscalls_h

SyscallDecl = collections.namedtuple("SyscallDecl", ["decl", "origin"])

class SyscallDesc:
    """SyscallDesc: The description of a syscall.

    Attributes:
      - entry: SyscallTblEntry, the syscall_tbl entry
      - decls: list of SyscallDecl, the function declarations that were found
          for that syscall, possibly empty
    """
    def __init__(self, entry, decls):
        self.entry = entry
        self.decls = decls

def main(argv):
    manpages.warm()
    syscall_tbl.warm()
    syscalls_h.warm()
    print()

    syscall_tbl_entries = syscall_tbl.get_x86_64_list()
    syscalls = list()
    count_entrypoint = 0
    for entry in syscall_tbl_entries:
        decls = list()

        if entry.entrypoint:
            for decl in syscalls_h.find_decls(entry.entrypoint):
                decls.append(SyscallDecl(fundecl.parse(decl),
                                         "Linux' syscalls.h"))

        if decl := manpages.get_decl(entry.name):
            decls.append(SyscallDecl(decl, "man pages"))

        syscalls.append(SyscallDesc(entry, decls))

    c_output.dump(syscalls)

    origins = {
            "not found": 0,
            "Linux' syscalls.h": 0,
            "man pages": 0
        }
    for desc in syscalls:
        if not desc.decls:
            origin = "not found"
        else:
            origin = desc.decls[-1].origin
        origins[origin] += 1

    print()
    print(f"{len(syscall_tbl_entries)} x86_64 syscalls listed in syscall_tbl:")
    print(f"  - {origins['man pages']} found in man pages,")
    print(f"""  - {origins["Linux' syscalls.h"]} found in Linux' syscalls.h,""")
    print(f"  - {origins['not found']} not found.")
    print(f"{len(syscall_tbl_entries) - origins['not found']} declarations "
          "found and dumped in \"syscalls.h\" and \"syscalls.c\".")

if __name__ == '__main__':
    exit(main(sys.argv))
