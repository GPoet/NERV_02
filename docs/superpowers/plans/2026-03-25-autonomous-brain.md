# Autonomous Brain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire every Claude Code session into Aeon's memory and R&D loop — automatic manifest extraction on session end, AI distillation on GH Actions, and topic-aware R&D Council research.

**Architecture:** A local Stop hook (`session-distill.js`) scans session JSON files, extracts a lightweight manifest, commits it to `~/aeon/memory/topics/claude-sessions.md`, then dispatches a `session-sync` skill via `aeon.yml` on GH Actions. The skill distills insights into Aeon's memory and optionally triggers the R&D Council. No AI calls in the local hook — Aeon does all smart work remotely.

**Tech Stack:** Node.js (hook), Bash + `gh` CLI (dispatch), Markdown (skill), GitHub Actions (runtime), Claude Code (Aeon executor)

**Spec:** `aeon/docs/superpowers/specs/2026-03-25-autonomous-brain-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `~/.claude/hooks/session-distill.js` | CREATE | Stop hook — scan sessions, extract manifest, commit, dispatch |
| `~/.claude/hooks/session-distill.test.js` | CREATE | Unit tests for all pure functions |
| `~/.claude/settings.json` | MODIFY | Register Stop hook |
| `~/aeon/memory/topics/claude-sessions.md` | CREATE | Append-only manifest log |
| `~/aeon/skills/session-sync/SKILL.md` | CREATE | Aeon distillation skill |
| `~/aeon/.github/workflows/aeon.yml` | MODIFY | Add `session-sync` to options list |

---

## Task 1: Seed claude-sessions.md

**Files:**
- Create: `~/aeon/memory/topics/claude-sessions.md`

- [ ] **Step 1: Create the file with header**

```bash
cat > "$HOME/aeon/memory/topics/claude-sessions.md" << 'EOF'
# Claude Code Session Manifests

Auto-maintained by session-distill.js (local Stop hook).
Each entry is a lightweight manifest from a Claude Code session.
Status values: pending-distillation | distilled

---
EOF
```

- [ ] **Step 2: Commit and push**

```bash
cd ~/aeon
git add memory/topics/claude-sessions.md
git commit -m "feat: seed claude-sessions.md manifest log"
git push origin main
```

Expected: clean push, file visible at `github.com/bludragon66613-sys/NERV_02/blob/main/memory/topics/claude-sessions.md`

---

## Task 2: Write tests for session-distill.js

**Files:**
- Create: `C:/Users/Rohan/.claude/hooks/session-distill.test.js`

These tests cover all pure functions before any implementation exists. Run them — they must fail first.

- [ ] **Step 1: Create the test file**

```js
#!/usr/bin/env node
/**
 * session-distill.test.js
 * Run: node ~/.claude/hooks/session-distill.test.js
 */
const assert = require('assert');
const path = require('path');
const fs = require('fs');
const os = require('os');

