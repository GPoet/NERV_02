# NERV Desktop — Plan 1: Foundation (Turborepo + Tauri Shell + Layout)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap a Turborepo monorepo with a working Tauri 2.x desktop app, shared UI package, the 3-column layout (left nav sidebar, main panel area, right status sidebar), and dark theme — no panels yet, just the shell.

**Architecture:** Turborepo monorepo with `apps/desktop` (Tauri 2 + React + Vite) and `packages/ui` (shared shadcn/ui components). The desktop app renders a 3-column layout: 52px icon nav (left), flexible main content (center), 220px status bar (right). Tailwind + shadcn/ui for all UI. No Next.js in the desktop app — Vite only.

**Tech Stack:** Tauri 2.x, React 19, Vite, TypeScript, Turborepo, shadcn/ui, Tailwind CSS 4, `@tauri-apps/api`

---

## File Map

**Created:**
- `nerv-desktop/` — monorepo root
- `nerv-desktop/turbo.json` — task pipeline
- `nerv-desktop/package.json` — workspace root
- `nerv-desktop/apps/desktop/` — Tauri app
- `nerv-desktop/apps/desktop/src-tauri/` — Rust backend (Tauri scaffold)
- `nerv-desktop/apps/desktop/src/main.tsx` — React entry
- `nerv-desktop/apps/desktop/src/App.tsx` — root with 3-column layout
- `nerv-desktop/apps/desktop/src/components/NavSidebar.tsx` — 52px left nav
- `nerv-desktop/apps/desktop/src/components/StatusSidebar.tsx` — 220px right status bar
- `nerv-desktop/apps/desktop/src/components/MainPanel.tsx` — center panel placeholder
- `nerv-desktop/apps/desktop/src/store/panel.ts` — active panel state (Zustand)
- `nerv-desktop/packages/ui/` — shared component library
- `nerv-desktop/packages/ui/src/index.ts` — re-exports
- `nerv-desktop/packages/ui/package.json`

**Modified:** nothing (greenfield)

---

### Task 1: Scaffold Turborepo Monorepo

**Files:**
- Create: `nerv-desktop/package.json`
- Create: `nerv-desktop/turbo.json`
- Create: `nerv-desktop/.gitignore`

- [ ] **Step 1: Create the monorepo root**

```bash
mkdir -p ~/nerv-desktop && cd ~/nerv-desktop
```

- [ ] **Step 2: Write `package.json`**

```json
{
  "name": "nerv-desktop",
  "private": true,
  "workspaces": ["apps/*", "packages/*"],
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "lint": "turbo run lint",
    "typecheck": "turbo run typecheck"
  },
  "devDependencies": {
    "turbo": "latest",
    "typescript": "^5.4.0"
  },
  "packageManager": "npm@10.8.0"
}
```

- [ ] **Step 3: Write `turbo.json`**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "out/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {},
    "typecheck": {
      "dependsOn": ["^build"]
    }
  }
}
```

- [ ] **Step 4: Write `.gitignore`**

```
node_modules/
dist/
.turbo/
target/
*.log
.env*.local
```

- [ ] **Step 5: Install Turborepo**

```bash
cd ~/nerv-desktop && npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 6: Commit**

```bash
cd ~/nerv-desktop
git init && git add .
git commit -m "chore: init turborepo monorepo"
```

---

### Task 2: Scaffold Tauri + React + Vite App

**Files:**
- Create: `apps/desktop/` (full Tauri scaffold)
- Create: `apps/desktop/package.json`
- Create: `apps/desktop/vite.config.ts`
- Create: `apps/desktop/tsconfig.json`
- Create: `apps/desktop/index.html`
- Create: `apps/desktop/src/main.tsx`

- [ ] **Step 1: Create the Tauri app via CLI**

```bash
cd ~/nerv-desktop
npm create tauri-app@latest apps/desktop -- --template react-ts --manager npm
```

When prompted:
- App name: `NERV`
- Window title: `NERV Command Center`
- Accept defaults for Rust

Expected: `apps/desktop/` created with `src-tauri/` and React scaffold.

