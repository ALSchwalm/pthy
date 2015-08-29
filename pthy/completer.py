from prompt_toolkit.completion import Completer, Completion
from jedi.api import Interpreter

from .utils import get_tokens_in_current_sexp


class HyCompleter(Completer):
    def __init__(self, repl):
        self.repl = repl

    def _is_dot_sexp(self, tokens):
        return (len(tokens) > 0 and
                tokens[0].name == "IDENTIFIER" and
                tokens[0].value == ".")

    def _complete_hy_while_typing(self, document):
        tokens = get_tokens_in_current_sexp(document)
        if len(tokens) == 1 and self._is_dot_sexp(tokens):
            return False
        char_before_cursor = document.char_before_cursor
        return document.text and (
            char_before_cursor.isalnum() or char_before_cursor in '_.-')

    def _fixup_contents(self, document):
        text = document.text_before_cursor
        tokens = get_tokens_in_current_sexp(document)
        if tokens:
            if self._is_dot_sexp(tokens):
                text = ".".join([id.value for id in tokens[1:]])
            else:
                text = text[tokens[0].source_pos.idx:]
        return text.replace("-", "_")

    def _find_hy_completions(self, partial_name):
        from hy.macros import _hy_macros
        from hy.compiler import load_stdlib, _stdlib, _compile_table
        from itertools import chain
        from keyword import iskeyword

        # Without this, built in macros will not load until after
        # the first sexp is evalutaed
        load_stdlib()

        matches = []

        # Add macros
        for namespace in _hy_macros.values():
            for name in namespace.keys():
                if name.startswith(partial_name):
                    matches.append(name)

        # Add builtins
        for name in chain(_stdlib.keys(), _compile_table.keys()):
            if str(name).startswith(partial_name) and not iskeyword(str(name)):
                matches.append(name)
        return matches

    def _fixup_completions(self, completions, document):
        normalized_completions = []
        tokens = get_tokens_in_current_sexp(document)
        if len(tokens) > 0 and tokens[0].value != "import":
            current_token = tokens[-1]
            matches = self._find_hy_completions(current_token.value)
            for match in matches:
                normalized_completions.append(
                    Completion(match, -len(current_token.value)))

        # Hide the transformations performed by hy
        for c in completions:
            c._name.value = c._name.value.replace("_", "-")

            c = Completion(c.name_with_symbols, len(c.complete) - len(c.name_with_symbols),
                           display=c.name_with_symbols)
            normalized_completions.append(c)

        def compare_fun(x):
            return (x.text.startswith('--'),
                    x.text.startswith('-'),
                    x.text.lower())
        return sorted(normalized_completions, key=compare_fun)

    def get_completions(self, document, complete_event):
        if complete_event.completion_requested or self._complete_hy_while_typing(document):
            text = self._fixup_contents(document)
            script = Interpreter(text, [self.repl.locals])

            if script:
                try:
                    completions = self._fixup_completions(script.completions(),
                                                          document)
                except Exception:
                    return ""
                else:
                    for c in completions:
                        yield c
        return ""
