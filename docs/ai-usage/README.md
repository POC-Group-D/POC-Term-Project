# AI-assisted development log

The course requires AI-augmented development ("vibe coding") to be documented
with reproducible, traceable artifacts. This folder is that record.

## What to log

Add one file per working session in `log/`, named
`YYYY-MM-DD-<member>-<topic>.md`, using the template below. Log every session
whose output was committed, including sessions whose output you heavily edited.

## Tools in use

| Tool | Model / version | Vendor | Used for |
|------|-----------------|--------|----------|
| Claude Code (desktop app) | Claude Opus 5.5 (`claude-opus-5-5`) | Anthropic | Planning, code, infrastructure and docs |

Add a row whenever a member starts using another tool or model.

Runtime models used by the v2 agent (for example Hugging Face models) are
documented separately in `agent-service/`, because they are part of the
product rather than the development process.

## Template

```markdown
# <Topic>

- Date:
- Member:
- Tool and model:
- Branch / PR:

## Prompts

<The prompts you gave, verbatim or lightly trimmed.>

## What the assistant produced

<Files created or changed, commands it ran.>

## Human review and changes

<What you checked, corrected or rejected.>
```
