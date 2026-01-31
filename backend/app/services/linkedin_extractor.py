"""
LinkedIn profile extractor service (secondary onboarding path).

Attempts to fetch public LinkedIn profile data via URL. This is designed
to fail gracefully -- LinkedIn aggressively blocks scraping, so returning
None is expected and normal behavior, NOT an error.

Usage::

    from app.services.linkedin_extractor import extract_from_linkedin_url

    profile = await extract_from_linkedin_url("https://linkedin.com/in/someone")
    if profile is None:
        # Expected -- fall back to resume upload
        ...
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import httpx

from app.services.resume_parser import Education, ExtractedProfile, WorkExperience

logger = logging.getLogger(__name__)

# Timeout for the HTTP request to LinkedIn
_TIMEOUT_SECONDS = 15.0

_LINKEDIN_URL_PATTERN = re.compile(r"linkedin\.com/in/", re.IGNORECASE)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _validate_linkedin_url(url: str) -> bool:
    """Check that the URL looks like a LinkedIn profile URL."""
    return bool(_LINKEDIN_URL_PATTERN.search(url))


def _parse_json_ld(html: str) -> Optional[dict]:
    """Try to extract JSON-LD structured data from the page HTML.

    LinkedIn sometimes includes schema.org Person data in a
    <script type="application/ld+json"> tag.
    """
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for script_tag in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script_tag.string or "")
                # Look for Person schema
                if isinstance(data, dict) and data.get("@type") == "Person":
                    return data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Person":
                            return item
            except (json.JSONDecodeError, TypeError):
                continue
    except Exception:
        pass
    return None


def _parse_meta_tags(html: str) -> dict:
    """Extract profile info from Open Graph and other meta tags."""
    result: dict = {}
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # og:title often has the name + headline
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title and og_title.get("content"):
            result["title"] = og_title["content"]

        # og:description may have summary text
        og_desc = soup.find("meta", {"property": "og:description"})
        if og_desc and og_desc.get("content"):
            result["description"] = og_desc["content"]

        # Profile-specific meta tags
        first_name = soup.find("meta", {"property": "profile:first_name"})
        last_name = soup.find("meta", {"property": "profile:last_name"})
        if first_name and first_name.get("content"):
            result["first_name"] = first_name["content"]
        if last_name and last_name.get("content"):
            result["last_name"] = last_name["content"]

    except Exception:
        pass
    return result


def _build_profile_from_data(
    json_ld: Optional[dict],
    meta: dict,
) -> Optional[ExtractedProfile]:
    """Attempt to construct an ExtractedProfile from scraped data.

    Returns None if insufficient data was found.
    """
    name = ""
    headline = None
    skills: list[str] = []
    experience: list[WorkExperience] = []
    education: list[Education] = []

    # Try JSON-LD first (richer data)
    if json_ld:
        name = json_ld.get("name", "")
        headline = json_ld.get("jobTitle") or json_ld.get("description")

        # Some JSON-LD includes worksFor
        works_for = json_ld.get("worksFor")
        if works_for:
            if isinstance(works_for, dict):
                works_for = [works_for]
            for org in works_for:
                if isinstance(org, dict):
                    experience.append(
                        WorkExperience(
                            company=org.get("name", "Unknown"),
                            title=json_ld.get("jobTitle", ""),
                        )
                    )

        # Education
        alumni_of = json_ld.get("alumniOf")
        if alumni_of:
            if isinstance(alumni_of, dict):
                alumni_of = [alumni_of]
            for school in alumni_of:
                if isinstance(school, dict):
                    education.append(
                        Education(institution=school.get("name", "Unknown"))
                    )

    # Fall back to meta tags
    if not name:
        first = meta.get("first_name", "")
        last = meta.get("last_name", "")
        name = f"{first} {last}".strip()

    if not name and meta.get("title"):
        # og:title is usually "Name - Title | LinkedIn"
        title_parts = meta["title"].split(" - ")
        if title_parts:
            name = title_parts[0].strip()
        if len(title_parts) > 1:
            headline = title_parts[1].split("|")[0].strip()

    if not headline and meta.get("description"):
        headline = meta["description"][:200]

    # Need at least a name to return something useful
    if not name or len(name) < 2:
        return None

    return ExtractedProfile(
        name=name,
        headline=headline,
        skills=skills,
        experience=experience,
        education=education,
    )


async def extract_from_linkedin_url(url: str) -> Optional[ExtractedProfile]:
    """Attempt to extract profile data from a LinkedIn profile URL.

    This function is designed to fail gracefully. LinkedIn aggressively
    blocks automated access, so returning None is normal and expected.

    Args:
        url: A LinkedIn profile URL (must contain "linkedin.com/in/").

    Returns:
        An ``ExtractedProfile`` if extraction succeeded, or ``None``
        if the profile could not be accessed or parsed.
    """
    try:
        if not _validate_linkedin_url(url):
            logger.info("Invalid LinkedIn URL format: %s", url)
            return None

        async with httpx.AsyncClient(
            timeout=_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )

            if response.status_code != 200:
                logger.info(
                    "LinkedIn returned status %d for %s",
                    response.status_code,
                    url,
                )
                return None

            html = response.text

        # Try to extract structured data
        json_ld = _parse_json_ld(html)
        meta = _parse_meta_tags(html)

        profile = _build_profile_from_data(json_ld, meta)

        if profile is None:
            logger.info("Insufficient data extracted from LinkedIn profile: %s", url)
            return None

        logger.info("Successfully extracted profile from LinkedIn: %s", url)
        return profile

    except httpx.TimeoutException:
        logger.info("LinkedIn request timed out for %s", url)
        return None
    except Exception:
        logger.info("LinkedIn extraction failed for %s", url, exc_info=True)
        return None
