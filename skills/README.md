# Agent skills

Portable instructions for coding agents that work on this repository. Each skill is a directory with a `SKILL.md` file: YAML frontmatter (`name`, `description`, optional `version`) plus markdown instructions.

## Layout

```
skills/
├── README.md
└── <skill-name>/
    └── SKILL.md
```

## Using with an agent

Point your agent runtime at this folder (or copy/symlink a skill into its skills path). The agent should load `SKILL.md` when the task matches the skill `description` in the frontmatter.

| Skill | Path | Purpose |
|-------|------|---------|
| `run-icecream-simulator` | [run-icecream-simulator/SKILL.md](run-icecream-simulator/SKILL.md) | Execute `run.py` / `run_full_cycle` and interpret reports during reasoning |

## Adding skills

1. Create `skills/<skill-name>/SKILL.md`.
2. Set `name` (kebab-case) and `description` (what it does + when to use it).
3. Document commands and APIs; keep the body focused on actions the agent should run.
