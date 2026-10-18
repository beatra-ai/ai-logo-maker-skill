# AGENTS.md

This repository publishes Beatra Agent Skills for Claude Code, Cursor, Codex, Windsurf, Cline, OpenClaw,
and any other agent that loads `SKILL.md`. Each skill lives in `skills/ai-logo-maker/` and starts at its `SKILL.md`;
follow that file, not this one, when you run the skill.

## Install

```bash
npx skills add beatra-ai/ai-logo-maker-skill
gh skill install beatra-ai/ai-logo-maker-skill ai-logo-maker
```

## Rules for agents

- Rendering uses credits on the person's Beatra account. A paid step runs only when the person asks for that
  exact render or approves the confirmation card the skill shows; follow the skill's own card rules.
- The skills contain no self-updater and never replace their own files. Update with the tool that installed
  them: `npx skills update ai-logo-maker` or `gh skill update ai-logo-maker`.
- Model names and output limits in `README.md` come from a dated catalog snapshot; for live availability
  and credit prices at runtime, read the live catalog:
  https://docs.beatra.ai/en/docs/models
- Full reference for every Beatra skill: https://beatra.ai/llms-full.txt
