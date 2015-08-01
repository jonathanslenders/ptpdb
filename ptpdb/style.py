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
    Token.PdbCommand:                              'bold',
    Token.CompletionHint.Symbol:                   '#9a8888',
    Token.CompletionHint.Parameter:                '#ba4444 bold',
    Token.Toolbar.Status.Pdb.Filename:             'bg:#222222 #aaaaaa',
    Token.Toolbar.Status.Pdb.Lineno:               'bg:#222222 #ffffff',
    Token.Toolbar.Status.Pdb.Shortcut.Key:         'bg:#222222 #aaaaaa',
    Token.Toolbar.Status.Pdb.Shortcut.Description: 'bg:#222222 #aaaaaa',

    Token.Toolbar.Location:             'underline',
    Token.Toolbar.Location.Filename:    '',
    Token.Toolbar.Location.Lineno:      '',
}

def get_ui_style():
    style = {}
    style.update(default_ui_style)
    style.update(ptpdb_style_extensions)
    return style
