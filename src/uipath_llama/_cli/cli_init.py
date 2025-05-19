import asyncio
import json

from uipath._cli.middlewares import MiddlewareResult

from ._utils._config import LlamaConfig


async def llama_init_middleware_async(entrypoint: str) -> MiddlewareResult:
    """Middleware to check for llama.json and create uipath.json with schemas"""
    config = LlamaConfig()
    if not config.exists:
        return MiddlewareResult(
            should_continue=True
        )  # Continue with normal flow if no llama.json

    try:
        config.load_config()

        entrypoints = []

        uipath_data = {
            "entryPoints": entrypoints
        }

        config_path = "uipath.json"

        with open(config_path, "w") as f:
            json.dump(uipath_data, f, indent=4)

        return MiddlewareResult(
            should_continue=False,
            info_message=f"Configuration file {config_path} created successfully.",
        )

    except Exception as e:
        return MiddlewareResult(
            should_continue=False,
            error_message=f"Error processing Llama agent configuration: {str(e)}",
            should_include_stacktrace=True,
        )


def mcp_init_middleware(entrypoint: str) -> MiddlewareResult:
    """Middleware to check for llama.json and create uipath.json with schemas"""
    return asyncio.run(llama_init_middleware_async(entrypoint))
