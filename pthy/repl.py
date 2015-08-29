import traceback
from hy.cmdline import HyREPL as DefaultHyREPL
from pygments.lexers import PythonTracebackLexer
from pygments.styles.default import DefaultStyle


class HyREPL(DefaultHyREPL):
    def evaluate(self, code):
        return DefaultHyREPL.runsource(self, code, "<input>", "single")

    def showtraceback(self):
        tokens = PythonTracebackLexer().get_tokens(traceback.format_exc())
        self.cli.print_tokens(tokens, style=DefaultStyle)
