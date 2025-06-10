# Multi-Modal Book Writer Agent

A UiPath LlamaIndex agent that automatically generates complete books with chapters, illustrations, and multi-modal content, demonstrating the use of **job attachments** for handling multiple files in UiPath automations.

## What it does

This agent creates a complete book on any given topic by:

1. **Generating a book outline** with chapter titles and descriptions
2. **Writing detailed chapter content** with engaging text
3. **Creating visual illustrations** for each chapter using AI image generation
4. **Producing PDF documents** for each chapter with formatted text and images
5. **Uploading all files as job attachments** to demonstrate multi-modal file handling

## Key Features

- **Multi-modal content generation**: Combines text, images, and PDF creation
- **Job attachments demonstration**: Shows how to handle multiple files in UiPath jobs
- **Workflow-based architecture**: Uses LlamaIndex workflows for structured processing
- **AI-powered content**: Leverages OpenAI for both text and image generation

## Workflow Architecture

```mermaid
flowchart TD
    step__done["_done"]:::stepStyle
    step_create_chapter_files["create_chapter_files"]:::stepStyle
    step_generate_book_outline["generate_book_outline"]:::stepStyle
    step_generate_chapters_content["generate_chapters_content"]:::stepStyle
    step_upload_chapter_files["upload_chapter_files"]:::stepStyle
    event_ChaptersContentEvent([<p>ChaptersContentEvent</p>]):::defaultEventStyle
    event_ChaptersFilesEvent([<p>ChaptersFilesEvent</p>]):::defaultEventStyle
    event_BookRequestEvent([<p>BookRequestEvent</p>]):::defaultEventStyle
    event_BookOutlineEvent([<p>BookOutlineEvent</p>]):::defaultEventStyle
    event_BookCompleteEvent([<p>BookCompleteEvent</p>]):::stopEventStyle
    event_BookCompleteEvent --> step__done
    step_create_chapter_files --> event_ChaptersFilesEvent
    event_ChaptersContentEvent --> step_create_chapter_files
    step_generate_book_outline --> event_BookOutlineEvent
    event_BookRequestEvent --> step_generate_book_outline
    step_generate_chapters_content --> event_ChaptersContentEvent
    event_BookOutlineEvent --> step_generate_chapters_content
    step_upload_chapter_files --> event_BookCompleteEvent
    event_ChaptersFilesEvent --> step_upload_chapter_files
    classDef stepStyle fill:#f2f0ff,line-height:1.2
    classDef externalStyle fill:#f2f0ff,line-height:1.2
    classDef defaultEventStyle fill-opacity:0
    classDef stopEventStyle fill:#bfb6fc
    classDef inputRequiredStyle fill:#f2f0ff,line-height:1.2
```

## Usage

The agent accepts two inputs:
- **topic**: The subject for the book (e.g., "Machine Learning", "Cooking", "Space Exploration")
- **num_chapters**: Number of chapters to generate (recommended: 3-5)

## Sample Demonstration

This sample demonstrates how UiPath can handle complex multi-modal workflows that generate and manage multiple file types as job attachments, making it ideal for document generation, content creation, and automated publishing workflows.

## Dependencies

- Python ≥3.10
- UiPath LlamaIndex integration
- OpenAI API (for text and image generation)
- ReportLab (for PDF generation)
