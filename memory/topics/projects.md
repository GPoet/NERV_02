# Projects

Notes on active projects — NERV, Aeon, Dashboard, and related systems.

---

## Aeon — Autonomous Brain / Session Distillation
*2026-03-25T05:30 IST session (62 exchanges, ~95 min)*
- Built Stop hook (`session-distill.js`) that captures session manifests after each Claude Code session ends
- Hook writes lightweight manifest to `memory/topics/claude-sessions.md` with files, topics, exchange count
- `skills/session-sync/SKILL.md` distills pending manifests into structured memory via GitHub Actions
- Updated `aeon.yml` to dispatch `session-sync` skill

## NERV Desktop App
*2026-03-24 session*
- Designed Tauri 2.x + React desktop command center (10 panels)
- Architecture: Turborepo monorepo, WS server at :5558 for agent interaction
- Surfaces 156 aigency02 agents, 39 Aeon skills, 205+ superpowers
- Next: write spec doc → spec review → writing-plans → implementation
