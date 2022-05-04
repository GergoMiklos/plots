# plots

Experiments for serving ipynb notebook files through Tornado websockets as a web application

---

### How it works:

- The client connects through web socket
- The server reads and compiles the notebook's source code and executes it cell by cell
- The notebook calls widgets
- The widgets send their states to the client
- The client displays the widgets

- On user input the client sends the updated states to the server
- The server calculates wich cell to execute again
