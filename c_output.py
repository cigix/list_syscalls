#!/usr/bin/env python3

"""
c_output.py: Utilities to output the list of syscalls as C.
"""

import fundecl
import typedecl
import syscall_tbl
import syscalls_h

SPECIAL_NAMES = {
    "argv": ("CHAR_PP", "ARGV"),
    "envp": ("CHAR_PP", "ENVP")
}

SPECIAL_INTS = {
    "size_t": "SIZE_T",
    "ssize_t": "SSIZE_T"
}
for size in (8, 16, 32, 64):
    SPECIAL_INTS[f"int{size}_t"] = f"INT{size}"
    SPECIAL_INTS[f"s{size}"] = f"INT{size}"
    SPECIAL_INTS[f"__s{size}"] = f"INT{size}"
    SPECIAL_INTS[f"uint{size}_t"] = f"UINT{size}"
    SPECIAL_INTS[f"u{size}"] = f"UINT{size}"
    SPECIAL_INTS[f"__u{size}"] = f"UINT{size}"

def simplify(decl):
    """simplify(decl): Simplify a C type specification.

    Args:
      - decl: typedecl.TypeDecl, the type specification

    Return: str, the simplified type.

    Turn a specification into a simplified string, for example:
      simplify(TypeDecl("const char * const *")) == "CHAR_PP"
    If the TypeDecl has a matching typespec and identifier, it may be given a
    more specific string:
      simplify(TypeDecl("const char * const * argv")) == "ARGV"
    """
    # Remove qualifiers and the eventual identifier
    clean = list(filter(lambda part: isinstance(part, typedecl.TypeSpecifier)
                                     or isinstance(part, typedecl.Pointer),
                        decl.typespec))
    # At this point, we should have some TypeSpecifiers (at least 1), then some
    # Pointers (possibly 0).
    pointercount = 0
    while isinstance(clean[-1 - pointercount], typedecl.Pointer):
        pointercount += 1
    if 0 < pointercount:
        spec = clean[:-pointercount]
    else:
        spec = clean

    if spec[0].tokens[0] in typedecl.TAG_SPECIFIERS:
        # struct, union, or enum
        assert len(spec) == 1, "remaining specifiers after struct/union/enum"
        simplified = "UNKNOWN" # Not supported
    elif spec[0].tokens[0] in SPECIAL_INTS.keys():
        assert len(spec) == 1, "remaining specifiers after integer typedef"
        simplified = SPECIAL_INTS[spec[0].tokens[0]]
    elif (typedecl.TYPE_SPECIFIERS_EXTRA_RE.fullmatch(spec[0].tokens[0])
          or spec[0].tokens[0] in typedecl.TYPE_SPECIFIERS_EXTRA):
        assert len(spec) == 1, "remaining specifiers after typedef"
        simplified = "UNKNOWN" # Not supported
    elif spec[0].tokens[0] == "void":
        assert len(spec) == 1, "remaining specifiers after void"
        assert pointercount > 0, "void specifier without pointer"
        simplified = "VOID"
    else:
        # integral type
        base = None
        signedness = None
        size = None

        for token in spec[0].tokens:
            match token:
                case "char" | "int":
                    assert base is None, "multiple integer specifiers"
                    base = token
                case "signed" | "unsigned":
                    assert signedness is None, "multiple sign specifiers"
                    signedness = token
                case "short":
                    assert size is None, (
                            "multiple size specifiers with \"short\"")
                    assert base is None, (
                            "size specifier after integer specifier")
                    size = "short"
                case "long":
                    assert base is None, (
                            "size specifier after integer specifier")
                    if size is None:
                        size = "long"
                    else:
                        assert size == "long", (
                                "multiple size specifiers with \"long\"")
                        size = "longlong"
                case _:
                    raise ValueError("Unknown token: " + token)

        sign = ""
        if signedness:
            sign = "U" if signedness == "unsigned" else "S"
        if base is None:
            base = "int"

        if base == "char":
            assert size is None, "size specifier with \"char\""
            simplified = sign + "CHAR"
        else: # base == "int"
            if size is None:
                simplified = sign + "INT"
            else:
                simplified = sign + size.upper()

    if 0 < pointercount:
        if simplified == "UNKNOWN":
            # It does not matter the amount of indirection
            simplified += "_P"
        else:
            simplified += '_' + 'P' * pointercount

    if decl.identifier is not None:
        if decl.identifier.tokens[0] in SPECIAL_NAMES.keys():
            if simplified == SPECIAL_NAMES[decl.identifier.tokens[0]][0]:
                simplified = SPECIAL_NAMES[decl.identifier.tokens[0]][1]

    return simplified

def dump(syscalls):
    """dump(syscalls): Dump the syscalls' data to C files.

    Args:
      - syscalls: list of tuple (SyscallTblEntry, FunDecl), the data about
          each syscall

    Create two files, syscalls.h and syscalls.c, which contain declarations and
    definitions describing each syscall programmatically.
    """
    types = [
        "NONE",
        "UNKNOWN",
        "VOID",
        "CHAR",
        "UCHAR",
        "SHORT",
        "USHORT",
        "INT",
        "UINT",
        "LONG",
        "ULONG",
        "I8", "I16", "I32", "I64",
        "U8", "U16", "U32", "U64",
        "SIZE_T"
    ]
    with open("syscalls.c", "w") as f:
        f.write(f"""#include "syscalls.h"

#include <stddef.h>

struct syscall_entry syscalls[{len(syscalls) + 1}] =
{{
""")
        for entry, decl in syscalls:
            f.write("  // ")
            f.write(repr(decl).replace(entry.entrypoint, entry.name))
            f.write(";\n")
            f.write(f"  {{{entry.number}, ")
            f.write('"' + entry.name + '", ')
            f.write(str(len(decl.param_list)) + ", ")
            t = simplify(decl.return_type)
            if t not in types:
                types.append(t)
            f.write(t + ", ")
            ps = list()
            for param in decl.param_list:
                t = simplify(param)
                if t not in types:
                    types.append(t)
                ps.append(t)
            ps += ["NONE"] * (6 - len(decl.param_list))
            f.write("{" + ", ".join(ps) + "}},\n")
        f.write("""  {-1, NULL, 6, UNKNOWN, {UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN}}
};
""")

    with open("syscalls.h", "w") as f:
        f.write(f"""#pragma once

enum TYPE
{{
  {''',
  '''.join(types)}
}};

struct syscall_entry
{{
  int nr;
  const char *name;
  int argc;
  enum TYPE retval;
  enum TYPE args[6];
}};

extern struct syscall_entry syscalls[{len(syscalls) + 1}];
""")

def _main():
    for syscall in syscall_tbl.get_x86_64_list():
        if syscall.entrypoint:
            for decl in syscalls_h.find_decls(syscall.entrypoint):
                f = fundecl.FunDecl(decl)
                print(simplify(f.return_type), end='')
                print(" ", end='')
                print(syscall.name, end='')
                print("(", end='')
                print(", ".join(map(simplify, f.param_list)), end='')
                print(")")

if __name__ == "__main__":
    _main()
