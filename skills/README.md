# DVRazer agent skills

Agent Skills (`SKILL.md` + references) that teach coding agents such as
Claude Code how to use and extend DVRazer.

| Skill | Use it for |
|---|---|
| [`dvrazer`](dvrazer/SKILL.md) | Using the library: loading instrument exports, interpolation/arithmetic/averaging/peaks, plotting. References: [instruments](dvrazer/references/instruments.md), [plotting](dvrazer/references/plotting.md). |
| [`dvrazer-add-instrument`](dvrazer-add-instrument/SKILL.md) | Working in this repo: adding or fixing an instrument parser, its tests, example and docs. |

## Install

Claude Code discovers skills in `~/.claude/skills/` (all projects) or
`<project>/.claude/skills/` (one project). Symlink them so they stay in sync
with the repo:

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/dvrazer" ~/.claude/skills/dvrazer
ln -s "$(pwd)/skills/dvrazer-add-instrument" ~/.claude/skills/dvrazer-add-instrument
```

(run from the repository root). Other agents that support the Agent Skills
format can load the folders directly.

## Maintenance

When an import path, factory method, return type or plotting behaviour
changes, update the matching skill file in the same commit. Every code
snippet in these files should run against the current package.