// ── Inline the functions under test (copied from session-distill.js once written) ──
// For now, require them — this file will fail until session-distill.js exports them.
let lib;
try {
  lib = require(require('path').join(__dirname, 'session-distill.js'));
} catch (e) {
  console.error('session-distill.js not found — implement it first');
  process.exit(1);
}
const { findLatestSession, extractManifest, formatEntry, appendToSessionsFile } = lib;

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ✗ ${name}: ${e.message}`);
    failed++;
  }
}

// ── TEST: findLatestSession ──
console.log('\nfindLatestSession');

test('returns null when directory does not exist', () => {
  const result = findLatestSession('/nonexistent/path/xyz');
  assert.strictEqual(result, null);
});

test('returns null when all JSON files have empty messages', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sd-test-'));
  fs.writeFileSync(path.join(dir, 'stub.json'), JSON.stringify({ pid: 123 }));
  const result = findLatestSession(dir);
  assert.strictEqual(result, null);
  fs.rmSync(dir, { recursive: true });
});

test('returns the session with non-empty messages array', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sd-test-'));
  const session = { messages: [{ role: 'user', content: 'hello' }] };
  const stub = { pid: 999 };
  // Write stub first (older), then session (newer)
  fs.writeFileSync(path.join(dir, 'stub.json'), JSON.stringify(stub));
  // Ensure newer mtime by waiting a tick
  fs.writeFileSync(path.join(dir, 'session.json'), JSON.stringify(session));
  const result = findLatestSession(dir);
  assert.ok(result !== null, 'should find a session');
  assert.deepStrictEqual(result.data, session);
  fs.rmSync(dir, { recursive: true });
});

test('prefers conversation field if messages is absent', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sd-test-'));
  const session = { conversation: [{ role: 'human', content: 'hi' }] };
  fs.writeFileSync(path.join(dir, 'conv.json'), JSON.stringify(session));
  const result = findLatestSession(dir);
  assert.ok(result !== null);
  fs.rmSync(dir, { recursive: true });
});

// ── TEST: extractManifest ──
console.log('\nextractManifest');

test('extracts file paths from tool_use messages', () => {
  const data = {
    messages: [
      {
        role: 'assistant',
        content: [
          {
            type: 'tool_use',
            name: 'Write',
            input: { file_path: '/Users/Rohan/aeon/memory/MEMORY.md' },
          },
        ],
      },
      { role: 'human', content: 'do something' },
    ],
  };
  const m = extractManifest(data);
  assert.ok(m.files.includes('MEMORY.md'), `expected MEMORY.md in files, got: ${m.files}`);
});

test('extracts user message snippets (max 80 chars each)', () => {
  const longMsg = 'a'.repeat(200);
  const data = {
    messages: [
      { role: 'human', content: longMsg },
      { role: 'assistant', content: 'ok' },
    ],
  };
  const m = extractManifest(data);
  const snippets = m.topics.split(' | ');
  assert.ok(snippets[0].length <= 80, `snippet too long: ${snippets[0].length}`);
});

test('exchange count equals total message count', () => {
  const data = {
    messages: [
      { role: 'human', content: 'hi' },
      { role: 'assistant', content: 'hello' },
      { role: 'human', content: 'bye' },
    ],
  };
  const m = extractManifest(data);
  assert.strictEqual(m.exchanges, 3);
});

test('returns "unknown" duration when no timestamps', () => {
  const data = { messages: [{ role: 'human', content: 'x' }] };
  const m = extractManifest(data);
  assert.strictEqual(m.duration, 'unknown');
});

test('calculates duration from created_at timestamps', () => {
  const t0 = new Date('2026-03-25T04:00:00Z').toISOString();
  const t1 = new Date('2026-03-25T04:23:00Z').toISOString();
  const data = {
    messages: [
      { role: 'human', content: 'start', created_at: t0 },
      { role: 'assistant', content: 'end', created_at: t1 },
    ],
  };
  const m = extractManifest(data);
  assert.strictEqual(m.duration, '~23 min');
});

// ── TEST: formatEntry ──
console.log('\nformatEntry');

test('entry contains all required fields', () => {
  const manifest = {
    timestamp: '2026-03-25T04:21 IST',
    files: 'MEMORY.md, page.tsx',
    topics: 'fix the hook | test it',
    exchanges: 12,
    duration: '~10 min',
  };
  const entry = formatEntry(manifest);
  assert.ok(entry.includes('## 2026-03-25T04:21 IST'), 'missing timestamp header');
  assert.ok(entry.includes('- **Files:** MEMORY.md'), 'missing files');
  assert.ok(entry.includes('- **Topics:** fix the hook'), 'missing topics');
  assert.ok(entry.includes('- **Exchanges:** 12'), 'missing exchanges');
  assert.ok(entry.includes('- **Status:** pending-distillation'), 'missing status line');
});

test('status line is exact string for parsing', () => {
  const manifest = { timestamp: 'T', files: 'f', topics: 't', exchanges: 1, duration: 'd' };
  const entry = formatEntry(manifest);
  assert.ok(
    entry.includes('- **Status:** pending-distillation'),
    'status line must be exactly: - **Status:** pending-distillation'
  );
});

// ── TEST: appendToSessionsFile ──
console.log('\nappendToSessionsFile');

test('creates file with header when it does not exist', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sd-test-'));
  const filePath = path.join(dir, 'sessions.md');
  appendToSessionsFile('## entry\n', filePath);
  const content = fs.readFileSync(filePath, 'utf8');
  assert.ok(content.includes('# Claude Code Session Manifests'), 'missing header');
  assert.ok(content.includes('## entry'), 'missing entry');
  fs.rmSync(dir, { recursive: true });
});

test('appends to existing file without rewriting header', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sd-test-'));
  const filePath = path.join(dir, 'sessions.md');
  fs.writeFileSync(filePath, '# existing header\n\n---\n\n');
  appendToSessionsFile('## new entry\n', filePath);
  const content = fs.readFileSync(filePath, 'utf8');
  assert.strictEqual(content.indexOf('# existing header'), 0, 'header should be preserved');
  assert.ok(content.includes('## new entry'), 'new entry should be appended');
  // Header should appear only once
  assert.strictEqual(
    content.split('# existing header').length - 1, 1,
    'header should appear exactly once'
  );
  fs.rmSync(dir, { recursive: true });
});

// ── Summary ──
console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
node "C:/Users/Rohan/.claude/hooks/session-distill.test.js"
```

