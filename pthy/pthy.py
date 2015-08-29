#!/usr/bin/env python
from __future__ import unicode_literals
from os.path import expanduser

from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.shortcuts import create_default_application, create_eventloop
from prompt_toolkit.history import FileHistory
from prompt_toolkit.filters import Condition

from pygments.styles.monokai import MonokaiStyle
from pygments.lexers.lisp import HyLexer

from hy.lex import LexException, tokenize

from .validator import HyValidator
from .completer import HyCompleter
from .keybindings import load_modified_bindings
from .repl import HyREPL


def main():
    hy_repl = HyREPL()
    eventloop = create_eventloop()
    validator = HyValidator()
    history = FileHistory(expanduser("~/.pthy_history"))

    def src_is_multiline():
        if app and app.buffer:
            text = app.buffer.document.text
            try:
                if '\n' in text:
                    return True
                tokenize(text)
            except LexException:
                return True
        return False

    app = create_default_application("λ: ", validator=validator,
                                     multiline=Condition(src_is_multiline),
                                     lexer=HyLexer,
                                     style=MonokaiStyle,
                                     history=history,
                                     completer=HyCompleter(hy_repl))
    cli = CommandLineInterface(application=app, eventloop=eventloop)
    load_modified_bindings(app.key_bindings_registry)

    hy_repl.cli = cli

    try:
        while True:
            try:
                code_obj = cli.run()
                hy_repl.evaluate(code_obj.text)
            except KeyboardInterrupt:
                pass
    except EOFError:
        pass
    finally:
        eventloop.close()

if __name__ == '__main__':
    main()