- [ ] **Step 2: Verify it runs**

```bash
cd ~/nerv-desktop/apps/desktop && npm install && npm run tauri dev
```

Expected: Desktop window opens showing default Vite+React page. Close it.

- [ ] **Step 3: Add to workspace — update root `package.json` if needed**

Ensure `"workspaces": ["apps/*", "packages/*"]` covers the new app. Run from root:

```bash
cd ~/nerv-desktop && npm install
```

- [ ] **Step 4: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop
git commit -m "chore: scaffold tauri+react+vite desktop app"
```

---

### Task 3: Install Tailwind CSS 4 + shadcn/ui

**Files:**
- Modify: `apps/desktop/vite.config.ts`
- Modify: `apps/desktop/src/main.tsx`
- Create: `apps/desktop/src/index.css`
- Modify: `apps/desktop/src-tauri/tauri.conf.json` (window size)

- [ ] **Step 1: Install Tailwind 4 and shadcn deps**

```bash
cd ~/nerv-desktop/apps/desktop
npm install tailwindcss @tailwindcss/vite
npm install class-variance-authority clsx tailwind-merge lucide-react
```

- [ ] **Step 2: Add Tailwind plugin to `vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  clearScreen: false,
  server: { port: 1420, strictPort: true },
})
```

- [ ] **Step 3: Write `src/index.css`**

```css
@import "tailwindcss";

:root {
  --background: 0 0% 3.9%;
  --foreground: 0 0% 98%;
  --muted: 0 0% 14.9%;
  --muted-foreground: 0 0% 63.9%;
  --border: 0 0% 14.9%;
  --accent: 245 58% 51%;
}

