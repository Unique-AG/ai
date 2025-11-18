from pathlib import Path
from typing import Self

import httpx
import requests
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel

# Set up Jinja2 environment
_template_dir = Path(__file__).parent
_jinja_env = Environment(loader=FileSystemLoader(_template_dir))
_markdown_template = _jinja_env.get_template("transcript_template.j2")


class Words(BaseModel):
    word: str
    punctuated_word: str
    start: float
    end: float
    confidence: float


class Sentences(BaseModel):
    text: str
    start: float
    end: float
    words: list[Words]


class Paragraphs(BaseModel):
    text: str
    start: float
    end: float
    speaker: int
    sentences: list[Sentences]


class Transcript(BaseModel):
    text: str
    number_of_speakers: int
    paragraphs: list[Paragraphs]


class SpeakerData(BaseModel):
    name: str | None = None
    role: str | None = None
    company: str | None = None

    @property
    def display_name(self) -> str:
        """Return formatted speaker name with optional role and company."""
        if not self.name:
            return "Unknown Speaker"

        details = [detail for detail in (self.role, self.company) if detail]
        if details:
            return f"{self.name} ({' - '.join(details)})"

        return self.name


class SpeakerMapping(BaseModel):
    speaker: int
    speaker_data: SpeakerData


class QuartrEarningsCallTranscript(BaseModel):
    """Quartr earnings call transcript with speaker mapping and markdown export.

    This class represents a complete earnings call transcript from Quartr API,
    including the raw transcript data, speaker identification, and metadata.
    It provides functionality to export the transcript to markdown format with
    properly formatted speaker names and sections.

    Attributes:
        version (str): Version of the transcript schema format (e.g., "1.0").
        event_id (int): Unique identifier for the earnings call event.
        company_id (int): Unique identifier for the company.
        transcript (Transcript): The complete transcript data including paragraphs,
            sentences, words, and speaker assignments.
        speaker_mapping (list[SpeakerMapping]): List of speaker ID to speaker data
            mappings. Maps numeric speaker IDs to real names, roles, and companies.
            Defaults to empty list if no speaker mapping is provided.

    Methods:
        to_markdown: Export transcript to markdown format with speaker headers.

    Note:
        - Speaker IDs in the transcript are integers starting from 0
        - If a speaker has no mapping, they appear as "Speaker {id}" in markdown
        - The markdown template can be customized by passing a custom Jinja2 template
    """

    version: str
    event_id: int
    company_id: int
    transcript: Transcript
    speaker_mapping: list[SpeakerMapping] = []

    @classmethod
    async def from_quartr_transcript_url_async(cls, url: str) -> Self:
        """Create a QuartrEarningsCallTranscript from a Quartr URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        response.raise_for_status()
        return cls.model_validate_json(response.json())

    @classmethod
    def from_quartr_transcript_url(cls, url: str) -> Self:
        """Create a QuartrEarningsCallTranscript from a Quartr URL."""
        response = requests.get(url)
        response.raise_for_status()
        return cls.model_validate_json(response.text)

    def to_markdown(self, markdown_template: Template = _markdown_template) -> str:
        """Generate markdown representation of the transcript using Jinja template."""
        return markdown_template.render(
            transcript=self.transcript,
            get_speaker_name=self._get_speaker_name,
        )

    def _get_speaker_name(self, speaker_id: int) -> str:
        return next(
            (
                mapping.speaker_data.display_name
                for mapping in self.speaker_mapping
                if mapping.speaker == speaker_id and mapping.speaker_data.name
            ),
            f"Speaker {speaker_id}",
        )
