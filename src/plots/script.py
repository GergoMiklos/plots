from typing import Optional, List

from src.plots.util import get_filename


class ScriptInfo:
    """
    Script scope:
    Information about notebook script
    [global-script cache]
    """

    def __init__(self, script_path: str):
        self.script_path = script_path
        self.name = get_filename(script_path)
        self.n_cells = None
        self.compiled_cells: Optional[List[NotebookCell]] = None

        # self.script_hash = None (for detecting changes)
        # self.widget_states = None (global pre-cached)
        # self.statistics = None


class NotebookCell:
    def __init__(self, cell_id, cell_index, cell_code):
        self.id = cell_id
        self.index = cell_index
        self.code = cell_code
