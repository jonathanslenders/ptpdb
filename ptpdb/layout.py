from __future__ import unicode_literals, absolute_import

from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.controls import TokenListControl

from ptpython.prompt_style import PromptStyle

from pygments.token import Token
from pygments.lexers import PythonLexer

import linecache
import os

__all__ = (
    'PdbPromptStyle',
    'CallStack',
    'format_stack_entry',
)

class PdbPromptStyle(PromptStyle):
    """
    Pdb prompt.

    Show "(pdb)" when we have a pdb command or '>>>' when the user types a
    Python command.
    """
    def __init__(self, pdb_commands):
        self.pdb_commands = pdb_commands

    def in_tokens(self, cli):
        b = cli.buffers[DEFAULT_BUFFER]

        command = b.document.text.lstrip()
        if command:
            command = command.split()[0]

        if any(c.startswith(command) for c in self.pdb_commands):
            return [(Token.Prompt, '(pdb) ')]
        else:
            return [(Token.Prompt, '  >>> ')]

    def in2_tokens(self, cli, width):
        return [
            (Token.Prompt, '  ... ')
        ]

    def out_tokens(self, cli):
        return []  # Not used.


python_lexer = PythonLexer(
    stripnl=False,
    stripall=False,
    ensurenl=False)


class CallStack(TokenListControl):
    def __init__(self, pdb_ref):
        def get_tokens(cli):
            """
            See bdb.py, format_stack_entry.
            """
            pdb = pdb_ref()
            result = []

            for i, (frame, lineno) in enumerate(pdb.stack):
                is_selected = i == pdb.callstack_selected_frame
                has_focus = is_selected and pdb.callstack_focussed

                result.extend(format_stack_entry(pdb, frame, lineno, has_focus))

                # Focus cursor.
                if is_selected:
                    result.append((Token.SetCursorPosition, ' '))

                result.append((Token, '\n'))

            return result

        super(CallStack, self).__init__(
            get_tokens, has_focus=Condition(lambda cli: pdb_ref().callstack_focussed))


def format_stack_entry(pdb, frame, lineno, has_focus=False):
    result = []

    if frame is pdb.curframe:
        result.append((Token.CurrentLine, '->'))
        result.append((Token, ' '))
    else:
        result.append((Token, '   '))

    filename = pdb.canonic(frame.f_code.co_filename)

    # Filename/lineno
    token = Token.Name.Selected if has_focus else Token.Name
    result.append((token, os.path.basename(filename)))
    result.append((Token.Number, '(%r)' % lineno))

    # co_name
    if frame.f_code.co_name:
        result.append((Token.Name, frame.f_code.co_name))
    else:
        result.append((Token.Name, '<lambda>'))

    # Args.
    if '__args__' in frame.f_locals:
        args = frame.f_locals['__args__']
        result.append((Token.Name, repr(args)))
    else:
        result.append((Token.Punctuation, '()'))

    # Return value.
    if '__return__' in frame.f_locals:
        rv = frame.f_locals['__return__']
        result.append((Token.Operator, '->'))
        result.append((Token, repr(rv)))

    result.append((Token, '\n'))
    if has_focus:
        result.append((Token.SelectedFrame, ''))
    result.append((Token, '     '))

    line = linecache.getline(filename, lineno, frame.f_globals).strip()
    result.extend(python_lexer.get_tokens(line))

    return result
