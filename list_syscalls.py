#!/usr/bin/env python3

import collections
import sys

import c_output
import fundecl
import html_output
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

ALL_SOURCES=("linux", "man")
ALL_FORMATS=("c", "html")

SOURCE_NAME={
        "linux": "Linux' syscalls.h",
        "man": "man pages"
    }
FORMAT_FILES={
        "c": ("syscalls.h", "syscalls.c"),
        "html": ("syscalls.html",)
    }

def main(argv):
    if {"-h", "-help", "--help"} & set(argv[1:]):
        print(f"""Usage: {argv[0]} [options...]

Options:
    -s SOURCES  Specify the sources to get data from, comma separated.
                Valid sources: {", ".join(ALL_SOURCES)}
                Default: all
    -f FORMATS  Specify the formats to output as, comma separated.
                Valid formats: {", ".join(ALL_FORMATS)}
                Default: all
""")
        return 0

    try:
        sindex = argv.index("-s")
    except ValueError:
        sindex = -1
    if sindex == len(argv) - 1:
        print("ERROR: -s requires a parameter", file=sys.stderr)
        return 1
    if sindex == -1:
        sources = ALL_SOURCES
    else:
        sources = [
                arg.strip().lower()
                for arg in argv[sindex + 1].split(',')
            ]
        if invalid := set(sources) - set(ALL_SOURCES):
            print(f"ERROR: Unknown sources: {' '.join(invalid)}",
                  file=sys.stderr)
            return 1

    try:
        findex = argv.index("-f")
    except ValueError:
        findex = -1
    if findex == len(argv) - 1:
        print("ERROR: -f requires a parameter", file=sys.stderr)
        return 1
    if findex == -1:
        formats = ALL_FORMATS
    else:
        formats = [
                arg.strip().lower()
                for arg in argv[findex + 1].split(',')
            ]
        if invalid := set(formats) - set(ALL_FORMATS):
            print(f"ERROR: Unknown formats: {' '.join(invalid)}",
                  file=sys.stderr)
            return 1

    entries = syscall_tbl.get_x86_64_list()
    descs = list()
    for entry in entries:
        decls = list()
        for source in sources:
            match source:
                case "linux":
                    if entry.entrypoint:
                        for decl in syscalls_h.find_decls(entry.entrypoint):
                            decls.append(SyscallDecl(fundecl.parse(decl),
                                                     SOURCE_NAME["linux"]))
                case "man":
                    if decl := manpages.get_decl(entry.name):
                        decls.append(SyscallDecl(decl, SOURCE_NAME["man"]))
        descs.append(SyscallDesc(entry, decls))

    if "c" in formats:
        c_output.dump(descs)
    if "html" in formats:
        html_output.dump(descs)

    origins = dict()
    not_found = 0
    for desc in descs:
        if not desc.decls:
            not_found += 1
        else:
            for origin in {decl.origin for decl in desc.decls}:
                if origin in origins:
                    origins[origin] += 1
                else:
                    origins[origin] = 1

    print()
    print(f"{len(entries)} x86_64 syscalls listed in syscall_tbl:")
    for source in reversed(sources):
        name = SOURCE_NAME[source]
        print(f"  - {origins[name]} declarations found in {name},")
    print(f"  - {not_found} not found anywhere.")
    print(f"{len(entries) - not_found} declarations dumped in:")
    for f in formats:
        print(f"  - {' and '.join(FORMAT_FILES[f])}")

if __name__ == '__main__':
    exit(main(sys.argv))
