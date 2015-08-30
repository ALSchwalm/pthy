from prompt_toolkit.filters import Condition, Always, HasSelection, IsMultiline, HasSearch
from prompt_toolkit.key_bindings.utils import create_handle_decorator
from prompt_toolkit.keys import Keys
from prompt_toolkit.document import Document
from hy.lex import tokenize

from .utils import get_tokens_in_current_sexp


def get_column_indent(buffer):
    from hy.macros import _hy_macros
    from hy.compiler import _compile_table

    tokens = get_tokens_in_current_sexp(buffer.document)
    if len(tokens) == 0:
        return buffer.document.cursor_position_col
    elif len(tokens) == 1 or tokens[0].name == "LPAREN":
        return tokens[0].source_pos.colno - 1
    else:
        for module, namespace in _hy_macros.items():
            if module is None:
                for macro in namespace.keys():
                    if macro == tokens[0].value:
                        return tokens[0].source_pos.colno
        for name in _compile_table.keys():
            if str(name) == tokens[0].value and len(str(name)) > 1:
                return tokens[0].source_pos.colno
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
        text = b.document.text_after_cursor
        return text == '' or (text.isspace() and not '\n' in text)

    def lexes(b):
        try:
            tokenize(b.text)
        except Exception:
            return False
        return True

    @handle(Keys.ControlJ, filter=~has_selection & IsMultiline() & ~HasSearch(),
            save_before=False)
    def _(event):
        b = event.current_buffer

        # We don't need full validation here, just test if hy
        # can lex the text
        if at_the_end(b) and lexes(b):
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
        if at_the_end(b) and lexes(b):
            b.accept_action.validate_and_handle(event.cli, b)
        else:
            auto_newline(b)
