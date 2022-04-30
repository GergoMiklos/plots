import asyncio
import json
import sys
import threading
import time
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

# import asyncio todo: we need different loops in different threads, otherwise everything will be execed on the main
# from tornado.platform.asyncio import AnyThreadEventLoopPolicy
# asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

ioloop = tornado.ioloop.IOLoop.current()


# TODO !!! : https://www.tornadoweb.org/en/stable/web.html#thread-safety-notes

# todo: locking states, threadpool, cleanup

class WsHandler(tornado.websocket.WebSocketHandler):

    async def open(self):
        print("New client connected")
        await self.write_message("You are connected")
        self.read_queue = Queue(1)
        self.singleton = Singleton.get_current()
        self.singleton.open(self)

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
    # todo  shuold be: store the collection of script runners, nothing else
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
        self.ws: WsHandler = None
        self.sr = None
        self.periodic = None

    def open(self, ws):
        self.ws = ws
        self.sr = ScriptRunner(ScriptRunContext('../../nb_script.ipynb'))
        # todo use server instead of ws, so it can contain logic (like blocking output on rerun)
        self.ws.on_message = self.sr.rerun
        self.periodic = tornado.ioloop.PeriodicCallback(self.output, callback_time=100, jitter=0.1)
        ioloop.spawn_callback(self.listening)
        self.periodic.start()

    def output(self):
        if len(self.sr.ctx.output) > 0:
            self.write_message(self.sr.ctx.output.pop(0))

    async def listening(self):
        print('listening...')
        while True:
            e = await self.sr.ctx.q.get()
            self.write_message(e)

    def write_message(self, message):
        self.ws.write_message(">>> " + message)


class ScriptRunner:
    def __init__(self, ctx: ScriptRunContext = None):
        self.script_path = ctx.script_path
        self.script_thread = None
        self.ctx = ctx

    def rerun(self, msg):
        if self.script_thread and self.script_thread.is_alive():
            self.ctx.data = 'rerun: ' + msg
        self.run()

    def run(self):
        print('Starting thread...')
        self.script_thread = threading.Thread(
            target=self._run_script_thread,
            name="ScriptRunner:" + self.script_path,
            args=[self.ctx]
        )
        self.script_thread.start()
        self.script_thread.join()  # todo not needed?
        print('Ctx data after run:', json.dumps(self.ctx.data, indent=4))

    def _run_script_thread(self, ctx):  # todo we should do an infinite thread
        print('Running thread...')
        set_script_run_context(ctx)
        self.nb_runner = NotebookRunner(ctx.script_path)
        self.nb_runner.run()


class NotebookRunner:
    """
    Todo: what is the difference between:
    - [ nbcleint: https://nbclient.readthedocs.io/en/latest/reference/nbclient.html ] does not fit to reqs
    - IPython InteractiveShell: https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html
    """

    def __init__(self, path):
        self.module = None
        self.path = path

    def run(self,):
        print('Running notebook...')
        with open(self.path, "r", encoding="utf-8") as file:
            notebook = nbformat.read(file, 4)

        if not self.module:
            module = types.ModuleType("__main__")
            module.__file__ = self.path
            module.__loader__ = self
            sys.modules["__main__"] = module
            self.module = module

        for cell in notebook.cells:
            if cell.cell_type == 'code':
                exec(cell.source, self.module.__dict__)  # todo transform cell with IPython

        print_module(self.module.__dict__)

    def run_cell(self, cell_i=None):
        print('Running cell...')
        with open(self.path, "r", encoding="utf-8") as file:
            notebook = nbformat.read(file, 4)

        cell = [cell for cell in notebook.cells if  cell.cell_type == 'code'][cell_i]
        exec(cell.source, self.module.__dict__)  # todo transform cell with IPython

        print_module(self.module.__dict__)


def get_filename(path):
    return path.split('/\\')[-1].replace('.ipynb', '')

def print_module(module):
    print(json.dumps(module.__dict__))


application = tornado.web.Application([
    (r"/", WsHandler),
])
application.listen(8888)

ioloop.start()
