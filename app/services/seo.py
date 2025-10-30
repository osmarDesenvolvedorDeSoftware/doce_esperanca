"""Utilities to centralize SEO metadata generation for the public website."""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence, Union

DEFAULT_SITE_NAME = "Doce Esperança"
DEFAULT_SITE_DESCRIPTION = (
    "Projeto social de Recife que transforma doações em oportunidades e apoia "
    "famílias com ações de solidariedade, voluntariado e transparência."
)
DEFAULT_KEYWORDS: Sequence[str] = (
    "Doce Esperança",
    "ONG Doce Esperança",
    "solidariedade",
    "projetos sociais",
    "doações",
    "voluntariado",
    "impacto social",
    "Recife",
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: Union[str, None]) -> str:
    """Return ``value`` stripped from HTML tags and normalized whitespace."""

    if not value:
        return ""

    stripped = _HTML_TAG_RE.sub(" ", str(value))
    normalized = _WHITESPACE_RE.sub(" ", stripped)
    return normalized.strip()


def summarize_text(
    *candidates: Optional[str],
    fallback: str = "",
    width: int = 155,
    placeholder: str = "…",
) -> str:
    """Return a shortened summary based on the first non-empty candidate."""

    for candidate in candidates:
        cleaned = clean_text(candidate)
        if cleaned:
            return textwrap.shorten(cleaned, width=width, placeholder=placeholder)

    cleaned_fallback = clean_text(fallback)
    if cleaned_fallback:
        return textwrap.shorten(cleaned_fallback, width=width, placeholder=placeholder)

    return ""


def _deduplicate_keywords(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        candidate = str(value).strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(candidate)
    return result


@dataclass
class SeoMetadata:
    """Container for SEO metadata rendered in templates."""

    title: str
    description: str
    keywords: Union[Sequence[str], str, None] = field(default=None)
    canonical: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_type: str = "website"
    og_image: Optional[str] = None
    og_url: Optional[str] = None
    og_locale: str = "pt_BR"
    twitter_card: str = "summary_large_image"
    twitter_title: Optional[str] = None
    twitter_description: Optional[str] = None
    twitter_image: Optional[str] = None
    structured_data: Optional[Union[Sequence[Mapping[str, object]], Mapping[str, object]]] = None
    noindex: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a dict ready to be consumed by Jinja templates."""

        keywords_value: Optional[str]
        if isinstance(self.keywords, str):
            keywords_value = self.keywords.strip() or None
        else:
            combined: list[str] = []
            if self.keywords:
                combined.extend(self.keywords)
            keywords_value = ", ".join(_deduplicate_keywords(combined)) or None

        og_title = self.og_title or self.title
        og_description = self.og_description or self.description
        twitter_title = self.twitter_title or og_title
        twitter_description = self.twitter_description or og_description
        twitter_image = self.twitter_image or self.og_image
        og_url = self.og_url or self.canonical

        return {
            "title": self.title,
            "description": self.description,
            "keywords": keywords_value,
            "canonical": self.canonical,
            "og_title": og_title,
            "og_description": og_description,
            "og_type": self.og_type,
            "og_image": self.og_image,
            "og_url": og_url,
            "og_locale": self.og_locale,
            "twitter_card": self.twitter_card,
            "twitter_title": twitter_title,
            "twitter_description": twitter_description,
            "twitter_image": twitter_image,
            "structured_data": self.structured_data,
            "noindex": self.noindex,
        }


def build_metadata(
    *,
    title: str,
    description: str,
    canonical: Optional[str] = None,
    keywords: Optional[Sequence[str]] = None,
    extra_keywords: Optional[Sequence[str]] = None,
    append_default_keywords: bool = True,
    **overrides: object,
) -> dict[str, object]:
    """Build SEO metadata using sensible defaults and sanitization."""

    keyword_pool: list[str] = []
    if append_default_keywords:
        keyword_pool.extend(DEFAULT_KEYWORDS)
    if keywords:
        keyword_pool.extend(keywords)
    if extra_keywords:
        keyword_pool.extend(extra_keywords)

    metadata = SeoMetadata(
        title=title,
        description=description,
        canonical=canonical,
        keywords=_deduplicate_keywords(keyword_pool),
        **overrides,
    )
    return metadata.as_dict()


def build_organization_schema(
    *,
    site_name: str,
    base_url: str,
    logo_url: Optional[str] = None,
    description: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    same_as: Optional[Sequence[str]] = None,
) -> Mapping[str, object]:
    """Return Schema.org metadata for the NGO organization."""

    address_schema: Optional[MutableMapping[str, object]] = None
    if address:
        lines = [line.strip() for line in address.splitlines() if line.strip()]
        if lines:
            address_schema = {"@type": "PostalAddress", "streetAddress": lines[0]}
            if len(lines) >= 2:
                address_schema["addressLocality"] = lines[1]
            if len(lines) >= 3:
                address_schema["addressRegion"] = lines[2]

    schema: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "NGO",
        "name": site_name,
        "url": base_url,
    }
    if description:
        schema["description"] = description
    if logo_url:
        schema["logo"] = logo_url
    if email:
        schema["email"] = email
    if phone:
        schema["telephone"] = phone
    if address_schema:
        schema["address"] = address_schema
    if same_as:
        schema["sameAs"] = [link for link in same_as if link]

    contact_points: list[Mapping[str, object]] = []
    if phone or email:
        contact_point: dict[str, object] = {"@type": "ContactPoint", "contactType": "Customer Service"}
        if phone:
            contact_point["telephone"] = phone
        if email:
            contact_point["email"] = email
        contact_points.append(contact_point)
    if contact_points:
        schema["contactPoint"] = contact_points

    return schema


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Return a ``datetime`` from an ISO 8601 string if possible."""

    if not value:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue

    if candidate.endswith("Z"):
        try:
            without_z = candidate[:-1]
            return datetime.fromisoformat(without_z)
        except ValueError:
            return None

    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


__all__ = [
    "DEFAULT_KEYWORDS",
    "DEFAULT_SITE_DESCRIPTION",
    "DEFAULT_SITE_NAME",
    "SeoMetadata",
    "build_metadata",
    "build_organization_schema",
    "clean_text",
    "parse_iso_datetime",
    "summarize_text",
]
