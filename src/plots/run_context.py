import threading
from typing import Optional


class SessionContext:
    def __init__(self, widget_states, send_widget):
        self.widget_states = widget_states
        self.send_widget = send_widget


class RunContext:
    """
    Script execution scope (per websocket message):
    Necessary elements for the running script on its own thread,
    to be able to get user's input and send output
    """

    def __init__(self, session_context: SessionContext):
        self.session_context = session_context
        self.current_cell_id = None
        self.current_cell_index = None
        self.current_widget_index = None
        self.stop_execution = False


RUN_CONTEXT_ATTR_NAME = 'RUN_CONTEXT_ATTR_NAME'


def set_run_context(ctx: RunContext, thread: Optional[threading.Thread] = None):
    if thread is None:
        thread = threading.current_thread()

    setattr(thread, RUN_CONTEXT_ATTR_NAME, ctx)


def get_run_context(thread: Optional[threading.Thread] = None) -> RunContext:
    if thread is None:
        thread = threading.current_thread()

    return getattr(thread, RUN_CONTEXT_ATTR_NAME)

# class SessionState:
#     """
#     Session scope (websocket session between messages):
#     Persistent execution information between notebook script runs,
#     to handle reruns (specific cells), input and output changes
#     [session cache]
#     """
#
#     def __init__(self, session_id, websocket):
#         pass
#
#
# class UserState:
#     """
#     User scope (between websocket sessions):
#     Persistent information between sessions
#     [user-script cache]
#     """
#
#     def __init__(self):
#         pass
