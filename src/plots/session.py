import json
from typing import Dict, Optional, Any, List

from src.plots.run_context import SessionContext
from src.plots.runner import ScriptRunner
from src.plots.script import ScriptInfo
from src.plots.util import to_json, from_json
from src.plots.widget import Widget


class InputMessage:
    def __init__(self, message_type, data):
        self.message_type = message_type
        self.data = data

    @classmethod
    def from_json(cls, json_str) -> "InputMessage":
        message = cls(**json.loads(json_str))
        if message.message_type == WidgetStateUpdate.MESSAGE_TYPE:
            message.data = [WidgetStateUpdate(**json_dict) for json_dict in message.data]
        return message


class WidgetStateUpdate:
    MESSAGE_TYPE = 'WIDGET_STATE_UPDATE'

    def __init__(self, widget_key, value):
        self.widget_key = widget_key
        self.value = value

    @classmethod
    def from_json(cls, json_str) -> "WidgetStateUpdate":
        return cls(**json.loads(json_str))


class OutputMessage:
    def __init__(self, message_type, data):
        self.message_type = message_type
        self.data = data


class WidgetState:  # = Output message
    def __init__(self, widget_type, cell_id, cell_index, widget_index, widget: Widget):
        self.widget_key = widget.key
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

    async def send_widget_states(self, widget_states: Optional[List[WidgetState]] = None):
        if not widget_states:
            widget_states = self.widget_states.values()

        def widget_state_sorter(widget_state: WidgetState):
            return widget_state.widget_index, widget_state.cell_index

        widget_states.sort(key=widget_state_sorter)

        await self.websocket.write_message(to_json(
            OutputMessage(message_type='WIDGET_STATES', data=widget_states)
        ))  # todo: batching

    async def _on_input(self, message_str):
        """
        Receiving inputs from the client, given by its input key.
        If the input value changed, reruns the script with the new value
        """
        message = InputMessage.from_json(message_str)
        if not message.message_type == WidgetStateUpdate.MESSAGE_TYPE:
            return

        # FIXME: investigate locking strategies for input state
        n_cells = self.script_runner.script_info.n_cells + 1
        smallest_cell_index = n_cells + 1
        for state_update in message.data:
            widget_state = self.widget_states.get(state_update.widget_key)
            if widget_state is not None and not widget_state.widget.value == state_update.value:
                self.widget_states[state_update.widget_key].widget.value = state_update.value
                cell_index = self.widget_states[state_update.widget_key].cell_index
                if cell_index < smallest_cell_index:
                    smallest_cell_index = cell_index

        if smallest_cell_index < n_cells:
            self.script_runner.run(cell_index=smallest_cell_index)

    def send_widget(self, widget: Widget, cell_id, cell_index, widget_index):
        """
        Sending output to the client through the websocket
        Should be called from the script thread
        """
        self.widget_states[widget.key] = WidgetState(
            widget_type=widget.WIDGET_TYPE,
            cell_id=cell_id,
            cell_index=cell_index,
            widget_index=widget_index,
            widget=widget
        )  # todo: not re-create but update?

        # todo: do not send if nothing changed? Later: hash and cache
        # Using ioloop callback, because Tornado web server is available only from the main thread
        self.ioloop.add_callback(self.send_widget_states, [self.widget_states[widget.key]])

    def close(self):
        print('Session closed')
