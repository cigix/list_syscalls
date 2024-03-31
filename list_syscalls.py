#!/usr/bin/env python3

import collections
import sys

import c_output
import fundecl
import glibc
import html_output
import manpages
import musl
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

ALL_SOURCES=("linux", "man", "musl", "glibc")
ALL_FORMATS=("c", "html")

SOURCE_NAME={
        "linux": "Linux' syscalls.h",
        "man": "man pages",
        "musl": "musl libc",
        "glibc": "GNU libc"
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

About sources:
  linux: Linux' `syscalls.h` headers. Provides declarations for the kernel-side
         entrypoints.
         Good quality: exhaustive, lacks return values.
  man:   Linux `man-pages` project. Provides high-level descriptions on how a
         syscall should be called assuming the presence of a libc.
         High quality: exhaustive, sometimes too detailed for our simple parser.
  musl:  musl libc. Provides simple declarations for the libc wrappers.
         Low quality: minimal, lacks parameter names.
  glibc: GNU libc. Provides declarations for the libc wrappers.
         Low quality: bad coverage, often declarations are too complex for our
         simple parser.

  Not all sources are guaranteed to provide the same, or even compatible,
  declarations, or even a declaration at all for each syscall.

  If multiple declarations appear for one syscall (either because multiple
  sources were used, and/or one source produced multiple declarations), they are
  fed in command line order to the formatters.

About formats:
  c:     Describe the syscalls with a C array of structures, one declaration per
         syscall (the last one provided by the sources).
  html:  Describe the syscalls with an HTML table. All declarations are used.

  When using an output format that can only describe one declaration, we
  recommend sticking to high quality sources.
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

    syscall_tbl.warm()
    if "linux" in sources:
        syscalls_h.warm()
    if "man" in sources:
        manpages.warm()
    if "musl" in sources:
        musl.warm()
    if "glibc" in sources:
        glibc.warm()
    print()

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
                case "musl":
                    for header in manpages.get_headers(entry.name):
                        for decl in musl.find_decls(entry.name, header):
                            decls.append(SyscallDecl(decl, SOURCE_NAME["musl"]))
                case "glibc":
                    for header in manpages.get_headers(entry.name):
                        for decl in glibc.find_decls(entry.name, header):
                            decls.append(
                                    SyscallDecl(decl, SOURCE_NAME["glibc"]))
        descs.append(SyscallDesc(entry, decls))

    if "c" in formats:
        c_output.dump(descs)
    if "html" in formats:
        html_output.dump(descs)

    origins = dict()
    lastorigins = dict()
    not_found = 0
    for desc in descs:
        if not desc.decls:
            not_found += 1
        else:
            for origin in {decl.origin for decl in desc.decls}:
                origins.setdefault(origin, 0)
                origins[origin] += 1
            lastorigin = desc.decls[-1].origin
            lastorigins.setdefault(lastorigin, 0)
            lastorigins[lastorigin] += 1

    print()
    print(f"{len(entries)} x86_64 syscalls listed in syscall_tbl:")
    for source in reversed(sources):
        name = SOURCE_NAME[source]
        if name in origins:
            print(f"  - {origins[name]}({lastorigins.get(name, 0)}) "
                  f"declarations found in {name},")
    print(f"  - {not_found} not found anywhere.")
    print(f"{len(entries) - not_found} declarations dumped in:")
    for f in formats:
        print(f"  - {' and '.join(FORMAT_FILES[f])}")

if __name__ == '__main__':
    exit(main(sys.argv))
