from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)


class JokeEvent(Event):
    joke: str


class JokeFlow(Workflow):
    pass

    @step
    async def generate_joke(self, ev: StartEvent) -> JokeEvent:
        topic = ev.topic

        prompt = f"Write your best joke about {topic}."
        response = f"response for prompt: {prompt}"
        return JokeEvent(joke=str(response))

    @step
    async def critique_joke(self, ev: JokeEvent) -> StopEvent:
        joke = ev.joke

        response = f"Mock critique for: {joke}"
        return StopEvent(result=str(response))


agent = JokeFlow(timeout=60, verbose=False)
