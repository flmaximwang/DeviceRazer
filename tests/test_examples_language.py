"""Language checks for the bundled example scripts.

The agent bundle ships ``examples/`` as-is, so every example must be readable
in English. This guards against Chinese prose creeping back into docstrings,
comments, help strings or printed labels.
"""

import re
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"

#: CJK Unified Ideographs. The examples are English-only, so any hit is a bug.
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def test_no_cjk_characters_in_examples():
    """No example script may contain CJK characters."""
    example_files = sorted(EXAMPLES_DIR.rglob("*.py"))
    assert example_files, f"no example scripts found under {EXAMPLES_DIR}"

    violations = []
    for path in example_files:
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if CJK_PATTERN.search(line):
                relative = path.relative_to(EXAMPLES_DIR.parent)
                violations.append(f"{relative}:{lineno}: {line.strip()}")

    assert not violations, "CJK characters found in example scripts:\n" + "\n".join(
        violations
    )