* { box-sizing: border-box; }
body { margin: 0; background: hsl(var(--background)); color: hsl(var(--foreground)); font-family: 'Geist', system-ui, sans-serif; }
```

- [ ] **Step 4: Update `src-tauri/tauri.conf.json` window size**

Find the `"windows"` array and set:

```json
{
  "label": "main",
  "title": "NERV Command Center",
  "width": 1400,
  "height": 900,
  "minWidth": 1200,
  "minHeight": 700,
  "decorations": true,
  "transparent": false
}
```

- [ ] **Step 5: Initialize shadcn**

```bash
cd ~/nerv-desktop/apps/desktop
npx shadcn@latest init
```

When prompted: TypeScript yes, style Default, base color Zinc, CSS variables yes, path alias `@/*`.

- [ ] **Step 6: Add a test component to verify**

```bash
npx shadcn@latest add button tooltip
```

- [ ] **Step 7: Verify Tailwind + shadcn works**

```bash
npm run tauri dev
```

Expected: Window opens, no CSS errors in console.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: add tailwind 4 + shadcn/ui to desktop app"
```

---

### Task 4: Install Zustand for Panel State

**Files:**
- Create: `apps/desktop/src/store/panel.ts`

- [ ] **Step 1: Install Zustand**

```bash
cd ~/nerv-desktop/apps/desktop && npm install zustand
```

- [ ] **Step 2: Write `src/store/panel.ts`**

```typescript
import { create } from 'zustand'

export type PanelId = 'CLI' | 'SESSIONS' | 'MCP' | 'OPENCLAW' | 'AEON' | 'SUPERPOWERS' | 'AGENCY' | 'AIGENCY' | 'MEMORY' | 'CONFIG'

interface PanelState {
  activePanel: PanelId
  setPanel: (id: PanelId) => void
}

export const usePanelStore = create<PanelState>((set) => ({
  activePanel: 'CLI',
  setPanel: (id) => set({ activePanel: id }),
}))
```

- [ ] **Step 3: Commit**

```bash
git add src/store/panel.ts && git commit -m "feat: add zustand panel state store"
```

---

### Task 5: Build Left Nav Sidebar (52px icon strip)

**Files:**
- Create: `apps/desktop/src/components/NavSidebar.tsx`

- [ ] **Step 1: Write `NavSidebar.tsx`**

```typescript
import { usePanelStore, PanelId } from '@/store/panel'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Terminal, MonitorCog, Cpu, Activity, Zap, Brain, Command, Bot, Database, Settings } from 'lucide-react'

const NAV_ITEMS: { id: PanelId; icon: React.ElementType; label: string; color: string }[] = [
  { id: 'CLI',        icon: Terminal,    label: 'NERV Terminal',    color: '#6366f1' },
  { id: 'SESSIONS',   icon: MonitorCog,  label: 'Sessions',         color: '#22c55e' },
  { id: 'MCP',        icon: Cpu,         label: 'MCP Inspector',    color: '#a78bfa' },
  { id: 'OPENCLAW',   icon: Activity,    label: 'OpenClaw Monitor', color: '#f59e0b' },
  { id: 'AEON',       icon: Zap,         label: 'Aeon Skills',      color: '#f59e0b' },
  { id: 'SUPERPOWERS',icon: Brain,       label: 'Superpowers',      color: '#c084fc' },
  { id: 'AGENCY',     icon: Command,     label: 'Agency / NEXUS',   color: '#f97316' },
  { id: 'AIGENCY',    icon: Bot,         label: 'Aigency02',        color: '#3b82f6' },
  { id: 'MEMORY',     icon: Database,    label: 'Memory Browser',   color: '#ec4899' },
  { id: 'CONFIG',     icon: Settings,    label: 'Config',           color: '#71717a' },
]

export function NavSidebar() {
  const { activePanel, setPanel } = usePanelStore()

  return (
    <TooltipProvider delayDuration={300}>
      <aside className="flex flex-col items-center w-[52px] min-h-screen bg-[#0a0a0a] border-r border-[#1a1a1a] py-3 gap-1 shrink-0">
        {/* Logo mark */}
        <div className="w-8 h-8 rounded bg-indigo-600 flex items-center justify-center text-xs font-bold text-white mb-4">N</div>

        {NAV_ITEMS.map(({ id, icon: Icon, label, color }) => {
          const isActive = activePanel === id
          return (
            <Tooltip key={id}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => setPanel(id)}
                  className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
                    isActive
                      ? 'bg-[#1a1a1a] ring-1 ring-[#333]'
                      : 'hover:bg-[#111] opacity-50 hover:opacity-100'
                  }`}
                >
                  <Icon size={16} style={{ color: isActive ? color : '#888' }} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p className="text-xs">{label}</p>
              </TooltipContent>
            </Tooltip>
          )
        })}
      </aside>
    </TooltipProvider>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/NavSidebar.tsx && git commit -m "feat: add nav sidebar with 10 panel icons"
```

---

### Task 6: Build Right Status Sidebar (220px)

**Files:**
- Create: `apps/desktop/src/components/StatusSidebar.tsx`
- Create: `apps/desktop/src/hooks/useNervStatus.ts`

- [ ] **Step 1: Write `src/hooks/useNervStatus.ts` — polls :5555 and :5557 health**

```typescript
import { useState, useEffect } from 'react'

interface McpServer { name: string; tools: number; status: 'ok' | 'error' | 'connecting' }
interface NervStatus {
  mcp: McpServer[]
  openclawModel: string
  openclawRpm: number
  openclawRpmMax: number
  proxyConnected: boolean
  activeJobs: { name: string; elapsedMs: number }[]
}

const EMPTY: NervStatus = {
  mcp: [
    { name: 'github',    tools: 0, status: 'connecting' },
    { name: 'claude-mem',tools: 0, status: 'connecting' },
    { name: 'vercel',    tools: 0, status: 'connecting' },
    { name: 'qmd',       tools: 0, status: 'connecting' },
  ],
  openclawModel: '—',
  openclawRpm: 0,
  openclawRpmMax: 60,
  proxyConnected: false,
  activeJobs: [],
}

export function useNervStatus() {
  const [status, setStatus] = useState<NervStatus>(EMPTY)
  const [dashConnected, setDashConnected] = useState(false)

  useEffect(() => {
    async function poll() {
      try {
        const r = await fetch('http://localhost:5555/api/status', { signal: AbortSignal.timeout(2000) })
        if (r.ok) {
          const data = await r.json()
          setStatus(data)
          setDashConnected(true)
        }
      } catch {
        setDashConnected(false)
      }
    }
    poll()
    const t = setInterval(poll, 5000)
    return () => clearInterval(t)
  }, [])

  return { status, dashConnected }
}
```

- [ ] **Step 2: Write `src/components/StatusSidebar.tsx`**

```typescript
import { useNervStatus } from '@/hooks/useNervStatus'

function StatusDot({ status }: { status: 'ok' | 'error' | 'connecting' }) {
  return (
    <span className={`w-1.5 h-1.5 rounded-full inline-block ${
      status === 'ok' ? 'bg-green-500' : status === 'error' ? 'bg-red-500' : 'bg-yellow-500 animate-pulse'
    }`} />
  )
}

export function StatusSidebar() {
  const { status, dashConnected } = useNervStatus()

  return (
    <aside className="w-[220px] min-h-screen bg-[#0a0a0a] border-l border-[#1a1a1a] p-3 shrink-0 flex flex-col gap-4 text-xs">
      {/* Dashboard connection */}
      <div>
        <div className="text-[10px] text-zinc-600 uppercase tracking-widest mb-2">Infrastructure</div>
        <div className="flex items-center gap-2">
          <StatusDot status={dashConnected ? 'ok' : 'connecting'} />
          <span className="text-zinc-400">NERV Dashboard</span>
          <span className="ml-auto text-zinc-600">:5555</span>
        </div>
      </div>

      {/* MCP servers */}
      <div>
        <div className="text-[10px] text-zinc-600 uppercase tracking-widest mb-2">MCP Servers</div>
        <div className="flex flex-col gap-1.5">
          {status.mcp.map(s => (
            <div key={s.name} className="flex items-center gap-2">
              <StatusDot status={s.status} />
              <span className="text-zinc-400">{s.name}</span>
              {s.tools > 0 && <span className="ml-auto text-zinc-600">{s.tools}t</span>}
            </div>
          ))}
        </div>
      </div>

      {/* OpenClaw */}
      <div>
        <div className="text-[10px] text-zinc-600 uppercase tracking-widest mb-2">OpenClaw</div>
        <div className="flex items-center gap-2 mb-1">
          <StatusDot status={status.proxyConnected ? 'ok' : 'connecting'} />
          <span className="text-zinc-400 truncate">{status.openclawModel}</span>
        </div>
        <div className="w-full h-1 bg-zinc-800 rounded-full">
          <div
            className="h-1 bg-amber-500 rounded-full transition-all"
            style={{ width: `${(status.openclawRpm / status.openclawRpmMax) * 100}%` }}
          />
        </div>
        <div className="text-zinc-600 mt-0.5">{status.openclawRpm}/{status.openclawRpmMax} rpm</div>
      </div>

      {/* Active jobs */}
      {status.activeJobs.length > 0 && (
        <div>
          <div className="text-[10px] text-zinc-600 uppercase tracking-widest mb-2">Active Jobs</div>
          <div className="flex flex-col gap-1.5">
            {status.activeJobs.map((j, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                <span className="text-zinc-400 truncate">{j.name}</span>
                <span className="ml-auto text-zinc-600">{Math.floor(j.elapsedMs / 1000)}s</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Spacer + version */}
      <div className="mt-auto text-[10px] text-zinc-700">NERV v1.0.0</div>
    </aside>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/StatusSidebar.tsx src/hooks/useNervStatus.ts
git commit -m "feat: add status sidebar with MCP + OpenClaw health polling"
```

---

### Task 7: Wire Up 3-Column Layout in App.tsx

**Files:**
- Create: `apps/desktop/src/components/MainPanel.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/main.tsx`

- [ ] **Step 1: Write `src/components/MainPanel.tsx` placeholder**

```typescript
import { usePanelStore } from '@/store/panel'

export function MainPanel() {
  const { activePanel } = usePanelStore()

  return (
    <main className="flex-1 min-h-screen bg-[#0d0d0d] flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl font-bold text-zinc-800 mb-2">◈</div>
        <div className="text-zinc-600 text-sm font-mono">{activePanel}</div>
        <div className="text-zinc-700 text-xs mt-1">panel not yet implemented</div>
      </div>
    </main>
  )
}
```

- [ ] **Step 2: Write `src/App.tsx`**

```typescript
import { NavSidebar } from '@/components/NavSidebar'
import { MainPanel } from '@/components/MainPanel'
import { StatusSidebar } from '@/components/StatusSidebar'

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0a0a]">
      <NavSidebar />
      <MainPanel />
      <StatusSidebar />
    </div>
  )
}
```

- [ ] **Step 3: Update `src/main.tsx` to import CSS**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 4: Run the app and verify layout**

```bash
cd ~/nerv-desktop/apps/desktop && npm run tauri dev
```

Expected:
- 1400×900 dark window
- Left: 52px sidebar with 10 icons
- Center: placeholder showing active panel name
- Right: 220px status bar with MCP/OpenClaw sections
- Clicking nav icons switches the center panel name

- [ ] **Step 5: Commit**

```bash
git add src/App.tsx src/main.tsx src/components/MainPanel.tsx
git commit -m "feat: wire up 3-column app layout"
```

---

### Task 8: Create Shared `packages/ui`

**Files:**
- Create: `packages/ui/package.json`
- Create: `packages/ui/tsconfig.json`
- Create: `packages/ui/src/index.ts`
- Create: `packages/ui/src/cn.ts`

- [ ] **Step 1: Create `packages/ui/package.json`**

```json
{
  "name": "@nerv/ui",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts",
    "./cn": "./src/cn.ts"
  },
  "peerDependencies": {
    "react": "^19.0.0"
  }
}
```

- [ ] **Step 2: Write `packages/ui/src/cn.ts`**

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 3: Write `packages/ui/src/index.ts`**

```typescript
export { cn } from './cn'
// Future: export shared Panel, StatusDot, etc.
```

- [ ] **Step 4: Install shared package in desktop app**

```bash
cd ~/nerv-desktop/apps/desktop
npm install @nerv/ui@* --workspace
```

- [ ] **Step 5: Refactor `NavSidebar.tsx` to use `@nerv/ui`'s cn**

Replace the import in `NavSidebar.tsx`:
```typescript
// before
import { clsx } from 'clsx'
// after
import { cn } from '@nerv/ui/cn'
```

(Only if NavSidebar was using clsx directly — otherwise skip this step.)

- [ ] **Step 6: Commit**

```bash
git add packages/ui
git commit -m "feat: add @nerv/ui shared package with cn utility"
```

---

### Task 9: Add `packages/nerv-core` (API Client + Types)

**Files:**
- Create: `packages/nerv-core/package.json`
- Create: `packages/nerv-core/src/index.ts`
- Create: `packages/nerv-core/src/types.ts`
- Create: `packages/nerv-core/src/client.ts`

- [ ] **Step 1: Create `packages/nerv-core/package.json`**

```json
{
  "name": "@nerv/core",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  }
}
```

- [ ] **Step 2: Write `src/types.ts`**

```typescript
export type PanelId = 'CLI' | 'SESSIONS' | 'MCP' | 'OPENCLAW' | 'AEON' | 'SUPERPOWERS' | 'AGENCY' | 'AIGENCY' | 'MEMORY' | 'CONFIG'

export interface McpServer {
  name: string
  tools: number
  status: 'ok' | 'error' | 'connecting'
}

export interface NervStatus {
  mcp: McpServer[]
  openclawModel: string
  openclawRpm: number
  openclawRpmMax: number
  proxyConnected: boolean
  activeJobs: { name: string; elapsedMs: number }[]
}

export interface JobRecord {
  id: string
  skill: string
  status: 'pending' | 'running' | 'success' | 'failed'
  startedAt: number
  output?: string
}
```

- [ ] **Step 3: Write `src/client.ts`**

```typescript
const NERV_BASE = 'http://localhost:5555'

export async function fetchNervStatus(): Promise<Response> {
  return fetch(`${NERV_BASE}/api/status`, { signal: AbortSignal.timeout(2000) })
}

export async function fetchJobs(): Promise<Response> {
  return fetch(`${NERV_BASE}/api/agency/jobs/snapshot`, { signal: AbortSignal.timeout(2000) })
}

export async function dispatchSkill(skill: string, token: string): Promise<Response> {
  return fetch(`${NERV_BASE}/api/agency/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ skill }),
  })
}
```

- [ ] **Step 4: Write `src/index.ts`**

```typescript
export * from './types'
export * from './client'
```

- [ ] **Step 5: Refactor `useNervStatus.ts` to use `@nerv/core`**

```bash
cd ~/nerv-desktop/apps/desktop && npm install @nerv/core@* --workspace
```

Update the import:
```typescript
// before: local fetch call
// after:
import { fetchNervStatus, NervStatus } from '@nerv/core'
```

- [ ] **Step 6: Commit**

```bash
git add packages/nerv-core
git commit -m "feat: add @nerv/core shared API client and types"
```

---

### Task 10: Add `/api/status` Endpoint to NERV Dashboard

> This task modifies the **existing NERV dashboard** at `~/aeon/dashboard/` to expose the status data the desktop app needs.

**Files:**
- Create: `~/aeon/dashboard/app/api/status/route.ts`

- [ ] **Step 1: Write the status route**

```typescript
import { NextResponse } from 'next/server'
import { requireAuth } from '@/lib/auth'

