#!/usr/bin/env python
"""
Python debugger prompt.
Enhanced version of Pdb, using a prompt-toolkit front-end.

Usage::

    from prompt_toolkit.contrib.pdb import set_trace
    set_trace()
"""
from __future__ import unicode_literals, absolute_import, print_function
from pygments.lexers import PythonLexer
from pygments.token import Token

from prompt_toolkit.buffer import Buffer, AcceptAction
from prompt_toolkit.completion import Completer
from prompt_toolkit.contrib.regular_languages.completion import GrammarCompleter
from prompt_toolkit.contrib.regular_languages.validation import GrammarValidator
from prompt_toolkit.document import Document
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import IsDone, Always, Condition
from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.layout.containers import HSplit, Window, ConditionalContainer, FloatContainer, Float, VSplit, ScrollOffsets
from prompt_toolkit.layout.controls import BufferControl, FillControl
from prompt_toolkit.layout.dimension import LayoutDimension
from prompt_toolkit.layout.lexers import Lexer, PygmentsLexer
from prompt_toolkit.layout.margins import Margin, NumberredMargin, ScrollbarMargin
from prompt_toolkit.layout.processors import ConditionalProcessor
from prompt_toolkit.layout.utils import iter_token_lines
from prompt_toolkit.shortcuts import create_eventloop
from prompt_toolkit.validation import Validator
from prompt_toolkit.layout.highlighters import SearchHighlighter, SelectionHighlighter

from ptpython.completer import PythonCompleter
from ptpython.layout import CompletionVisualisation
from ptpython.python_input import PythonInput
from ptpython.repl import embed
from ptpython.validator import PythonValidator

from .commands import commands_with_help, shortcuts
from .completers import PythonFileCompleter, PythonFunctionCompleter, BreakPointListCompleter, AliasCompleter, PdbCommandsCompleter
from .grammar import create_pdb_grammar
from .key_bindings import load_custom_pdb_key_bindings
from .layout import PdbPromptStyle, CallStack, format_stack_entry
from .toolbars import PdbShortcutsToolbar, SourceTitlebar, StackTitlebar, BreakPointInfoToolbar
from .completion_hints import CompletionHint
from .style import get_ui_style

import linecache
import os
import pdb
import sys
import weakref


__all__ = (
    'PtPdb',
    'set_trace',
)


class DynamicCompleter(Completer):
    """
    Proxy to a real completer which we can change at runtime.
    """
    def __init__(self, get_completer_func):
        self.get_completer_func = get_completer_func

    def get_completions(self, document, complete_event):
        for c in self.get_completer_func().get_completions(document, complete_event):
            yield c


class DynamicValidator(Validator):
    """
    Proxy to a real validator which we can change at runtime.
    """
    def __init__(self, get_validator_func):
        self.get_validator_func = get_validator_func

    def validate(self, document):
        return self.get_validator_func().validate(document)


class PdbLexer(Lexer):
    def __init__(self):
        self.python_lexer = PygmentsLexer(PythonLexer)

    def get_tokens(self, cli, text):
        parts = text.split(None, 1)
        first_word = parts[0] if parts else ''

        # When the first word is a PDB command:
        if first_word in shortcuts.keys() or first_word in commands_with_help.keys():
            # PDB:
            if cli.is_done:
                return [
                    (Token.PdbCommand, ' %s ' % first_word),
                    (Token, ' '),
                    (Token, parts[1] if len(parts) > 1 else ''),
                ]
            else:
                return [(Token.Text, text)]

        # Otherwise, highlight as Python code.
        else:
            return self.python_lexer.get_tokens(cli, text)


def get_line_prefix_tokens(is_break, is_current_line):
    """
    Return the tokens to show in the left margin of a source code listing.
    """
    if is_break:
        if is_current_line:
            return [
                (Token.Break, 'B'),
                (Token.CurrentLine, '->')
            ]
        else:
            return [(Token.Break, ' B ')]
    else:
        if is_current_line:
            return [
                (Token.CurrentLine, '->'),
                (Token, ' ')
            ]
        else:
            return [(Token, '   ')]


