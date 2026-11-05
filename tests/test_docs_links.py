"""Guard: every relative link in README.md and docs/ resolves on disk.

The documentation tree is shipped inside the wheel (``dvrazer/_bundle/docs``),
so a link that only resolves in the author's checkout is a broken link for every
agent that installs the package.  Each relative link target is resolved against
the markdown file that contains it.
"""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"

#: The markdown files whose relative links are checked.
LINKED_FILES = [REPO_ROOT / "README.md", *sorted(DOCS_ROOT.rglob("*.md"))]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def _relative_targets(path: Path) -> list[str]:
    """Return the relative link targets of one markdown file."""
    targets = []
    for raw in LINK_RE.findall(path.read_text(encoding="utf-8")):
        target = raw.strip()
        if not target or target.startswith("#"):
            continue
        if target.startswith(EXTERNAL_PREFIXES):
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        else:
            target = target.split()[0]
        # A trailing ``#anchor`` points inside the target file, not at a file.
        target = target.split("#", 1)[0]
        if target:
            targets.append(target)
    return targets


def test_relative_links_resolve():
    broken = []
    for path in LINKED_FILES:
        for target in _relative_targets(path):
            if not (path.parent / target).resolve().exists():
                broken.append(f"{path.relative_to(REPO_ROOT)} -> {target}")

    assert not broken, "broken relative links:\n" + "\n".join(broken)
