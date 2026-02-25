"""Skill loader for AI Functions.

Resolves, reads, and processes SKILL.md files for skill-backed AI functions.
"""

import re
from pathlib import Path
from typing import Any, NamedTuple


class SkillVariable(NamedTuple):
    """A variable declared in a SKILL.md ## Variables section."""

    name: str
    type_hint: str | None = None
    description: str | None = None


def resolve_skill_path(skill_name: str) -> Path:
    """Resolve a skill name to its SKILL.md file path.

    Args:
        skill_name: Name of the skill directory.

    Returns:
        Absolute path to the SKILL.md file.

    Raises:
        ValueError: If skill_name is empty or contains path separators.
        FileNotFoundError: If the SKILL.md file does not exist.
    """
    if not skill_name:
        raise ValueError("Skill name must not be empty")

    if "/" in skill_name or "\\" in skill_name or "\0" in skill_name:
        raise ValueError(f"Skill name must not contain path separators: {skill_name!r}")

    skills_root = (Path.cwd() / "skills").resolve()
    path = (skills_root / skill_name / "SKILL.md").resolve()

    if not path.is_relative_to(skills_root):
        raise ValueError(f"Skill path escapes skills directory: {skill_name!r}")

    if not path.is_file():
        raise FileNotFoundError(f"Skill '{skill_name}' not found: {path}")
    return path


def strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from content.

    If content starts with ``---``, everything up to and including the
    next ``---`` line is removed.

    Args:
        content: Raw file content.

    Returns:
        Content with frontmatter removed (if present).
    """
    if not content.startswith("---"):
        return content

    # Find the closing --- (must be on its own line)
    end = content.find("\n---", 3)
    if end == -1:
        return content

    # Skip past the closing --- and the newline after it
    after = end + 4  # len("\n---")
    if after < len(content) and content[after] == "\n":
        after += 1
    return content[after:]


_VARIABLE_PATTERN = re.compile(
    r"^-\s+"
    r"(?P<name>\w+)"
    r"(?:\s*\((?P<type>[^)]+)\))?"
    r"(?:\s*:\s*(?P<desc>.+))?"
    r"$",
    re.MULTILINE,
)


def parse_variables(content: str) -> list[SkillVariable]:
    """Parse the ``## Variables`` section of a SKILL.md file.

    Each variable line has the form::

        - name (type): description

    Type hint and description are optional.

    Args:
        content: SKILL.md content (frontmatter already stripped).

    Returns:
        List of parsed variables. Empty list if no Variables section found.
    """
    # Find the ## Variables section
    match = re.search(r"^## Variables\s*$", content, re.MULTILINE)
    if not match:
        return []

    # Extract text until the next ## heading or end of content
    start = match.end()
    next_heading = re.search(r"^## ", content[start:], re.MULTILINE)
    section = content[start : start + next_heading.start()] if next_heading else content[start:]

    variables: list[SkillVariable] = []
    for m in _VARIABLE_PATTERN.finditer(section):
        variables.append(
            SkillVariable(
                name=m.group("name"),
                type_hint=m.group("type"),
                description=m.group("desc"),
            )
        )
    return variables


def build_variable_context(variables: list[SkillVariable], bound_args: dict[str, Any]) -> str:
    """Build the ``## Current Input`` markdown section from variables and arguments.

    Args:
        variables: Declared skill variables.
        bound_args: Function arguments.

    Returns:
        Formatted markdown section.

    Raises:
        ValueError: If a declared variable is not present in bound_args.
    """
    lines = ["## Current Input", ""]
    for var in variables:
        if var.name not in bound_args:
            raise ValueError(
                f"Skill variable '{var.name}' is not present in function parameters. "
                f"Available parameters: {', '.join(bound_args.keys())}"
            )
        lines.append(f"- **{var.name}**: {str(bound_args[var.name])}")
    return "\n".join(lines)


def load_skill(skill_name: str, bound_args: dict[str, Any]) -> str:
    """Load a SKILL.md file and return the prompt with variable context.

    Args:
        skill_name: Name of the skill (resolves to ``./skills/{name}/SKILL.md``).
        bound_args: Function arguments to inject as context.

    Returns:
        The skill content with structured variable context appended.

    Raises:
        FileNotFoundError: If the SKILL.md file cannot be found.
        ValueError: If skill_name is empty, content is empty, or SKILL.md
                    declares variables not present in bound_args.
    """
    path = resolve_skill_path(skill_name)
    content = path.read_text()

    if not content.strip():
        raise ValueError(f"Skill '{skill_name}' has empty content: {path}")

    content = strip_frontmatter(content)
    variables = parse_variables(content)

    if variables:
        context = build_variable_context(variables, bound_args)
        return content.rstrip() + "\n\n" + context
    return content
