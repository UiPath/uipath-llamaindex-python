from typing import Optional

from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)


class TopicEvent(StartEvent):
    topic: str
    param: Optional[str] = None


class JokeEvent(Event):
    joke: str


class CritiqueEvent(StopEvent):
    joke: str
    critique: str
    param: Optional[str] = None


class JokeFlow(Workflow):
    pass

    @step
    async def generate_joke(self, ev: TopicEvent) -> JokeEvent:
        topic = ev.topic

        prompt = f"Write your best joke about {topic}."
        response = f"response for prompt: {prompt}"
        return JokeEvent(joke=str(response))

    @step
    async def critique_joke(self, ev: JokeEvent) -> CritiqueEvent:
        joke = ev.joke

        response = f"Mock critique for: {joke}"
        return CritiqueEvent(joke=joke, critique=str(response))


agent = JokeFlow(timeout=60, verbose=False)