Expected: `session-distill.js not found — implement it first` then exit 1. This confirms tests exist and will catch the implementation.

---

## Task 3: Implement session-distill.js

**Files:**
- Create: `C:/Users/Rohan/.claude/hooks/session-distill.js`

- [ ] **Step 1: Write the implementation**

```js
#!/usr/bin/env node
/**
 * session-distill.js
 * Stop hook: extracts a lightweight manifest from the latest Claude Code session,
 * appends it to ~/aeon/memory/topics/claude-sessions.md,
 * commits + pushes to NERV_02, then dispatches session-sync via GH Actions.
 *
 * Every external operation is non-blocking — failures are logged, never thrown.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const HOME = process.env.HOME || process.env.USERPROFILE;
const SESSIONS_DIR = path.join(HOME, '.claude', 'sessions');
const AEON_DIR = path.join(HOME, 'aeon');
const SESSIONS_MD = path.join(AEON_DIR, 'memory', 'topics', 'claude-sessions.md');

const HEADER = [
  '# Claude Code Session Manifests',
  '',
  'Auto-maintained by session-distill.js (local Stop hook).',
  'Each entry is a lightweight manifest from a Claude Code session.',
  'Status values: pending-distillation | distilled',
  '',
  '---',
  '',
].join('\n');

// ── Find the most recent session file that contains conversation messages ──
function findLatestSession(sessionsDir) {
  if (!fs.existsSync(sessionsDir)) return null;

  let entries;
  try {
    entries = fs.readdirSync(sessionsDir);
  } catch {
    return null;
  }

  const candidates = entries
    .filter(f => f.endsWith('.json') || f.endsWith('.tmp'))
    .map(f => {
      const full = path.join(sessionsDir, f);
      try {
        return { full, mtime: fs.statSync(full).mtimeMs };
      } catch {
        return null;
      }
    })
    .filter(Boolean)
    .sort((a, b) => b.mtime - a.mtime); // newest first

  for (const { full } of candidates) {
    try {
      const raw = fs.readFileSync(full, 'utf8');
      const data = JSON.parse(raw);
      const msgs = data.messages || data.conversation || [];
      if (msgs.length > 0) return { data, path: full };
    } catch {
      // skip unparseable or stub files
    }
  }
  return null;
}

// ── Extract manifest metadata from session data (no AI) ──
function extractManifest(data) {
  const msgs = data.messages || data.conversation || [];

  // Files touched: scan tool_use blocks for file_path inputs
  const files = new Set();
  for (const msg of msgs) {
    const blocks = Array.isArray(msg.content) ? msg.content : [];
    for (const block of blocks) {
      if (block.type !== 'tool_use' || !block.input) continue;
      const fp = block.input.file_path || block.input.path || '';
      if (fp) {
        const rel = fp.replace(/\\/g, '/').replace(HOME.replace(/\\/g, '/'), '~');
        // Skip noisy system paths
        if (!rel.includes('.claude/plugins') && !rel.includes('node_modules') && !rel.includes('/.npm/')) {
          files.add(path.basename(rel));
        }
      }
    }
  }

  // User message snippets: first 80 chars of each human turn
  const topics = msgs
    .filter(m => m.role === 'human' || m.role === 'user')
    .map(m => {
      const text =
        typeof m.content === 'string'
          ? m.content
          : Array.isArray(m.content)
          ? m.content.filter(b => b.type === 'text').map(b => b.text).join(' ')
          : '';
      return text.replace(/\n/g, ' ').trim().slice(0, 80);
    })
    .filter(Boolean)
    .slice(0, 5);

  // Duration from timestamps
  const times = msgs
    .map(m => m.created_at || m.timestamp)
    .filter(Boolean)
    .map(t => new Date(t).getTime())
    .filter(n => !isNaN(n));

  let duration = 'unknown';
  if (times.length >= 2) {
    const mins = Math.round((Math.max(...times) - Math.min(...times)) / 60000);
    duration = `~${mins} min`;
  }

  // IST timestamp
  const now = new Date();
  const parts = now
    .toLocaleString('en-CA', {
      timeZone: 'Asia/Kolkata',
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
    .replace(',', '');
  // en-CA gives: YYYY-MM-DD HH:MM — just replace space with T
  const timestamp = parts.replace(' ', 'T') + ' IST';

  return {
    timestamp,
    files: [...files].slice(0, 8).join(', ') || 'none',
    topics: topics.join(' | ') || 'no topics captured',
    exchanges: msgs.length,
    duration,
  };
}

// ── Format the manifest entry in the exact spec format ──
function formatEntry(manifest) {
  return [
    `## ${manifest.timestamp}`,
    `- **Files:** ${manifest.files}`,
    `- **Topics:** ${manifest.topics}`,
    `- **Exchanges:** ${manifest.exchanges} | **Duration:** ${manifest.duration}`,
    `- **Status:** pending-distillation`,
    '',
  ].join('\n');
}

