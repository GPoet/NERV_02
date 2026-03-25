# NERV Desktop — Plan 4: Remaining Panels (Agency, Memory, Sessions, Config)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Prerequisite:** Plans 1–3 complete. `MainPanel.tsx`, `@nerv/core`, panel router, and auth (sessionStorage `nerv_token`) must exist.

**Goal:** Replace the 7 "coming soon" placeholder panels with working implementations for Agency (skill dispatch), Sessions (GH Actions run history), Memory (file browser), and Config (token + connection settings).

**Architecture:** Each panel is a standalone React component that fetches from the existing NERV dashboard API at `localhost:5555`. Auth is `Authorization: Bearer <token>` from `sessionStorage.getItem('nerv_token')`. A shared `apiFetch` helper in `@nerv/core` handles auth headers consistently. Panels are lazy-loaded via the existing `MainPanel.tsx` router. SUPERPOWERS, AIGENCY, and AEON panels remain as stubs — out of scope for this plan.

**Tech Stack:** React + TypeScript, Zustand (existing), Tailwind CSS, `@nerv/core` shared types, dashboard APIs at `:5555`

---

## File Map

**Created:**
- `packages/nerv-core/src/api.ts` — `apiFetch(path, options?)` helper with auth header injection
- `apps/desktop/src/hooks/useSkills.ts` — fetches `/api/skills` (skill list)
- `apps/desktop/src/hooks/useRuns.ts` — fetches `/api/runs` (GH Actions run history), polls 30s
- `apps/desktop/src/hooks/useMemory.ts` — fetches `/api/memory` (memory files)
- `apps/desktop/src/panels/AgencyPanel.tsx` — skill browser + dispatch + live job feed
- `apps/desktop/src/panels/SessionsPanel.tsx` — GitHub Actions run table
- `apps/desktop/src/panels/MemoryPanel.tsx` — memory file sidebar + content viewer
- `apps/desktop/src/panels/ConfigPanel.tsx` — token input, connection status, port reference

**Modified:**
- `packages/nerv-core/src/types.ts` — add `Skill`, `Run`, `MemoryFile` types
- `packages/nerv-core/src/index.ts` — re-export `apiFetch` from new `api.ts`
- `apps/desktop/src/components/MainPanel.tsx` — add lazy imports + routes for 4 new panels

---

### Task 1: Add Types to `@nerv/core` + `apiFetch` helper

**Files:**
- Modify: `packages/nerv-core/src/types.ts`
- Create: `packages/nerv-core/src/api.ts`
- Modify: `packages/nerv-core/src/index.ts`

- [ ] **Step 1: Add new types to `packages/nerv-core/src/types.ts`**

Append to the end of the file:

```typescript
export interface Skill {
  name: string
  description: string
  enabled: boolean
  schedule: string
}

export interface Run {
  id: number | string
  workflow: string
  status: 'queued' | 'in_progress' | 'completed' | 'waiting'
  conclusion: 'success' | 'failure' | 'cancelled' | 'skipped' | null
  created_at: string
  url: string
}

export interface MemoryFile {
  filename: string
  name: string
  description: string
  type: 'user' | 'feedback' | 'project' | 'reference' | 'index' | 'savepoint'
  body: string
  mtime: number
}
```

- [ ] **Step 2: Create `packages/nerv-core/src/api.ts`**

```typescript
const BASE = 'http://localhost:5555'

function getToken(): string {
  try { return sessionStorage.getItem('nerv_token') ?? '' } catch { return '' }
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = getToken()
  return fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  })
}
```

- [ ] **Step 3: Re-export from `packages/nerv-core/src/index.ts`**

Check what's currently in `index.ts`:

```bash
cat ~/nerv-desktop/packages/nerv-core/src/index.ts
```

Add to the exports:

```typescript
export { apiFetch } from './api'
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd ~/nerv-desktop && npm run build 2>&1 | grep -E "error|warning" | head -20
```

Expected: No type errors in `nerv-core`.

- [ ] **Step 5: Commit**

