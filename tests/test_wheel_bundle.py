"""End-to-end check that the built wheel really ships the agent bundle.

This test is marked ``slow``: it runs a real ``uv build``, installs the wheel
into a fresh temporary virtual environment and inspects the bundle from a
working directory outside the checkout.  The default test run deselects it
(``addopts = ["-m", "not slow"]`` in ``pyproject.toml``); run it explicitly
with::

    uv run pytest -m slow

Everything is written under ``tmp_path``, so the repository is never polluted
with a ``dist/`` directory.  The temporary venv gets its runtime dependencies
from the running interpreter's site-packages through a ``.pth`` file instead
of the network: ``--system-site-packages`` only exposes the *base* Python's
packages, which under uv is a bare managed interpreter.
"""

import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import textwrap
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Bundle directories exposed by :func:`dvrazer.bundle_path`.
BUNDLE_KINDS = ("docs", "examples", "skills")

#: Files that must be present in a kind's bundle directory (relative paths).
REQUIRED_FILES = {
    "docs": ("index.md",),
    "examples": (),  # checked separately: at least one example.py at any depth
    "skills": ("dvrazer/SKILL.md",),
}

# Runs inside the temporary venv, from a directory outside the checkout.  It
# prints one JSON object; the assertions live in the test below so a failure
# can show the entire payload.
_INSPECT_SCRIPT = textwrap.dedent(
    """
    import json

    import dvrazer

    def inspect(kind):
        root = dvrazer.bundle_path(kind)
        missing = [name for name in REQUIRED[kind] if not (root / name).is_file()]
        examples = sorted(
            str(path.relative_to(root)) for path in root.rglob("example.py")
        )
        forbidden = sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.name == ".DS_Store"
            or "__pycache__" in path.parts
            or (path.is_file() and path.suffix in (".pyc", ".png"))
        )
        return {
            "path": str(root),
            "is_dir": root.is_dir(),
            "missing": missing,
            "examples": examples,
            "forbidden": forbidden,
        }

    REQUIRED = {
        "docs": ("index.md",),
        "examples": (),
        "skills": ("dvrazer/SKILL.md",),
    }
    print(json.dumps({
        "dvrazer_file": dvrazer.__file__,
        "bundles": {kind: inspect(kind) for kind in ("docs", "examples", "skills")},
    }))
    """
)


def _uv() -> str:
    """Return the ``uv`` executable or skip: the slow test needs it."""
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is not installed, cannot build and install the wheel")
    return uv


def _run(command, *, cwd, env=None):
    """Run a subprocess, capturing text output for failure messages."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=15 * 60,
    )


def _describe(result) -> str:
    return (
        f"command: {' '.join(str(part) for part in result.args)}\n"
        f"exit code: {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":  # pragma: no cover - the project targets POSIX CI
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _build_distribution(tmp_path: Path, uv: str) -> tuple[Path, Path]:
    """Build into ``tmp_path/dist`` and return the ``(wheel, sdist)`` pair."""
    dist = tmp_path / "dist"
    command = [uv, "build", "--out-dir", str(dist)]
    result = _run(command, cwd=REPO_ROOT)
    if result.returncode != 0:
        # A warm uv cache can build without a network at all; retrying offline
        # keeps the check usable on offline machines with a seeded cache.
        offline = _run([*command, "--offline"], cwd=REPO_ROOT)
        if offline.returncode != 0:
            pytest.fail(
                "uv build failed; tried both the normal and the offline cache\n"
                + _describe(result)
                + "\n--- retry with --offline ---\n"
                + _describe(offline)
            )
        result = offline

    wheels = sorted(dist.glob("dvrazer-*.whl"))
    assert len(wheels) == 1, (
        f"expected exactly one wheel in {dist}, found {wheels}\n"
        + _describe(result)
    )
    sdists = sorted(dist.glob("dvrazer-*.tar.gz"))
    assert len(sdists) == 1, (
        f"expected exactly one sdist in {dist}, found {sdists}\n"
        + _describe(result)
    )
    return wheels[0], sdists[0]


def _assert_sdist_ships_skill(sdist: Path) -> None:
    """A wheel built from this sdist must be able to ship ``skills/dvrazer``.

    ``.claude/skills/dvrazer`` is a tracked symlink to ``skills/dvrazer``.
    Hatchling's file walker de-duplicates directories by inode; if it visits
    the symlink first, the real ``skills/dvrazer`` is pruned from the sdist
    and the wheel silently loses the main skill.
    """
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getnames()

    assert any(name.endswith("/skills/dvrazer/SKILL.md") for name in members), (
        f"the sdist at {sdist} is missing skills/dvrazer/SKILL.md:\n"
        + "\n".join(name for name in members if "/skills/" in name)
    )
    leaked = [name for name in members if "/.claude/" in name]
    assert leaked == [], (
        f"the sdist at {sdist} contains the .claude symlink target: {leaked}"
    )


def _create_venv(tmp_path: Path, uv: str) -> tuple[Path, Path]:
    """Create a venv with access to the base interpreter's site-packages."""
    venv_dir = tmp_path / "venv"
    attempts = [
        [uv, "venv", "--system-site-packages", "--python", sys.executable, str(venv_dir)],
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)],
    ]
    failures = []
    for command in attempts:
        result = _run(command, cwd=tmp_path)
        if result.returncode == 0:
            python = _venv_python(venv_dir)
            if python.is_file():
                return venv_dir, python
        failures.append(_describe(result))

    pytest.fail("could not create a temporary virtual environment\n" + "\n\n".join(failures))


