from uipath._cli.middlewares import Middlewares

from ._cli.cli_new import openai_agents_new_middleware


def register_middleware():
    """This function will be called by the entry point system when uipath-openai-agents is installed"""
    Middlewares.register("new", openai_agents_new_middleware)
