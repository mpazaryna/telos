"""Skill discovery and intent routing."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    """A skill parsed from a markdown file."""

    name: str
    description: str
    body: str


def _parse_frontmatter(content: str) -> tuple[str, str]:
    """Parse YAML frontmatter from markdown content.

    Returns (description, body). Uses simple string splitting per spec.
    """
    stripped = content.strip()
    if not stripped.startswith("---"):
        return "(no description)", content

    # Split on --- delimiters
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return "(no description)", content

    frontmatter = parts[1]
    body = parts[2].strip()

    # Extract description field
    description = "(no description)"
    for line in frontmatter.strip().splitlines():
        if line.strip().startswith("description:"):
            description = line.split(":", 1)[1].strip()
            break

    return description, body


def discover_skills(skills_dir: Path) -> list[Skill]:
    """Discover all SKILL.md files in subdirectories.

    Returns a list of Skill objects sorted by name.
    """
    if not skills_dir.exists():
        return []

    skills = []
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        content = path.read_text()
        description, body = _parse_frontmatter(content)
        skills.append(Skill(
            name=path.parent.name,
            description=description,
            body=body,
        ))

    return skills


def keyword_match(user_input: str, skills: list[Skill]) -> Skill | None:
    """Match user input against skill names using substring matching.

    Matches longest skill name first to avoid partial collisions.
    Case-insensitive.
    """
    lowered = user_input.lower()
    # Sort by name length descending — longest match first
    sorted_skills = sorted(skills, key=lambda s: len(s.name), reverse=True)
    for skill in sorted_skills:
        if skill.name.lower() in lowered:
            return skill
    return None


def api_route(
    user_input: str,
    skills: list[Skill],
    client: object | None = None,
) -> Skill | None:
    """Route intent via Anthropic API call.

    Returns the matched Skill or None. Requires ANTHROPIC_API_KEY in environment.
    If no API key is set, returns None.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    manifest = "\n".join(f"- {s.name}: {s.description}" for s in skills)
    system = (
        "You are a skill router. Given a list of available skills and a user request, "
        "respond with ONLY the skill name that best matches the request. "
        "If no skill matches, respond with NONE. "
        "Do not include any explanation, punctuation, or preamble — just the skill name or NONE."
    )
    user_message = f"Available skills:\n{manifest}\n\nUser request: {user_input}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=64,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    skill_name = response.content[0].text.strip()
    if skill_name == "NONE":
        return None

    # Find the skill by name
    for skill in skills:
        if skill.name == skill_name:
            return skill

    return None


def route_intent(
    user_input: str,
    skills: list[Skill],
    client: object | None = None,
) -> Skill | None:
    """Two-pass intent routing: keyword match first, then API.

    Returns matched Skill or None.
    """
    # Pass 1: keyword match
    result = keyword_match(user_input, skills)
    if result is not None:
        return result

    # Pass 2: API routing
    return api_route(user_input, skills, client=client)
