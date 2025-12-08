from uipath.platform.common import CreateTask, InvokeProcess, WaitJob, WaitTask, WaitEscalation, CreateEscalation
from workflows.events import InputRequiredEvent


class InvokeProcessEvent(InvokeProcess, InputRequiredEvent):
    pass


class WaitJobEvent(WaitJob, InputRequiredEvent):
    pass


class CreateTaskEvent(CreateTask, InputRequiredEvent):
    pass


class WaitTaskEvent(WaitTask, InputRequiredEvent):
    pass

class WaitEscalationEvent(WaitEscalation, InputRequiredEvent):
    pass

class CreateEscalationEvent(CreateEscalation, InputRequiredEvent):
    pass
