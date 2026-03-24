# NERV Agency — Design Spec
**Date:** 2026-03-24
**Status:** Approved for implementation
**Project:** ~/aeon/dashboard (Next.js 16, PM2, localhost:5555)

---

## 1. Goal

Expand the NERV dashboard with two new sections:
- **`/agency`** — NEXUS Command Center: intent input, auto-dispatch, pipeline tracker, job board
- **`/agents`** — Agent Catalog: all agents/skills searchable, one-click dispatch

Powered by the Aigency02 NEXUS doctrine (7 phases, 3 modes, 4 scenario runbooks).

---

## 2. Architecture

### PM2 Process Map
```
nerv-dashboard   :5555   Next.js 16 dashboard (existing)
openclaw-proxy   :5557   Express sidecar — holds WS to OpenClaw, accepts HTTP POSTs
```

### New Files
```
~/aeon/dashboard/
├── app/
│   ├── agency/page.tsx
│   ├── agents/page.tsx
│   └── api/
│       ├── agency/classify/route.ts
│       ├── agency/dispatch/route.ts
│       ├── agency/jobs/route.ts
│       ├── agents/catalog/route.ts
│       ├── agents/refresh/route.ts
│       └── auth/token/route.ts        ← issues client JWT from DASHBOARD_SECRET
├── lib/
│   ├── catalog.ts
│   ├── dispatch.ts
│   ├── jobs.ts
│   └── auth.ts
├── .cache/
│   ├── agents.json                    ← pre-built catalog
│   └── command-registry.json          ← command usage stats (was ~/aeon/.command-registry.json)
├── .jobs/                             ← atomic job files
└── openclaw-proxy/
    └── index.js

# Add to ~/aeon/dashboard/.gitignore:
.cache/
.jobs/
```

### Environment Variables (ecosystem.config.cjs)
```
AEON_REPO_ROOT        = C:/Users/Rohan/aeon
AEON_REPO             = bludragon66613-sys/NERV_02
DASHBOARD_SECRET      = <random 32-char secret, never NEXT_PUBLIC_>
GITHUB_TOKEN          = <gh token with workflow scope>
OPENCLAW_PROXY_URL    = http://localhost:5557
OPENCLAW_PROXY_SECRET = <random 32-char secret for proxy auth>
OPENCLAW_WS_URL       = ws://127.0.0.1:18789
AEON_WORKFLOW_FILE    = aeon.yml
AEON_REGISTRY_PATH    = C:/Users/Rohan/aeon/dashboard/.cache/command-registry.json
JWT_TTL_SECONDS       = 86400
```

**CRITICAL:** `DASHBOARD_SECRET` and `OPENCLAW_PROXY_SECRET` must NEVER be `NEXT_PUBLIC_` variables. They must never appear in the client JS bundle.

---

## 3. Components

### 3.1 `/agency` — NEXUS Command Center

**Layout:**
- Mode bar: `NEXUS-Micro` | `NEXUS-Sprint` | `NEXUS-Full`
- Scenario picker: Startup MVP / Enterprise Feature / Marketing Campaign / Incident Response / Custom
- Intent input + DISPATCH button
- Dispatch result: auto-dispatched (green banner) or suggestion cards (amber) requiring confirm
- Active pipeline: phase tracker (Phase 0→6), current agent, status badge
- Job board: skill, status, dispatched_at, output preview, [view] link

**Auto-dispatch rule:**

A skill is **read-only** if its catalog entry has `destructive: false` (or the field is absent). A skill is **destructive** if its catalog entry or `.md` frontmatter has `destructive: true`. If frontmatter is absent, apply this static fallback list:

```
# Always destructive (always show confirm modal):
hl-trade, hl-alpha, hl-monitor (with trade params), memory-flush,
self-review (with push flag), build-skill, feature, article,
changelog, idea-capture (with push)

# Everything else → read-only → auto-dispatch
```

The `readOnly` field in the classify response (Section 3.3) must match this rule.

