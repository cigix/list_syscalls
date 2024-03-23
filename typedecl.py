"""
typedecl.py: Simple parser for C declarations or type specifications.
"""

import re

import clex

IGNORE_TOKEN = {
    "__user",
    "asmlinkage"
}
TYPE_SPECIFIERS_EXTRA = {
    "fd_set",
    "u32",
    "__s32",
    "u64",
    "__u32"
}
TYPE_SPECIFIERS_EXTRA_RE = re.compile(r"\w+_t")

# C17, section 6.7.2
TYPE_SPECIFIERS = {
    "void",
    "char",
    "short",
    "int",
    "long",
    "float",
    "double",
    "signed",
    "unsigned",
    "_Bool",
    "_Complex"
}
TAG_SPECIFIERS = {
    "struct",
    "union",
    "enum"
}

# C17, section 6.7.3
TYPE_QUALIFIERS = {
    "const",
    "restrict",
    "volatile",
    "_Atomic"
}

# C17, section 6.7.6
POINTER = { "*" }

# C17, section 6.4.2.1, except universal-character-name
IDENTIFIER_RE = re.compile(r"[A-Z_a-z]\w*")

class TypePart:
    """TypePart: A part of a C declaration or type specification.

    Attributes:
      - tokens: list of str, the tokens making up the part

    Static methods:
      - match(list of str) -> int: How many tokens should be part of a TypePart
          instance, 0 indicating no match for this TypePart class.
      - allowafter() -> tuple of class: What TypeParts are syntactically allowed
          after this one?
    """
    def __init__(self, tokens):
        self.tokens = tokens

    def __repr__(self):
        return ' '.join(self.tokens)

class TypeSpecifier(TypePart):
    """TypeSpecifier: A C type specifier (C17, section 6.7.2)."""
    @staticmethod
    def match(tokens):
        if (tokens[0] in (TYPE_SPECIFIERS | TYPE_SPECIFIERS_EXTRA)
            or TYPE_SPECIFIERS_EXTRA_RE.fullmatch(tokens[0])):
            return 1
        if tokens[0] in TAG_SPECIFIERS:
            return 2
        return 0

    @staticmethod
    def allowafter():
        return (TypeSpecifier, TypeQualifier, Pointer, Identifier)

class TypeQualifier(TypePart):
    """TypeQualifier: A C type qualifier (C17, section 6.7.3)."""
    @staticmethod
    def match(tokens):
        if tokens[0] in TYPE_QUALIFIERS:
            return 1
        return 0

    @staticmethod
    def allowafter():
        return (TypeSpecifier, TypeQualifier, Pointer, Identifier)

class Pointer(TypePart):
    """Pointer: A C pointer declarator (C17, section 6.7.6)."""
    @staticmethod
    def match(tokens):
        if tokens[0] in POINTER:
            return 1
        return 0

    @staticmethod
    def allowafter():
        return (TypeQualifier, Pointer, Identifier)

class Identifier(TypePart):
    """Identifier: A C identifier (C17, section 6.4.2.1)."""
    @staticmethod
    def match(tokens):
        if IDENTIFIER_RE.fullmatch(tokens[0]):
            return 1
        return 0

    @staticmethod
    def allowafter():
        return tuple()

def parse(tokens):
    """parse(tokens): Parse tokens into TypeParts.

    Args:
      - tokens: list of str, the tokens to parse

    Return: list of TypePart, the parts of the type declaration or
    specification.

    Raise ValueError if parsing fails.
    """
    next_partcls = (TypeSpecifier, TypeQualifier)
    parts = list()

    while tokens:
        if tokens[0] in IGNORE_TOKEN:
            tokens = tokens[1:]
            continue
        for partcls in next_partcls:
            if count := partcls.match(tokens):
                parts.append(partcls(tokens[:count]))
                tokens = tokens[count:]
                next_partcls = partcls.allowafter()
                break
        else:
            raise ValueError("Cannot match tokens at: " + ' '.join(tokens))

    return parts


class TypeDecl:
    """TypeDecl: A C declaration or type specification."""
    def __init__(self, decl):
        tokens = clex.clex(decl)
        try:
            parts = parse(tokens)
        except ValueError as e:
            raise ValueError("Not a valid C type specification: " + decl + '\n'
                             + e.args[0])
        if isinstance(parts[-1], Identifier):
            self.typespec = parts[:-1]
            self.identifier = parts[-1]
        else:
            self.typespec = parts
            self.identifier = None

    def __repr__(self):
        ret = ' '.join(map(repr, self.typespec))
        if self.identifier:
            ret += ' ' + repr(self.identifier)
        return ret
