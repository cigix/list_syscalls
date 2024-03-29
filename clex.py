"""
clex.py: Simple C lexer.
"""

import re

SPACERE = re.compile("\s+")
IDRE = re.compile("\w+")
OTHER_TOKENS = {
    "...",
    "[[noreturn]]",
    "[[deprecated]]"
}

def clex(text):
    """clex(text): Simple lexer for C code.

    Args:
      - text: str, the text to lex

    This is a simple lexer, that only separates runs of [[:alnum:]_] from spaces
    and other symbols. Especially, it will separate tokens that are usually
    multiple symbols, like "+=".

    Return: list of str, the tokens.
    """
    tokens = list()
    while text:
        if match := SPACERE.match(text):
            text = text[match.end():]
            continue
        if match := IDRE.match(text):
            tokens.append(match.group())
            text = text[match.end():]
            continue
        for other in OTHER_TOKENS:
            if text.startswith(other):
                tokens.append(other)
                text = text[len(other):]
                break
        else:
            tokens.append(text[0])
            text = text[1:]
    return tokens