**Suggestion cards (ambiguous flow):**
When the classifier returns `ambiguous: true`, show 3 suggestion cards. Each card has a title, description, and DISPATCH button. Clicking dispatches directly (no second confirm for read-only; confirm modal for destructive).

**Multi-phase NEXUS pipeline:**
Phase advancement (quality gates between Phase 0→6) is **deferred to a future iteration**. In this release, NEXUS-Sprint and NEXUS-Full modes dispatch Phase 0 agents only and show a banner: "Phase 0 dispatched. Manual phase advancement coming soon." NEXUS-Micro is fully implemented.

### 3.2 `/agents` — Agent Catalog

**Catalog sources** (exact directory and glob per source):

| Source | Path | Glob | Count | Type |
|--------|------|------|-------|------|
| Aigency02 agents | `~/aigency02/` | `**/*.md` excluding `strategy/`, `examples/`, `scripts/`, `skills/`, `README*`, `CONTRIBUTING*`, `LICENSE*` | 156 | `aigency02` |
| Aeon skills | `~/aeon/skills/` | `*/SKILL.md` | 39 | `aeon` |
| Global agents | `~/.claude/agents/` | `*.md` | 207 | `local` |

**Slug derivation (exact algorithm):**
```typescript
slug = path.basename(file, '.md').toLowerCase().replace(/[^a-z0-9]+/g, '-')
```

**Deduplication priority:** aigency02 > local > aeon. If two entries share a slug, the higher-priority source wins and the duplicate is dropped silently.

**Note:** Aigency02 agents are also installed to `~/.claude/agents/` via `install.sh`. They will appear in both sources — dedup handles this. Final unique count is determined at build time by the catalog builder; do not hardcode an estimate.

**Path resolution:** All `~` paths are resolved via `path.join(os.homedir(), ...)` — never use literal `~` strings with `path.join` on Windows.

**UI:**
- Search bar + Division filter (Engineering / Design / Marketing / Aeon Skills / Game Dev / Specialized / All)
- Grid of agent cards: name, division badge, one-line description, [ACTIVATE]
- [ACTIVATE] → modal with pre-filled NEXUS activation prompt (editable) + [CONFIRM DISPATCH] button

### 3.3 Intent Classifier (`POST /api/agency/classify`)

**Request:**
```typescript
{ intent: string, idempotencyKey: string }
// idempotencyKey: UUIDv4 generated client-side on each DISPATCH button press
// (not per keystroke — generated once when user submits)
```

**Client debounce:** 500ms after last keystroke before enabling DISPATCH button. UUIDv4 idempotencyKey is generated at button press time (not on keystroke). Each press generates a new UUID — retrying the same intent generates a new key and a new classify call.

**Server cache:** `Map<idempotencyKey, ClassifyResult>` — TTL 5 minutes. Cache key is `idempotencyKey` alone (strategy file hash is embedded in result for dispatch-time verification, not used as cache key).

**Strategy file:** `~/aigency02/strategy/nexus-strategy.md`
Hashed with SHA-256 at server startup and on each cache miss. Hash stored in classify result.

**Claude prompt:**
```
system: [contents of nexus-strategy.md]
user: Classify this request and return JSON matching this schema exactly:
{
  skill: string,              // best matching aeon skill or agent name
  mode: 'micro'|'sprint'|'full',
  dispatchType: 'aeon'|'local'|'nexus-scenario',
  readOnly: boolean,          // true if skill is non-destructive
  ambiguous: boolean,         // true if intent is unclear
  suggestions: [{             // populated only when ambiguous=true, max 3
    skill: string,
    mode: string,
    dispatchType: string,
    readOnly: boolean,
    label: string,
    description: string
  }],
  reasoning: string,
  strategyHash: string        // echo back the SHA-256 of nexus-strategy.md
}
```

### 3.4 Dispatcher (`POST /api/agency/dispatch`)

**Request:**
```typescript
{
  skill: string,
  mode: string,
  dispatchType: 'aeon' | 'local' | 'nexus-scenario',
  readOnly: boolean,
  strategyHash: string,       // must match current nexus-strategy.md hash
  scenarioName?: string       // for nexus-scenario type
}
```