```bash
cd ~/nerv-desktop
git add packages/nerv-core/src/types.ts packages/nerv-core/src/api.ts packages/nerv-core/src/index.ts
git commit -m "feat: add Skill/Run/MemoryFile types + apiFetch helper to nerv-core"
```

---

### Task 2: Data Hooks (`useSkills`, `useRuns`, `useMemory`)

**Files:**
- Create: `apps/desktop/src/hooks/useSkills.ts`
- Create: `apps/desktop/src/hooks/useRuns.ts`
- Create: `apps/desktop/src/hooks/useMemory.ts`

- [ ] **Step 1: Write `useSkills.ts`**

```typescript
import { useState, useEffect } from 'react'
import { apiFetch } from '@nerv/core'
import type { Skill } from '@nerv/core'

export function useSkills() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch('/api/skills')
      .then(r => r.json())
      .then(d => { setSkills(d.skills ?? []); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [])

  return { skills, loading, error }
}
```

- [ ] **Step 2: Write `useRuns.ts`**

```typescript
import { useState, useEffect } from 'react'
import { apiFetch } from '@nerv/core'
import type { Run } from '@nerv/core'

export function useRuns() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    function poll() {
      apiFetch('/api/runs')
        .then(r => r.json())
        .then(d => { setRuns(d.runs ?? []); setLoading(false) })
        .catch(() => setLoading(false))
    }
    poll()
    const t = setInterval(poll, 30_000)
    return () => clearInterval(t)
  }, [])

  return { runs, loading }
}
```

- [ ] **Step 3: Write `useMemory.ts`**

```typescript
import { useState, useEffect } from 'react'
import { apiFetch } from '@nerv/core'
import type { MemoryFile } from '@nerv/core'

export function useMemory() {
  const [files, setFiles] = useState<MemoryFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch('/api/memory')
      .then(r => r.json())
      .then(d => { setFiles(d.files ?? []); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [])

  return { files, loading, error }
}
```

- [ ] **Step 4: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop/src/hooks/useSkills.ts apps/desktop/src/hooks/useRuns.ts apps/desktop/src/hooks/useMemory.ts
git commit -m "feat: add useSkills, useRuns, useMemory data hooks"
```

---

### Task 3: Agency Panel

**Files:**
- Create: `apps/desktop/src/panels/AgencyPanel.tsx`

The Agency panel has three zones:
- **Left** (w-64): Searchable skill list. Click to select.
- **Right top**: Selected skill name + dispatch controls (dispatch type toggle: `aeon` vs `local`, Dispatch button).
- **Right bottom**: Live job feed from `useJobStream` (already exists — reuse it).

- [ ] **Step 1: Write `AgencyPanel.tsx`**

```typescript
import { useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useSkills } from '@/hooks/useSkills'
import { useJobStream } from '@/hooks/useJobStream'
import { apiFetch } from '@nerv/core'
import type { Skill, SkillRun } from '@nerv/core'

type DispatchType = 'aeon' | 'local'

const JOB_COLORS: Record<SkillRun['status'], string> = {
  queued:    'bg-zinc-800 text-zinc-400',
  running:   'bg-blue-950 text-blue-300 animate-pulse',
  success:   'bg-green-950 text-green-300',
  failed:    'bg-red-950 text-red-400',
  cancelled: 'bg-zinc-900 text-zinc-600',
}

