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
    """FunDecl: A C function declaration.

    Attributes:
      - name: str, the name of the function
      - return_type: TypeDecl, the return type of the function
      - param_list: list of TypeDecl, the parameters of the function, possibly
          empty
    """
    def __init__(self, name, return_type, param_list):
        self.name = name
        self.return_type = return_type
        self.param_list = param_list

    def __repr__(self):
        return (f"{self.return_type} {self.name}("
                + ", ".join(map(repr, self.param_list)) + ')')

class SysFunDecl(FunDecl):
    """SysFunDecl(FunDecl): A syscall function declaration.

    Attributes are the same as FunDecl, however the function should be stylized
    as: `{return_value} syscall(SYS_{name}[, {param_list}...])`.
    """
    def __repr__(self):
        params = [f"SYS_{self.name}"] + list(map(repr, self.param_list))
        return f"{self.return_type} syscall(" + ", ".join(params) + ')'

def parse(decl):
    """parse(decl): Parse a function declaration.

    Args:
      - decl: str, the function declaration

    Return: instance of FunDecl.
    """
    match = FUNDECLRE.fullmatch(decl)
    if match is None:
        raise ValueError(f"Not a valid C function declaration: {decl}")

    # Separate return type + name from params; parse params
    try:
        left_part = typedecl.TypeDecl(match.group(1))
        param_list = [
            typedecl.TypeDecl(paramdecl)
            for paramdecl in match.group(2).split(',')
        ]
    except ValueError as e:
        raise ValueError(f"Not a valid C function declaration: {decl}\n"
                         + e.args[0])

    # Separate return type from name
    if left_part.identifier is None:
        raise ValueError(f"Not a valid C function declaration: {decl}")
    name = left_part.identifier.tokens[0]
    return_type = left_part
    return_type.identifier = None

    # If param_list is ["void"] -> empty param_list
    if (len(param_list) == 1
        and len(param_list[0].typespec) == 1
        and isinstance(param_list[0].typespec[0], typedecl.TypeSpecifier)
        and param_list[0].typespec[0].tokens == ["void"]):
        param_list = list()

    # Check that only the last parameter could be an ellipsis
    for param in param_list[:-1]:
        if (len(param.typespec) == 1
            and isinstance(param.typespec[0], typedecl.CEllipsis)):
            raise ValueError(f"Not a valid C function declaration: {decl}")

    # Check that only the first parameter could be a SYS_* constant
    for param in param_list[1:]:
        if (len(param.typespec) == 1
            and isinstance(param.typespec[0], typedecl.SYSConstant)):
            raise ValueError(f"Not a valid C function declaration: {decl}")

    is_syscall = name == "syscall"
    has_sys_constant = (len(param_list) > 0
                        and len(param_list[0].typespec) == 1
                        and isinstance(param_list[0].typespec[0],
                                       typedecl.SYSConstant))
    # Check that they are either both false or both true
    if is_syscall != has_sys_constant:
        raise ValueError(f"Not a valid C function declaration: {decl}")

    if is_syscall:
        return SysFunDecl(param_list[0].typespec[0].tokens[0][4:],
                          return_type, param_list[1:])
    return FunDecl(name, return_type, param_list)

def _main():
    syscall_tbl_entries = syscall_tbl.get_x86_64_list()
    entrypoints = [e.entrypoint for e in syscall_tbl_entries if e.entrypoint]
    for entrypoint in entrypoints:
        for decl in syscalls_h.find_decls(entrypoint):
            print(parse(decl))

if __name__ == "__main__":
    _main()
