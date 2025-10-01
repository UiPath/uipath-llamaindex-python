from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)


class DataEvent(StartEvent):
    numbers: list[int]


class ProcessedEvent(Event):
    sum_result: int
    count: int


class ResultEvent(StopEvent):
    sum_result: int
    count: int
    average: float


class MathFlow(Workflow):
    @step
    async def calculate_sum(self, ev: DataEvent) -> ProcessedEvent:
        numbers = ev.numbers

        total = sum(numbers)
        count = len(numbers)

        return ProcessedEvent(sum_result=total, count=count)

    @step
    async def calculate_average(self, ev: ProcessedEvent) -> ResultEvent:
        sum_result = ev.sum_result
        count = ev.count

        average = sum_result / count if count > 0 else 0

        return ResultEvent(sum_result=sum_result, count=count, average=average)


agent = MathFlow(timeout=60, verbose=False)
