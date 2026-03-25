# NERV Desktop — Plan 2: Core Panels (CLI, MCP Inspector, OpenClaw Monitor)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Prerequisite:** Plan 1 must be complete. The 3-column shell, Zustand store, and `@nerv/core` package must exist.

**Goal:** Implement three functional panels inside the NERV desktop shell: a CLI terminal (chat interface to NERV), an MCP Inspector (live server health + tool list), and an OpenClaw Monitor (model queue, rate limits, proxy status).

**Architecture:** Each panel is a self-contained React component in `apps/desktop/src/panels/`. `MainPanel.tsx` from Plan 1 becomes a router that renders the active panel. The CLI panel communicates with the NERV dashboard's `/api/runs` endpoint for skill dispatch and uses a local `xterm.js` terminal for output. MCP and OpenClaw panels poll `/api/status`.

**Tech Stack:** React 19, `@xterm/xterm` (terminal emulator), `@xterm/addon-fit`, Zustand, `@nerv/core` (API client), shadcn/ui (ScrollArea, Badge, Separator)

---

## File Map

**Created:**
- `apps/desktop/src/panels/CliPanel.tsx` — NERV Terminal chat + xterm output
- `apps/desktop/src/panels/McpPanel.tsx` — MCP server list with tool browser
- `apps/desktop/src/panels/OpenclawPanel.tsx` — model queue + rate chart + proxy status
- `apps/desktop/src/panels/index.ts` — barrel export
- `apps/desktop/src/hooks/useJobStream.ts` — SSE job updates from :5555
- `apps/desktop/src/hooks/useMcpStatus.ts` — MCP server polling
- `apps/desktop/src/hooks/useOpenclawStatus.ts` — OpenClaw polling

**Modified:**
- `apps/desktop/src/components/MainPanel.tsx` — route to panel components
- `packages/nerv-core/src/types.ts` — add `McpTool`, `OpenclawStats` types
- `packages/nerv-core/src/client.ts` — add `fetchMcpTools()`, `fetchOpenclawStats()`

---

### Task 1: Update Types and Client in `@nerv/core`

**Files:**
- Modify: `packages/nerv-core/src/types.ts`
- Modify: `packages/nerv-core/src/client.ts`

- [ ] **Step 1: Add types to `packages/nerv-core/src/types.ts`**

Append to the existing file:

```typescript
export interface McpTool {
  name: string
  description: string
  inputSchema?: object
}

export interface McpServerDetail extends McpServer {
  tools: number
  toolList?: McpTool[]
  latencyMs?: number
}

export interface OpenclawStats {
  primaryModel: string
  fallbackModel: string
  rpm: number
  rpmMax: number
  proxyConnected: boolean
  totalRequests: number
  errorRate: number
  queueDepth: number
}

export interface SkillRun {
  id: string
  skill: string
  status: 'queued' | 'running' | 'success' | 'failed' | 'cancelled'
  startedAt: number
  completedAt?: number
  output?: string
  error?: string
}
```

- [ ] **Step 2: Add fetchers to `packages/nerv-core/src/client.ts`**

Append:

```typescript
export async function fetchMcpDetail(serverName: string): Promise<Response> {
  return fetch(`${NERV_BASE}/api/mcp/${serverName}`, { signal: AbortSignal.timeout(3000) })
}

export async function fetchOpenclawStats(): Promise<Response> {
  return fetch(`http://localhost:5557/api/stats`, { signal: AbortSignal.timeout(2000) })
}

