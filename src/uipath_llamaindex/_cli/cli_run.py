import asyncio
import logging
from os import environ as env
from typing import Optional

from dotenv import load_dotenv
from uipath._cli._runtime._contracts import UiPathTraceContext
from uipath._cli.middlewares import MiddlewareResult

from ._runtime._context import UiPathLlamaIndexRuntimeContext
from ._runtime._exception import UiPathLlamaIndexRuntimeError
from ._runtime._runtime import UiPathLlamaIndexRuntime
from ._utils._config import LlamaIndexConfig

logger = logging.getLogger(__name__)
load_dotenv()


def llamaindex_run_middleware(
    entrypoint: Optional[str], input: Optional[str], resume: bool, **kwargs
) -> MiddlewareResult:
    """Middleware to handle LlamaIndex agent execution"""

    config = LlamaIndexConfig()
    if not config.exists:
        return MiddlewareResult(
            should_continue=True
        )  # Continue with normal flow if no llama_index.json

    try:

        async def execute():
            context = UiPathLlamaIndexRuntimeContext.from_config(
                env.get("UIPATH_CONFIG_PATH", "uipath.json"), **kwargs
            )
            context.config = config
            context.entrypoint = entrypoint
            context.input = input
            context.resume = resume
            context.debug = kwargs.get("debug", False)
            context.input_file = kwargs.get("input_file", None)
            context.execution_output_file = kwargs.get("execution_output_file", None)
            context.is_eval_run = kwargs.get("is_eval_run", False)
            context.logs_min_level = env.get("LOG_LEVEL", "INFO")
            context.job_id = env.get("UIPATH_JOB_KEY")
            context.trace_id = env.get("UIPATH_TRACE_ID")
            context.tracing_enabled = env.get("UIPATH_TRACING_ENABLED", True)
            context.trace_context = UiPathTraceContext(
                enabled=env.get("UIPATH_TRACING_ENABLED", True),
                trace_id=env.get("UIPATH_TRACE_ID"),
                parent_span_id=env.get("UIPATH_PARENT_SPAN_ID"),
                root_span_id=env.get("UIPATH_ROOT_SPAN_ID"),
                job_id=env.get("UIPATH_JOB_KEY"),
                org_id=env.get("UIPATH_ORGANIZATION_ID"),
                tenant_id=env.get("UIPATH_TENANT_ID"),
                process_key=env.get("UIPATH_PROCESS_UUID"),
                folder_key=env.get("UIPATH_FOLDER_KEY"),
            )

            env["UIPATH_REQUESTING_PRODUCT"] = "uipath-python-sdk"
            env["UIPATH_REQUESTING_FEATURE"] = "llamaindex"

            async with UiPathLlamaIndexRuntime.from_context(context) as runtime:
                await runtime.execute()

        asyncio.run(execute())

        return MiddlewareResult(should_continue=False, error_message=None)

    except UiPathLlamaIndexRuntimeError as e:
        return MiddlewareResult(
            should_continue=False,
            error_message=e.error_info.detail,
            should_include_stacktrace=True,
        )
    except Exception as e:
        return MiddlewareResult(
            should_continue=False,
            error_message=f"Error: {str(e)}",
            should_include_stacktrace=True,
        )