**Strategy hash verification:** Before dispatching, recompute SHA-256 of nexus-strategy.md. If hash differs from `strategyHash` in request, return `409 Conflict` with message "Strategy file changed since classification. Please re-submit."

**Dispatch paths:**

```typescript
if (dispatchType === 'aeon') {
  // GitHub Actions workflow_dispatch
  const res = await fetch(
    `https://api.github.com/repos/${AEON_REPO}/actions/workflows/${AEON_WORKFLOW_FILE}/dispatches`,
    { method: 'POST', headers: { Authorization: `Bearer ${GITHUB_TOKEN}` },
      body: JSON.stringify({ ref: 'main', inputs: { skill } }) }
  )
  if (!res.ok) {
    // Map status codes to job error states:
    // 401/403 → 'failed:auth'  422 → 'failed:invalid-skill'  429 → 'failed:rate-limited'
    // 5xx → 'failed:github-error'
    writeJob({ ...job, status: `failed:${errorType}`, error: await res.text() })
    return
  }
}

if (dispatchType === 'local') {
  // OpenClaw proxy — proxy has its own auth
  POST http://localhost:5557/dispatch
  headers: { Authorization: `Bearer ${OPENCLAW_PROXY_SECRET}` }
  body: { agent: skill, prompt: activationPrompt }
}

if (dispatchType === 'nexus-scenario') {
  // Load and parse runbook with js-yaml + Zod
  // On parse/validation failure → writeJob({ status: 'failed:parse-error', error: err.message })
  // Dispatch Phase 0 agents only (multi-phase deferred)
  // Parent job: id=UUID, skill=scenarioName, phase=0, status='running'
  // Child jobs: one per Phase 0 agent, parentId=parent.id, status='pending'→'running'
  // Parent status: 'running' while any child is running; 'completed' when all children complete
}
```

### 3.5 Job Store (`lib/jobs.ts`)

**Job status enum:**
```typescript
type JobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed:auth'
  | 'failed:invalid-skill'
  | 'failed:rate-limited'
  | 'failed:github-error'
  | 'failed:parse-error'
  | 'failed:unknown'
  | 'cancelled'
```

**Job schema:**
```typescript
type Job = {
  id: string             // UUIDv4
  skill: string
  mode: string
  dispatchType: string
  status: JobStatus
  readOnly: boolean
  dispatched_at: string  // ISO 8601
  completed_at?: string
  output?: string
  error?: string
  phase?: number
  strategyHash: string
  parentId?: string      // for NEXUS sub-jobs
}
```

**Atomic write (Windows-safe):**
```typescript
import { writeFile, rename } from 'fs/promises'
// Use write-file-atomic npm package which handles Windows NTFS atomicity
import writeFileAtomic from 'write-file-atomic'

async function writeJob(job: Job) {
  const p = path.join(JOBS_DIR, `${job.id}.json`)
  await writeFileAtomic(p, JSON.stringify(job, null, 2))
}
```

Add `write-file-atomic` to `package.json`.

### 3.6 SSE Job Stream (`GET /api/agency/jobs`)

```typescript
// Per-connection state (in-memory, not persisted):
const sentSnapshots = new Map<string, JobStatus>() // jobId → last sent status

// Poll .jobs/ every 3s:
// - Read all *.json files
// - For each: if not in sentSnapshots OR status changed → send event
// - Update sentSnapshots

// Heartbeat:
setInterval(() => controller.enqueue(': keepalive\n\n'), 15_000)

// Reconnection: Last-Event-ID does NOT replay missed events — accepted gap.
// Jobs dispatched or completed during the SSE drop will appear in the snapshot
// with correct final state (ordered by dispatched_at). Intermediate states missed
// during the gap are not recoverable and not required — this is acceptable.
// On EventSource 'error': client calls GET /api/agency/jobs/snapshot (returns all
// current jobs as one JSON array), resets local state from snapshot, then reconnects SSE.