function elapsed(job: SkillRun): string {
  const ms = (job.completedAt ?? Date.now()) - job.startedAt
  const s = Math.floor(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${s % 60}s`
}

export function AgencyPanel() {
  const { skills, loading } = useSkills()
  const jobs = useJobStream()
  const [selected, setSelected] = useState<Skill | null>(null)
  const [dispatchType, setDispatchType] = useState<DispatchType>('aeon')
  const [query, setQuery] = useState('')
  const [dispatching, setDispatching] = useState(false)
  const [lastResult, setLastResult] = useState<string | null>(null)

  const filtered = skills.filter(s =>
    s.name.includes(query.toLowerCase()) || s.description.toLowerCase().includes(query.toLowerCase())
  )

  async function dispatch() {
    if (!selected) return
    setDispatching(true)
    setLastResult(null)
    try {
      const r = await apiFetch('/api/agency/dispatch', {
        method: 'POST',
        body: JSON.stringify({ skill: selected.name, dispatchType }),
      })
      const d = await r.json()
      setLastResult(r.ok ? `✓ Dispatched (job ${d.jobId ?? 'queued'})` : `✗ ${d.error ?? 'Failed'}`)
    } catch (e) {
      setLastResult(`✗ ${String(e)}`)
    } finally {
      setDispatching(false)
    }
  }

  return (
    <div className="flex h-full">
      {/* Skill list */}
      <div className="w-64 border-r border-[#1a1a1a] flex flex-col shrink-0">
        <div className="p-3 border-b border-[#1a1a1a]">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search skills…"
            className="w-full bg-[#111] border border-[#222] rounded px-2 py-1 text-xs text-zinc-300 placeholder-zinc-600 outline-none focus:border-indigo-700"
          />
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 flex flex-col gap-1">
            {loading && <div className="text-zinc-600 text-xs p-2">Loading…</div>}
            {filtered.map(skill => (
              <button
                key={skill.name}
                onClick={() => setSelected(skill)}
                className={`w-full text-left px-3 py-2 rounded text-xs transition-all ${
                  selected?.name === skill.name
                    ? 'bg-indigo-950/60 border border-indigo-800/50 text-indigo-200'
                    : 'hover:bg-[#111] text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <div className="font-mono font-medium">{skill.name}</div>
                {skill.description && (
                  <div className="text-zinc-600 mt-0.5 truncate">{skill.description}</div>
                )}
              </button>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Right pane */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Dispatch controls */}
        <div className="p-4 border-b border-[#1a1a1a] shrink-0">
          {selected ? (
            <div className="flex flex-col gap-3">
              <div>
                <div className="font-mono text-sm text-zinc-200">{selected.name}</div>
                {selected.description && (
                  <div className="text-xs text-zinc-500 mt-0.5">{selected.description}</div>
                )}
              </div>
              <div className="flex items-center gap-3">
                {/* Dispatch type toggle */}
                <div className="flex rounded border border-[#222] overflow-hidden text-xs">
                  {(['aeon', 'local'] as DispatchType[]).map(t => (
                    <button
                      key={t}
                      onClick={() => setDispatchType(t)}
                      className={`px-3 py-1.5 transition-colors ${
                        dispatchType === t ? 'bg-indigo-900 text-indigo-200' : 'text-zinc-500 hover:text-zinc-300'
                      }`}
                    >
                      {t === 'aeon' ? '⚡ GitHub Actions' : '⚙ Local'}
                    </button>
                  ))}
                </div>
                <button
                  onClick={dispatch}
                  disabled={dispatching}
                  className="px-4 py-1.5 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-40 text-white text-xs rounded font-medium transition-colors"
                >
                  {dispatching ? 'Dispatching…' : 'Dispatch'}
                </button>
              </div>
              {lastResult && (
                <div className={`text-xs font-mono ${lastResult.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>
                  {lastResult}
                </div>
              )}
            </div>
          ) : (
            <div className="text-zinc-600 text-sm">Select a skill to dispatch</div>
          )}
        </div>

        {/* Live job feed */}
        <div className="p-4 flex flex-col gap-2 flex-1 overflow-hidden">
          <div className="text-[10px] text-zinc-600 uppercase tracking-widest mb-1">Live Jobs</div>
          <ScrollArea className="flex-1">
            <div className="flex flex-col gap-1.5">
              {jobs.length === 0 && (
                <div className="text-zinc-700 text-xs">No jobs yet</div>
              )}
              {jobs.slice(0, 30).map(job => (
                <div
                  key={job.id}
                  className={`flex items-center gap-3 px-3 py-2 rounded text-xs font-mono ${JOB_COLORS[job.status]}`}
                >
                  <span className="flex-1 truncate">{job.skill}</span>
                  <span className="opacity-60">{elapsed(job)}</span>
                  <span className="uppercase text-[10px]">{job.status}</span>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop/src/panels/AgencyPanel.tsx
git commit -m "feat: implement Agency panel with skill dispatch + live job feed"
```

---

### Task 4: Sessions Panel

**Files:**
- Create: `apps/desktop/src/panels/SessionsPanel.tsx`

Shows last 20 GitHub Actions runs. Polls every 30s. Click row opens GitHub URL.

- [ ] **Step 1: Write `SessionsPanel.tsx`**

```typescript
import { useRuns } from '@/hooks/useRuns'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { Run } from '@nerv/core'

const STATUS_DOT: Record<string, string> = {
  queued:      'bg-zinc-500',
  in_progress: 'bg-blue-400 animate-pulse',
  completed:   'bg-zinc-600',
  waiting:     'bg-yellow-600',
}

const CONCLUSION_COLOR: Record<string, string> = {
  success:   'text-green-400',
  failure:   'text-red-400',
  cancelled: 'text-zinc-500',
  skipped:   'text-zinc-600',
}

function statusLabel(run: Run): { text: string; color: string } {
  if (run.status !== 'completed') {
    return { text: run.status.replace('_', ' '), color: 'text-blue-400' }
  }
  return {
    text: run.conclusion ?? 'completed',
    color: CONCLUSION_COLOR[run.conclusion ?? ''] ?? 'text-zinc-400',
  }
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export function SessionsPanel() {
  const { runs, loading } = useRuns()

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[#1a1a1a] shrink-0 flex items-center justify-between">
        <div className="text-[10px] text-zinc-600 uppercase tracking-widest">GitHub Actions Runs</div>
        <div className="text-[10px] text-zinc-700">auto-refreshes every 30s</div>
      </div>
      <ScrollArea className="flex-1">
        {loading && (
          <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">Loading…</div>
        )}
        <div className="flex flex-col divide-y divide-[#111]">
          {runs.map(run => {
            const { text, color } = statusLabel(run)
            return (
              <button
                key={run.id}
                onClick={() => run.url && window.open(run.url, '_blank')}
                className="flex items-center gap-3 px-4 py-3 hover:bg-[#111] text-left w-full transition-colors"
              >
                <div className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[run.status] ?? 'bg-zinc-600'}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-zinc-300 truncate">{run.workflow}</div>
                  <div className="text-xs text-zinc-600 mt-0.5">{timeAgo(run.created_at)}</div>
                </div>
                <div className={`text-xs font-mono capitalize shrink-0 ${color}`}>{text}</div>
              </button>
            )
          })}
          {!loading && runs.length === 0 && (
            <div className="flex items-center justify-center h-32 text-zinc-700 text-sm">
              No runs found
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop/src/panels/SessionsPanel.tsx
git commit -m "feat: implement Sessions panel with GH Actions run history"
```

---

### Task 5: Memory Panel

**Files:**
- Create: `apps/desktop/src/panels/MemoryPanel.tsx`

Two-column: left sidebar lists memory files grouped by type, right pane shows selected file's body as preformatted text.

- [ ] **Step 1: Write `MemoryPanel.tsx`**

```typescript
import { useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useMemory } from '@/hooks/useMemory'
import type { MemoryFile } from '@nerv/core'

const TYPE_ORDER: MemoryFile['type'][] = ['index', 'project', 'user', 'feedback', 'reference', 'savepoint']

const TYPE_COLOR: Record<MemoryFile['type'], string> = {
  index:     'text-indigo-400',
  project:   'text-amber-400',
  user:      'text-sky-400',
  feedback:  'text-emerald-400',
  reference: 'text-violet-400',
  savepoint: 'text-zinc-500',
}

const TYPE_LABEL: Record<MemoryFile['type'], string> = {
  index:     'Index',
  project:   'Project',
  user:      'User',
  feedback:  'Feedback',
  reference: 'Reference',
  savepoint: 'Savepoints',
}

export function MemoryPanel() {
  const { files, loading, error } = useMemory()
  const [selected, setSelected] = useState<MemoryFile | null>(null)

  const grouped = TYPE_ORDER.reduce<Record<MemoryFile['type'], MemoryFile[]>>((acc, t) => {
    acc[t] = files.filter(f => f.type === t)
    return acc
  }, {} as Record<MemoryFile['type'], MemoryFile[]>)

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 border-r border-[#1a1a1a] flex flex-col shrink-0">
        <div className="px-3 py-2 border-b border-[#1a1a1a]">
          <div className="text-[10px] text-zinc-600 uppercase tracking-widest">Memory Files</div>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2">
            {loading && <div className="text-zinc-600 text-xs p-2">Loading…</div>}
            {error && <div className="text-red-500 text-xs p-2">{error}</div>}
            {TYPE_ORDER.map(type => {
              const group = grouped[type]
              if (!group.length) return null
              return (
                <div key={type} className="mb-3">
                  <div className={`text-[10px] uppercase tracking-widest px-2 mb-1 ${TYPE_COLOR[type]}`}>
                    {TYPE_LABEL[type]}
                  </div>
                  {group.map(f => (
                    <button
                      key={f.filename}
                      onClick={() => setSelected(f)}
                      className={`w-full text-left px-2 py-1.5 rounded text-xs transition-all ${
                        selected?.filename === f.filename
                          ? 'bg-[#1a1a1a] text-zinc-200'
                          : 'text-zinc-500 hover:text-zinc-300 hover:bg-[#111]'
                      }`}
                    >
                      <div className="truncate font-mono">{f.name || f.filename}</div>
                      {f.description && (
                        <div className="truncate text-zinc-700 mt-0.5">{f.description}</div>
                      )}
                    </button>
                  ))}
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Content pane */}
      <ScrollArea className="flex-1 p-4">
        {!selected ? (
          <div className="flex items-center justify-center h-full text-zinc-700 text-sm">
            Select a memory file to view
          </div>
        ) : (
          <div>
            <div className="mb-4">
              <h2 className="text-base font-semibold text-zinc-200 font-mono">{selected.name}</h2>
              {selected.description && (
                <p className="text-xs text-zinc-500 mt-0.5">{selected.description}</p>
              )}
              <div className={`text-[10px] mt-1 uppercase tracking-wider ${TYPE_COLOR[selected.type]}`}>
                {TYPE_LABEL[selected.type]}
              </div>
            </div>
            <pre className="text-xs text-zinc-400 whitespace-pre-wrap font-mono leading-relaxed">
              {selected.body}
            </pre>
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop/src/panels/MemoryPanel.tsx
git commit -m "feat: implement Memory browser panel"
```

---

### Task 6: Config Panel

**Files:**
- Create: `apps/desktop/src/panels/ConfigPanel.tsx`

Allows the user to set their `nerv_token` (saved to sessionStorage), shows current connection health for all three services.

- [ ] **Step 1: Write `ConfigPanel.tsx`**

```typescript
import { useState, useEffect } from 'react'
import { useNervStatus } from '@/hooks/useNervStatus'

const PORTS = [
  { label: 'NERV Dashboard', port: 5555, desc: 'Next.js + API routes' },
  { label: 'OpenClaw Proxy', port: 5557, desc: 'Claude API proxy' },
  { label: 'NERV WS Server', port: 5558, desc: 'Desktop WebSocket (Tauri)' },
]

export function ConfigPanel() {
  const [token, setToken] = useState('')
  const [saved, setSaved] = useState(false)
  const status = useNervStatus()

  useEffect(() => {
    setToken(sessionStorage.getItem('nerv_token') ?? '')
  }, [])

  function saveToken() {
    sessionStorage.setItem('nerv_token', token)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="p-6 max-w-lg flex flex-col gap-8">

      {/* Token */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-3">Authentication</h2>
        <div className="flex flex-col gap-2">
          <label className="text-xs text-zinc-500">NERV Token (JWT from dashboard)</label>
          <div className="flex gap-2">
            <input
              type="password"
              value={token}
              onChange={e => setToken(e.target.value)}
              placeholder="eyJ..."
              className="flex-1 bg-[#111] border border-[#222] rounded px-3 py-2 text-xs text-zinc-300 font-mono placeholder-zinc-700 outline-none focus:border-indigo-700"
            />
            <button
              onClick={saveToken}
              className="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-xs rounded font-medium transition-colors"
            >
              {saved ? 'Saved ✓' : 'Save'}
            </button>
          </div>
          <p className="text-[10px] text-zinc-600">
            Stored in sessionStorage — cleared when the app closes. Get a token from{' '}
            <span className="font-mono text-zinc-500">localhost:5555/api/auth/token</span>
          </p>
        </div>
      </section>

      {/* Services */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-3">Services</h2>
        <div className="flex flex-col gap-2">
          {PORTS.map(({ label, port, desc }) => {
            const connected = port === 5555
              ? status?.proxyConnected !== undefined
              : port === 5557
              ? status?.proxyConnected === true
              : true // WS server — just show port
            return (
              <div key={port} className="flex items-center gap-3 p-3 bg-[#111] border border-[#1a1a1a] rounded">
                <div className={`w-2 h-2 rounded-full shrink-0 ${connected ? 'bg-green-500' : 'bg-zinc-600'}`} />
                <div className="flex-1">
                  <div className="text-xs text-zinc-300">{label}</div>
                  <div className="text-[10px] text-zinc-600">{desc}</div>
                </div>
                <div className="font-mono text-xs text-zinc-500">:{port}</div>
              </div>
            )
          })}
        </div>
      </section>

      {/* MCP Servers */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-3">MCP Servers</h2>
        <div className="flex flex-col gap-2">
          {(status?.mcp ?? []).map(s => (
            <div key={s.name} className="flex items-center gap-3 p-3 bg-[#111] border border-[#1a1a1a] rounded">
              <div className={`w-2 h-2 rounded-full shrink-0 ${
                s.status === 'ok' ? 'bg-green-500' : s.status === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
              }`} />
              <div className="flex-1 font-mono text-xs text-zinc-400">{s.name}</div>
              <div className="text-[10px] text-zinc-600">{s.tools} tools</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
```

> **Note:** `useNervStatus` returns the full `NervStatus` from `/api/status`. Check if it already exists as `useMcpStatus` returns only the `mcp` array. You need to either create a `useNervStatus` hook that returns the full status object, or use the existing data from `useMcpStatus` + `useOpenclawStatus`.

- [ ] **Step 2: Create `useNervStatus.ts` (if not already present)**

Check first:

```bash
ls ~/nerv-desktop/apps/desktop/src/hooks/
```

If `useNervStatus.ts` doesn't exist, create it:

```typescript
import { useState, useEffect } from 'react'
import type { NervStatus } from '@nerv/core'

export function useNervStatus() {
  const [status, setStatus] = useState<NervStatus | null>(null)

  useEffect(() => {
    async function poll() {
      try {
        const r = await fetch('http://localhost:5555/api/status', { signal: AbortSignal.timeout(2000) })
        if (!r.ok) return
        const data = await r.json()
        setStatus(data)
      } catch {}
    }
    poll()
    const t = setInterval(poll, 5000)
    return () => clearInterval(t)
  }, [])

  return status
}
```

- [ ] **Step 3: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop/src/panels/ConfigPanel.tsx apps/desktop/src/hooks/useNervStatus.ts
git commit -m "feat: implement Config panel with token management + service status"
```

---

### Task 7: Wire All Panels into `MainPanel.tsx`

**Files:**
- Modify: `apps/desktop/src/components/MainPanel.tsx`

- [ ] **Step 1: Read current `MainPanel.tsx`**

```bash
cat ~/nerv-desktop/apps/desktop/src/components/MainPanel.tsx
```

- [ ] **Step 2: Add lazy imports for the 4 new panels**

```typescript
const AgencyPanel   = lazy(() => import('@/panels/AgencyPanel').then(m => ({ default: m.AgencyPanel })))
const SessionsPanel = lazy(() => import('@/panels/SessionsPanel').then(m => ({ default: m.SessionsPanel })))
const MemoryPanel   = lazy(() => import('@/panels/MemoryPanel').then(m => ({ default: m.MemoryPanel })))
const ConfigPanel   = lazy(() => import('@/panels/ConfigPanel').then(m => ({ default: m.ConfigPanel })))
```

- [ ] **Step 3: Add routes in the JSX**

Replace the catch-all placeholder condition with explicit routes:

```typescript
{activePanel === 'CLI'       && <CliPanel />}
{activePanel === 'MCP'       && <McpPanel />}
{activePanel === 'OPENCLAW'  && <OpenclawPanel />}
{activePanel === 'AGENCY'    && <AgencyPanel />}
{activePanel === 'SESSIONS'  && <SessionsPanel />}
{activePanel === 'MEMORY'    && <MemoryPanel />}
{activePanel === 'CONFIG'    && <ConfigPanel />}
{!['CLI','MCP','OPENCLAW','AGENCY','SESSIONS','MEMORY','CONFIG'].includes(activePanel) && (
  <PanelPlaceholder id={activePanel} />
)}
```

- [ ] **Step 4: Verify Vite builds cleanly**

```bash
cd ~/nerv-desktop/apps/desktop && npm run build 2>&1 | tail -20
```

Expected: No TypeScript or import errors. Build output in `dist/`.

- [ ] **Step 5: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop/src/components/MainPanel.tsx
git commit -m "feat: wire Agency, Sessions, Memory, Config panels into router"
```

---

### Task 8: Integration Test + Push

- [ ] **Step 1: Verify NERV dashboard is running**

```bash
curl -s http://localhost:5555/api/status | python -c "import sys,json; d=json.load(sys.stdin); print('OK:', bool(d.get('mcp')))"
```

Expected: `OK: True`

- [ ] **Step 2: Get a token and set it in the desktop app**

Open the desktop app, navigate to CONFIG panel, enter a token from:

```bash
curl -s -X POST http://localhost:5555/api/auth -H "Content-Type: application/json" \
  -d '{"password":"'$(grep DASHBOARD_SECRET ~/aeon/.env.local 2>/dev/null | cut -d= -f2 || echo "change-me-32-char-secret-xxxxxxxx")'"}'
```

Or use the token already in sessionStorage if the app was previously authenticated.

- [ ] **Step 3: Test each panel manually**

- **AGENCY**: Click a skill (e.g. `heartbeat`) → dispatch type `local` → Dispatch → verify result message appears
- **SESSIONS**: Navigate to SESSIONS → verify run list loads (or "No runs found" if GH token not set)
- **MEMORY**: Navigate to MEMORY → verify file list loads → click `MEMORY.md` → verify body renders
- **CONFIG**: Navigate to CONFIG → verify MCP server list renders from `/api/status`

- [ ] **Step 4: Push both repos**

```bash
cd ~/nerv-desktop && git push origin master
```

---

## What Plans 1–4 Deliver Together

| Feature | Plan |
|---------|------|
| Turborepo monorepo + Tauri shell | 1 |
| 3-column dark layout + NavSidebar | 1 |
| `@nerv/ui` + `@nerv/core` shared packages | 1 |
| CLI terminal (xterm + SSE job stream) | 2 |
| MCP Inspector | 2 |
| OpenClaw Monitor | 2 |
| WebSocket server + toast notifications | 3 |
| `nerv-sdk.js` agent client | 3 |
| Agency panel (skill dispatch + live feed) | 4 |
| Sessions panel (GH Actions run history) | 4 |
| Memory browser | 4 |
| Config panel (token + service health) | 4 |

## Remaining (Future Plans)

- **AEON** — Skill detail view + schedule editor (needs PATCH /api/skills)
- **AIGENCY** — 156-agent catalog from `~/aigency02/` (needs `/api/agents/catalog`)
- **SUPERPOWERS** — Skills browser from `~/.claude/` (needs new API endpoint)