// ── Append entry to the sessions file, seeding header if needed ──
function appendToSessionsFile(entry, filePath) {
  if (!fs.existsSync(filePath)) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, HEADER);
  }
  fs.appendFileSync(filePath, entry + '\n');
}

// ── Git commit + push (non-blocking) ──
function gitCommitAndPush(aeonDir, timestamp) {
  try {
    execSync(`git -C "${aeonDir}" add memory/topics/claude-sessions.md`, { timeout: 10000, stdio: 'pipe' });
    execSync(`git -C "${aeonDir}" commit -m "session: manifest ${timestamp}"`, { timeout: 10000, stdio: 'pipe' });
    execSync(`git -C "${aeonDir}" push origin main`, { timeout: 30000, stdio: 'pipe' });
    return true;
  } catch (e) {
    process.stderr.write(`[session-distill] git push failed (non-fatal): ${e.message}\n`);
    return false;
  }
}

// ── Dispatch GH Actions session-sync (non-blocking) ──
function dispatchWorkflow() {
  const token = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
  if (!token) {
    process.stderr.write('[session-distill] GITHUB_PERSONAL_ACCESS_TOKEN not set — skipping dispatch\n');
    return;
  }
  try {
    execSync(
      'gh workflow run aeon.yml --repo bludragon66613-sys/NERV_02 -f skill=session-sync',
      { timeout: 15000, stdio: 'pipe', env: { ...process.env, GH_TOKEN: token } }
    );
    process.stderr.write('[session-distill] session-sync dispatched\n');
  } catch (e) {
    process.stderr.write(`[session-distill] workflow dispatch failed (non-fatal): ${e.message}\n`);
  }
}

