import asyncio
import sys
import threading
import types
from typing import Optional, Any
from uuid import uuid4

import nbformat
import tornado.web
import tornado.websocket
import tornado.ioloop
from tornado import httputil
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from tornado.queues import Queue

from src.plots.run_context import ScriptRunContext, set_script_run_context

ioloop = tornado.ioloop.IOLoop.current()


class WsHandler(tornado.websocket.WebSocketHandler):

    async def open(self):
        print("New client connected")
        await self.write_message("You are connected")
        self.read_queue = Queue(1)
        self.singleton = Singleton.get_current()
        self.singleton.open(self)
        ioloop.spawn_callback(self.singleton.listen)

    async def on_message(self, message):
        # self.singleton.on_message(message)
        print('Putting message:', message)
        await self.read_queue.put(message)

    async def read_message(self):
        print('Waiting message...')
        msg = await self.read_queue.get()
        print('Got message:', msg)
        return msg

    def on_close(self):
        print("Client disconnected")

    def check_origin(self, origin):
        return True


class Singleton:  # todo not sure about that this should be singleton
    _singleton: Optional["Singleton"] = None

    @classmethod
    def get_current(cls) -> "Singleton":
        if Singleton._singleton is None:
            Singleton._singleton = Singleton()

        return Singleton._singleton

    def __init__(self):
        if Singleton._singleton is not None:
            raise RuntimeError("Singleton already initialized. Use .get_current() instead")
        Singleton._singleton = self
        self.ws = None
        self.sr = None

    def open(self, ws):
        self.ws = ws
        self.sr = ScriptRunner('../../nb_script.ipynb', ScriptRunContext(ws))
        # todo use server instead of ws, so it can contain logic (like blocking output on rerun)

    async def listen(self):
        print('Listening...')
        while True:
            msg = await self.ws.read_message()
            print('Running script on message:', msg)
            self.sr.run()

    # def on_message(self, message):
    #     print('Running script on message:', message)
    #     self.sr.run()

    def write_message(self, message):
        self.ws.write_message("You said: " + message)


class ScriptRunner:
    def __init__(self, script_path, ctx: ScriptRunContext = None):
        self.script_path = script_path
        self.script_thread = None
        self.ctx = ctx

    def run(self):
        print('Starting thread...')
        self.script_thread = threading.Thread(
            target=self._run_script_thread,
            name="ScriptRunner." + self.script_path,
        )
        self.script_thread.start()

    def _run_script_thread(self):  # todo we should do an infinite thread
        print('Running thread...')
        asyncio.set_event_loop(asyncio.new_event_loop())
        # todo grab event loop from main thread: https://github.com/tornadoweb/tornado/issues/3069
        set_script_run_context(self.ctx)
        nb_runner = NotebookRunner(self.script_path)
        nb_runner.run()


class NotebookRunner:
    """
    Todo: what is the difference between:
    - [ nbcleint: https://nbclient.readthedocs.io/en/latest/reference/nbclient.html ] does not fit to reqs
    - IPython InteractiveShell: https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html
    """

    def __init__(self, path):
        self.path = path

    def run(self):
        print('Running notebook...')
        with open(self.path, "r", encoding="utf-8") as file:
            notebook = nbformat.read(file, 4)

        module = types.ModuleType("__main__")
        module.__file__ = self.path
        module.__loader__ = self
        sys.modules["__main__"] = module

        for cell in notebook.cells:
            if cell.cell_type == 'code':
                exec(cell.source, module.__dict__)  # todo transform cell


def get_filename(path):
    return path.split('/\\')[-1].replace('.ipynb', '')


application = tornado.web.Application([
    (r"/", WsHandler),
])
application.listen(8888)

ioloop.start()
