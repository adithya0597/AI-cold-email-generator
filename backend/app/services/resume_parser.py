"""
Resume parser service with OpenAI structured outputs.

Extracts text from PDF/DOCX files, then uses GPT-4o-mini with Pydantic
response_format to produce structured profile data.

Usage::

    from app.services.resume_parser import extract_profile_from_resume

    profile = await extract_profile_from_resume(file_bytes, "resume.pdf")
    print(profile.name, profile.skills)
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models for structured extraction
# ---------------------------------------------------------------------------


class WorkExperience(BaseModel):
    """A single work experience entry extracted from a resume."""

    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class Education(BaseModel):
    """A single education entry extracted from a resume."""

    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    graduation_year: Optional[str] = None


class ExtractedProfile(BaseModel):
    """Structured profile data extracted from a resume via LLM."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    headline: Optional[str] = None
    skills: list[str] = []
    experience: list[WorkExperience] = []
    education: list[Education] = []


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

MIN_TEXT_LENGTH = 50


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF file.

    Args:
        file_bytes: Raw PDF file content.

    Returns:
        Concatenated text from all pages.

    Raises:
        ValueError: If the PDF appears to be image-based (too little text).
    """
    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n".join(pages_text).strip()

    if len(full_text) < MIN_TEXT_LENGTH:
        raise ValueError(
            "This file appears to be image-based. "
            "Please upload a text-based PDF or DOCX file."
        )

    return full_text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text content from a DOCX file.

    Args:
        file_bytes: Raw DOCX file content.

    Returns:
        Concatenated text from all paragraphs.

    Raises:
        ValueError: If the document contains too little text.
    """
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs).strip()

    if len(full_text) < MIN_TEXT_LENGTH:
        raise ValueError(
            "This document appears to be empty or contains only images. "
            "Please upload a text-based PDF or DOCX file."
        )

    return full_text


# ---------------------------------------------------------------------------
# LLM-powered profile extraction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a resume parser. Extract structured information from the resume "
    "text provided. Be accurate -- only include information explicitly present "
    "in the resume. Do not infer or fabricate any details."
)

# Truncate resume text to ~2K tokens worth of characters
_MAX_TEXT_CHARS = 8000


async def extract_profile_from_resume(
    file_bytes: bytes,
    filename: str,
) -> ExtractedProfile:
    """Extract structured profile data from a resume file.

    Determines file type from the filename extension, extracts raw text,
    then calls OpenAI structured outputs (GPT-4o-mini) to parse the
    resume into an ``ExtractedProfile``.

    Args:
        file_bytes: Raw file content (PDF or DOCX).
        filename: Original filename, used for extension detection.

    Returns:
        An ``ExtractedProfile`` with the parsed data.

    Raises:
        ValueError: If the file type is unsupported or the file is image-based.
    """
    # Determine file type and extract text
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        raw_text = extract_text_from_pdf(file_bytes)
    elif ext == "docx":
        raw_text = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type '.{ext}'. Please upload a PDF or DOCX file."
        )

    # Truncate to stay within token limits
    truncated_text = raw_text[:_MAX_TEXT_CHARS]

    # Call OpenAI structured outputs via the SDK (not raw httpx)
    from openai import AsyncOpenAI

    client = AsyncOpenAI()  # reads OPENAI_API_KEY from env

    completion = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": truncated_text},
        ],
        response_format=ExtractedProfile,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        logger.error("OpenAI structured output returned None for %s", filename)
        raise ValueError(
            "Failed to extract profile data from resume. "
            "Please try again or upload a different file."
        )

    return parsed
