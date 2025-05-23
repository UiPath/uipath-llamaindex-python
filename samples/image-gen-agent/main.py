import os
import re
import tempfile
import uuid

import httpx
from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.llms.openai import OpenAI
from llama_index.tools.openai import OpenAIImageGenerationToolSpec
from uipath import UiPath


# Define the events
class TopicEvent(StartEvent):
    """Event representing the image generation topic input."""

    topic: str


class ImageEvent(Event):
    """Event representing the generated image."""

    topic: str
    image_url: str


class NamedImageEvent(Event):
    """Event representing the image with a generated name."""

    topic: str
    image_url: str
    image_name: str


class OutputEvent(StopEvent):
    """Event representing the final output."""

    image_name: str
    attachment_id: uuid.UUID


# Define the workflow
class ImageGenerationFlow(Workflow):
    """Workflow that generates an image from a topic and uploads it as an attachment."""

    @step
    async def generate_image(self, ev: TopicEvent) -> ImageEvent:
        """Generate an image based on the topic."""
        topic = ev.topic

        # Generate image
        image_tool = OpenAIImageGenerationToolSpec()

        image_url = image_tool.image_generation(text=topic)

        # Return the event with the image URL
        return ImageEvent(topic=topic, image_url=image_url)

    @step
    async def generate_image_name(self, ev: ImageEvent) -> NamedImageEvent:
        """Generate a descriptive filename for the image using LLM."""
        # Create a prompt for the LLM to generate a filename
        prompt = f"""
        Create a short, descriptive filename for an image based on this topic: "{ev.topic}"

        The filename should:
        - Be 2-5 words
        - Use underscores instead of spaces
        - Be lowercase
        - End with .png
        - Not include any special characters other than underscores
        - Be descriptive of the image content

        Return ONLY the filename with no additional text or explanations.
        """

        # Call the LLM to generate a name
        llm = OpenAI(model="gpt-3.5-turbo")
        response = await llm.acomplete(prompt)

        # Clean up the response
        image_name = str(response).strip()

        # Ensure it follows our naming conventions
        image_name = image_name.lower()
        image_name = re.sub(
            r"[^\w\s\.]", "", image_name
        )  # Remove special chars except dots
        image_name = re.sub(r"\s+", "_", image_name)  # Replace spaces with underscores

        # Make sure it ends with .png
        if not image_name.endswith(".png"):
            image_name = image_name.rstrip(".") + ".png"

        # Return the event with the image name
        return NamedImageEvent(
            topic=ev.topic, image_url=ev.image_url, image_name=image_name
        )

    @step
    async def upload_attachment(self, ev: NamedImageEvent) -> OutputEvent:
        """Download the image and upload it to UiPath."""
        # Create temp file to store the image
        temp_dir = tempfile.mkdtemp()
        image_path = os.path.join(temp_dir, "temp_image.png")

        # Download the image using httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(ev.image_url)
            if response.status_code == 200:
                # Save the image content to file
                with open(image_path, "wb") as f:
                    f.write(response.content)
            else:
                raise Exception(f"Failed to download image: {response.status_code}")

        # Upload to UiPath using async method
        uipath_client = UiPath()
        attachment_id = await uipath_client.jobs.create_attachment_async(
            name=ev.image_name,
            source_path=image_path,
            category="generated_images",
            job_key=os.environ.get("UIPATH_JOB_KEY"),
            folder_key=os.environ.get("UIPATH_FOLDER_KEY"),
        )

        # Return the final event
        return OutputEvent(
            image_name=ev.image_name,
            attachment_id=attachment_id,
        )


# Create the workflow agent
image_flow = ImageGenerationFlow(timeout=60, verbose=True)
