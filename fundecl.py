#!/usr/bin/env python3

"""
fundecl.py: Simple parser for C function definitions.
"""

import re

import typedecl
import syscall_tbl
import syscalls_h

FUNDECLRE = re.compile(r"([^;]+)\(([^)]*)\);?", re.S)

class FunDecl:
    """FunDecl: A C function declaration."""
    def __init__(self, decl):
        match = FUNDECLRE.fullmatch(decl)
        if match is None:
            raise ValueError(f"Not a valid C function declaration: {decl}")

        try:
            left_part = typedecl.TypeDecl(match.group(1))
            self.param_list = [
                typedecl.TypeDecl(paramdecl)
                for paramdecl in match.group(2).split(',')
            ]
        except ValueError as e:
            raise ValueError(f"Not a valid C function declaration: {decl}\n"
                             + e.args[0])

        if left_part.identifier is None:
            raise ValueError(f"Not a valid C function declaration: {decl}")

        self.name = repr(left_part.identifier)
        self.return_type = left_part
        self.return_type.identifier = None

        if (len(self.param_list) == 1
            and len(self.param_list[0].typespec) == 1
            and isinstance(self.param_list[0].typespec[0],
                           typedecl.TypeSpecifier)
            and self.param_list[0].typespec[0].tokens == ["void"]):
            self.param_list = list()

    def __repr__(self):
        return (f"{self.return_type} {self.name}("
                + ", ".join(map(repr, self.param_list)) + ')')

def _main():
    syscall_tbl_entries = syscall_tbl.get_x86_64_list()
    entrypoints = [e.entrypoint for e in syscall_tbl_entries if e.entrypoint]
    for entrypoint in entrypoints:
        for decl in syscalls_h.find_decls(entrypoint):
            fundecl = FunDecl(decl)
            print(fundecl)

if __name__ == "__main__":
    _main()
