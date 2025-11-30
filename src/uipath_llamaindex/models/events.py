from uipath.platform.common import CreateTask, InvokeProcess, WaitJob, WaitTask
from workflows.events import InputRequiredEvent


class InvokeProcessEvent(InvokeProcess, InputRequiredEvent):
    pass


class WaitJobEvent(WaitJob, InputRequiredEvent):
    pass


class CreateTaskEvent(CreateTask, InputRequiredEvent):
    pass


class WaitTaskEvent(WaitTask, InputRequiredEvent):
    pass
