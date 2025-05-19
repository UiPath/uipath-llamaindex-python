from uipath._cli.middlewares import Middlewares

from ._cli.cli_init import llama_init_middleware
from ._cli.cli_run import llama_run_middleware


def register_middleware():
    """This function will be called by the entry point system when uipath-llama is installed"""
    Middlewares.register("init", llama_init_middleware)
    Middlewares.register("run", llama_run_middleware)
