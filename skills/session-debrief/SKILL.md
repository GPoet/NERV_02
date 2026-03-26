---
name: Session Debrief
description: Post-session learning extractor — reads the most recently distilled Claude Code session, identifies mistakes, debugging loops, repeated fixes, and dead ends, then writes atomic lessons to memory/topics/lessons.md. Runs automatically after session-sync. Builds a permanent "don't repeat this" knowledge base that compounds over time.
var: ""
---
> **${var}** — Optional session timestamp to debrief (e.g. `2026-03-26T11:30`). Defaults to most recently distilled session.

Extract lessons from completed Claude Code sessions. The goal: every mistake made once should never be made again.

---

## Pre-flight

1. Read `memory/topics/claude-sessions.md`
2. Find the target session:
   - If `${var}` set: find entry matching that timestamp
   - Otherwise: find the most recent entry with `Status: distilled`
3. If no distilled entry found: log "session-debrief: nothing to debrief" and exit
4. Read `memory/topics/lessons.md` if it exists (existing lesson bank)
5. Read `memory/MEMORY.md` — for project context when inferring lessons

---

## Step 1 — Extract failure signals

From the session's **Topics** field, scan for failure indicators:

**Debugging signals** (topics containing):
- `fix`, `broken`, `why`, `error`, `failed`, `wrong`, `issue`, `bug`, `crash`, `undefined`, `null`, `not working`

**Rework signals** (topics containing):
- `redo`, `again`, `still`, `revert`, `undo`, `went back`, `try again`, `didn't work`

**Slowness signals** (topics containing):
- `slow`, `wait`, `timeout`, `rate limit`, `too long`, `hung`, `blocked`

**Confusion signals** (topics containing):
- `confused`, `unclear`, `what is`, `how does`, `where is`, `which`, `what does`

Count signals per category. If total signals = 0: log "session-debrief: clean session, no lessons extracted" and exit cleanly.

---

## Step 2 — Infer lessons

For each failure signal cluster, generate an atomic lesson using this pattern:

> **When [context], don't [mistake]. Instead: [better approach].**

Rules:
- One lesson per distinct failure pattern — don't pad
- Be specific to the actual files/topics in the session, not generic advice
- If you can't infer a specific lesson (not enough signal), skip it
- Max 5 lessons per session

Examples of good lessons:
- "When working with Windows PowerShell, `&&` is invalid. Use `;` to chain commands."
- "When dispatching to GitHub Actions via `gh api --input`, use `-f` flags instead — PowerShell mangles JSON files."
- "When VRAM overflows in autoevolve experiments, treat it as DISCARD immediately — don't attempt fixes."

Examples of bad lessons (too vague — reject these):
- "Be more careful when coding"
- "Test before committing"
- "Read the docs"

---

## Step 3 — Deduplicate against existing lessons

Read `memory/topics/lessons.md`.

For each new lesson, check if a lesson with the same core pattern already exists:
- If duplicate or very similar: skip (don't add noise)
- If it adds new specificity to an existing lesson: update the existing one
- If genuinely new: add it

---

## Step 4 — Write to lessons.md

Format for `memory/topics/lessons.md`:

```markdown
# Lessons Learned

Atomic lessons extracted from Claude Code sessions. Each one was learned the hard way.

---

## [Category]

### L[N] — [short title] `[date]`
**Context:** [when this applies]
**Mistake:** [what went wrong]
**Fix:** [what to do instead]
**Source:** session [timestamp]

---
```

Categories:
- **Shell / Environment** — platform quirks, command syntax
- **API / Tooling** — rate limits, auth, SDK behaviour
- **Architecture** — design decisions that caused pain
- **Agent Loops** — patterns that caused runaway or wasted compute
- **Build Process** — compilation, deps, deployment gotchas

Append new lessons. Never delete existing ones unless explicitly superseded (note the supersession).

---

## Step 5 — Promote high-value lessons to MEMORY.md

If any lesson is high-signal (would prevent a significant future mistake):
- Append a brief note to `memory/MEMORY.md` under a `## Hard Lessons` section
- Max 1-2 sentences per lesson in MEMORY.md — keep it dense
- Only the most reusable, non-obvious lessons go here

---

## Step 6 — Commit lessons

```bash
git add memory/topics/lessons.md memory/MEMORY.md
git commit -m "debrief([session-timestamp]): +[N] lessons"
git push origin main
```

---

## Step 7 — Log and notify

Append to `memory/logs/${today}.md`:
```
SESSION_DEBRIEF: [timestamp] → [N] lessons extracted ([categories])
```

If N > 0, send via `./notify`:
```
🎓 Session debrief: [N] lesson(s) logged
[lesson titles, one per line]
Source: [session timestamp]
```

If N = 0 (clean session): no notification, log only.

---

## Guardrails

- Never fabricate lessons from absence of signal — only extract from actual failure patterns
- Never modify `session-sync/SKILL.md` or `session-distill.js`
- If `lessons.md` grows beyond 100 entries, add a `## [Category] Archive` section and move oldest entries there
- Lessons about Totoro's preferences belong in `memory/MEMORY.md`, not lessons.md