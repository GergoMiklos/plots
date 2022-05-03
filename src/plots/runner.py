import sys
import threading
import types
from typing import Optional

import nbformat

from src.plots.run_context import set_run_context, RunContext, get_run_context, SessionContext
from src.plots.script import NotebookCell, ScriptInfo
from src.plots.util import generate_id


class ScriptRunner:
    def __init__(self, script_info: ScriptInfo, session_context: SessionContext):
        self.session_context: SessionContext = session_context
        self.script_info: ScriptInfo = script_info
        self.script_module = None
        self.script_thread: Optional[threading.Thread] = None

    def _precompile_script(self):
        with open(self.script_info.script_path, "r", encoding="utf-8") as file:
            notebook = nbformat.read(file, 4)

        cell_index = 0
        compiled_cells = []
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                cell_code = compile(
                    cell.source,  # TODO: transform cell with IPython
                    # Pass in the file path, so it can show up in exceptions.
                    self.script_info.script_path,
                    # We're compiling entire blocks of Python, so we need "exec" mode
                    mode="exec",
                    # Don't inherit any flags or "future" statements.
                    flags=0,
                    dont_inherit=1,
                    # Use the default optimization options.
                    optimize=-1,
                )
                compiled_cells.append(NotebookCell(generate_id(), cell_index, cell_code))
                cell_index += 1

        self.script_info.compiled_cells = compiled_cells
        self.script_info.n_cells = cell_index
        self.script_module = None  # todo: check script hash

    def _setup_script_module(self):
        module = types.ModuleType("__main__")
        module.__file__ = self.script_info.script_path
        module.__loader__ = self
        sys.modules["__main__"] = module
        self.script_module = module

    def _should_rerun(self, cell_index):
        if not cell_index:
            return True

        if not self.script_thread or not self.script_thread.is_alive():
            return True

        if get_run_context(self.script_thread).current_cell_index >= cell_index:
            get_run_context(self.script_thread).stop_execution = True
            return True

    def run(self, cell_index=None):
        if not self._should_rerun(cell_index):
            return

        print('Starting thread...')
        thread_run_context = RunContext(self.session_context)

        self.script_thread = threading.Thread(
            target=self._execute_script_thread,
            name=f"ScriptRunner:{self.script_info.name}:{generate_id()}",
            args=[thread_run_context, cell_index]
        )
        self.script_thread.start()

        # self.script_thread.join()  # FIXME: only for debug
        # print_module(self.script_module)

    def _calculate_cells_to_execute(self, cell_id=None):
        if cell_id is None:
            return self.script_info.compiled_cells

        for cell in self.script_info.compiled_cells:
            if cell_id == cell.id:
                return self.script_info.compiled_cells[cell.index:]

        # could not find the cell, return the whole notebook to execute
        return self.script_info.compiled_cells

    def _execute_script_thread(self, thread_run_context: RunContext, cell_index=None):
        if self.script_info.compiled_cells is None:
            self._precompile_script()

        if self.script_module is None:
            self._setup_script_module()

        set_run_context(thread_run_context)

        print('Running cells...')
        for cell in self._calculate_cells_to_execute(cell_index):

            thread_run_context.current_cell_id = cell.id
            thread_run_context.current_cell_index = cell.index
            thread_run_context.current_widget_index = 0

            exec(cell.code, self.script_module.__dict__)

            if thread_run_context.stop_execution:
                print('Script stopped')
                return

# class NotebookRunner:
#     """ Investigate:
#   nbclient: https://nbclient.readthedocs.io/en/latest/reference/nbclient.html
#   IPython InteractiveShell: https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html
#     """