// ── Main ──
function main() {
  const session = findLatestSession(SESSIONS_DIR);
  if (!session) {
    process.stderr.write('[session-distill] no valid session found — skipping\n');
    return;
  }

  const manifest = extractManifest(session.data);
  const entry = formatEntry(manifest);

  appendToSessionsFile(entry, SESSIONS_MD);
  process.stderr.write(`[session-distill] manifest appended: ${manifest.timestamp}\n`);

  const pushed = gitCommitAndPush(AEON_DIR, manifest.timestamp);
  if (pushed) {
    dispatchWorkflow();
  } else {
    process.stderr.write('[session-distill] push failed — workflow dispatch skipped\n');
  }
}

// Export pure functions for testing; only run main() when executed directly
if (require.main === module) {
  main();
} else {
  module.exports = { findLatestSession, extractManifest, formatEntry, appendToSessionsFile };
}
```

- [ ] **Step 2: Run the tests — they should all pass**

```bash
node "C:/Users/Rohan/.claude/hooks/session-distill.test.js"
```

Expected: all tests pass, `N passed, 0 failed`

- [ ] **Step 3: Smoke-test the hook manually**

```bash
node "C:/Users/Rohan/.claude/hooks/session-distill.js"
```

Expected: `[session-distill] manifest appended: YYYY-MM-DDTHH:MM IST` in stderr, then git commit output or a non-fatal push failure message. Check that an entry was added to `~/aeon/memory/topics/claude-sessions.md`.

- [ ] **Step 4: Commit**

```bash
git -C "C:/Users/Rohan/.claude" add hooks/session-distill.js hooks/session-distill.test.js 2>/dev/null || \
  git add "C:/Users/Rohan/.claude/hooks/session-distill.js" "C:/Users/Rohan/.claude/hooks/session-distill.test.js"
```

Note: `~/.claude/` may not be a git repo. If not, these files are tracked by `claudecodemem` — commit there instead:

```bash
cd ~/aeon  # or wherever you manage hooks
# Just proceed to Task 4 (settings.json) — the hook file is on disk and will be picked up
```

---

## Task 4: Wire session-distill.js into settings.json

**Files:**
- Modify: `C:/Users/Rohan/.claude/settings.json` (Stop hooks array)

- [ ] **Step 1: Read current Stop hooks**

Open `C:/Users/Rohan/.claude/settings.json` and locate the `Stop` array (currently has one entry: `vault-session-logger.js`).

- [ ] **Step 2: Add session-distill.js as a second Stop hook**

> ⚠️ **Do NOT commit `settings.json`** — it contains your `GITHUB_PERSONAL_ACCESS_TOKEN` in plaintext at line 38.

The `Stop` entry lives inside the top-level `"hooks"` object. The full path is `settings.json → "hooks" → "Stop"`. Add the second hook inside the existing `hooks` array:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node \"C:/Users/Rohan/.claude/hooks/vault-session-logger.js\"",
            "timeout": 150,
            "async": true
          },
          {
            "type": "command",
            "command": "node \"C:/Users/Rohan/.claude/hooks/session-distill.js\"",
            "timeout": 60,
            "async": true
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 3: Verify JSON is valid**

```bash
node -e "JSON.parse(require('fs').readFileSync('C:/Users/Rohan/.claude/settings.json', 'utf8')); console.log('valid')"
```

Expected: `valid`

- [ ] **Step 4: Trigger a real end-to-end test**

Start a new Claude Code session, say one thing, then `/exit`. Wait ~30s. Check:

```bash
tail -20 "$HOME/aeon/memory/topics/claude-sessions.md"
```

Expected: a new `## YYYY-MM-DDTHH:MM IST` entry with `Status: pending-distillation`