export async function dispatchNervCommand(command: string, token: string): Promise<Response> {
  return fetch(`${NERV_BASE}/api/nerv/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ command }),
  })
}
```

- [ ] **Step 3: Commit**

```bash
cd ~/nerv-desktop
git add packages/nerv-core/src/
git commit -m "feat: add McpTool, OpenclawStats, SkillRun types to nerv-core"
```

---

### Task 2: Add Panel Router to `MainPanel.tsx`

**Files:**
- Modify: `apps/desktop/src/components/MainPanel.tsx`
- Create: `apps/desktop/src/panels/index.ts`

- [ ] **Step 1: Write `src/panels/index.ts` placeholder**

```typescript
export { CliPanel } from './CliPanel'
export { McpPanel } from './McpPanel'
export { OpenclawPanel } from './OpenclawPanel'
```

- [ ] **Step 2: Update `MainPanel.tsx` to route by active panel**

```typescript
import { usePanelStore } from '@/store/panel'
import { lazy, Suspense } from 'react'

const CliPanel       = lazy(() => import('@/panels/CliPanel').then(m => ({ default: m.CliPanel })))
const McpPanel       = lazy(() => import('@/panels/McpPanel').then(m => ({ default: m.McpPanel })))
const OpenclawPanel  = lazy(() => import('@/panels/OpenclawPanel').then(m => ({ default: m.OpenclawPanel })))

function PanelPlaceholder({ id }: { id: string }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl font-bold text-zinc-800 mb-2">◈</div>
        <div className="text-zinc-600 font-mono text-sm">{id}</div>
        <div className="text-zinc-700 text-xs mt-1">coming in a future plan</div>
      </div>
    </div>
  )
}

export function MainPanel() {
  const { activePanel } = usePanelStore()

  return (
    <main className="flex-1 min-h-screen bg-[#0d0d0d] overflow-hidden flex flex-col">
      <Suspense fallback={<PanelPlaceholder id={activePanel} />}>
        {activePanel === 'CLI'       && <CliPanel />}
        {activePanel === 'MCP'       && <McpPanel />}
        {activePanel === 'OPENCLAW'  && <OpenclawPanel />}
        {!['CLI','MCP','OPENCLAW'].includes(activePanel) && <PanelPlaceholder id={activePanel} />}
      </Suspense>
    </main>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/MainPanel.tsx src/panels/index.ts
git commit -m "feat: add panel router with lazy loading"
```

---

### Task 3: Install `xterm.js`

**Files:**
- Modify: `apps/desktop/package.json` (dependency added via npm)

- [ ] **Step 1: Install xterm**

```bash
cd ~/nerv-desktop/apps/desktop
npm install @xterm/xterm @xterm/addon-fit @xterm/addon-web-links
```

- [ ] **Step 2: Add xterm CSS import to `index.css`**

Append to `src/index.css`:

```css
@import "@xterm/xterm/css/xterm.css";
```

- [ ] **Step 3: Commit**

```bash
git add package.json src/index.css
git commit -m "feat: install xterm.js for CLI panel"
```

---

### Task 4: Build CLI Panel (`CliPanel.tsx`)

**Files:**
- Create: `apps/desktop/src/panels/CliPanel.tsx`
- Create: `apps/desktop/src/hooks/useJobStream.ts`

- [ ] **Step 1: Write `src/hooks/useJobStream.ts`**

```typescript
import { useState, useEffect, useRef } from 'react'
import type { SkillRun } from '@nerv/core'

export function useJobStream() {
  const [jobs, setJobs] = useState<SkillRun[]>([])
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const token = sessionStorage.getItem('nerv_token')
    if (!token) return

    const es = new EventSource(`http://localhost:5555/api/agency/jobs?token=${token}`)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const job: SkillRun = JSON.parse(e.data)
        setJobs(prev => {
          const idx = prev.findIndex(j => j.id === job.id)
          if (idx === -1) return [job, ...prev].slice(0, 50)
          const next = [...prev]
          next[idx] = job
          return next
        })
      } catch {}
    }

    return () => es.close()
  }, [])

  return jobs
}
```

- [ ] **Step 2: Write `src/panels/CliPanel.tsx`**

```typescript
import { useRef, useEffect, useState, useCallback } from 'react'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { useJobStream } from '@/hooks/useJobStream'
import type { SkillRun } from '@nerv/core'

const NERV_BANNER = `\x1b[1;34m
  ███╗   ██╗███████╗██████╗ ██╗   ██╗
  ████╗  ██║██╔════╝██╔══██╗██║   ██║
  ██╔██╗ ██║█████╗  ██████╔╝██║   ██║
  ██║╚██╗██║██╔══╝  ██╔══██╗╚██╗ ██╔╝
  ██║ ╚████║███████╗██║  ██║ ╚████╔╝
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝  ╚═══╝
\x1b[0m\x1b[2mCommand Center v1.0\x1b[0m\r\n\r\n`

function JobBadge({ job }: { job: SkillRun }) {
  const color = {
    queued: 'bg-zinc-700 text-zinc-300',
    running: 'bg-blue-900 text-blue-300 animate-pulse',
    success: 'bg-green-900 text-green-300',
    failed: 'bg-red-900 text-red-300',
    cancelled: 'bg-zinc-800 text-zinc-500',
  }[job.status]

  return (
    <div className={`flex items-center gap-2 px-2 py-1 rounded text-xs font-mono ${color}`}>
      <span>{job.skill}</span>
      <span className="opacity-60">{job.status}</span>
    </div>
  )
}

