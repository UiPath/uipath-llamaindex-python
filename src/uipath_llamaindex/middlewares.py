from uipath._cli.middlewares import Middlewares

from ._cli.cli_init import llamaindex_init_middleware
from ._cli.cli_new import llamaindex_new_middleware
from ._cli.cli_run import llamaindex_run_middleware


def register_middleware():
    """This function will be called by the entry point system when uipath-llamaindex is installed"""
    Middlewares.register("init", llamaindex_init_middleware)
    Middlewares.register("run", llamaindex_run_middleware)
    Middlewares.register("new", llamaindex_new_middleware)
