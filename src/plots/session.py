import json
from typing import Dict, Optional

from src.plots.run_context import SessionContext
from src.plots.runner import ScriptRunner
from src.plots.script import ScriptInfo
from src.plots.util import to_json
from src.plots.widget import Widget


class InputMessage:
    def __init__(self, widget_key, widget_type, value):
        self.widget_key = widget_key
        self.widget_type = widget_type
        self.value = value

    @classmethod
    def from_json(cls, json_str) -> "InputMessage":
        return cls(**json.loads(json_str))


class WidgetState:  # = Output message
    def __init__(self, widget_key, widget_type, cell_id, cell_index, widget_index, widget: Widget):
        self.widget_key = widget_key
        self.widget_type = widget_type
        self.cell_id = cell_id
        self.cell_index = cell_index
        self.widget_index = widget_index
        self.widget: Widget = widget


class SessionHandler:  # session based handler for messages and everything
    def __init__(self, session_id, websocket, ioloop, script_info: ScriptInfo):
        self.session_id = session_id
        # Tornado web server is available only from the main thread,
        # which can be reached by executing a callback through the main ioloop.
        # See: https://www.tornadoweb.org/en/stable/web.html#thread-safety-notes
        self.ioloop = ioloop

        self.widget_states: Dict[str, WidgetState] = {}

        self.websocket = websocket
        self.websocket.on_message = self._on_input

        self.script_runner = ScriptRunner(
            script_info=script_info,
            session_context=SessionContext(self.widget_states, self.send_widget)
        )
        self.script_runner.run()

    async def send_widget_states(self, widget_states: Optional[Dict[str, WidgetState]] = None):
        if not widget_states:
            widget_states = self.widget_states

        await self.websocket.write_message(to_json(widget_states))  # todo: sorting and batching

        # def widget_state_sorter(widget_state: WidgetState):
        #     return widget_state.widget_index, widget_state.cell_index

    async def _on_input(self, message_str):
        """
        Receiving inputs from the client, given by its input key.
        If the input value changed, reruns the script with the new value
        """
        message = InputMessage.from_json(message_str)
        # FIXME: investigate locking strategies for input state
        widget_state = self.widget_states.get(message.widget_key)
        if widget_state is not None and not widget_state.widget.value == message.value:
            self.widget_states[message.widget_key].widget.value = message.value
            self.script_runner.run(cell_id=widget_state.cell_id)
        else:
            print('Rerun skipped with message key:', message.widget_key)

    def send_widget(self, widget: Widget, cell_id, cell_index, widget_index):
        """
        Sending output to the client through the websocket
        Should be called from the script thread
        """
        self.widget_states[widget.key] = WidgetState(
            widget_key=widget.key,
            widget_type=widget.WIDGET_TYPE,
            cell_id=cell_id,
            cell_index=cell_index,
            widget_index=widget_index,
            widget=widget
        )  # todo: not re-create but update?

        # todo: do not send if nothing changed? Later: hash and cache
        # Using ioloop callback, because Tornado web server is available only from the main thread
        self.ioloop.add_callback(self.send_widget_states, {widget.key: self.widget_states[widget.key]})

    def close(self):
        print('Session closed')
