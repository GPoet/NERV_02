# Autonomous Brain — Design Spec
**Date:** 2026-03-25
**Status:** Approved (v2 — post review fixes)
**Approach:** B — Distillation Subagent + Aeon Sync (Hybrid)

---

## Problem

Claude Code has no memory between sessions beyond what is explicitly written to `~/.claude/memory/`. Most session value (decisions made, preferences revealed, corrections, work done) is lost. The R&D Council runs on a fixed schedule with no awareness of what Rohan has been working on. There is no feedback loop between Claude Code sessions and Aeon's research.

## Goals

1. **Better memory capture** — structured insights extracted from every session automatically
2. **Preference learning** — Claude adapts to working style over time
3. **Cross-session context** — each session starts knowing what we left off on
4. **R&D automation** — R&D Council researches topics from recent sessions, no manual focus input needed
5. **Proactive alerts** — Telegram alert when research is directly relevant to current work

---

## Architecture

```
[Claude Code session ends]
         ↓
session-distill.js  (Stop hook, async, non-blocking)
  • scans ~/.claude/sessions/*.json for most-recent file with non-empty messages[]
  • extracts lightweight manifest (files touched, user message snippets, duration)
  • appends manifest entry → ~/aeon/memory/topics/claude-sessions.md
  • git commit + push to NERV_02  (non-blocking — fails silently if push fails)
  • gh workflow run aeon.yml --field skill=session-sync
         ↓
[GH Actions: session-sync skill via aeon.yml]
  • reads memory/topics/claude-sessions.md — processes entries with Status: pending-distillation
  • Claude distills: decisions, corrections, built, open threads, preferences revealed
  • updates memory/MEMORY.md and relevant memory/topics/ files
  • marks processed entries: Status: distilled
  • scores overall session relevance to Aeon research domains (0–10)
  • if relevance ≥ 7 → gh workflow run rd-council-cron.yml --field focus="[session topics]"
  • commits all changes
         ↓
[R&D Council — triggered or scheduled]
  Phase 1 already reads memory/topics/ — picks up claude-sessions.md automatically
  • researches topics present in recent session manifest entries
  • writes memo → memory/logs/rd-council-YYYY-MM-DD.md → /rnd page
  • ./notify Telegram summary (existing behaviour)
  • HIGH RELEVANCE: if any finding directly matches session work → extra ./notify alert
```

**Principle:** Local hook is dumb and fast (no API calls, no auth dependency). Aeon on GH Actions does all AI-heavy work with full Claude access and no timeout pressure. The rd-council skill is NOT modified — it already reads `memory/topics/` in Phase 1.

---

## Components

### 1. session-distill.js (NEW)
**Location:** `~/.claude/hooks/session-distill.js`
**Trigger:** Stop hook, `async: true`, timeout: 60

**Session data source:** Scans `~/.claude/sessions/*.json` — picks the file with the highest `mtime` that has a non-empty `messages` (or `conversation`) array. This is the same strategy used by `vault-session-logger.js`. Falls back silently if no valid file found.

**What it extracts (no AI):**
- Files touched: tool_use messages with tool_name Read/Write/Edit/Bash, extract file_path from input
- User message snippets: first 80 chars of each `role: "human"` message content
- Exchange count: total messages
- Duration: `last_message.created_at - first_message.created_at` (if timestamps present)

**Manifest entry — exact format (writer and reader must match exactly):**
```markdown
## 2026-03-25T04:21 IST
- **Files:** dashboard/app/rnd/page.tsx, hooks/session-distill.js
- **Topics:** run it via terminal | are you learning | autonomous brain design
- **Exchanges:** 18 | **Duration:** ~23 min
- **Status:** pending-distillation
```

