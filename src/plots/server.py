from typing import Optional, Union, Dict

import tornado.ioloop
import tornado.web
import tornado.websocket

from src.plots.script import ScriptInfo
from src.plots.session import SessionHandler
from src.plots.util import generate_id


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    async def on_message(self, message: Union[str, bytes]):
        pass

    async def open(self, script_name_param):
        print("New client connected")
        server = Server.get_current()
        await server.open_connection(self, script_name_param)

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

        self.ioloop = None
        self.tornado_web_application = None

        self.scripts: Dict[str, ScriptInfo] = {}
        self.sessions: Dict[str, SessionHandler] = {}

    def start(self, port=8888):
        """
        Starts the tornado web application
        """
        self.ioloop = tornado.ioloop.IOLoop.current()

        self.tornado_web_application = tornado.web.Application([
            (r"/ws/(.*)", WebSocketHandler),
        ])
        self.tornado_web_application.listen(port)
        print('Application started listening on port', port)

        self.ioloop.start()

    async def open_connection(self, websocket: WebSocketHandler, script_name):
        script_info = self.scripts.get(script_name)
        # todo: try to check in a default folder, also read those on startup
        if not script_info:
            raise tornado.web.HTTPError(404)  # todo investigate: sending error in ws

        session_id = generate_id()

        websocket.on_close = lambda: self.close_connection(session_id)

        session_handler = SessionHandler(session_id, websocket, self.ioloop, script_info)
        self.sessions[session_id] = session_handler

    def close_connection(self, session_id):
        self.sessions[session_id].close()
        del self.sessions[session_id]

    def add_script(self, script_path):
        script_info = ScriptInfo(script_path)
        self.scripts[script_info.name] = script_info

    def get_available_scripts(self):
        return self.scripts.keys()
