"""Tests for skill loader.

Tests cover: path resolution, frontmatter stripping, variable parsing,
variable context building, and the top-level load_skill function.
"""

from pathlib import Path

import pytest

from ai_functions.skills.loader import (
    SkillVariable,
    build_variable_context,
    load_skill,
    parse_variables,
    resolve_skill_path,
    strip_frontmatter,
)


class TestResolveSkillPath:
    """Tests for resolve_skill_path."""

    def test_empty_skill_name_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            resolve_skill_path("")

    def test_missing_file_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError, match="not found"):
            resolve_skill_path("nonexistent")

    def test_missing_file_includes_skill_name_and_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError, match="nonexistent") as exc_info:
            resolve_skill_path("nonexistent")
        assert str(tmp_path) in str(exc_info.value)

    def test_resolves_existing_skill(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        skill_dir = tmp_path / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# test")

        result = resolve_skill_path("my-skill")
        assert result == skill_file.resolve()

    def test_path_traversal_with_dotdot_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="path separator"):
            resolve_skill_path("../../etc/passwd")

    def test_forward_slash_in_name_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="path separator"):
            resolve_skill_path("foo/bar")

    def test_backslash_in_name_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="path separator"):
            resolve_skill_path("foo\\bar")

    def test_null_byte_in_name_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="path separator"):
            resolve_skill_path("foo\0bar")

    def test_symlink_escaping_skills_dir_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Create a real file outside skills/
        outside = tmp_path / "secret"
        outside.mkdir()
        (outside / "SKILL.md").write_text("secret content")

        # Create a symlink inside skills/ pointing outside
        skill_dir = tmp_path / "skills" / "evil"
        skill_dir.mkdir(parents=True)
        symlink = skill_dir / "SKILL.md"
        symlink.symlink_to(outside / "SKILL.md")

        with pytest.raises(ValueError, match="escapes skills directory"):
            resolve_skill_path("evil")


class TestStripFrontmatter:
    """Tests for strip_frontmatter."""

    def test_no_frontmatter(self):
        content = "# Hello\n\nWorld"
        assert strip_frontmatter(content) == content

    def test_strips_frontmatter(self):
        content = "---\nname: test\n---\n# Hello\n\nWorld"
        assert strip_frontmatter(content) == "# Hello\n\nWorld"

    def test_no_closing_delimiter(self):
        content = "---\nname: test\n# Hello"
        assert strip_frontmatter(content) == content

    def test_empty_frontmatter(self):
        content = "---\n---\n# Hello"
        assert strip_frontmatter(content) == "# Hello"

    def test_frontmatter_with_complex_yaml(self):
        content = "---\nname: test\ndescription: A long description\ntags:\n  - a\n  - b\n---\nBody"
        assert strip_frontmatter(content) == "Body"


class TestParseVariables:
    """Tests for parse_variables."""

    def test_no_variables_section(self):
        content = "# Skill\n\nSome content"
        assert parse_variables(content) == []

    def test_full_variable_format(self):
        content = "## Variables\n\n- text (str): The input text\n- count (int): How many"
        result = parse_variables(content)
        assert len(result) == 2
        assert result[0] == SkillVariable("text", "str", "The input text")
        assert result[1] == SkillVariable("count", "int", "How many")

    def test_name_and_description_only(self):
        content = "## Variables\n\n- text: The input text"
        result = parse_variables(content)
        assert len(result) == 1
        assert result[0] == SkillVariable("text", None, "The input text")

    def test_name_and_type_only(self):
        content = "## Variables\n\n- text (str)"
        result = parse_variables(content)
        assert len(result) == 1
        assert result[0] == SkillVariable("text", "str", None)

    def test_name_only(self):
        content = "## Variables\n\n- text"
        result = parse_variables(content)
        assert len(result) == 1
        assert result[0] == SkillVariable("text", None, None)

    def test_stops_at_next_heading(self):
        content = "## Variables\n\n- text (str): Input\n\n## Instructions\n\n- Do stuff"
        result = parse_variables(content)
        assert len(result) == 1
        assert result[0].name == "text"


class TestBuildVariableContext:
    """Tests for build_variable_context."""

    def test_basic_context(self):
        variables = [SkillVariable("text", "str", "Input")]
        result = build_variable_context(variables, {"text": "hello world"})
        assert "## Current Input" in result
        assert "- **text**: hello world" in result

    def test_missing_variable_raises(self):
        variables = [SkillVariable("text", "str", "Input")]
        with pytest.raises(ValueError, match="not present in function parameters"):
            build_variable_context(variables, {"other": "value"})

    def test_extra_bound_args_ignored(self):
        variables = [SkillVariable("text", "str", "Input")]
        result = build_variable_context(variables, {"text": "hello", "extra": "ignored"})
        assert "extra" not in result

    def test_value_rendered_with_str(self):
        variables = [SkillVariable("count", "int", "Number")]
        result = build_variable_context(variables, {"count": 42})
        assert "- **count**: 42" in result

    def test_multiple_variables(self):
        variables = [
            SkillVariable("a", "str", "First"),
            SkillVariable("b", "int", "Second"),
        ]
        result = build_variable_context(variables, {"a": "hello", "b": 99})
        assert "- **a**: hello" in result
        assert "- **b**: 99" in result


class TestLoadSkill:
    """Tests for the top-level load_skill function."""

    def _write_skill(self, tmp_path: Path, name: str, content: str) -> None:
        skill_dir = tmp_path / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content)

    def test_happy_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._write_skill(
            tmp_path,
            "test-skill",
            "---\nname: test\n---\n# Skill\n\n## Variables\n\n- text (str): Input\n\n## Instructions\n\nDo it.",
        )
        result = load_skill("test-skill", {"text": "hello"})
        assert "# Skill" in result
        assert "## Current Input" in result
        assert "- **text**: hello" in result
        # Frontmatter should be stripped
        assert "name: test" not in result

    def test_no_variables_section(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._write_skill(tmp_path, "simple", "# Simple skill\n\nJust do the thing.")
        result = load_skill("simple", {"text": "hello"})
        assert "# Simple skill" in result
        assert "## Current Input" not in result

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError, match="missing"):
            load_skill("missing", {})

    def test_empty_skill_name(self):
        with pytest.raises(ValueError, match="must not be empty"):
            load_skill("", {})

    def test_empty_file_content(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._write_skill(tmp_path, "empty", "   \n  ")
        with pytest.raises(ValueError, match="empty content"):
            load_skill("empty", {})

    def test_variable_not_in_bound_args(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._write_skill(tmp_path, "strict", "# Skill\n\n## Variables\n\n- text (str): Input")
        with pytest.raises(ValueError, match="not present in function parameters"):
            load_skill("strict", {"other": "value"})

    def test_frontmatter_stripped(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._write_skill(tmp_path, "fm", "---\nname: fm\ndescription: test\n---\n# Content")
        result = load_skill("fm", {})
        assert result.startswith("# Content")
        assert "---" not in result