export function CliPanel() {
  const termRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<XTerm | null>(null)
  const fitRef = useRef<FitAddon | null>(null)
  const [input, setInput] = useState('')
  const jobs = useJobStream()

  // Initialize xterm
  useEffect(() => {
    if (!termRef.current) return

    const term = new XTerm({
      theme: {
        background: '#0d0d0d',
        foreground: '#e4e4e7',
        cursor: '#6366f1',
        selectionBackground: '#3f3f46',
      },
      fontFamily: '"Geist Mono", "Fira Code", monospace',
      fontSize: 12,
      lineHeight: 1.5,
      cursorBlink: true,
      scrollback: 5000,
    })

    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(termRef.current)
    fit.fit()
    term.write(NERV_BANNER)
    term.write('\x1b[2m39 skills available · 4 MCP servers connected · OpenClaw :5557\x1b[0m\r\n\r\n')

    xtermRef.current = term
    fitRef.current = fit

    const ro = new ResizeObserver(() => fit.fit())
    ro.observe(termRef.current)

    return () => { ro.disconnect(); term.dispose() }
  }, [])

  // Print job updates to terminal
  useEffect(() => {
    const term = xtermRef.current
    if (!term || jobs.length === 0) return
    const latest = jobs[0]
    if (latest.status === 'success') {
      term.write(`\x1b[32m✓ ${latest.skill} completed\x1b[0m\r\n`)
    } else if (latest.status === 'failed') {
      term.write(`\x1b[31m✗ ${latest.skill} failed\x1b[0m\r\n`)
    }
  }, [jobs])

  const handleSubmit = useCallback(async () => {
    const cmd = input.trim()
    if (!cmd) return
    setInput('')

    const term = xtermRef.current
    if (term) {
      term.write(`\x1b[36m❯ ${cmd}\x1b[0m\r\n`)
    }

    try {
      const token = sessionStorage.getItem('nerv_token') ?? ''
      const r = await fetch('http://localhost:5555/api/nerv/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ command: cmd }),
      })
      const data = await r.json()
      if (term) {
        term.write(`\x1b[2m${JSON.stringify(data, null, 2).replace(/\n/g, '\r\n')}\x1b[0m\r\n\r\n`)
      }
    } catch (e) {
      if (term) term.write(`\x1b[31mError: ${e}\x1b[0m\r\n`)
    }
  }, [input])

  return (
    <div className="flex flex-col h-full">
      {/* Job strip */}
      {jobs.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-[#1a1a1a] overflow-x-auto shrink-0">
          {jobs.slice(0, 6).map(j => <JobBadge key={j.id} job={j} />)}
        </div>
      )}

      {/* Terminal output */}
      <div ref={termRef} className="flex-1 overflow-hidden p-1" />

      {/* Input bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-t border-[#1a1a1a] shrink-0">
        <span className="text-indigo-400 font-mono text-sm">❯</span>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder="dispatch skill, ask NERV..."
          className="flex-1 bg-transparent text-sm font-mono text-zinc-200 outline-none placeholder:text-zinc-700"
          autoFocus
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Run and verify CLI panel**

```bash
cd ~/nerv-desktop/apps/desktop && npm run tauri dev
```

Click the CLI (terminal) icon. Expected:
- xterm renders with NERV banner
- Input bar at bottom
- No console errors

- [ ] **Step 4: Commit**

```bash
git add src/panels/CliPanel.tsx src/hooks/useJobStream.ts
git commit -m "feat: implement CLI terminal panel with xterm.js + SSE job stream"
```

---

### Task 5: Add `/api/nerv/command` Endpoint to NERV Dashboard

> Modifies the existing NERV dashboard.

**Files:**
- Create: `~/aeon/dashboard/app/api/nerv/command/route.ts`

- [ ] **Step 1: Write the command route**

```typescript
import { NextResponse } from 'next/server'
import { requireAuth } from '@/lib/auth'

export async function POST(req: Request) {
  const auth = requireAuth(req)
  if (!auth.ok) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const { command } = await req.json() as { command: string }

  if (!command?.trim()) {
    return NextResponse.json({ error: 'empty command' }, { status: 400 })
  }

  // Parse DISPATCH: prefix for direct skill dispatch
  if (command.startsWith('DISPATCH:')) {
    try {
      const payload = JSON.parse(command.slice('DISPATCH:'.length).trim())
      // Forward to agency dispatch
      const r = await fetch('http://localhost:3000/api/agency/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: req.headers.get('Authorization') ?? '' },
        body: JSON.stringify(payload),
      })
      return NextResponse.json(await r.json())
    } catch (e) {
      return NextResponse.json({ error: String(e) }, { status: 400 })
    }
  }

  // Echo unknown commands for now — future: Claude interpretation
  return NextResponse.json({ ok: true, echo: command, message: 'Command received. Full NERV interpreter coming in a future release.' })
}
```

- [ ] **Step 2: Reload dashboard and test**

```bash
cd ~/aeon && pm2 reload nerv-dashboard
curl -X POST http://localhost:5555/api/nerv/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{"command":"hello"}'
```

Expected: JSON with `{ ok: true, echo: "hello", ... }`

- [ ] **Step 3: Commit**

```bash
cd ~/aeon
git add dashboard/app/api/nerv/command/route.ts
git commit -m "feat: add /api/nerv/command endpoint for desktop CLI panel"
```

---

### Task 6: Build MCP Inspector Panel

**Files:**
- Create: `apps/desktop/src/panels/McpPanel.tsx`
- Create: `apps/desktop/src/hooks/useMcpStatus.ts`

- [ ] **Step 1: Write `src/hooks/useMcpStatus.ts`**

```typescript
import { useState, useEffect } from 'react'
import type { McpServerDetail } from '@nerv/core'

const DEFAULTS: McpServerDetail[] = [
  { name: 'github',    tools: 0, status: 'connecting' },
  { name: 'claude-mem',tools: 0, status: 'connecting' },
  { name: 'vercel',    tools: 0, status: 'connecting' },
  { name: 'qmd',       tools: 0, status: 'connecting' },
]

export function useMcpStatus() {
  const [servers, setServers] = useState<McpServerDetail[]>(DEFAULTS)

  useEffect(() => {
    async function poll() {
      try {
        const r = await fetch('http://localhost:5555/api/status', { signal: AbortSignal.timeout(2000) })
        if (!r.ok) return
        const data = await r.json()
        if (Array.isArray(data.mcp)) {
          setServers(data.mcp)
        }
      } catch {}
    }
    poll()
    const t = setInterval(poll, 5000)
    return () => clearInterval(t)
  }, [])

  return servers
}
```

- [ ] **Step 2: Write `src/panels/McpPanel.tsx`**

```typescript
import { useState } from 'react'
import { useMcpStatus } from '@/hooks/useMcpStatus'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import type { McpServerDetail } from '@nerv/core'

function StatusBadge({ status }: { status: McpServerDetail['status'] }) {
  const variants = {
    ok: 'bg-green-900 text-green-300',
    error: 'bg-red-900 text-red-300',
    connecting: 'bg-yellow-900 text-yellow-300',
  }
  return <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${variants[status]}`}>{status}</span>
}

function ServerCard({ server, selected, onSelect }: { server: McpServerDetail; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 rounded-lg border transition-all ${
        selected ? 'bg-purple-950/40 border-purple-800/50' : 'bg-[#111] border-[#1a1a1a] hover:border-[#333]'
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-zinc-200">{server.name}</span>
        <StatusBadge status={server.status} />
      </div>
      <div className="text-xs text-zinc-600">
        {server.tools > 0 ? `${server.tools} tools available` : 'no tools yet'}
      </div>
    </button>
  )
}

export function McpPanel() {
  const servers = useMcpStatus()
  const [selected, setSelected] = useState<string | null>(null)
  const selectedServer = servers.find(s => s.name === selected)

  return (
    <div className="flex h-full">
      {/* Server list */}
      <div className="w-64 border-r border-[#1a1a1a] p-3 flex flex-col gap-2 shrink-0">
        <div className="text-[10px] text-zinc-600 uppercase tracking-widest mb-1">MCP Servers</div>
        {servers.map(s => (
          <ServerCard
            key={s.name}
            server={s}
            selected={selected === s.name}
            onSelect={() => setSelected(selected === s.name ? null : s.name)}
          />
        ))}
      </div>

      {/* Tool browser */}
      <ScrollArea className="flex-1 p-4">
        {!selectedServer ? (
          <div className="flex items-center justify-center h-full text-zinc-700 text-sm">
            Select a server to browse tools
          </div>
        ) : (
          <div>
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-zinc-200">{selectedServer.name}</h2>
              <p className="text-xs text-zinc-600 mt-0.5">{selectedServer.tools} tools · {selectedServer.status}</p>
            </div>
            {selectedServer.toolList && selectedServer.toolList.length > 0 ? (
              <div className="flex flex-col gap-2">
                {selectedServer.toolList.map(tool => (
                  <div key={tool.name} className="p-3 bg-[#111] border border-[#1a1a1a] rounded-lg">
                    <div className="font-mono text-sm text-purple-300">{tool.name}</div>
                    <div className="text-xs text-zinc-600 mt-1">{tool.description}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-zinc-700 text-sm">Tool list not available — server may be connecting</div>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
```

- [ ] **Step 3: Install shadcn ScrollArea + Badge**

```bash
cd ~/nerv-desktop/apps/desktop
npx shadcn@latest add scroll-area badge separator
```

- [ ] **Step 4: Run and verify MCP panel**

Click MCP icon. Expected:
- Left column: 4 server cards with status badges
- Clicking a card selects it and shows tool browser on right

- [ ] **Step 5: Commit**

```bash
git add src/panels/McpPanel.tsx src/hooks/useMcpStatus.ts
git commit -m "feat: implement MCP inspector panel with server + tool browser"
```

---

### Task 7: Build OpenClaw Monitor Panel

**Files:**
- Create: `apps/desktop/src/panels/OpenclawPanel.tsx`
- Create: `apps/desktop/src/hooks/useOpenclawStatus.ts`

- [ ] **Step 1: Write `src/hooks/useOpenclawStatus.ts`**

```typescript
import { useState, useEffect } from 'react'
import type { OpenclawStats } from '@nerv/core'

const DEFAULT: OpenclawStats = {
  primaryModel: '—',
  fallbackModel: '—',
  rpm: 0, rpmMax: 60,
  proxyConnected: false,
  totalRequests: 0,
  errorRate: 0,
  queueDepth: 0,
}

export function useOpenclawStatus() {
  const [stats, setStats] = useState<OpenclawStats>(DEFAULT)

  useEffect(() => {
    async function poll() {
      try {
        const r = await fetch('http://localhost:5557/api/stats', { signal: AbortSignal.timeout(2000) })
        if (r.ok) setStats(await r.json())
      } catch {
        // proxy not running — use dashboard status as fallback
        try {
          const r2 = await fetch('http://localhost:5555/api/status', { signal: AbortSignal.timeout(2000) })
          if (r2.ok) {
            const d = await r2.json()
            setStats(prev => ({
              ...prev,
              primaryModel: d.openclawModel ?? prev.primaryModel,
              rpm: d.openclawRpm ?? prev.rpm,
              rpmMax: d.openclawRpmMax ?? prev.rpmMax,
              proxyConnected: d.proxyConnected ?? false,
            }))
          }
        } catch {}
      }
    }
    poll()
    const t = setInterval(poll, 3000)
    return () => clearInterval(t)
  }, [])

  return stats
}
```

- [ ] **Step 2: Write `src/panels/OpenclawPanel.tsx`**

```typescript
import { useOpenclawStatus } from '@/hooks/useOpenclawStatus'

function Gauge({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div>
      <div className="flex justify-between text-xs text-zinc-500 mb-1">
        <span>{label}</span>
        <span className="font-mono">{value} / {max}</span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

function Stat({ label, value, mono = false }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="text-[10px] text-zinc-600 uppercase tracking-widest">{label}</div>
      <div className={`text-zinc-200 ${mono ? 'font-mono text-sm' : 'text-sm'}`}>{value}</div>
    </div>
  )
}

export function OpenclawPanel() {
  const stats = useOpenclawStatus()
  const rpmPct = Math.round((stats.rpm / stats.rpmMax) * 100)

  return (
    <div className="p-6 flex flex-col gap-6 max-w-2xl">
      <div>
        <h2 className="text-lg font-semibold text-zinc-200">OpenClaw Gateway</h2>
        <p className="text-xs text-zinc-600 mt-0.5">Proxy at :5557 · Anthropic + OpenAI routing</p>
      </div>

      {/* Connection status */}
      <div className="flex items-center gap-3 p-3 bg-[#111] border border-[#1a1a1a] rounded-lg">
        <span className={`w-2.5 h-2.5 rounded-full ${stats.proxyConnected ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'}`} />
        <span className="text-sm text-zinc-300">{stats.proxyConnected ? 'Proxy connected' : 'Proxy connecting...'}</span>
      </div>

      {/* Model info */}
      <div className="grid grid-cols-2 gap-4 p-4 bg-[#111] border border-[#1a1a1a] rounded-lg">
        <Stat label="Primary Model" value={stats.primaryModel} mono />
        <Stat label="Fallback Model" value={stats.fallbackModel} mono />
        <Stat label="Total Requests" value={stats.totalRequests.toLocaleString()} />
        <Stat label="Error Rate" value={`${(stats.errorRate * 100).toFixed(1)}%`} />
      </div>

      {/* Rate gauges */}
      <div className="p-4 bg-[#111] border border-[#1a1a1a] rounded-lg flex flex-col gap-4">
        <Gauge value={stats.rpm} max={stats.rpmMax} label="Requests per Minute" color={rpmPct > 80 ? '#ef4444' : '#f59e0b'} />
        <Gauge value={stats.queueDepth} max={20} label="Queue Depth" color="#6366f1" />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Run and verify OpenClaw panel**

Click OpenClaw icon. Expected:
- Connection status badge (yellow if proxy not running)
- Model names from `/api/status`
- Rate gauges

- [ ] **Step 4: Commit**

```bash
git add src/panels/OpenclawPanel.tsx src/hooks/useOpenclawStatus.ts
git commit -m "feat: implement OpenClaw monitor panel with rate gauges"
```

---

### Task 8: Add `/api/stats` to OpenClaw Proxy

> Modifies `~/aeon/openclaw-proxy/index.js` to expose a stats endpoint.

**Files:**
- Modify: `~/aeon/openclaw-proxy/index.js`

- [ ] **Step 1: Add stats tracking and endpoint**

In `openclaw-proxy/index.js`, add a stats counter object near the top:

```javascript
const stats = {
  totalRequests: 0,
  recentRequests: [], // timestamps for RPM calculation
  errors: 0,
  queueDepth: 0,
}
```

After each proxied request completes, push `Date.now()` to `recentRequests` and trim to last 60 seconds.

Add a GET endpoint:

```javascript
app.get('/api/stats', (req, res) => {
  const now = Date.now()
  const recentMs = stats.recentRequests.filter(t => now - t < 60000)
  stats.recentRequests = recentMs // prune

  res.json({
    primaryModel: currentModel ?? 'claude-haiku-4-5',
    fallbackModel: fallbackModel ?? '—',
    rpm: recentMs.length,
    rpmMax: 60,
    proxyConnected: wsConnected,
    totalRequests: stats.totalRequests,
    errorRate: stats.totalRequests > 0 ? stats.errors / stats.totalRequests : 0,
    queueDepth: stats.queueDepth,
  })
})
```

> Adapt variable names to match what's already in `index.js` — read the file first.

- [ ] **Step 2: Reload proxy and test**

```bash
cd ~/aeon && pm2 reload openclaw-proxy
curl http://localhost:5557/api/stats
```

Expected: JSON with model, rpm, etc.

- [ ] **Step 3: Commit**

```bash
cd ~/aeon
git add openclaw-proxy/index.js
git commit -m "feat: add /api/stats endpoint to openclaw proxy"
```

---

### Task 9: Final Integration Test for Plan 2

- [ ] **Step 1: Start services**

```bash
cd ~/aeon && pm2 start ecosystem.config.cjs
```

- [ ] **Step 2: Start desktop app**

```bash
cd ~/nerv-desktop/apps/desktop && npm run tauri dev
```

- [ ] **Step 3: Test each panel**

| Panel | Expected |
|-------|----------|
| CLI   | xterm banner visible, input bar works, typing + Enter echoes command |
| MCP   | 4 server cards shown, selecting one shows tool browser |
| OpenClaw | Connection status, model name from proxy, RPM gauge |
| Others | "coming in a future plan" placeholder |

- [ ] **Step 4: Push all changes**

```bash
cd ~/nerv-desktop && git push
cd ~/aeon && git push
```
