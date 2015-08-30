#!/usr/bin/env python
from __future__ import unicode_literals
from os.path import expanduser

from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.shortcuts import create_default_application, create_eventloop
from prompt_toolkit.history import FileHistory
from prompt_toolkit.filters import Condition, IsDone, IsMultiline
from prompt_toolkit.layout.processors import HighlightMatchingBracketProcessor, BracketsMismatchProcessor, ConditionalProcessor
from prompt_toolkit.layout.margins import ConditionalMargin, NumberredMargin

from pygments.lexers.lisp import HyLexer

from hy.lex import LexException, tokenize

from .validator import HyValidator
from .completer import HyCompleter
from .keybindings import load_modified_bindings
from .repl import HyREPL
from .style import HyStyle


def main():
    hy_repl = HyREPL()
    eventloop = create_eventloop()
    validator = HyValidator()
    history = FileHistory(expanduser("~/.pthy_history"))

    def src_is_multiline():
        if app and app.buffer:
            text = app.buffer.document.text
            if '\n' in text:
                return True
        return False

    app = create_default_application("λ: ", validator=validator,
                                     multiline=Condition(src_is_multiline),
                                     lexer=HyLexer,
                                     style=HyStyle,
                                     history=history,
                                     completer=HyCompleter(hy_repl),
                                     display_completions_in_columns=True,
                                     extra_input_processors=[
                                         ConditionalProcessor(
                                             processor=HighlightMatchingBracketProcessor(),
                                             filter=~IsDone())
                                     ])

    # Somewhat ugly trick to add a margin to the multiline input
    # without needing to define a custom layout
    app.layout.children[0].children[1].content.content.margin = ConditionalMargin(
        NumberredMargin(),
        filter=IsMultiline())

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
