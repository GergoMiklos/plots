import json
import sys
import threading
import types
from typing import Optional, Any
from uuid import uuid4

import nbformat
import tornado.web
import tornado.websocket
import tornado.ioloop

from src.plots.run_context import RunContext, set_run_context, ScriptInfo, SessionState

# todo: locking states, threadpool, cleanup

ioloop = tornado.ioloop.IOLoop.current()


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    async def open(self):
        print("New client connected")
        await self.write_message("You are connected")
        # self.read_queue = Queue(1)
        server = Server.get_current()
        server.open(self)

    # async def on_message(self, message):
    #     print(message)

    # async def on_message(self, message):
    #     # self.singleton.on_message(message)
    #     print('Putting message:', message)
    #     await self.read_queue.put(message)
    #
    # async def read_message(self):
    #     print('Waiting message...')
    #     msg = await self.read_queue.get()
    #     print('Got message:', msg)
    #     return msg

    # def on_close(self):
    #     print("Client disconnected")

    def check_origin(self, origin):
        return True


class Server:
    _singleton: Optional["Server"] = None

    @classmethod
    def get_current(cls) -> "Server":
        if Server._singleton is None:
            Server._singleton = Server()
        return Server._singleton

    def __init__(self):
        if Server._singleton is not None:
            raise RuntimeError("Singleton already initialized. Call 'get_current' instead")
        Server._singleton = self

        self.scripts = {}
        self.sessions = {}

    def open(self, websocket: WebSocketHandler):
        script_info = ScriptInfo('../../nb_script.ipynb')  # todo get by url + create if missing
        session_id = uuid4()

        websocket.on_close = lambda _: self.close(session_id)

        self.sessions[session_id] = SessionHandler(session_id, websocket, ioloop, script_info)

    def close(self, session_id):
        self.sessions[session_id].close()
        del self.sessions[session_id]


class SessionHandler:  # session based handler for messages and everything
    def __init__(self, session_id, websocket, ioloop, script_info: ScriptInfo):
        self.session_id = session_id
        # Tornado web server is available only from the main thread,
        # which can be reached by executing a callback through the main ioloop.
        # See: https://www.tornadoweb.org/en/stable/web.html#thread-safety-notes
        self.ioloop = ioloop

        self.websocket = websocket
        self.websocket.on_message = self._on_input

        self.script_runner = ScriptRunner(
            run_context=RunContext(write_output=self._write_output),
            script_info=script_info
        )
        self.script_runner.run()

    def _on_input(self, message):
        print('input:', message)
        self.script_runner.run()

    def _write_output(self, message):
        ioloop.add_callback(self.websocket.write_message, message)

    def close(self):
        print('Session closed!')


class ScriptRunner:
    def __init__(self, run_context: RunContext, script_info: ScriptInfo):
        self.run_context = run_context
        self.script_info = script_info
        self.script_module = None
        self.script_thread = None

    def run(self):
        print('Starting thread...')
        self.script_thread = threading.Thread(
            target=self._run_script,
            name="ScriptRunner:" + self.script_info.name,
        )
        self.script_thread.start()

        self.script_thread.join()  # todo only for debug
        print_module(self.script_module)

    def _run_script(self):
        set_run_context(self.run_context)

        with open(self.script_info.script_path, "r", encoding="utf-8") as file:
            notebook = nbformat.read(file, 4)

        if not self.script_module:
            module = types.ModuleType("__main__")
            module.__file__ = self.script_info.script_path
            module.__loader__ = self
            sys.modules["__main__"] = module
            self.script_module = module

        print('Running cells...')
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                exec(cell.source, self.script_module.__dict__)  # todo transform cell with IPython, compile


# class NotebookRunner:
#     """ Investigate:
#   nbclient: https://nbclient.readthedocs.io/en/latest/reference/nbclient.html
#   IPython InteractiveShell: https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html
#     """


def print_module(module):
    import pprint
    pp = pprint.PrettyPrinter(depth=4)
    builtins = ['__name__', '__doc__', '__package__', '__loader__', '__spec__', '__file__', '__builtins__']
    user_data = {key: module.__dict__[key] for key in module.__dict__ if key not in builtins}
    pp.pprint(f"{user_data=}")


application = tornado.web.Application([
    (r"/", WebSocketHandler),
])
port = 8888
application.listen(port)
print('Application started listening on port', port)

ioloop.start()