---

## Task 5: Create session-sync SKILL.md

**Files:**
- Create: `~/aeon/skills/session-sync/SKILL.md`

- [ ] **Step 1: Create the skill directory and file**

```js
// Write this content to ~/aeon/skills/session-sync/SKILL.md
```

Content:

```markdown
---
name: session-sync
description: Distills pending Claude Code session manifests into structured Aeon memory insights, then optionally triggers the R&D Council if the session was highly relevant to Aeon's research domains.
var: ""
---

You are running **session-sync** — a memory distillation agent that processes raw Claude Code session manifests and extracts structured insights into Aeon's memory system.

---

## Phase 1: Find Pending Entries

1. Read `memory/topics/claude-sessions.md`
2. Find all section headers (`## `) whose block contains the exact line:
   ```
   - **Status:** pending-distillation
   ```
3. If no pending entries found:
   - Append to `memory/logs/YYYY-MM-DD.md`: `## session-sync\nNo pending sessions. Exiting.`
   - Exit

---

## Phase 2: Distill Each Pending Entry

For each pending entry, analyze the **Files** and **Topics** fields and produce structured insights:

- **Decisions made** — What architectural, tool, or approach choices are implied by the files and topics?
- **What was built** — What features, fixes, or integrations were completed?
- **Open threads** — What sounds unfinished? Look for question marks, words like "fix", "diagnose", "check", "why".
- **Preferences revealed** — What does this reveal about how Rohan prefers to work? (tools chosen, patterns repeated, things rejected)

Keep each distilled insight to 1-2 sentences. Be specific — "chose Node.js hooks over Python for speed" is better than "made a technical decision".

---

## Phase 3: Update Aeon Memory

