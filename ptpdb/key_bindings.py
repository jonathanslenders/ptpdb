from __future__ import unicode_literals
from prompt_toolkit.document import Document
from prompt_toolkit.enums import DEFAULT_BUFFER, DUMMY_BUFFER
from prompt_toolkit.filters import HasFocus, Condition
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.keys import Keys

__all__ = (
    'load_custom_pdb_key_bindings',
)


def load_custom_pdb_key_bindings(ptpdb, registry):
    """
    Custom key bindings.
    """
    handle = registry.add_binding

    source_code_has_focus = HasFocus('source_code') & Condition(
        lambda cli: not ptpdb.python_input.show_exit_confirmation)

    def return_text(event, text):
        buffer = event.cli.buffers[DEFAULT_BUFFER]
        buffer.document = Document(text)
        event.cli.set_return_value(buffer.document)

    @handle(Keys.ControlX, eager=True)
    def _(event):
        """
        Switch focus between source code and CLI.

        Eager, because we want to ignore CtrlX-CtrlE and other key bindings
        starting with CtrlX.
        """
        vi_state = ptpdb.python_input.key_bindings_manager.get_vi_state(event.cli)

        if event.cli.current_buffer_name == DEFAULT_BUFFER:
            event.cli.focus('source_code')
            vi_state.input_mode = InputMode.NAVIGATION

        elif event.cli.current_buffer_name == 'source_code' and not ptpdb.callstack_focussed:
            ptpdb.callstack_focussed = True
            event.cli.focus(DUMMY_BUFFER)

        else:
            ptpdb.callstack_focussed = False
            event.cli.focus(DEFAULT_BUFFER)
            vi_state.input_mode = InputMode.INSERT

    @handle(' ', filter=source_code_has_focus)
    @handle('b', filter=source_code_has_focus)
    @handle(Keys.ControlJ, filter=source_code_has_focus)
    def _(event):
        """
        Set/clear break.
        """
        lineno = event.cli.current_buffer.document.cursor_position_row + 1

        filename = ptpdb.canonic(ptpdb.curframe.f_code.co_filename)
        breaks = ptpdb.breaks

        if lineno in breaks.get(filename, []):
            ptpdb.clear_break(filename, lineno)
        else:
            ptpdb.set_break(filename, lineno)

    @handle('n', filter=source_code_has_focus)
    def _(event):
        """
        Debug: Next.
        """
        return_text(event, 'next')

    @handle('s', filter=source_code_has_focus)
    def _(event):
        """
        Debug: Step
        """
        return_text(event, 'step')

    @handle('c', filter=source_code_has_focus)
    def _(event):
        """
        Debug: Continue.
        """
        return_text(event, 'continue')

    @handle('q', filter=source_code_has_focus)
    def _(event):
        " Quit. "
        ptpdb.python_input.show_exit_confirmation = True

    @handle(Keys.ControlC, filter=~HasFocus(DEFAULT_BUFFER))
    def _(event):
        " Focus prompt again, wherever we are. "
        vi_state = ptpdb.python_input.key_bindings_manager.get_vi_state(event.cli)

        ptpdb.callstack_focussed = False
        event.cli.focus(DEFAULT_BUFFER)
        vi_state.input_mode = InputMode.INSERT

    # Call stack key bindings.

    call_stack_has_focus = Condition(lambda cli: ptpdb.callstack_focussed)
    handle = registry.add_binding

    @handle(Keys.Up, filter=call_stack_has_focus)
    @handle(Keys.ControlP, filter=call_stack_has_focus)
    @handle('k', filter=call_stack_has_focus)
    def _(event):
        " Go to previous frame. "
        if ptpdb.callstack_selected_frame > 0:
            ptpdb.callstack_selected_frame -= 1

    @handle(Keys.Down, filter=call_stack_has_focus)
    @handle(Keys.ControlN, filter=call_stack_has_focus)
    @handle('j', filter=call_stack_has_focus)
    def _(event):
        " Go to next frame. "
        if ptpdb.callstack_selected_frame < len(ptpdb.stack) - 1:
            ptpdb.callstack_selected_frame += 1

    @handle(Keys.ControlJ, filter=call_stack_has_focus)
    def _(event):
        """
        Go up/down to the selected frame.
        """
        # Find index of current frame.
        current = 0
        selected = ptpdb.callstack_selected_frame

        for i, (frame, lineno) in enumerate(ptpdb.stack):
            if frame is ptpdb.curframe:
                current = i

        if current > selected:
            return_text(event, 'up %i' % (current - selected))

        elif current < selected:
            return_text(event, 'down  %i' % (selected - current))