**After appending manifest:**
1. `git -C ~/aeon add memory/topics/claude-sessions.md`
2. `git -C ~/aeon commit -m "session: manifest $(date +%Y-%m-%dT%H:%M)"`
3. `git -C ~/aeon push origin main` — wrapped in try/catch, failure is logged but does NOT throw
4. `gh workflow run aeon.yml --repo bludragon66613-sys/NERV_02 -f skill=session-sync` — requires `GITHUB_PERSONAL_ACCESS_TOKEN` in env. Guard: if env var missing, log warning and skip dispatch (don't fail).

**Error handling:** Every step is wrapped. Hook exits cleanly regardless of failures. A failed push or dispatch means the session is not distilled — acceptable, not catastrophic.

### 2. settings.json update
**Location:** `~/.claude/settings.json`
**Change:** Add entry to the existing `Stop` hooks array:
```json
{
  "type": "command",
  "command": "node \"C:/Users/Rohan/.claude/hooks/session-distill.js\"",
  "timeout": 60,
  "async": true
}
```

### 3. session-sync skill (NEW)
**Location:** `~/aeon/skills/session-sync/SKILL.md`
**Invoked via:** `aeon.yml` workflow with `skill=session-sync`

**Steps:**
1. Read `memory/topics/claude-sessions.md`
2. Find all entries where the line `- **Status:** pending-distillation` appears (exact match)
3. For each pending entry, extract: files list, topics list, exchange count
4. Distill insights:
   - **Decisions** — infer from topics and files what architectural/tool choices were made
   - **What was built** — which files were created/modified and what they likely do
   - **Open threads** — topics mentioned that sound unfinished (questions, "fix", "diagnose")
   - **Preferences revealed** — communication patterns, tools chosen, rejected approaches
5. Append distilled insights to `memory/MEMORY.md` (under a `## Recent Session Insights` section)
6. Update relevant topic files in `memory/topics/` (e.g. `projects.md` if NERV mentioned)
7. Replace `- **Status:** pending-distillation` with `- **Status:** distilled` for each processed entry
8. Score overall relevance: count how many topics relate to crypto / dev / AI / intel domains
9. If score ≥ 7: `gh workflow run rd-council-cron.yml --repo bludragon66613-sys/NERV_02 -f focus="[comma-separated session topics]"`
10. Append log entry to `memory/logs/YYYY-MM-DD.md`

**Note on dispatch:** Uses `$GH_TOKEN` which in `aeon.yml` is set to `secrets.GH_GLOBAL || secrets.GITHUB_TOKEN`. `GH_GLOBAL` is a PAT with `workflow` scope — required for triggering other workflows from within Actions. `GITHUB_TOKEN` cannot trigger `workflow_dispatch` on the same repo (GitHub limitation). If `GH_GLOBAL` is not set, the dispatch step is skipped with a logged warning.

### 4. aeon.yml update
**Location:** `~/aeon/.github/workflows/aeon.yml`
**Change:** Add `session-sync` to the `options:` list under `skill:` input, in alphabetical order (between `search-skill` and `security-digest`).

### 5. R&D Council — NO CHANGES NEEDED
The `rd-council` skill already reads `memory/topics/` in Phase 1 (step 3: "Read `memory/topics/` if any files exist"). Once `claude-sessions.md` exists there, it will be read automatically on every council run. The council's existing Telegram notification covers the summary alert. No modifications required.

### 6. claude-sessions.md (NEW, seeded on first run)
**Location:** `~/aeon/memory/topics/claude-sessions.md`
**Created by:** session-distill.js on first session end after deployment
**Header:**
```markdown
# Claude Code Session Manifests

This file is auto-maintained by session-distill.js (local Stop hook).
Each entry is a lightweight manifest from a Claude Code session.
Status values: pending-distillation | distilled

---
```

---

## Data Flow Summary

| Step | Who | What | When |
|------|-----|------|------|
| Session ends | session-distill.js (local) | Extracts manifest, commits to Aeon repo | Immediately on stop |
| session-sync runs | Aeon (GH Actions) | Distills insights, updates memory | ~2-5 min after stop |
| rd-council triggered | Aeon (GH Actions) | Topic-aware research + Telegram memo | If relevance ≥ 7, within 10 min |
| Next session starts | vault-session-context.js (existing) | Injects recent session context | Unchanged |
| Scheduled rd-council | Aeon (GH Actions) | Always reads claude-sessions.md | Mon + Thu 09:00 IST |

---

## Files Changed (6)

| File | Action | Notes |
|------|--------|-------|
| `~/.claude/hooks/session-distill.js` | CREATE | Stop hook |
| `~/.claude/settings.json` | MODIFY | Add Stop hook entry |
| `~/aeon/skills/session-sync/SKILL.md` | CREATE | New Aeon skill |
| `~/aeon/.github/workflows/aeon.yml` | MODIFY | Add session-sync to options list |
| `~/aeon/memory/topics/claude-sessions.md` | CREATE | Seeded with header by hook |
| `~/aeon/skills/rd-council/SKILL.md` | NO CHANGE | Already reads memory/topics/ |

---

## Prerequisites

- `~/aeon` must have git remote configured with push credentials (SSH or cached HTTPS)
- `GITHUB_PERSONAL_ACCESS_TOKEN` must be set in `~/.claude/settings.json` `env:` (already present)
- `GH_GLOBAL` secret must be set in NERV_02 repo for cross-workflow dispatch from GH Actions

---

## Success Criteria

- [ ] Session ends → manifest entry appears in `claude-sessions.md` within 60s
- [ ] session-sync marks entries `distilled` and updates `memory/MEMORY.md` within 5 min of session end
- [ ] Next rd-council run includes session topics in its Phase 1 context (visible in memo)
- [ ] After 5 sessions, `claude-sessions.md` shows a clear thread of evolving work context
- [ ] When session relevance ≥ 7, rd-council is triggered and Telegram alert arrives within 15 min

---

## Out of Scope

- Modifying `vault-session-logger.js` (unchanged)
- Modifying `vault-session-context.js` (unchanged)
- `/rnd` engagement tracking (Approach C — future)
- skill-evolve integration for R&D skills (Approach C — future)
- Direct relevance-scored Telegram alerts per finding (rd-council's existing summary is sufficient for now)
