from llama_index.core.workflow import InputRequiredEvent
from uipath.models import CreateAction, InvokeProcess, WaitAction, WaitJob


class InvokeProcessEvent(InvokeProcess, InputRequiredEvent):
    pass


class WaitJobEvent(WaitJob, InputRequiredEvent):
    pass


class CreateActionEvent(CreateAction, InputRequiredEvent):
    pass


class WaitActionEvent(WaitAction, InputRequiredEvent):
    pass
