import linecache
import os

from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.controls import FormattedTextControl
from ptpython.prompt_style import PromptStyle
from pygments.lexers import PythonLexer

__all__ = (
    "PdbPromptStyle",
    "CallStack",
    "format_stack_entry",
)


class PdbPromptStyle(PromptStyle):
    """
    Pdb prompt.

    Show "(pdb)" when we have a pdb command or '>>>' when the user types a
    Python command.
    """

    def __init__(self, pdb_commands):
        self.pdb_commands = pdb_commands

    def in_prompt(self):
        b = cli.buffers[DEFAULT_BUFFER]

        command = b.document.text.lstrip()
        if command:
            command = command.split()[0]

        if any(c.startswith(command) for c in self.pdb_commands):
            return [("class:prompt", "(pdb) ")]
        else:
            return [("class:prompt", "  >>> ")]

    def in2_prompt(self, width: int):
        return [("class:prompt", "  ... ")]

    def out_prompt(self):
        return []  # Not used.


python_lexer = PythonLexer(stripnl=False, stripall=False, ensurenl=False)


class CallStack(FormattedTextControl):
    def __init__(self, pdb_ref):
        def get_text():
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
                    result.append(("[SetCursorPosition]", " "))

                result.append(("", "\n"))

            return result

        super().__init__(
            get_text,
            #            has_focus=Condition(lambda cli: pdb_ref().callstack_focussed)
        )


def format_stack_entry(pdb, frame, lineno, has_focus=False):
    result = []

    if frame is pdb.curframe:
        result.append(("class:current-line", "->"))
        result.append(("", " "))
    else:
        result.append(("", "   "))

    filename = pdb.canonic(frame.f_code.co_filename)

    # Filename/lineno
    token = "class:name.selected" if has_focus else "class:name"
    result.append((token, os.path.basename(filename)))
    result.append(("class:number", "(%r)" % lineno))

    # co_name
    if frame.f_code.co_name:
        result.append(("class:name", frame.f_code.co_name))
    else:
        result.append(("class:name", "<lambda>"))

    # Args.
    if "__args__" in frame.f_locals:
        args = frame.f_locals["__args__"]
        result.append(("class:name", repr(args)))
    else:
        result.append(("class:punctuation", "()"))

    # Return value.
    if "__return__" in frame.f_locals:
        rv = frame.f_locals["__return__"]
        result.append(("class:operator", "->"))
        result.append(("", repr(rv)))

    result.append(("", "\n"))
    if has_focus:
        result.append(("class:selected-frame", ""))
    result.append(("", "     "))

    line = linecache.getline(filename, lineno, frame.f_globals).strip()
    result.extend(python_lexer.get_tokens(line))

    return result