// Cleanup:
request.signal.addEventListener('abort', () => {
  clearInterval(heartbeat)
  clearInterval(poller)
  controller.close()
})
```

### 3.7 Auth Middleware (`lib/auth.ts`)

**Server-side middleware** applied to ALL `/api/*` routes including existing routes (`/api/nerv/`, `/api/intel/`, `/api/skills/`, `/api/auth/`, `/api/memory/`, `/api/rnd/`).

**Retrofitting existing routes:** Every existing route handler must import and call `requireAuth(req)` as its first statement. All existing `fetch()` calls in existing page components (`app/nerv/page.tsx`, `app/intel/page.tsx`, etc.) must be updated to include `Authorization: Bearer <token>` header.

**Client token bootstrap:**
```
1. On app load, client checks sessionStorage for 'nerv_token'
2. If absent or expired: POST /api/auth/token (no auth required on this endpoint)
   → Note: same-origin headers are NOT a reliable security mechanism — any HTTP
     client can spoof them. Security relies on DASHBOARD_SECRET strength + short TTL.
     Token issuance is intentionally open since the dashboard is localhost-only.
   → issues a signed JWT: { exp: now + JWT_TTL_SECONDS, iat: now }
   → signed with DASHBOARD_SECRET using HS256
3. Client stores JWT in sessionStorage as 'nerv_token'
4. All subsequent fetch() calls include: Authorization: Bearer <jwt>
5. Server validates JWT signature on every /api/* request (except /api/auth/token)
```

`DASHBOARD_SECRET` never leaves the server. The client receives only a derived JWT.

### 3.8 OpenClaw Proxy Sidecar (`openclaw-proxy/index.js`)

```javascript
// Express :5557
// Auth: validates Authorization: Bearer ${OPENCLAW_PROXY_SECRET} on POST /dispatch
// Persistent WS: connects to ws://127.0.0.1:18789 at startup, reconnects on drop
// POST /dispatch { agent, prompt } → sends to OpenClaw WS → awaits response → returns

// PM2 config in ecosystem.config.cjs:
{
  name: 'openclaw-proxy',
  cwd: 'C:/Users/Rohan/aeon/dashboard/openclaw-proxy',
  script: 'index.js',
  interpreter: 'C:/Program Files/nodejs/node.exe',
  env: { OPENCLAW_PROXY_SECRET: '...', OPENCLAW_WS_URL: 'ws://127.0.0.1:18789' },
  autorestart: true
}
```

### 3.9 Command Registry

**Location:** `~/aeon/dashboard/.cache/command-registry.json` (controlled by `AEON_REGISTRY_PATH` env var)

**Schema:**
```typescript
type CommandRegistry = {
  commands: {
    [commandName: string]: {
      usage: number
      last_used: string   // ISO 8601
      category: string    // derived from command path prefix (e.g. 'gsd', 'lang', 'session')
    }
  }
}
```

**Hook trigger:** PostToolUse hook fires on `Bash` tool use where the command matches `/^\/[a-z]/ ` (slash command pattern). Write uses `write-file-atomic` for safety.

**Hook location:** `~/.claude/settings.json` PostToolUse section. Script reads `AEON_REGISTRY_PATH` env var to find the registry file.

### 3.10 Catalog Builder (`lib/catalog.ts`)

**Startup assertion:**
```typescript
if (!process.env.AEON_REPO_ROOT) {
  console.error('FATAL: AEON_REPO_ROOT not set')
  process.exit(1)
}
```

**Build process:**
1. Discover files from all three sources (Section 3.2 globs)
2. For each file: extract name + description from frontmatter (`name:`, `description:`) or first `# H1` line
3. Extract `destructive:` field from frontmatter if present; apply static fallback list if absent
4. Derive slug per algorithm in Section 3.2
5. Dedup by slug (aigency02 > local > aeon)
6. Write to `.cache/agents.json` using `write-file-atomic`

**Runs:** At Next.js server startup (in `instrumentation.ts`) and on `POST /api/agents/refresh`.
`instrumentation.ts` must export `export const runtime = 'nodejs'` — catalog builder uses `fs`, `path`, `os.homedir()`, and `process.exit()` which are unavailable in the Edge runtime.

---

## 4. Data Flows

### Read-only intent → auto-dispatch
```
User types → 500ms debounce → DISPATCH pressed
→ client generates UUIDv4 idempotencyKey
→ POST /api/agency/classify { intent, idempotencyKey }
→ Claude returns { skill: "hl-intel", readOnly: true, ambiguous: false, ... }
→ readOnly=true → skip confirm
→ POST /api/agency/dispatch { skill, dispatchType: "aeon", strategyHash, ... }
→ server verifies strategyHash → GH Actions workflow_dispatch
→ writeJob({ status: "running", ... })
→ SSE pushes job to UI job board
→ Server polls GH Actions API every 30s → writeJob({ status: "completed", output })
→ SSE pushes updated job
```

### Ambiguous → suggest → dispatch
```
User types vague intent → classify returns { ambiguous: true, suggestions: [...] }
→ UI shows 3 suggestion cards
→ User clicks one:
  - readOnly → dispatch immediately
  - destructive → confirm modal → dispatch
```

### Destructive intent → confirm → dispatch
```
classify returns { skill: "hl-trade", readOnly: false }
→ UI shows confirm modal with skill name + reasoning
→ User clicks CONFIRM → POST /api/agency/dispatch
```

### NEXUS Scenario (Phase 0 only, this release)
```
User picks "Startup MVP" → selects NEXUS-Sprint
→ Load ~/aigency02/strategy/runbooks/scenario-startup-mvp.md
→ Parse with js-yaml + Zod schema validation
   - On parse error → show error banner, do not dispatch
→ Extract Phase 0 agent list
→ Show phase 0 agents in confirm modal → user confirms
→ Create parent job + child job per Phase 0 agent
→ Dispatch each Phase 0 agent as NEXUS-Micro (local dispatch)
→ Show "Phase 0 dispatched. Manual phase advancement coming soon." banner
```

---

## 5. Navigation

Add to existing nav bar (following existing button pattern):
```
◈ AGENCY   (color: orange / amber)   href="/agency"
◈ AGENTS   (color: blue)             href="/agents"
```

---

## 6. Implementation Order

1. **`.gitignore`** — add `.cache/` and `.jobs/` entries
2. **`ecosystem.config.cjs`** — add all new env vars, add `openclaw-proxy` PM2 process
3. **`package.json`** — add `write-file-atomic`, `js-yaml`, `zod`, `jsonwebtoken`
4. **`lib/auth.ts`** — JWT validation middleware + `/api/auth/token` bootstrap endpoint
5. **Retrofit existing routes** — add `requireAuth` to all existing `/api/*` handlers; update existing page `fetch()` calls to send `Authorization` header
6. **`openclaw-proxy/index.js`** — Express sidecar with WS persistence and auth
7. **`lib/catalog.ts`** + `instrumentation.ts` — startup assertion + catalog build
8. **`/api/agents/catalog`** + **`/api/agents/refresh`** — serve and rebuild catalog
9. **`/agents/page.tsx`** — catalog UI
10. **`lib/jobs.ts`** — atomic job store
11. **`/api/agency/classify`** — intent router with Claude + cache
12. **`/api/agency/dispatch`** — GH Actions + proxy dispatch + error mapping
13. **`/api/agency/jobs`** + **`/api/agency/jobs/snapshot`** — SSE stream + snapshot endpoint
14. **`/agency/page.tsx`** — command center UI
15. **`~/.claude/settings.json`** — PostToolUse hook for command registry
16. **`pm2 save`** — persist updated process list

---

## 7. Out of Scope (this release)

- NEXUS multi-phase advancement (Phase 1→6 quality gates) — Phase 0 only
- NEXUS-Full mode — deferred until NEXUS-Micro proven
- Vercel deployment — dashboard stays local only
- Multi-user support
- Billing / usage tracking
- Mobile UI
- Command registry dashboard UI (registry written, UI deferred)
