from bdb import Breakpoint

from prompt_toolkit.filters import Condition, is_done
from prompt_toolkit.layout import ConditionalContainer, FormattedTextControl, Window

__all__ = [
    "PdbShortcutsToolbar",
    "SourceTitlebar",
    "StackTitlebar",
    "BreakPointInfoToolbar",
]


class PdbShortcutsToolbar:
    """
    Toolbar which shows the Pdb status. (current line and line number.)
    """

    def __init__(self, pdb_ref):
        def get_tokens():
            if pdb_ref().callstack_focussed:
                return [
                    ("class:toolbar.shortcuts.description", " "),
                    ("class:toolbar.shortcuts.key", "[Ctrl-X]"),
                    ("class:toolbar.shortcuts.description", " Focus CLI "),
                    ("class:toolbar.shortcuts.key", "[Enter]"),
                    ("class:toolbar.shortcuts.description", " Go to frame "),
                    ("class:toolbar.shortcuts.key", "[Arrows]"),
                    ("class:toolbar.shortcuts.description", " Navigate "),
                ]
            elif cli.current_buffer_name == "source_code":
                return [
                    ("class:toolbar.shortcuts.description", " "),
                    ("class:toolbar.shortcuts.key", "[Ctrl-X]"),
                    ("class:toolbar.shortcuts.description", " Focus CLI "),
                    ("class:toolbar.shortcuts.key", "[s]"),
                    ("class:toolbar.shortcuts.description", "tep "),
                    ("class:toolbar.shortcuts.key", "[n]"),
                    ("class:toolbar.shortcuts.description", "ext "),
                    ("class:toolbar.shortcuts.key", "[c]"),
                    ("class:toolbar.shortcuts.description", "ontinue "),
                    ("class:toolbar.shortcuts.key", "[q]"),
                    ("class:toolbar.shortcuts.description", "uit "),
                    ("class:toolbar.shortcuts.key", "[b]"),
                    ("class:toolbar.shortcuts.description", "reak "),
                    ("class:toolbar.shortcuts.key", "[Arrows]"),
                    ("class:toolbar.shortcuts.description", " Navigate "),
                ]
            else:
                return [
                    ("class:toolbar.shortcuts.description", " "),
                    ("class:toolbar.shortcuts.key", "[Ctrl-X]"),
                    ("class:toolbar.shortcuts.description", " Focus source code "),
                ]

        self.container = ConditionalContainer(
            Window(FormattedTextControl(get_tokens), height=1, style="class:toolbar",),
            filter=~is_done,
        )

    def __pt_container__(self):
        return self.container


class SourceTitlebar:
    """
    Toolbar which shows the filename and line number.
    """

    def __init__(self, pdb_ref):
        def get_tokens():
            pdb = pdb_ref()

            return [
                ("class:toolbar.title", "\u2500\u2500"),
                ("class:toolbar.title.text", " "),
                ("class:toolbar.title.text", pdb.curframe.f_code.co_filename or "None"),
                ("class:toolbar.title.text", " : %s " % pdb.curframe.f_lineno),
            ]

        self.container = Window(
            FormattedTextControl(get_tokens),
            height=1,
            style="class:toolbar.title",
            char="\u2500",
        )

    def __pt_container__(self):
        return self.container


class StackTitlebar:
    """
    """

    def __init__(self, pdb_ref):
        def get_tokens():
            pdb = pdb_ref()

            result = [
                ("class:toolbar.title", "\u2500\u2500"),
                ("class:toolbar.title.text", " Stack "),
            ]

            if pdb.callstack_focussed:
                text = "(frame %i/%i) " % (
                    pdb.callstack_selected_frame + 1,
                    len(pdb.stack),
                )
                result.append(("class:toolbar.title.text", text))

            return result

        self.container = Window(
            FormattedTextControl(get_tokens),
            height=1,
            style="class:toolbar",
            char="\u2500",
        )

    def __pt_container__(self):
        return self.container


class BreakPointInfoToolbar:
    """
    Show info about the current breakpoint.
    """

    def __init__(self, pdb_ref):
        token = "class:break"

        def get_break():
            """ Get Breakpoints. """
            pdb = pdb_ref()
            filename = pdb.canonic(pdb.curframe.f_code.co_filename)
            lineno = cli.buffers["source_code"].document.cursor_position_row + 1
            if (filename, lineno) in Breakpoint.bplist:
                return Breakpoint.bplist[filename, lineno]
            else:
                return []

        def get_tokens():
            breaks = get_break()
            result = []

            for b in breaks:
                if not b.enabled:
                    result.append((token, " [disabled]"))

                result.append((token, " "))
                result.append((token, "BP %i" % b.number))

                if b.cond:
                    result.append((token, " "))
                    result.append((token + ".condition", " "))
                    result.append((token + ".condition", str(b.cond)))
                    result.append((token + ".condition", " "))

                if b.hits:
                    text = "hit" if b.hits == 1 else "hits"
                    result.append((token, ", %i %s" % (b.hits, text)))
                result.append((token, " "))

            return result

        self.container = ConditionalContainer(
            Window(FormattedTextControl(get_tokens), height=1),
            filter=Condition(lambda: bool(get_break())),
        )

    def __pt_container__(self):
        return self.container
