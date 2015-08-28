#!/usr/bin/env python
from __future__ import unicode_literals
import ast
import traceback

from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, Always, HasSelection, IsMultiline, HasSearch
from prompt_toolkit.shortcuts import create_default_application, create_eventloop
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.key_bindings.utils import create_handle_decorator
from prompt_toolkit.keys import Keys
from prompt_toolkit.completion import Completer, Completion

from pygments.styles.default import DefaultStyle
from pygments.styles.monokai import MonokaiStyle
from pygments.lexers import PythonTracebackLexer
from pygments.lexers.lisp import HyLexer

from jedi.api import Interpreter

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
            raise ValidationError(message='Syntax Error:' + e.message,
                                  index=len(code.text))


class HyCompleter(Completer):
    def __init__(self, repl):
        self.repl = repl

    def _complete_hy_while_typing(self, document):
        tokens = get_tokens_in_current_sexp(document)
        if len(tokens) == 1 and (tokens[0].name == "IDENTIFIER"
                                 and tokens[0].value == "."):
            return False
        char_before_cursor = document.char_before_cursor
        return document.text and (
            char_before_cursor.isalnum() or char_before_cursor in '_.-')

    def _fixup_contents(self, document):
        text = document.text_before_cursor
        tokens = get_tokens_in_current_sexp(document)
        if tokens:
            if tokens[0].name == "IDENTIFIER" and tokens[0].value == ".":
                text = ".".join([id.value for id in tokens[1:]])
            else:
                text = text[tokens[0].source_pos.idx:]
        return text.replace("-", "_")

    def _fixup_completions(self, completions):
        # hack to hide the fact that hy converts '-' to '_'
        for c in completions:
            c._name.value = c._name.value.replace("_", "-")
        return completions

    def get_completions(self, document, complete_event):
        if complete_event.completion_requested or self._complete_hy_while_typing(document):
            text = self._fixup_contents(document)
            script = Interpreter(text, [self.repl.locals])

            if script:
                try:
                    completions = self._fixup_completions(script.completions())
                except Exception:
                    return ""
                else:
                    for c in completions:
                        yield Completion(c.name_with_symbols, len(c.complete) - len(c.name_with_symbols),
                                         display=c.name_with_symbols)
        return ""


def get_tokens_in_current_sexp(document):
    text = document.text_before_cursor
    tokens = list(lexer.lex(text))

    paren_count = 0
    for i, token in enumerate(tokens[::-1]):
        if token.name == "RPAREN":
            paren_count += 1
        elif token.name == "LPAREN":
            if paren_count == 0:
                break
            paren_count -= 1
    return tokens[len(tokens)-i:]


def get_column_indent(buffer):
    tokens = get_tokens_in_current_sexp(buffer.document)
    if len(tokens) == 0:
        return buffer.document.cursor_position_col
    elif len(tokens) == 1:
        return tokens[0].source_pos.colno - 1
    else:
        return tokens[1].source_pos.colno - 1


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

    @handle(Keys.ControlJ, filter=~has_selection & IsMultiline() & ~HasSearch(),
            save_before=False)
    def _(event):
        b = event.current_buffer
        lexes = True
        try:
            # We don't need full validation here, just test if hy
            # can lex the text
            tokenize(b.text)
        except Exception:
            lexes = False
        if at_the_end(b) and lexes:
            b.document = Document(
                text=b.text.rstrip(),
                cursor_position=len(b.text.rstrip()))

            b.accept_action.validate_and_handle(event.cli, b)
        else:
            auto_newline(b)

    @handle(Keys.ControlJ, filter=~has_selection & ~IsMultiline() & ~HasSearch(),
            save_before=False)
    def _(event):
        b = event.current_buffer
        if at_the_end(b):
            b.accept_action.validate_and_handle(event.cli, b)
        else:
            auto_newline(b)


def main():
    hy_repl = MyHyREPL()
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
                                     lexer=HyLexer,
                                     style=MonokaiStyle,
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
