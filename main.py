""" TODO list for features:
- refactor (/)
threadpool (?)
locking states, better state handling
message types (?)
heartbeat/idle message (e.g. script started, finished, skipped...)
error handling
cleanup
logging
- decode json to obj (e.g. protobuf) (/)
gzip, binary
default source directory
pre run for script metadata -> run without ws
run in background (extended socket scoped session) -> run without ws
- handle order of outputs (/)
doc comments
- split source files (/)
delete widget (e.g. cell ran, but no widget update)

get full state
static file handler
nb widgets
more widget
turn into a package
add typing everywhere
cookies
get available scripts

------ BASE -----

get nb source code from...
test
security
layouts

----- MVP -----

apis
schedule
favourites
"""

from src.plots.server import Server

server = Server.get_current()

server.add_script('../../nb_script.ipynb')

server.start(8888)
