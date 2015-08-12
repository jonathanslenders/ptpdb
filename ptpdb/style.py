from __future__ import unicode_literals

from ptpython.style import default_ui_style
from pygments.token import Token

__all__ = (
    'ptpdb_style_extensions',
    'get_ui_style',
)


ptpdb_style_extensions = {
    # Pdb tokens.
    Token.Prompt.BeforeInput:                      'bold #008800',
    Token.CompletionHint.Symbol:                   '#9a8888',
    Token.CompletionHint.Parameter:                '#ba4444 bold',
    Token.Toolbar.Status.Pdb.Filename:             'bg:#222222 #aaaaaa',
    Token.Toolbar.Status.Pdb.Lineno:               'bg:#222222 #ffffff',
    Token.Toolbar.Status.Pdb.Shortcut.Key:         'bg:#222222 #aaaaaa',
    Token.Toolbar.Status.Pdb.Shortcut.Description: 'bg:#222222 #aaaaaa',

    Token.Toolbar.Shortcuts.Key:          'bg:#444444 #ffffff',
    Token.Toolbar.Shortcuts.Description:  'bg:#888888 #ffffff',

    Token.Toolbar.Title:             '#888888',
    Token.Toolbar.Title.Text:    'bg:#444444 #ffffff',

    Token.Menu.Completions.MultiColumnMeta: 'bg:#ffffff #000000 bold',

    Token.Break: 'bg:#ff4444 #ffffff',
    Token.Break.Condition: 'bg:#880000 #ffffff',
    Token.CurrentLine: 'bg:#4444ff #ffffff',
    Token.Separator: '#888888',

    Token.Name.Selected: 'bold underline',

    Token.Pdb.Error: '#aa0000 bold',

    Token.PdbCommand: 'bg:#444444 #ffffff bold',
}

def get_ui_style():
    style = {}
    style.update(default_ui_style)
    style.update(ptpdb_style_extensions)
    return style
