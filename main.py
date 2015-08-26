#!/usr/bin/env python
from __future__ import unicode_literals
import ast
import sys
import traceback

from io import StringIO

from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, Always, HasSelection, IsMultiline
from prompt_toolkit.shortcuts import create_default_application, create_eventloop, create_default_layout
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.key_bindings.utils import create_handle_decorator
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.lexers import PygmentsLexer

from pygments.styles.default import DefaultStyle
from pygments.lexers import PythonTracebackLexer
from pygments.lexers.lisp import HyLexer

from hy.cmdline import HyREPL
from hy.lex import LexException, PrematureEndOfInput, tokenize, lexer
from hy.compiler import hy_compile


class MyHyREPL(HyREPL):
    def evaluate(self, code):
        return HyREPL.runsource(self, code, "<input>", "single")

    def showtraceback(self):
        tokens = PythonTracebackLexer().get_tokens(traceback.format_exc())
        self.cli.print_tokens(tokens, style=DefaultStyle)


class HyValidator(Validator):
    def validate(self, code):
        try:
            tokens = tokenize(code.text)
        except PrematureEndOfInput:
            raise ValidationError(message='Unexpected end of input',
                                  index=len(code.text))
        except LexException as e:
            raise ValidationError(message=str(e),
                                  index=len(code.text))

        try:
            _ast = hy_compile(tokens, "__console__", root=ast.Interactive)
            # code = ast_compile(ast, filename, symbol)
        except Exception as e:
            raise ValidationError(message='Syntax Error',
                                  index=len(code.text))


def get_column_indent(buffer):
    """A quick hack to find the correct indentation
    from the current point.
    """
    text = buffer.document.text[:buffer.cursor_position+1]
    tokens = list(lexer.lex(text))
    paren_count = 0
    for i, token in enumerate(tokens[::-1]):
        if token.name == "RPAREN":
            paren_count += 1
        elif token.name == "LPAREN":
            if paren_count == 0:
                break
            paren_count -= 1
    if len(tokens) > len(tokens) - i + 1:
        next_token = tokens[len(tokens) - i + 1]
        colno = next_token.source_pos.colno - 1
    elif len(tokens) > len(tokens) - i:
        colno = tokens[len(tokens) - i].source_pos.colno - 1
    else:
        colno = tokens[-1].source_pos.colno
    return colno


def auto_newline(buffer):
    spaces = get_column_indent(buffer)
    buffer.insert_text('\n')
    for _ in range(spaces):
        buffer.insert_text(" ")


def load_modified_bindings(registry, filter=Always()):
    handle = create_handle_decorator(registry, filter)
    has_selection = HasSelection()

    def at_the_end(b):
        """ we consider the cursor at the end when there is no text after
        the cursor, or only whitespace. """
        text = b.document.text_after_cursor
        return text == '' or (text.isspace() and not '\n' in text)

    @handle(Keys.ControlJ, filter=~has_selection & IsMultiline(),
            save_before=False)
    def _(event):
        b = event.current_buffer
        if at_the_end(b) and b.validate():
            b.document = Document(
                text=b.text.rstrip(),
                cursor_position=len(b.text.rstrip()))

            b.accept_action.validate_and_handle(event.cli, b)
        else:
            auto_newline(b)

    @handle(Keys.ControlJ, filter=~has_selection & ~IsMultiline(),
            save_before=False)
    def _(event):
        b = event.current_buffer
        if at_the_end(b):
            b.accept_action.validate_and_handle(event.cli, b)
        else:
            auto_newline(b)


def main():
    eventloop = create_eventloop()
    validator = HyValidator()

    def src_is_multiline():
        if app and app.buffer:
            text = app.buffer.document.text
            try:
                tokenize(text)
                if '\n' in text:
                    return True
            except LexException:
                return True
        return False

    app = create_default_application("λ: ", validator=validator,
                                     multiline=Condition(src_is_multiline),
                                     lexer=HyLexer)
    cli = CommandLineInterface(application=app, eventloop=eventloop)
    load_modified_bindings(app.key_bindings_registry)

    hy_repl = MyHyREPL()
    hy_repl.cli = cli

    try:
        while True:
            code_obj = cli.run()
            hy_repl.evaluate(code_obj.text)
    except EOFError:
        pass
    finally:
        eventloop.close()

if __name__ == '__main__':
    main()