class SourceCodeMargin(Margin):
    """
    Margin that shows 'B' and '->' for breaks and the current line.
    """
    def __init__(self, ptpdb):
        self.ptpdb = ptpdb

    def get_width(self, cli):
        return 3

    def create_margin(self, cli, window_render_info, width, height):
        filename = self.ptpdb.curframe.f_code.co_filename
        breaklist = self.ptpdb.get_file_breaks(filename)
        curframe = self.ptpdb.curframe

        visible_line_to_input_line = window_render_info.visible_line_to_input_line

        result = []

        for y in range(window_render_info.window_height):
            lineno = visible_line_to_input_line.get(y)

            if lineno is not None:
                is_current_line = lineno + 1 == curframe.f_lineno
                is_break = (lineno + 1) in breaklist
                result.extend(get_line_prefix_tokens(is_break, is_current_line))

            result.append((Token, '\n'))

        return result

    def invalidation_hash(self, cli, document):
        filename = self.ptpdb.curframe.f_code.co_filename

        return (
            tuple(self.ptpdb.get_file_breaks(filename)),
            self.ptpdb.curframe.f_lineno
        )


class PtPdb(pdb.Pdb):
    def __init__(self):
        pdb.Pdb.__init__(self)

        # Cache for the grammar.
        self._grammar_cache = None  # (current_pdb_commands, grammar) tuple.

        self.completer = None
        self.validator = None
        self.lexer = None

        self._source_code_window = Window(
            BufferControl(
                buffer_name='source_code',
                lexer=PygmentsLexer(PythonLexer),
                highlighters=[
                    SearchHighlighter(preview_search=Always()),
                    SelectionHighlighter(),
                ],
            ),
            left_margins=[
                SourceCodeMargin(self),
                NumberredMargin('source_code'),
            ],
            right_margins=[ScrollbarMargin()],
            scroll_offsets=ScrollOffsets(top=2, bottom=2),
            height=LayoutDimension(preferred=10))

        # Callstack window.
        callstack = CallStack(weakref.ref(self))
        self.callstack_focussed = False  # When True, show cursor there, and allow navigation through it.
        self.callstack_selected_frame = 0  # Top frame.

        show_pdb_content_filter = ~IsDone() & Condition(
                    lambda cli: not self.python_input.show_exit_confirmation)

        self.python_input = PythonInput(
            get_locals=lambda: self.curframe.f_locals,
            get_globals=lambda: self.curframe.f_globals,
            _completer=DynamicCompleter(lambda: self.completer),
            _validator=DynamicValidator(lambda: self.validator),
            _accept_action = self._create_accept_action(),
            _extra_buffers={'source_code': Buffer(read_only=True)},
            _input_buffer_height=LayoutDimension(min=2, max=4),
            _lexer=PdbLexer(),
            _extra_buffer_processors=[
                ConditionalProcessor(
                    processor=CompletionHint(),
                    filter=~IsDone())
                ],
            _extra_layout_body=ConditionalContainer(
                HSplit([
                    VSplit([
                        HSplit([
                            SourceTitlebar(weakref.ref(self)),
                            FloatContainer(
                                content=self._source_code_window,
                                floats=[
                                    Float(right=0, bottom=0,
                                          content=BreakPointInfoToolbar(weakref.ref(self)))
                                ]),
                        ]),
                        HSplit([
                            Window(width=LayoutDimension.exact(1),
                                   height=LayoutDimension.exact(1),
                                   content=FillControl('\u252c', token=Token.Toolbar.Title)),
                            Window(width=LayoutDimension.exact(1),
                                   content=FillControl('\u2502', token=Token.Separator)),
                        ]),
                        HSplit([
                            StackTitlebar(weakref.ref(self)),
                            Window(callstack,
                                   scroll_offsets=ScrollOffsets(top=2, bottom=2),
                                   right_margins=[ScrollbarMargin()],
                                   height=LayoutDimension(preferred=10)),
                        ]),
                    ]),
                ]),
                filter=show_pdb_content_filter),
            _extra_toolbars=[
                ConditionalContainer(
                    PdbShortcutsToolbar(weakref.ref(self)),
                    show_pdb_content_filter)
            ],
            history_filename=os.path.expanduser('~/.ptpdb_history'),
        )

        # Override prompt style.
        self.python_input.all_prompt_styles['pdb'] = PdbPromptStyle(self._get_current_pdb_commands())
        self.python_input.prompt_style = 'pdb'

        # Override exit message.
        self.python_input.exit_message = 'Do you want to quit BDB? This raises BdbQuit.'

        # Set UI styles.
        self.python_input.ui_styles = {
            'ptpdb': get_ui_style(),
        }
        self.python_input.use_ui_colorscheme('ptpdb')

        # Set autocompletion style. (Multi-column works nicer.)
        self.python_input.completion_visualisation = CompletionVisualisation.MULTI_COLUMN

        # Load additional key bindings.
        load_custom_pdb_key_bindings(self, self.python_input.key_bindings_registry)

        self.cli = CommandLineInterface(
            eventloop=create_eventloop(),
            application=self.python_input.create_application())

    def _create_accept_action(self):
        """
        Create an AcceptAction for the input buffer that replaces shortcuts
        like 's' with the full command ('step') before returning it.
        """
        def handler(cli, buffer):
            # Get first part.
            parts = buffer.text.strip().split(None, 1)
            if len(parts) == 0:
                first, rest = '', ''
            elif len(parts) == 1:
                first, rest = parts[0], ''
            else:
                first, rest = parts

            # Replace text in buffer and return it.
            buffer.document = Document(shortcuts.get(first, first) + ' ' + rest)
            cli.set_return_value(buffer.document)
        return AcceptAction(handler)

    def cmdloop(self, intro=None):
        """
        Copy/Paste of pdb.Pdb.cmdloop. But using our own CommandLineInterface
        for reading input instead.
        """
        self.preloop()

        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            if self.cmdqueue:
                line = self.cmdqueue.pop(0)
            else:
                if self.use_rawinput:
                    line = self._get_input()

            line = self.precmd(line)
            stop = self.onecmd(line)
            stop = self.postcmd(stop, line)
        self.postloop()

    def _get_current_pdb_commands(self):
        return (
            list(commands_with_help.keys()) +
            list(shortcuts.keys()) +
            list(self.aliases.keys()))

    def _create_grammar(self):
        """
        Return the compiled grammar for this PDB shell.

        The grammar of PDB depends on the available list of PDB commands (which
        depends on the currently defined aliases.) Therefor we generate a new
        grammar when it changes, but cache it otherwise. (It's still expensive
        to compile.)
        """
        pdb_commands = self._get_current_pdb_commands()

        if self._grammar_cache is None or self._grammar_cache[0] != pdb_commands:
            self._grammar_cache = [
                pdb_commands,
                create_pdb_grammar(pdb_commands)]

        return self._grammar_cache[1]

    def _get_input(self):
        """
        Read PDB input. Return input text.
        """
        # Reset multiline/paste mode every time.
        self.python_input.paste_mode = False
        self.python_input.currently_multiline = False

        # Set source code document.
        self._show_source_code(self.curframe.f_code.co_filename)

        self.cli.buffers[DEFAULT_BUFFER].document = Document('')

        # Select the current frame of the stack.
        for i, (frame, lineno) in enumerate(self.stack):
            if frame is self.curframe:
                self.callstack_selected_frame = i
                break

        # Set up a new completer and validator for the new grammar.
        g = self._create_grammar()

        self.completer = GrammarCompleter(g, completers={
            'enabled_breakpoint': BreakPointListCompleter(only_enabled=True),
            'disabled_breakpoint': BreakPointListCompleter(only_disabled=True),
            'alias_name': AliasCompleter(self),
            'python_code': PythonCompleter(lambda: self.curframe.f_globals, lambda: self.curframe.f_locals),
            'breakpoint': BreakPointListCompleter(),
            'pdb_command': PdbCommandsCompleter(self),
            'python_file': PythonFileCompleter(),
            'python_function': PythonFunctionCompleter(self),
        })
        self.validator = GrammarValidator(g, {
            'python_code': PythonValidator()
        })

        # Make sure not to start in Vi navigation mode.
        self.python_input.key_bindings_manager.reset(self.cli)
        self.cli.buffers[DEFAULT_BUFFER].reset()

        def pre_run():
            self._source_code_window.vertical_scroll = 100000 # source_code_doc.line_count

        try:
            return self.cli.run(reset_current_buffer=False, pre_run=pre_run).text
        except EOFError:
            # Turn Control-D key press into a 'quit' command.
            return 'quit'

    def _show_source_code(self, filename):
        """
        Show the source code in the `source_code` buffer.
        """
        source_code_doc = self._get_source_code_document(filename)
        self.cli.buffers['source_code']._set_text(source_code_doc.text + '\n')
        self.cli.buffers['source_code']._set_cursor_position(source_code_doc.cursor_position)

    def _get_source_code_document(self, filename):
        """
        Return source code around current line as string.
        """
        source_code = [l.decode('utf-8') for l in linecache.getlines(filename)]
        source_code = ''.join(source_code)
        document = Document(source_code)

        return Document(document.text, document.translate_row_col_to_index(
            row=self.curframe.f_lineno - 1, col=0))

    #
    # Methods overriden from Pdb, in order to add highlighting.
    #

    def postcmd(self, stop, line):
        """
        Override 'postcmd': (Insert whitespace.)
        """
        print('')
        return pdb.Pdb.postcmd(self, stop, line)

    def preloop(self):
        print('')
        return pdb.Pdb.preloop(self)

    def do_interact(self, args):
        """
        Interact: start interpreter.
        (Override the 'pdb' implementation. We call ptpython instead.)
        """
        print('')
        ns = self.curframe.f_globals.copy()
        ns.update(self.curframe_locals)
        embed(globals=ns)

    def error(self, msg):
        """
        Override default error handler from PDB.
        """
        self.cli.print_tokens([
            (Token.Pdb.Error, '  %s  \n' % msg)
        ])

    def print_stack_entry(self, frame_lineno, prompt_prefix=': '):
        """
        Override `print_stack_entry` of Pdb, in order to add highlighting.
        """
        frame, lineno = frame_lineno

        tokens = []
        tokens.extend(format_stack_entry(self, frame, lineno))
        tokens.append((Token, '\n'))

        self.cli.print_tokens(tokens)

    def do_list(self, arg):
        """
        Override `Pdb.do_list`: Add highlighting.
        """
        self.lastcmd = 'list'
        last = None
        if arg and arg != '.':
            try:
                if ',' in arg:
                    first, last = arg.split(',')
                    first = int(first.strip())
                    last = int(last.strip())
                    if last < first:
                        # assume it's a count
                        last = first + last
                else:
                    first = int(arg.strip())
                    first = max(1, first - 5)
            except ValueError:
                self.error('Error in argument: %r' % arg)
                return
        elif self.lineno is None or arg == '.':
            first = max(1, self.curframe.f_lineno - 5)
        else:
            first = self.lineno + 1
        if last is None:
            last = first + 10
        filename = self.curframe.f_code.co_filename
        breaklist = self.get_file_breaks(filename)
        try:
            lines = linecache.getlines(filename, self.curframe.f_globals)
            self._print_lines_2(lines, first, last, breaklist,
                              self.curframe)
            self.lineno = min(last, len(lines))
            if len(lines) < last:
                self.message('[EOF]')
        except KeyboardInterrupt:
            pass
    do_l = do_list

    def _print_lines_2(self, lines, start, end, breaks=(), frame=None):
        """
        Similar to `Pdb._print_lines`, except that this takes all the lines
        of the given file as input, it uses Pygments for the highlighting,
        it does slicing, and it prints everything in color.
        """
        if frame:
            current_lineno = frame.f_lineno
        else:
            current_lineno = exc_lineno = -1

        # Highlight everything. (Highlighting works much better from the
        # beginning of the file.)
        all_tokens = python_lexer.get_tokens(''.join(lines))

        # Slice lines.
        lines = list(iter_token_lines(all_tokens))[start-1:end]

        # Add left margin. (Numbers + 'B' or '->'.)
        def add_margin(lineno, tokens):
            is_break = lineno in breaks
            is_current_line = lineno == current_lineno

            return get_line_prefix_tokens(is_break, is_current_line) \
                + [(Token.LineNumber, str(lineno).rjust(3) + ' ')] \
                + tokens

        lines = [add_margin(i + start, tokens) for i, tokens in enumerate(lines)]

        for l in lines:
            self.cli.print_tokens(l)

    def message(self, msg):
        """ Print message to stdout. This function is present in Pdb for
        Python3, but not in Python2. """
        print(msg, file=self.stdout)


python_lexer = PythonLexer(
    stripnl=False,
    stripall=False,
    ensurenl=False)


def set_trace():
    PtPdb().set_trace(sys._getframe().f_back)