// Public status endpoint — no auth required for local desktop app
export async function GET() {
  // Return static shape for now — future: pull from real sources
  return NextResponse.json({
    mcp: [
      { name: 'github',    tools: 12, status: 'ok' },
      { name: 'claude-mem',tools: 6,  status: 'ok' },
      { name: 'vercel',    tools: 18, status: 'ok' },
      { name: 'qmd',       tools: 0,  status: 'connecting' },
    ],
    openclawModel: 'claude-haiku-4-5',
    openclawRpm: 4,
    openclawRpmMax: 60,
    proxyConnected: true,
    activeJobs: [],
  })
}
```

- [ ] **Step 2: Test it**

```bash
curl http://localhost:5555/api/status
```

Expected: JSON with MCP servers, OpenClaw, jobs.

- [ ] **Step 3: Reload dashboard**

```bash
cd ~/aeon && pm2 reload nerv-dashboard
```

- [ ] **Step 4: Verify desktop app status sidebar populates**

Run `npm run tauri dev` from `apps/desktop`. Right sidebar should show green dots for github, claude-mem, vercel.

- [ ] **Step 5: Commit dashboard change**

```bash
cd ~/aeon
git add dashboard/app/api/status/route.ts
git commit -m "feat: add /api/status endpoint for desktop app"
```

---

### Task 11: Final Integration Test

- [ ] **Step 1: Start NERV dashboard**

```bash
cd ~/aeon && pm2 start ecosystem.config.cjs --only nerv-dashboard
```

- [ ] **Step 2: Start desktop app**

```bash
cd ~/nerv-desktop/apps/desktop && npm run tauri dev
```

- [ ] **Step 3: Verify all 10 nav icons present and clickable**

Click each icon — center panel should show the correct panel ID.

- [ ] **Step 4: Verify status sidebar shows live data**

Right sidebar should show:
- NERV Dashboard: green dot
- MCP servers: github/claude-mem/vercel green, qmd yellow
- OpenClaw: amber progress bar

- [ ] **Step 5: Push monorepo to GitHub**

```bash
cd ~/nerv-desktop
gh repo create bludragon66613-sys/nerv-desktop --private --source=. --remote=origin --push
```

- [ ] **Step 6: Final commit**

```bash
git add -A && git commit -m "feat: plan 1 complete — tauri shell + 3-column layout + status polling"
git push
```

---

## What's NOT in Plan 1 (covered in later plans)

- Panel implementations (CLI, MCP, etc.) → Plan 2
- WebSocket server for agent communication → Plan 3
- Rust backend logic beyond scaffold → Plan 2+
