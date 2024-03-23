#!/usr/bin/env python3

import sys

import c_output
import fundecl
import syscall_tbl
import syscalls_h

def main(argv):
    syscall_tbl.warm()
    syscalls_h.warm()
    print()

    syscall_tbl_entries = syscall_tbl.get_x86_64_list()
    syscalls = list()
    count_entrypoint = 0
    for entry in syscall_tbl_entries:
        if not entry.entrypoint:
            continue
        count_entrypoint += 1
        decls = syscalls_h.find_decls(entry.entrypoint)
        if len(decls) == 0:
            print("No declaration found for", entry.name, file=sys.stderr)
            continue
        elif 1 < len(decls):
            print(f"{len(decls)} declarations found for {entry.name}, keeping "
                  "the last one", file=sys.stderr)
            decl = decls[-1]
        else:
            decl = decls[0]
        syscalls.append((entry, fundecl.FunDecl(decl)))
    
    c_output.dump(syscalls)

    print()
    print(f"{len(syscall_tbl_entries)} x86_64 syscalls listed in syscall_tbl,")
    print(f"{count_entrypoint} of those have an entrypoint listed,")
    print(f"{len(syscalls)} declarations found and dumped in \"syscalls.h\" "
          "and \"syscalls.c\".")

if __name__ == '__main__':
    exit(main(sys.argv))
