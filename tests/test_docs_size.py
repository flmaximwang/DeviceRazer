"""Guards for the documentation tree: size limits and the index link graph."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
INDEX_PAGE = DOCS_ROOT / "index.md"

README_LINE_LIMIT = 500
DOCS_PAGE_LINE_LIMIT = 2500

# Every page of the documentation tree, relative to docs/.
DOCS_PAGES = [
    "index.md",
    "getting-started.md",
    "plotting.md",
    "plates.md",
    "concepts/architecture.md",
    "concepts/desc-anno.md",
    "concepts/signal.md",
    "concepts/signal-1d.md",
    "concepts/signal-collection.md",
    "instruments/index.md",
    "instruments/chemstation.md",
    "instruments/cary-winuv.md",
    "instruments/unicorn.md",
    "instruments/softmax-pro.md",
    "instruments/nanodrop2000.md",
    "instruments/chi660e.md",
    "instruments/multiscan-fc.md",
    "development/contributing.md",
    "development/adding-an-instrument.md",
]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _links_from_index() -> set[Path]:
    """Resolve the relative link targets in docs/index.md against docs/."""
    links = set()
    for raw_target in LINK_RE.findall(INDEX_PAGE.read_text(encoding="utf-8")):
        target = raw_target.strip().split()[0] if raw_target.strip() else ""
        if not target or target.startswith("#") or target.startswith(EXTERNAL_PREFIXES):
            continue
        target = target.split("#", 1)[0]
        if target:
            links.add((INDEX_PAGE.parent / target).resolve())
    return links


def test_required_docs_pages_exist():
    missing = [page for page in DOCS_PAGES if not (DOCS_ROOT / page).is_file()]
    assert not missing, f"missing documentation pages: {missing}"


def test_index_links_every_docs_page():
    linked = _links_from_index()
    unlinked = [
        page
        for page in DOCS_PAGES
        if page != "index.md" and (DOCS_ROOT / page).resolve() not in linked
    ]
    assert not unlinked, (
        "docs/index.md does not link these pages: "
        f"{unlinked}\nLinked targets: {sorted(str(p) for p in linked)}"
    )


def test_readme_under_line_limit():
    lines = _line_count(REPO_ROOT / "README.md")
    assert lines <= README_LINE_LIMIT, (
        f"README.md has {lines} lines, limit is {README_LINE_LIMIT}"
    )


def test_docs_pages_under_line_limit():
    oversized = {}
    for page in sorted(DOCS_ROOT.rglob("*.md")):
        lines = _line_count(page)
        if lines > DOCS_PAGE_LINE_LIMIT:
            oversized[str(page.relative_to(REPO_ROOT))] = lines
    assert not oversized, (
        f"documentation pages exceed {DOCS_PAGE_LINE_LIMIT} lines: {oversized}"
    )
