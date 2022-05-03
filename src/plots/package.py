import threading
from abc import ABC, abstractmethod

from src.plots.widget import Widget, TextInput, Text


class _BaseSession(ABC):
    @abstractmethod
    def text(self, value, key=None):
        pass

    @abstractmethod
    def text_input(self, label, key=None, default_value=None):
        # todo execution strategy: “cell”/”cells below”/”all cells"
        pass


class _InlineSession(_BaseSession):
    def text(self, value, key=None):
        print(value)

    def text_input(self, label, key=None, default_value=None):
        return input(label)


class _ServerSession(_BaseSession):
    def __init__(self):
        self._context = None

    def _set_run_context(self):
        from src.plots.run_context import get_run_context
        self._context = get_run_context()

    def text(self, value, key=None):
        self._widget(Text(value, key))

    def text_input(self, label, key=None, default_value=None):
        return self._input_widget(TextInput(default_value, label, key))

    def _input_widget(self, widget):
        self._set_run_context()

        if widget.key in self._context.session_context.widget_states.keys():  # todo: add cell id check
            widget.value = self._context.session_context.widget_states[widget.key].widget.value

        self._widget(widget)

        return widget.value

    def _widget(self, widget: Widget):
        self._set_run_context()
        self._context.current_widget_index += 1

        if self._context.stop_execution:  # FIXME: locking? Does not help here!
            return widget.value

        self._context.session_context.send_widget(
            widget,
            self._context.current_cell_id,
            self._context.current_cell_index,
            self._context.current_widget_index,
        )


def _get_app() -> _BaseSession:
    if threading.current_thread().name.startswith('ScriptRunner'):
        return _ServerSession()
    else:
        return _InlineSession()


app = _get_app()
