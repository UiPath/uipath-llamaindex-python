from llama_index.core.workflow import InputRequiredEvent
from uipath.platform.common import CreateTask, InvokeProcess, WaitJob, WaitTask


class InvokeProcessEvent(InvokeProcess, InputRequiredEvent):
    pass


class WaitJobEvent(WaitJob, InputRequiredEvent):
    pass


class CreateTaskEvent(CreateTask, InputRequiredEvent):
    pass


class WaitTaskEvent(WaitTask, InputRequiredEvent):
    pass
