from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from uipath_llamaindex.llms import UiPathOpenAI


class TopicEvent(StartEvent):
    topic: str


class JokeEvent(Event):
    joke: str


class CritiqueEvent(StopEvent):
    joke: str
    critique: str


class JokeFlow(Workflow):
    llm = UiPathOpenAI(model="gpt-4o-mini-2024-07-18")

    @step
    async def generate_joke(self, ev: TopicEvent) -> JokeEvent:
        topic = ev.topic

        prompt = f"Write your best joke about {topic}."
        response = await self.llm.acomplete(prompt)
        return JokeEvent(joke=str(response))

    @step
    async def critique_joke(self, ev: JokeEvent) -> CritiqueEvent:
        joke = ev.joke

        prompt = f"Give a thorough analysis and critique of the following joke: {joke}"
        response = await self.llm.acomplete(prompt)
        return CritiqueEvent(joke=joke, critique=str(response))


agent = JokeFlow(timeout=60, verbose=False)
