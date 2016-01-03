from __future__ import unicode_literals, absolute_import
from pygments.token import Token

from prompt_toolkit.layout.toolbars import TokenListToolbar
from prompt_toolkit.layout.screen import Char

from prompt_toolkit.filters import IsDone, Condition

from bdb import Breakpoint

__all__ = (
    'PdbShortcutsToolbar',
    'SourceTitlebar',
    'StackTitlebar',
    'BreakPointInfoToolbar',
)


class PdbShortcutsToolbar(TokenListToolbar):
    """
    Toolbar which shows the Pdb status. (current line and line number.)
    """
    def __init__(self, pdb_ref):
        token = Token.Toolbar.Shortcuts

        def get_tokens(cli):
            if pdb_ref().callstack_focussed:
                return [
                    (token.Description, ' '),
                    (token.Key, '[Ctrl-X]'),
                    (token.Description, ' Focus CLI '),
                    (token.Key, '[Enter]'),
                    (token.Description, ' Go to frame '),
                    (token.Key, '[Arrows]'),
                    (token.Description, ' Navigate '),
                ]
            elif cli.current_buffer_name == 'source_code':
                return [
                    (token.Description, ' '),
                    (token.Key, '[Ctrl-X]'),
                    (token.Description, ' Focus CLI '),
                    (token.Key, '[s]'),
                    (token.Description, 'tep '),
                    (token.Key, '[n]'),
                    (token.Description, 'ext '),
                    (token.Key, '[c]'),
                    (token.Description, 'ontinue '),
                    (token.Key, '[q]'),
                    (token.Description, 'uit '),
                    (token.Key, '[b]'),
                    (token.Description, 'reak '),
                    (token.Key, '[Arrows]'),
                    (token.Description, ' Navigate '),
                ]
            else:
                return [
                    (token.Description, ' '),
                    (token.Key, '[Ctrl-X]'),
                    (token.Description, ' Focus source code '),
                ]

        super(PdbShortcutsToolbar, self).__init__(get_tokens,
                                               default_char=Char(token=token.Description),
                                               filter=~IsDone())


class SourceTitlebar(TokenListToolbar):
    """
    Toolbar which shows the filename and line number.
    """
    def __init__(self, pdb_ref):
        token = Token.Toolbar.Title

        def get_tokens(cli):
            pdb = pdb_ref()

            return [
                (token, '\u2500\u2500'),
                (token.Text, ' '),
                (token.Text, pdb.curframe.f_code.co_filename or 'None'),
                (token.Text, ' : %s ' % pdb.curframe.f_lineno),
            ]

        super(SourceTitlebar, self).__init__(
            get_tokens, default_char=Char(token=token, char='\u2500'))


class StackTitlebar(TokenListToolbar):
    """
    """
    def __init__(self, pdb_ref):
        token = Token.Toolbar.Title

        def get_tokens(cli):
            pdb = pdb_ref()

            result = [
                (token, '\u2500\u2500'),
                (token.Text, ' Stack ')
            ]

            if pdb.callstack_focussed:
                text = '(frame %i/%i) ' % (pdb.callstack_selected_frame + 1, len(pdb.stack))
                result.append((token.Text, text))

            return result

        super(StackTitlebar, self).__init__(
            get_tokens, default_char=Char(token=token, char='\u2500'))


class BreakPointInfoToolbar(TokenListToolbar):
    """
    Show info about the current breakpoint.
    """
    def __init__(self, pdb_ref):
        token = Token.Break

        def get_break(cli):
            """ Get Breakpoints. """
            pdb = pdb_ref()
            filename = pdb.canonic(pdb.curframe.f_code.co_filename)
            lineno = cli.buffers['source_code'].document.cursor_position_row + 1
            if (filename, lineno) in Breakpoint.bplist:
                return Breakpoint.bplist[filename, lineno]
            else:
                return []

        def get_tokens(cli):
            breaks = get_break(cli)
            result = []

            for b in breaks:
                if not b.enabled:
                    result.append((token, ' [disabled]'))

                result.append((token, ' '))
                result.append((token, 'BP %i' % b.number))

                if b.cond:
                    result.append((token, ' '))
                    result.append((token.Condition, ' '))
                    result.append((token.Condition, str(b.cond)))
                    result.append((token.Condition, ' '))

                if b.hits:
                    text = 'hit' if b.hits == 1 else 'hits'
                    result.append((token, ', %i %s' % (b.hits, text)))
                result.append((token, ' '))

            return result

        super(BreakPointInfoToolbar, self).__init__(get_tokens,
                filter=Condition(lambda cli: bool(get_break(cli))))
