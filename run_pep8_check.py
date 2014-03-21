#!/usr/bin/env python

import pep8


def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level):
  r"""
  Use 2 spaces per indentation level.

  For really old code that you don't want to mess up, you can continue to
  use 8-space tabs.

  Okay: a = 1
  Okay: if a == 0:\n    a = 1
  E111:   a = 1

  Okay: for item in items:\n    pass
  E112: for item in items:\npass

  Okay: a = 1\nb = 2
  E113: a = 1\n    b = 2
  """

  # Copied from pep8.py, modified for TWO spaces.
  if indent_char == ' ' and indent_level % 2:
    yield 0, "E111 indentation is not a multiple of two"

  indent_expect = previous_logical.endswith(':')
  if indent_expect and indent_level <= previous_indent_level:
    yield 0, "E112 expected an indented block"
  if indent_level > previous_indent_level and not indent_expect:
    yield 0, "E113 unexpected indentation"


def reset_pep8_checks():
  for group in pep8._checks.iterkeys():
    pep8._checks[group] = {}
  pep8.init_checks_registry()


def main():
  pep8.indentation = indentation
  reset_pep8_checks()
  pep8._main()


if __name__ == '__main__':
  main()