def _site_packages(python: Path) -> Path:
    result = _run(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        cwd=python.parent,
    )
    assert result.returncode == 0, "could not query the temp venv site-packages\n" + _describe(result)
    return Path(result.stdout.strip())


def _seed_runtime_dependencies(venv_python: Path) -> None:
    """Make the running interpreter's packages importable in the temp venv.

    ``--system-site-packages`` exposes the base interpreter's site-packages,
    which for a uv-managed CPython contains none of the project dependencies.
    A ``.pth`` file adds the current environment's site-packages instead, so
    ``import dvrazer`` in the venv never needs to download numpy/pandas/...
    It is appended *after* the venv's own site-packages, so the wheel's copy
    of ``dvrazer`` still wins over an editable checkout install.
    """
    source = Path(sysconfig.get_path("purelib"))
    if not source.is_dir():
        pytest.skip(f"runtime dependencies not found at {source}, cannot import the wheel offline")

    target = _site_packages(venv_python)
    if target.resolve() == source.resolve():
        return  # --system-site-packages already provided them
    (target / "_dvrazer_test_deps.pth").write_text(f"{source}\n", encoding="utf-8")


def _install_wheel(tmp_path: Path, uv: str, venv_python: Path, wheel: Path) -> None:
    """Install the wheel into the temp venv without touching the network."""
    result = _run(
        [uv, "pip", "install", "--no-deps", "--python", str(venv_python), str(wheel)],
        cwd=tmp_path,
    )
    if result.returncode != 0:
        pytest.fail("uv pip install --no-deps failed\n" + _describe(result))


def _clean_environment() -> dict[str, str]:
    """Drop variables that could leak the checkout into the temp venv."""
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        env.pop(name, None)
    return env


def _inspect_installed_bundle(tmp_path: Path, venv_python: Path) -> dict:
    """Run the bundle inspection script outside the repository checkout."""
    run_dir = tmp_path / "outside-checkout"
    run_dir.mkdir()
    result = _run(
        [str(venv_python), "-c", _INSPECT_SCRIPT],
        cwd=run_dir,
        env=_clean_environment(),
    )
    if result.returncode != 0:
        pytest.fail("inspecting the installed bundle failed\n" + _describe(result))

    # The package import may print warnings on stdout in future versions;
    # the payload is the last line.
    lines = result.stdout.strip().splitlines()
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        pytest.fail("the temp venv did not print the expected JSON payload\n" + _describe(result))


def test_pyproject_keeps_dot_claude_out_of_the_build():
    """Fast regression guard for the ``skills/dvrazer`` packaging fix.

    ``.claude/skills/dvrazer`` is a tracked symlink to ``skills/dvrazer``.
    Without excluding ``.claude`` from the build walk, hatchling de-duplicates
    the two directories by inode, visits the symlink first and prunes the real
    ``skills/dvrazer`` from the sdist, so the wheel loses the main skill.  The
    slow test below proves the result; this one guards the setting itself.
    """
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    build = pyproject["tool"]["hatch"]["build"]

    assert build["exclude"] == ["/.claude"]
    assert build["skip-excluded-dirs"] is True


@pytest.mark.slow
def test_wheel_ships_agent_bundle(tmp_path):
    """The installed wheel resolves every bundle inside the temp venv.

    This is the end-to-end proof behind ``DeviceRazer-cem.1`` and
    ``DeviceRazer-cem.2``: build the wheel, install it into an isolated venv,
    then ask that installed copy where the docs, examples and skills are.
    The sdist shipped next to the wheel is checked as well, because a wheel
    built from it is what an index installs.
    """
    uv = _uv()
    wheel, sdist = _build_distribution(tmp_path, uv)
    _assert_sdist_ships_skill(sdist)
    venv_dir, venv_python = _create_venv(tmp_path, uv)
    _seed_runtime_dependencies(venv_python)
    _install_wheel(tmp_path, uv, venv_python, wheel)
    payload = _inspect_installed_bundle(tmp_path, venv_python)

    venv_root = venv_dir.resolve()
    checkout = REPO_ROOT.resolve()
    dvrazer_file = Path(payload["dvrazer_file"]).resolve()

    assert dvrazer_file.is_relative_to(venv_root), (
        f"the temp venv imported dvrazer from {dvrazer_file}, not from {venv_root}"
    )
    assert not dvrazer_file.is_relative_to(checkout), (
        f"the checkout at {checkout} shadowed the installed wheel: {dvrazer_file}"
    )

    for kind in BUNDLE_KINDS:
        info = payload["bundles"][kind]
        bundle = Path(info["path"]).resolve()

        assert info["is_dir"], f"{kind} bundle does not exist: {bundle}"
        assert bundle.is_relative_to(venv_root), (
            f"{kind} bundle resolved to {bundle}, outside the temp venv {venv_root}"
        )
        assert not bundle.is_relative_to(checkout), (
            f"{kind} bundle resolved to the checkout ({bundle}); the wheel's copy was not used"
        )
        assert bundle == dvrazer_file.parent / "_bundle" / kind, (
            f"{kind} bundle is at {bundle}, expected it under dvrazer/_bundle/{kind}"
        )
        assert info["missing"] == [], (
            f"{kind} bundle is missing {info['missing']} (contents: {info})"
        )
        assert info["forbidden"] == [], (
            f"{kind} bundle ships files that must be excluded: {info['forbidden']}"
        )

    assert payload["bundles"]["examples"]["examples"], (
        "the examples bundle has no example.py files: "
        f"{payload['bundles']['examples']}"
    )
