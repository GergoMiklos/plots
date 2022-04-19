import sys
import threading
import types
from typing import Optional, Any
from uuid import uuid4

import nbformat as nbformat
import tornado.web
import tornado.websocket
import tornado.ioloop
from tornado import httputil


class WsHandler(tornado.websocket.WebSocketHandler):

    async def open(self):
        print("New client connected")
        await self.write_message("You are connected")
        self.singleton = Singleton.get_current()

    async def on_message(self, message):
        self.singleton.write_message(message)

    def on_close(self):
        print("Client disconnected")

    def check_origin(self, origin):
        return True


class Singleton:
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
        self.socket = None
        self.nbr = None

    def open(self, socket):
        self.socket = socket
        self.nbr = NotebookRunner('../../nb_script.ipynb')

    def on_message(self, message):
        self.nbr.run()

    def write_message(self, message):
        self.socket.write_message("You said: " + message)



# class ScriptRunner:
#     def __init__(self, script_path, socket=None):
#         self.script_path = script_path
#         self.script_thread = None
#
#     def run(self):
#         self.script_thread = threading.Thread(
#             target=self._run_script_thread,
#             name="ScriptRunner." + self.script_path,
#         )
#         self.script_thread.start()
#
#     def _run_script_thread(self):
#         nb_runner = NotebookRunner(self.script_path)
#         nb_runner.run()


class NotebookRunner:
    """
    Todo: what is the difference between:
    - [ nbcleint: https://nbclient.readthedocs.io/en/latest/reference/nbclient.html ] does not fit to reqs
    - IPython InteractiveShell: https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html
    """

    def __init__(self, path):
        self.path = path

    def run(self):
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
tornado.ioloop.IOLoop.instance().start()
