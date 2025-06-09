import json
import os
import tempfile
from typing import Any, Dict, List

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
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from uipath import UiPath


# Define the events
class BookRequestEvent(StartEvent):
    """Event representing the book generation request."""

    topic: str
    num_chapters: int


class BookOutlineEvent(Event):
    """Event representing the generated book outline with chapter titles."""

    topic: str
    book_title: str
    chapters: List[Dict[str, Any]]


class ChaptersContentEvent(Event):
    """Event representing the chapters content."""

    topic: str
    book_title: str
    chapters_content: List[Dict[str, Any]]


class ChaptersFilesEvent(Event):
    """Event representing the chapters files."""

    topic: str
    book_title: str
    chapter_files: List[Dict[str, Any]]


class BookCompleteEvent(StopEvent):
    """Event representing the completed book with all attachments."""

    topic: str
    book_title: str
    total_chapters: int
    chapter_attachments: List[Dict[str, Any]]


# Define the workflow
class CompleteBookFlow(Workflow):
    """Workflow that generates a complete multi-modal book with chapters."""

    @step
    async def generate_book_outline(self, ev: BookRequestEvent) -> BookOutlineEvent:
        """Generate a book outline with chapter titles and descriptions."""
        prompt = f"""
        Create an outline for a {ev.num_chapters}-chapter book about: "{ev.topic}"

        Return a JSON structure with:
        {{
            "book_title": "Creative and engaging book title",
            "chapters": [
                {{
                    "chapter_num": 1,
                    "title": "Chapter title",
                    "description": "Brief description of what this chapter covers (2-3 sentences)",
                    "key_concepts": ["concept1", "concept2", "concept3"]
                }}
            ]
        }}

        Make it engaging and educational. Each chapter should have distinct themes that build upon each other.
        The book should flow logically from basic concepts to more advanced topics.
        """

        llm = OpenAI(model="gpt-4")
        response = await llm.acomplete(prompt)

        # Parse the JSON response
        try:
            outline = json.loads(str(response).strip())
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            outline = {
                "book_title": f"Complete Guide to {ev.topic}",
                "chapters": [
                    {
                        "chapter_num": i + 1,
                        "title": f"Chapter {i + 1}: {ev.topic} Fundamentals",
                        "description": f"This chapter covers fundamental concepts of {ev.topic}.",
                        "key_concepts": ["basics", "fundamentals", "introduction"],
                    }
                    for i in range(ev.num_chapters)
                ],
            }

        print(f" Book planned: {outline['book_title']}")
        for chapter in outline["chapters"]:
            print(f"   Chapter {chapter['chapter_num']}: {chapter['title']}")

        return BookOutlineEvent(
            topic=ev.topic,
            book_title=outline["book_title"],
            chapters=outline["chapters"],
        )

    @step
    async def generate_chapters_content(
        self, ev: BookOutlineEvent
    ) -> ChaptersContentEvent:
        """Generate detailed content."""
        print(f"\n Generating content for {len(ev.chapters)} chapters...")

        llm = OpenAI(model="gpt-4")
        chapters_content = []

        for i, chapter_info in enumerate(ev.chapters):
            print(
                f"   Writing Chapter {chapter_info['chapter_num']}: {chapter_info['title']}"
            )

            prompt = f"""
            Write a detailed chapter for the book: "{ev.book_title}"
            Overall book topic: "{ev.topic}"

            Chapter {chapter_info["chapter_num"]}: {chapter_info["title"]}
            Description: {chapter_info["description"]}
            Key concepts to cover: {", ".join(chapter_info.get("key_concepts", []))}

            This is chapter {i + 1} of {len(ev.chapters)} chapters.

            Write a comprehensive chapter (1000-1500 words) that:
            - Has clear sections and subsections with proper headings
            - Includes practical examples and real-world applications
            - Uses engaging storytelling and explanations
            - Has strong educational value
            - Flows logically and builds on previous concepts

            Also provide a 2-3 sentence summary of the chapter.

            Format your response as:
            CONTENT:
            [Full chapter content with markdown formatting]

            SUMMARY:
            [Brief summary here]
            """

            response = await llm.acomplete(prompt)
            response_text = str(response).strip()

            # Parse content and summary
            parts = response_text.split("SUMMARY:")
            content = parts[0].replace("CONTENT:", "").strip()
            summary = (
                parts[1].strip()
                if len(parts) > 1
                else f"Summary of {chapter_info['title']}"
            )

            chapter_content = {
                "chapter_num": chapter_info["chapter_num"],
                "title": chapter_info["title"],
                "description": chapter_info["description"],
                "content": content,
                "summary": summary,
            }
            chapters_content.append(chapter_content)

        print(f" All {len(chapters_content)} chapters written!")

        return ChaptersContentEvent(
            topic=ev.topic, book_title=ev.book_title, chapters_content=chapters_content
        )

    @step
    async def create_chapter_files(
        self, ev: ChaptersContentEvent
    ) -> ChaptersFilesEvent:
        """Create multiple file types for chapters."""
        print(f"\n Creating files for {len(ev.chapters_content)} chapters...")

        all_chapter_files = []

        for chapter in ev.chapters_content:
            print(
                f"   Creating files for Chapter {chapter['chapter_num']}: {chapter['title']}"
            )

            temp_dir = tempfile.mkdtemp()
            chapter_files = {}

            # 1. Create Markdown file (.md)
            md_filename = f"chapter_{chapter['chapter_num']:02d}_{self._sanitize_filename(chapter['title'])}.md"
            md_path = os.path.join(temp_dir, md_filename)

            md_content = f"""# Chapter {chapter["chapter_num"]}: {chapter["title"]}

*From: {ev.book_title}*

{chapter["content"]}

---

## Chapter Summary

{chapter["summary"]}

---
*Chapter {chapter["chapter_num"]} of {len(ev.chapters_content)} | Generated on 2025-06-09*
"""

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            chapter_files[md_filename] = md_path

            # 2. Create PDF file (.pdf)
            pdf_filename = f"chapter_{chapter['chapter_num']:02d}_{self._sanitize_filename(chapter['title'])}.pdf"
            pdf_path = os.path.join(temp_dir, pdf_filename)

            self._create_pdf(pdf_path, chapter, ev.book_title, len(ev.chapters_content))
            chapter_files[pdf_filename] = pdf_path

            # 3. Create JSON metadata file (.json)
            json_filename = f"chapter_{chapter['chapter_num']:02d}_metadata.json"
            json_path = os.path.join(temp_dir, json_filename)

            metadata = {
                "book_title": ev.book_title,
                "book_topic": ev.topic,
                "chapter_number": chapter["chapter_num"],
                "chapter_title": chapter["title"],
                "chapter_description": chapter["description"],
                "summary": chapter["summary"],
                "word_count": len(chapter["content"].split()),
                "progress": f"{chapter['chapter_num']}/{len(ev.chapters_content)}",
                "created_at": "2025-06-09",
                "file_types_generated": ["markdown", "pdf", "json", "txt", "png"],
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            chapter_files[json_filename] = json_path

            # 4. Create plain text summary (.txt)
            txt_filename = f"chapter_{chapter['chapter_num']:02d}_summary.txt"
            txt_path = os.path.join(temp_dir, txt_filename)

            txt_content = f"""BOOK: {ev.book_title}
{"=" * (len(ev.book_title) + 6)}

CHAPTER {chapter["chapter_num"]}: {chapter["title"].upper()}
{"-" * (len(chapter["title"]) + 15)}

DESCRIPTION:
{chapter["description"]}

SUMMARY:
{chapter["summary"]}

PROGRESS: Chapter {chapter["chapter_num"]} of {len(ev.chapters_content)}
WORD COUNT: {len(chapter["content"].split())} words
GENERATED: 2025-06-09

BOOK TOPIC: {ev.topic}
"""

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(txt_content)
            chapter_files[txt_filename] = txt_path

            # 5. Generate chapter illustration (.png)
            await self._generate_chapter_image(
                chapter, ev.book_title, ev.topic, temp_dir, chapter_files
            )

            chapter_file_info = {
                "chapter_num": chapter["chapter_num"],
                "chapter_title": chapter["title"],
                "files": chapter_files,
            }
            all_chapter_files.append(chapter_file_info)

        print(f" Files created for all {len(all_chapter_files)} chapters!")

        return ChaptersFilesEvent(
            topic=ev.topic,
            book_title=ev.book_title,
            chapter_files=all_chapter_files,
        )

    def _create_pdf(
        self,
        pdf_path: str,
        chapter: Dict[str, Any],
        book_title: str,
        total_chapters: int,
    ):
        """Create a professionally formatted PDF."""
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Book title
        book_title_p = Paragraph(book_title, styles["Title"])
        story.append(book_title_p)
        story.append(Spacer(1, 12))

        # Chapter title
        chapter_title = Paragraph(
            f"Chapter {chapter['chapter_num']}: {chapter['title']}", styles["Heading1"]
        )
        story.append(chapter_title)
        story.append(Spacer(1, 20))

        # Chapter description
        desc = Paragraph(f"<i>{chapter['description']}</i>", styles["Normal"])
        story.append(desc)
        story.append(Spacer(1, 20))

        # Add content (split into paragraphs)
        for paragraph in chapter["content"].split("\n\n"):
            if paragraph.strip():
                # Check if it's a heading (starts with # or ##)
                if paragraph.strip().startswith("#"):
                    # Remove markdown heading syntax
                    heading_text = paragraph.strip().lstrip("#").strip()
                    p = Paragraph(heading_text, styles["Heading2"])
                else:
                    p = Paragraph(paragraph.strip(), styles["Normal"])
                story.append(p)
                story.append(Spacer(1, 12))

        # Add summary section
        story.append(Spacer(1, 20))
        summary_title = Paragraph("Chapter Summary", styles["Heading2"])
        story.append(summary_title)
        story.append(Spacer(1, 12))

        summary_p = Paragraph(chapter["summary"], styles["Normal"])
        story.append(summary_p)

        # Footer
        story.append(Spacer(1, 30))
        footer = Paragraph(
            f"<i>Chapter {chapter['chapter_num']} of {total_chapters} | Generated on 2025-06-09</i>",
            styles["Normal"],
        )
        story.append(footer)

        doc.build(story)

    async def _generate_chapter_image(
        self,
        chapter: Dict[str, Any],
        book_title: str,
        topic: str,
        temp_dir: str,
        chapter_files: Dict[str, str],
    ):
        """Generate an illustration for the chapter."""
        prompt = f"""
        Create a professional, educational illustration for a book chapter.

        Book: "{book_title}"
        Chapter: "{chapter["title"]}"
        Topic: {topic}

        The image should be:
        - Clean and professional
        - Suitable for educational content
        - Visually represent the key themes of this specific chapter
        - Modern, minimalist style with good composition
        - Appropriate for inclusion in a technical/educational book

        Chapter focus: {chapter["description"]}
        """

        try:
            # Generate image
            image_tool = OpenAIImageGenerationToolSpec()
            image_url = image_tool.image_generation(text=prompt)

            # Download and save the image
            png_filename = f"chapter_{chapter['chapter_num']:02d}_illustration.png"
            png_path = os.path.join(temp_dir, png_filename)

            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                if response.status_code == 200:
                    with open(png_path, "wb") as f:
                        f.write(response.content)
                    chapter_files[png_filename] = png_path
                    print(f"     Generated illustration: {png_filename}")
        except Exception as e:
            print(
                f"     Could not generate image for chapter {chapter['chapter_num']}: {e}"
            )

    @step
    async def upload_chapter_files(self, ev: ChaptersFilesEvent) -> BookCompleteEvent:
        """Upload chapter files as attachments to UiPath."""
        print(f"\n Uploading files for all {len(ev.chapter_files)} chapters...")

        uipath_client = UiPath()
        all_chapter_attachments = []

        for chapter_info in ev.chapter_files:
            chapter_attachments = {}
            chapter_num = chapter_info["chapter_num"]
            chapter_title = chapter_info["chapter_title"]

            print(f"   Uploading Chapter {chapter_num}: {chapter_title}")

            for filename, file_path in chapter_info["files"].items():
                try:
                    # Determine file category based on extension
                    extension = os.path.splitext(filename)[1].lower()
                    category_map = {
                        ".md": "markdown_documents",
                        ".pdf": "pdf_documents",
                        ".json": "metadata_files",
                        ".txt": "text_files",
                        ".png": "illustrations",
                    }
                    category = category_map.get(extension, "book_files")

                    # Upload to UiPath
                    attachment_id = await uipath_client.jobs.create_attachment_async(
                        name=filename,
                        source_path=file_path,
                        category=category,
                        job_key=os.environ.get("UIPATH_JOB_KEY"),
                        folder_key=os.environ.get("UIPATH_FOLDER_KEY"),
                    )

                    chapter_attachments[filename] = attachment_id
                    print(f"     {filename} -> {attachment_id}")

                except Exception as e:
                    print(f"     Failed to upload {filename}: {e}")

            chapter_result = {
                "chapter_num": chapter_num,
                "chapter_title": chapter_title,
                "attachments": chapter_attachments,
                "file_count": len(chapter_attachments),
            }
            all_chapter_attachments.append(chapter_result)

        total_files = sum(len(ch["attachments"]) for ch in all_chapter_attachments)
        print(
            f"\n Book upload complete! {total_files} files uploaded across {len(all_chapter_attachments)} chapters"
        )

        return BookCompleteEvent(
            topic=ev.topic,
            book_title=ev.book_title,
            total_chapters=len(chapter_attachments),
            chapter_attachments=all_chapter_attachments,
        )

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file creation."""
        import re

        sanitized = re.sub(r"[^\w\s-]", "", filename)
        sanitized = re.sub(r"\s+", "_", sanitized)
        return sanitized.lower()


workflow = CompleteBookFlow(
    timeout=600, verbose=True
)  # Longer timeout for multiple chapters
