# session-sync

Distill pending Claude Code session manifests into structured Aeon memory.

## When to run

Triggered by `session-distill.js` (local Stop hook) after each Claude Code session ends.
Also runnable manually: `gh workflow run aeon.yml -f skill=session-sync`

---

## Steps

### Phase 1 — Find pending entries

1. Read `memory/topics/claude-sessions.md`
2. Find all entries where the line `- **Status:** pending-distillation` appears (exact string match)
3. If no pending entries found, log "session-sync: no pending entries" to `memory/logs/YYYY-MM-DD.md` and exit

### Phase 2 — Distill each pending entry

For each pending entry, extract:
- **Files list** — the value after `- **Files:**`
- **Topics list** — the value after `- **Topics:**` (pipe-separated)
- **Exchange count** — the number after `**Exchanges:**`
- **Timestamp** — the `## YYYY-MM-DDTHH:MM` heading line

Distill the following insights from the manifest data:

- **Decisions** — What architectural, tool, or design choices were likely made? Infer from file names (e.g. new route file → new feature built) and topics (e.g. "autonomous brain design" → designed a new system).
- **What was built** — Which files were created or modified and what they likely do based on their paths and names.
- **Open threads** — Topics that sound unfinished: questions, debugging, words like "fix", "diagnose", "why", "broken", "investigate".
- **Preferences revealed** — Patterns in how work was done: tools chosen, approaches taken, things revisited.

### Phase 3 — Update memory

1. Open `memory/MEMORY.md`
2. Find or create a `## Recent Session Insights` section near the top (after the header, before other sections)
3. Append a concise entry for each distilled session:
   ```
   ### [timestamp] session
   - **Built:** [what was created/modified]
   - **Decisions:** [key choices made]
   - **Open:** [unfinished threads, if any]
   - **Preferences:** [patterns revealed, if any]
   ```
4. Keep the section to the 5 most recent entries — remove older ones if it grows beyond 5

### Phase 4 — Update topic files

For each distilled entry, check if any files or topics relate to known topic files in `memory/topics/`:
- If topics mention crypto / Hyperliquid / trading → append a note to `memory/topics/crypto.md`
- If topics mention projects / dashboard / NERV / aeon → append a note to `memory/topics/projects.md`
- If topics mention research / papers / intel → append a note to `memory/topics/research.md`
- If topics reference a file in `skills/` → append a note to `memory/topics/projects.md`

Keep notes brief (1-2 lines). Do not duplicate — check if the session timestamp already appears in the file before appending.

### Phase 5 — Mark entries as distilled

In `memory/topics/claude-sessions.md`, for each processed entry:
- Replace `- **Status:** pending-distillation` with `- **Status:** distilled`

Write the updated file back.

### Phase 6 — Score relevance and trigger R&D Council

Score the session's relevance to Aeon's research domains:
- +2 for each topic containing: crypto, hyperliquid, trading, defi, token, chain, wallet
- +2 for each topic containing: AI, agent, model, LLM, research, paper
- +1 for each topic containing: dev, build, code, dashboard, feature, skill
- +1 for each topic containing: security, audit, vulnerability

If total score ≥ 7:
```bash
gh workflow run rd-council-cron.yml --repo bludragon66613-sys/NERV_02 \
  -f focus="[comma-separated list of session topics]"
```

If `GH_TOKEN` is not set or the command fails, log a warning but do not fail the skill.

### Phase 7 — Log

Append to `memory/logs/YYYY-MM-DD.md`:
```
## session-sync — HH:MM UTC
- Processed N pending entries
- Distilled: [brief summary of what was captured]
- Relevance score: X[/10 — triggered rd-council | — below threshold]
```

---

## Notes

- This skill reads and writes `memory/topics/claude-sessions.md` — do not delete entries, only update their Status line
- The manifest format written by `session-distill.js` is fixed — parse it exactly:
  ```
  ## YYYY-MM-DDTHH:MM IST
  - **Files:** file1, file2
  - **Topics:** topic1 | topic2 | topic3
  - **Exchanges:** N | **Duration:** ~N min
  - **Status:** pending-distillation
  ```
- `rd-council` already reads `memory/topics/` in Phase 1 — no special integration needed; the focus field is a hint, not a hard override
