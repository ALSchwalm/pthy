import ast
from prompt_toolkit.validation import Validator, ValidationError
from hy.lex import LexException, PrematureEndOfInput, tokenize
from hy.compiler import hy_compile


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
            hy_compile(tokens, "__console__", root=ast.Interactive)
        except Exception as e:
            if hasattr(e, "message"):
                raise ValidationError(message='Syntax Error:' + e.message,
                                      index=len(code.text))
            else:
                raise ValidationError(message='Syntax Error:' + str(e),
                                      index=len(code.text))
