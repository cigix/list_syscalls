# `list_syscalls`: Get a programmatic description of Linux x86\_64 syscalls

This project aims at automating the description of Linux x86\_64 syscalls for
use in other programs. Currently, the program builds a C array and a HTML table,
but other languages could be adapted.

This project is meant as an extension to, and was heavily inspired by, Filippo
Valsorda's
[Searchable Linux Syscall Table](https://filippo.io/linux-syscall-table/).

## How to use

Run (Internet connection required):
```bash
$ ./list_syscalls.py [-s <SOURCES>] [-f <FORMATS>]
```

This will fetch resources based on the SOURCES parameter, and create files based
on the FORMATS parameter. See `./list_syscalls.py --help` for more info.

The ability to connect to the Internet is required by the live retrieval and
building of files from the sources, including a mandatory one. The files are
then cached for subsequent runs, for up to 24 hours.

## What is the issue exactly?

For multiple reasons, no single source describes Linux syscalls:
* They exist at a boundary between kernel and userspace, there is no need for
  them to be described uniformly across that boundary.
* They are not restricted to being called from C code, there is no need to
  describe their interface in C.
* Their calling convention is different from regular C functions, so most use of
  them in C is actually done through wrappers, which are usually part of your
  libc.

Some notable sources for syscall information, and how many are actually
described (at the time of writing):
* Linux'
  [`arch/x86/entry/syscalls/syscall_64.tbl`](https://github.com/torvalds/linux/blob/v6.7/arch/x86/entry/syscalls/syscall_64.tbl)
  lists all the syscalls by name and ties them to their number and entry point
  function, but does not list parameters or return values. (409 syscalls, 373
  for x86\_64)
* Linux'
  [`include/linux/syscalls.h`](https://github.com/torvalds/linux/blob/master/include/linux/syscalls.h)
  references a lot of the entry point functions and their parameters, but not
  return values. This file is complemented by
  [`include/asm-generic/syscalls.h`](https://github.com/torvalds/linux/blob/master/include/asm-generic/syscalls.h). (456 entry point functions, with some duplicates)
* Linux' `/usr/include/asm/unistd_64.h` (build artefact generated from
  `syscall_64.tbl`, should also be provided with your distribution) provides
  macros for all the available syscalls on a given system, but that is only for
  the syscall number. (368 syscalls on my machine)
* The [GNU C Library](https://www.gnu.org/software/libc/) has `syscalls.list`s,
  from which the wrappers are generated, but they are very terse regarding
  parameters and return values. (188 syscalls)
* libcs also have headers that describe the wrappers, but they are neither
  centralised nor described in a central place.
* The [Linux man-pages](https://www.kernel.org/doc/man-pages/index.html) provide
  documentation for syscalls wrappers in section 2, but they are loosely
  formatted. (502 entries, not all for x86\_64)

## Current implementation

The current implementation uses the following data sources on syscalls:
* [Linux' `arch/x86/entry/syscalls/syscall_64.tbl`](https://github.com/torvalds/linux/blob/master/arch/x86/entry/syscalls/syscall_64.tbl) (mandatory),
* [Linux' `include/linux/syscalls.h`](https://github.com/torvalds/linux/blob/master/include/linux/syscalls.h) (optional),
* [Linux' `include/asm-generic/syscalls.h`](https://github.com/torvalds/linux/blob/master/include/asm-generic/syscalls.h) (optional),
* [man-pages' `man2/`](https://git.kernel.org/pub/scm/docs/man-pages/man-pages.git/tree/man2) (optional),
* [musl](https://musl.libc.org/) (optional),
* [glibc](https://sourceware.org/glibc/) (optional, requires a build),

all fetched at runtime from branch `master` on their respective repository.

The current implementation can output C arrays and structures, and a HTML table.
