"""The ``dvrazer`` skill wiring: tracked Claude Code symlink and ``bundle_path``.

Guards the agent-bundle acceptance criteria: ``.claude/skills/dvrazer`` is a
symlink to the source skill, the skill documents the ``bundle_path`` discovery
API, and the documented lookups actually resolve in the current checkout.
"""

import os
import pathlib

import matplotlib
import pytest

matplotlib.use("Agg")

import dvrazer

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLAUDE_SKILL_LINK = REPO_ROOT / ".claude" / "skills" / "dvrazer"
SKILL_DIR = REPO_ROOT / "skills" / "dvrazer"
SKILL_FILE = SKILL_DIR / "SKILL.md"

BUNDLE_KINDS = ("docs", "examples", "skills")


def test_claude_skill_is_a_symlink_to_the_source_skill():
    """Claude Code must load the live skill, never a stale copy of it."""
    assert os.path.islink(CLAUDE_SKILL_LINK), (
        f"{CLAUDE_SKILL_LINK} must be a symlink to {SKILL_DIR}, "
        f"not a directory copy"
    )
    assert CLAUDE_SKILL_LINK.resolve() == SKILL_DIR.resolve()
    assert (CLAUDE_SKILL_LINK / "SKILL.md").is_file()


def test_skill_documents_bundle_path():
    """The skill must teach agents how to find the installed bundle."""
    text = SKILL_FILE.read_text(encoding="utf-8")
    assert "Finding installed docs, examples and skills" in text
    for kind in BUNDLE_KINDS:
        assert f'bundle_path("{kind}")' in text, (
            f"skills/dvrazer/SKILL.md does not mention bundle_path({kind!r})"
        )


@pytest.mark.parametrize("kind", BUNDLE_KINDS)
def test_documented_bundle_lookup_runs(kind):
    """Execute the calls the skill tells agents to run."""
    path = dvrazer.bundle_path(kind)
    assert isinstance(path, pathlib.Path)
    assert path.is_dir()


def test_bundle_lookup_finds_the_skill_markdown():
    """The documented ``bundle_path("skills")`` lookup reaches this skill."""
    skills = dvrazer.bundle_path("skills")
    assert (skills / "dvrazer" / "SKILL.md").is_file()
    assert (dvrazer.bundle_path("docs") / "index.md").is_file()
    assert any(p.is_dir() for p in dvrazer.bundle_path("examples").iterdir())
