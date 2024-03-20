#!/usr/bin/env python3

import urllib.request
import re

LINUX_URL="https://raw.githubusercontent.com/torvalds/linux/master/include/linux/syscalls.h"

with urllib.request.urlopen(LINUX_URL) as response:
    header = response.read().decode()

SPACERE = re.compile(r"\s+", re.S)
COMMARE = re.compile(r"\s*,\s*")
STARRE = re.compile(r"\*(\w)")
DECLRE = re.compile(r'''
                    asmlinkage
                    \s
                    [^;]*?
                    \s
                    sys_\w+
                    \(
                    [^)]*
                    \)
                    ;
                    ''',
                    re.X | re.S)
PARTSRE = re.compile(r"asmlinkage\s(.*)\ssys_(\w+)\(([^)]*)\)")
NRRE = re.compile(r"\b__NR_(\w+)\b")

syscall_decl = dict()
for match in DECLRE.finditer(header):
    decl = SPACERE.sub(" ", match.group())
    parts = PARTSRE.search(decl).groups()
    syscall_decl[parts[1]] = parts

syscalls_unistd = set()
with open("/usr/include/asm/unistd_64.h") as f:
    for line in f:
        if match := NRRE.search(line):
            syscalls_unistd.add(match.group(1))

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

class Type:
    def __init__(self, typequalifiers):
        if isinstance(typequalifiers, str):
            spacedstars = STARRE.sub(r"\* \1", typequalifiers)
            typequalifierlist = spacedstars.split()
        elif isinstance(typequalifiers, list):
            typequalifierlist = typequalifiers
        else:
            raise TypeError()
        self.typelist = tuple(
            filter(lambda tq: tq not in {"const", "__user"},
                   typequalifierlist))

    def __repr__(self):
        return ' '.join(self.typelist)

    def describe(self):
        description = str()
        todo = list(self.typelist)
        while todo:
            if todo[0] == "*":
                description += "P"
                todo.pop(0)
            elif todo[0] == "void":
                description += "VOID"
                todo.pop(0)
            elif todo[0] in {"struct", "enum", "union"}:
                description += "UNKNOWN"
                todo.pop(0)
                todo.pop(0)
            elif todo[0] in {"char", "short", "int", "long"}:
                description += todo.pop(0).upper()
            elif todo[0] == "unsigned":
                if len(todo) > 1 and todo[1] in {"char", "short", "int", "long"}:
                    todo.pop(0)
                    description += "U" + todo.pop(0).upper()
                else:
                    todo.pop(0)
                    description += "UINT"
            elif todo[0] == "size_t":
                description += "SIZE_T"
                todo.pop(0)
            else:
                for size in {8, 16, 32, 64}:
                    if todo[0] in {f"int{size}_t", f"__s{size}", f"s{size}"}:
                        todo.pop(0)
                        description += "I" + str(size)
                        break
                    elif todo[0] in {f"uint{size}_t", f"__u{size}", f"u{size}"}:
                        todo.pop(0)
                        description += "U" + str(size)
                        break
                else:
                    #print("Unknown:", todo[0])
                    description += "UNKNOWN"
                    todo.pop(0)
        return description

class Parameter:
    def __init__(self, identifier):
        spacedstars = STARRE.sub(r"* \1", identifier)
        splitidentifier = spacedstars.split()
        if len(splitidentifier) == 1 or splitidentifier[-1] in {"*", "int"}:
            self.name = "__unnamed"
            self.type = Type(splitidentifier)
        else:
            self.name = splitidentifier[-1]
            self.type = Type(splitidentifier[:-1])

    def __repr__(self):
        return repr(self.type) + ' ' + self.name

    def describe(self):
        return self.type.describe()

class Syscall:
    def __init__(self, returntype, name, paramlist):
        self.returntype = Type(returntype)
        self.name = name
        if not paramlist or paramlist == "void":
            self.params = list()
        else:
            self.params = [
                    Parameter(param) for param in COMMARE.split(paramlist)
                ]

    def __repr__(self):
        return (repr(self.returntype)
                + ' '
                + self.name
                + '('
                + ', '.join(map(repr, self.params))
                + ')')

    def describe(self):
        return (self.name,
                self.returntype.describe(),
                tuple(map(Parameter.describe, self.params)))

syscalls = [
        Syscall(*syscall_decl[syscall])
        for syscall in syscall_decl.keys() & syscalls_unistd
    ]

for syscall in syscalls:
    t = syscall.returntype.describe()
    if t not in types:
        types.append(t)
    for parameter in syscall.params:
        t = parameter.type.describe()
        if t not in types:
            types.append(t)

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

with open("syscalls.c", "w") as f:
    f.write(f"""#include "syscalls.h"

#include <stddef.h>
#include <sys/syscall.h>

struct syscall_entry syscalls[{len(syscalls) + 1}] =
{{
""")
    for syscall in syscalls:
        f.write(f"  {{SYS_{syscall.name}, "
                + f'"{syscall.name}", '
                + f"{len(syscall.params)}, "
                + f"{syscall.returntype.describe()}, "
                + "{"
                + ", ".join([param.describe() for param in syscall.params]
                            + ["NONE"] * (6 - len(syscall.params)))
                + "}},\n")
    f.write("""  {-1, NULL, 6, UNKNOWN, {UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN}}
};
""")
