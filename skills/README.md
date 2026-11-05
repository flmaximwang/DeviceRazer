# DVRazer agent skills

Agent Skills (`SKILL.md` + references) that teach coding agents such as
Claude Code how to use and extend DVRazer. They ship inside the `dvrazer`
package, so an installed copy always matches the installed library version.

| Skill | Use it for |
|---|---|
| [`dvrazer`](dvrazer/SKILL.md) | Using the library: loading instrument exports, interpolation/arithmetic/averaging/peaks, plotting, and finding the bundled docs and examples. References: [instruments](dvrazer/references/instruments.md), [plotting](dvrazer/references/plotting.md). |
| [`dvrazer-add-instrument`](dvrazer-add-instrument/SKILL.md) | Working in this repo: adding or fixing an instrument parser, its tests, example and docs. |

## Where the skills live

- **In this checkout:** `skills/`.
- **In an installed package** (`pip install dvrazer`, `uv add dvrazer`):
  `dvrazer.bundle_path("skills")` returns the bundled `skills/` directory.
  The same call locates the docs and examples: `bundle_path("docs")` and
  `bundle_path("examples")`.
- **Claude Code in this repository:** `.claude/skills/dvrazer` is a checked-in
  relative symlink to `../../skills/dvrazer`, so Claude Code loads the live
  skill without any setup. Keep it a symlink (`git ls-files -s .claude` shows
  mode `120000`); never copy the directory over it.

## Install into Claude Code

Claude Code discovers skills in `~/.claude/skills/` (all projects) or
`<project>/.claude/skills/` (one project). Symlink them so they stay in sync
with the repo:

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/dvrazer" ~/.claude/skills/dvrazer
ln -s "$(pwd)/skills/dvrazer-add-instrument" ~/.claude/skills/dvrazer-add-instrument
```

(run from the repository root). Other agents that support the Agent Skills
format can load the folders directly or call `dvrazer.bundle_path("skills")`.

## Maintenance

Use the uv workflow (see [Contributing](../docs/development/contributing.md)):

```bash
uv sync                       # create/update .venv
uv run pytest                 # full test suite
uv run python -c "..."        # run a snippet exactly as an agent would
```

Every snippet in these files should run against the current package — execute
it, do not just proof-read it. When an import path, factory method, return type
or plotting behaviour changes, update the matching skill file in the same
commit.

The docs were restructured into an English tree: start at `docs/index.md`, use
`docs/instruments/<instrument>.md` for per-instrument notes, and
`docs/development/adding-an-instrument.md` for parser contributions. When
adding a parser, update `skills/dvrazer/references/instruments.md` and the
matching docs page together.