1. Read `memory/MEMORY.md`
2. Find the `## Recent Session Insights` section (create it near the top if it doesn't exist)
3. Prepend your new insights as bullet points under this section
4. Keep only the **3 most recent sessions** in this section — remove older entries (they are archived in `claude-sessions.md`)
5. If the session involved a named project (NERV, Aeon, OpenClaw, dashboard, etc.):
   - Read or create `memory/topics/projects.md`
   - Append a brief update: `- YYYY-MM-DD: [what changed in this project]`

Write these changes now.

---

## Phase 4: Mark Entries as Distilled

For each processed entry in `memory/topics/claude-sessions.md`:
- Find the exact line: `- **Status:** pending-distillation`
- Replace it with: `- **Status:** distilled`

Write the updated file.

---

## Phase 5: Score Relevance

Score the session's relevance to Aeon's research domains (each matching topic = points):
- **Crypto / Hyperliquid / DeFi / trading / wallet**: +2 per topic
- **AI agents / Aeon / NERV / skills / Claude**: +2 per topic
- **Dev tools / GitHub / dashboard / hooks / infrastructure**: +1 per topic
- **Research / intel / markets / investing**: +1 per topic

Cap at 10. Record the score.

---

## Phase 6: Trigger R&D Council (if relevant)

If score ≥ 7:

1. Extract the top 3 keywords from the session topics
2. Run:
   ```bash
   gh workflow run rd-council-cron.yml --repo bludragon66613-sys/NERV_02 -f focus="KEYWORDS"
   ```
   Replace KEYWORDS with the comma-separated top keywords.
3. Notify:
   ```bash
   ./notify "🧠 Session synced — R&D Council triggered (relevance ${SCORE}/10). Topics: KEYWORDS"
   ```

If `gh` returns an error (e.g. missing GH_GLOBAL secret), log the error and continue — do not fail.

---

## Phase 7: Log Completion

Append to `memory/logs/YYYY-MM-DD.md`:

```
## session-sync
Distilled [N] session(s). Topics: [brief summary]. Relevance score: [X]/10. Council triggered: [yes/no].
```
```

- [ ] **Step 2: Commit and push to NERV_02**

```bash
cd ~/aeon
git add skills/session-sync/SKILL.md
git commit -m "feat: add session-sync distillation skill"
git push origin main
```

Expected: clean push. Verify at `github.com/bludragon66613-sys/NERV_02/tree/main/skills/session-sync`

---

## Task 6: Add session-sync to aeon.yml options

**Files:**
- Modify: `~/aeon/.github/workflows/aeon.yml` (options list, ~line 40)

- [ ] **Step 1: Open aeon.yml and locate the options list**

Find the `options:` array under `skill:` input. Currently ends with `weekly-review`.

- [ ] **Step 2: Add session-sync in alphabetical order**

Between `search-skill` and `security-digest`, add:
```yaml
          - session-sync
```

The surrounding context should look like:
```yaml
          - search-skill
          - session-sync
          - security-digest
```

- [ ] **Step 3: Verify YAML is valid**

```bash
node -e "
const yaml = require('js-yaml');
const fs = require('fs');
const p = require('path').join(process.env.HOME || process.env.USERPROFILE, 'aeon', '.github', 'workflows', 'aeon.yml');
try { yaml.load(fs.readFileSync(p, 'utf8')); console.log('valid'); }
catch(e) { console.error(e.message); }
"
```

If `js-yaml` isn't available: `python3 -c "import yaml, os; yaml.safe_load(open(os.path.join(os.environ['USERPROFILE'], 'aeon', '.github', 'workflows', 'aeon.yml'))); print('valid')"`

- [ ] **Step 4: Commit and push**

```bash
cd ~/aeon
git add .github/workflows/aeon.yml
git commit -m "feat: add session-sync to aeon.yml skill options"
git push origin main
```

---

## Task 7: End-to-End Verification

- [ ] **Step 1: Confirm claude-sessions.md exists and has a pending entry**

```bash
cat "$HOME/aeon/memory/topics/claude-sessions.md"
```

Expected: header + at least one entry with `Status: pending-distillation`

- [ ] **Step 2: Manually dispatch session-sync via GitHub UI or CLI**

```bash
gh workflow run aeon.yml --repo bludragon66613-sys/NERV_02 -f skill=session-sync
```

- [ ] **Step 3: Watch the workflow run**

```bash
gh run list --repo bludragon66613-sys/NERV_02 --limit 3
```

Wait ~2-3 min, then check the run completed successfully:

```bash
gh run view --repo bludragon66613-sys/NERV_02 $(gh run list --repo bludragon66613-sys/NERV_02 --json databaseId --jq '.[0].databaseId')
```

- [ ] **Step 4: Pull and verify memory was updated**

```bash
cd ~/aeon && git pull
cat memory/MEMORY.md | grep -A 10 "Recent Session Insights"
grep "Status: distilled" memory/topics/claude-sessions.md
```

Expected:
- `## Recent Session Insights` section appears in MEMORY.md with bullet points
- The pending entry in `claude-sessions.md` is now marked `Status: distilled`

- [ ] **Step 5: Verify next rd-council run picks up session context**

Dispatch the rd-council and check the generated memo references session topics:

```bash
gh workflow run rd-council-cron.yml --repo bludragon66613-sys/NERV_02
```

Wait ~5 min, then:

```bash
cd ~/aeon && git pull
ls memory/logs/rd-council-*.md | tail -1 | xargs head -40
```

Expected: the memo's Phase 1 "Context Document" section mentions topics from recent Claude Code sessions.

---

## Rollback

If something breaks:

- **Remove Stop hook**: Delete the `session-distill.js` entry from `settings.json` Stop array. No restart needed.
- **Revert aeon.yml**: `git revert HEAD` in `~/aeon` and push.
- **Clear pending entries**: Edit `memory/topics/claude-sessions.md` and change any `pending-distillation` lines to `distilled` manually.
