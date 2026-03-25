# NERV Desktop — Plan 3: Agent Communication (WebSocket Server + nerv-sdk)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Prerequisite:** Plans 1 and 2 must be complete. Tauri shell, panel router, and `@nerv/core` must exist.

**Goal:** Give agents (OpenClaw, Aeon skills, GitHub Actions) the ability to autonomously push notifications, navigate the desktop UI, and update panel data in real time. Implement a WebSocket server on port 5558 (inside the Tauri Rust backend) with a REST fallback, and ship `nerv-sdk.js` — a tiny client library agents can import.

**Architecture:** Tauri's Rust backend runs an Axum WebSocket server on :5558. React frontend connects to it via Tauri's `invoke` IPC (not direct WS — Tauri manages the port). Agents outside the app connect via raw WebSocket or REST fallback at the same port. Messages are JSON: `{ type, payload }`. Auth via a shared bearer token stored in `~/.nerv-sdk-token`. `nerv-sdk.js` is a 150-line Node.js file with zero dependencies (uses `ws` package).

**Tech Stack:** Tauri 2 Rust backend (Axum + tokio-tungstenite), React (Tauri `invoke` + `listen` events), `nerv-sdk.js` (Node.js + `ws`), JWT token file auth

---

## File Map

**Created:**
- `apps/desktop/src-tauri/src/ws_server.rs` — Axum WS server on :5558
- `apps/desktop/src-tauri/src/main.rs` — updated to start ws_server thread
- `apps/desktop/src/hooks/useNervSocket.ts` — Tauri event listener for WS messages
- `apps/desktop/src/store/notifications.ts` — toast notification store
- `apps/desktop/src/components/NotificationToast.tsx` — toast renderer
- `nerv-sdk/nerv-sdk.js` — agent-side SDK (Node.js)
- `nerv-sdk/README.md` — usage docs

**Modified:**
- `apps/desktop/src-tauri/Cargo.toml` — add axum, tokio-tungstenite, serde_json deps
- `apps/desktop/src/App.tsx` — mount NotificationToast
- `apps/desktop/src/components/MainPanel.tsx` — handle `navigate` messages

---

### Task 1: Add Rust Dependencies to Tauri

**Files:**
- Modify: `apps/desktop/src-tauri/Cargo.toml`

- [ ] **Step 1: Read current `Cargo.toml`**

```bash
cat ~/nerv-desktop/apps/desktop/src-tauri/Cargo.toml
```

- [ ] **Step 2: Add dependencies under `[dependencies]`**

```toml
axum = { version = "0.7", features = ["ws"] }
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

> Note: Tauri 2 already uses tokio — verify the existing tokio version to avoid conflicts. Match the major version.

- [ ] **Step 3: Build to verify deps resolve**

```bash
cd ~/nerv-desktop/apps/desktop && npm run tauri build -- --debug 2>&1 | head -50
```

Expected: Cargo downloads and compiles new deps. No errors.

- [ ] **Step 4: Commit**

```bash
git add src-tauri/Cargo.toml src-tauri/Cargo.lock
git commit -m "chore: add axum + serde_json to tauri rust backend"
```

---

### Task 2: Write the WebSocket Server (`ws_server.rs`)

**Files:**
- Create: `apps/desktop/src-tauri/src/ws_server.rs`

- [ ] **Step 1: Write `ws_server.rs`**

```rust
use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};
use tokio::net::TcpListener;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct NervMessage {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub payload: Option<Value>,
}

pub type WsClients = Arc<Mutex<HashMap<String, tokio::sync::mpsc::UnboundedSender<Message>>>>;

#[derive(Clone)]
pub struct AppState {
    pub clients: WsClients,
    pub token: String,
}

/// Broadcast a message to all connected WebSocket clients
pub fn broadcast(state: &AppState, msg: &NervMessage) {
    let text = serde_json::to_string(msg).unwrap_or_default();
    let clients = state.clients.lock().unwrap();
    for tx in clients.values() {
        let _ = tx.send(Message::Text(text.clone().into()));
    }
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state))
}

async fn handle_socket(mut socket: WebSocket, state: AppState) {
    let id = uuid::Uuid::new_v4().to_string();
    let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();

    state.clients.lock().unwrap().insert(id.clone(), tx);

    loop {
        tokio::select! {
            Some(msg) = socket.recv() => {
                match msg {
                    Ok(Message::Text(text)) => {
                        // Forward received messages to Tauri frontend via stdout signal
                        println!("NERV_WS_MSG:{}", text);
                    }
                    Ok(Message::Close(_)) | Err(_) => break,
                    _ => {}
                }
            }
            Some(msg) = rx.recv() => {
                if socket.send(msg).await.is_err() { break; }
            }
            else => break,
        }
    }

    state.clients.lock().unwrap().remove(&id);
}

/// REST fallback: POST /notify, /navigate, /update
async fn rest_message(
    State(state): State<AppState>,
    Json(msg): Json<NervMessage>,
) -> impl IntoResponse {
    broadcast(&state, &msg);
    println!("NERV_WS_MSG:{}", serde_json::to_string(&msg).unwrap_or_default());
    Json(json!({ "ok": true }))
}

pub async fn start(port: u16, token: String) {
    let clients: WsClients = Arc::new(Mutex::new(HashMap::new()));
    let state = AppState { clients, token };

    let app = Router::new()
        .route("/ws", get(ws_handler))
        .route("/message", post(rest_message))
        .with_state(state);

    let listener = TcpListener::bind(format!("127.0.0.1:{}", port))
        .await
        .expect("failed to bind nerv ws server");

    println!("NERV WebSocket server listening on :{}", port);
    axum::serve(listener, app).await.unwrap();
}
```

- [ ] **Step 2: Add uuid dependency**

In `Cargo.toml` add:

```toml
uuid = { version = "1", features = ["v4"] }
```

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/ws_server.rs src-tauri/Cargo.toml
git commit -m "feat: add axum websocket server module to tauri backend"
```

---

### Task 3: Start WS Server in `main.rs`

**Files:**
- Modify: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Read current `main.rs`**

```bash
cat ~/nerv-desktop/apps/desktop/src-tauri/src/main.rs
```

- [ ] **Step 2: Add WS server startup**

Add to the top of the file:

```rust
mod ws_server;
```

In the `main` function, before `tauri::Builder::default()`, spawn the WS server:

```rust
let nerv_token = std::env::var("NERV_SDK_TOKEN").unwrap_or_else(|_| "nerv-local-dev-token".to_string());
tokio::spawn(ws_server::start(5558, nerv_token));
```

> Tauri 2 apps run in a tokio runtime — `tokio::spawn` works directly in `main`.

- [ ] **Step 3: Build and verify**

```bash
cd ~/nerv-desktop/apps/desktop && npm run tauri dev
```

Expected: Console shows `NERV WebSocket server listening on :5558`. No crash.

- [ ] **Step 4: Test WS connection with wscat**

```bash
npx wscat -c ws://localhost:5558/ws
```

Expected: Connected. Type `{"type":"ping"}` and it should not error.

- [ ] **Step 5: Commit**

```bash
git add src-tauri/src/main.rs
git commit -m "feat: spawn nerv ws server on :5558 at tauri startup"
```

---

### Task 4: Listen for WS Messages in React Frontend

**Files:**
- Create: `apps/desktop/src/hooks/useNervSocket.ts`
- Create: `apps/desktop/src/store/notifications.ts`

- [ ] **Step 1: Write `src/store/notifications.ts`**

```typescript
import { create } from 'zustand'

export interface Toast {
  id: string
  message: string
  type: 'info' | 'success' | 'error'
  expiresAt: number
}

interface NotificationState {
  toasts: Toast[]
  push: (msg: string, type?: Toast['type']) => void
  dismiss: (id: string) => void
}

export const useNotifications = create<NotificationState>((set) => ({
  toasts: [],
  push: (message, type = 'info') => {
    const id = crypto.randomUUID()
    set(s => ({ toasts: [...s.toasts, { id, message, type, expiresAt: Date.now() + 5000 }] }))
    setTimeout(() => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })), 5000)
  },
  dismiss: (id) => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}))
```

- [ ] **Step 2: Write `src/hooks/useNervSocket.ts`**

```typescript
import { useEffect } from 'react'
import { useNotifications } from '@/store/notifications'
import { usePanelStore, PanelId } from '@/store/panel'

interface NervMessage {
  type: 'notify' | 'navigate' | 'update' | 'alert'
  payload?: {
    message?: string
    panel?: PanelId
    data?: unknown
    severity?: 'info' | 'success' | 'error'
  }
}

export function useNervSocket() {
  const { push } = useNotifications()
  const { setPanel } = usePanelStore()

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:5558/ws')

    ws.onopen = () => console.log('[NERV] WS connected')
    ws.onclose = () => console.log('[NERV] WS disconnected')

    ws.onmessage = (e) => {
      try {
        const msg: NervMessage = JSON.parse(e.data)

        switch (msg.type) {
          case 'notify':
            push(msg.payload?.message ?? 'Notification', msg.payload?.severity ?? 'info')
            break
          case 'navigate':
            if (msg.payload?.panel) setPanel(msg.payload.panel)
            break
          case 'alert':
            push(msg.payload?.message ?? 'Alert', 'error')
            break
          case 'update':
            // Future: dispatch to panel-specific store
            console.log('[NERV] update', msg.payload)
            break
        }
      } catch {}
    }

    return () => ws.close()
  }, [push, setPanel])
}
```

- [ ] **Step 3: Commit**

```bash
git add src/hooks/useNervSocket.ts src/store/notifications.ts
git commit -m "feat: add WS message listener + notification store"
```

---

### Task 5: Build Toast Notification Renderer

**Files:**
- Create: `apps/desktop/src/components/NotificationToast.tsx`
- Modify: `apps/desktop/src/App.tsx`

- [ ] **Step 1: Write `src/components/NotificationToast.tsx`**

```typescript
import { useNotifications } from '@/store/notifications'
import { X } from 'lucide-react'

export function NotificationToast() {
  const { toasts, dismiss } = useNotifications()

  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg pointer-events-auto max-w-sm text-sm transition-all ${
            t.type === 'success' ? 'bg-green-950 border border-green-800 text-green-200' :
            t.type === 'error'   ? 'bg-red-950 border border-red-800 text-red-200' :
                                   'bg-zinc-900 border border-zinc-700 text-zinc-200'
          }`}
        >
          <span className="flex-1">{t.message}</span>
          <button onClick={() => dismiss(t.id)} className="opacity-50 hover:opacity-100 shrink-0">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Mount in `App.tsx`**

```typescript
import { NavSidebar } from '@/components/NavSidebar'
import { MainPanel } from '@/components/MainPanel'
import { StatusSidebar } from '@/components/StatusSidebar'
import { NotificationToast } from '@/components/NotificationToast'
import { useNervSocket } from '@/hooks/useNervSocket'

export default function App() {
  useNervSocket() // starts WS connection, handles messages

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0a0a]">
      <NavSidebar />
      <MainPanel />
      <StatusSidebar />
      <NotificationToast />
    </div>
  )
}
```

- [ ] **Step 3: Test notifications manually**

Start app, then from a separate terminal:

```bash
curl -X POST http://localhost:5558/message \
  -H "Content-Type: application/json" \
  -d '{"type":"notify","payload":{"message":"hl-intel complete","severity":"success"}}'
```

Expected: Green toast appears in bottom-right of app window.

- [ ] **Step 4: Test navigation**

```bash
curl -X POST http://localhost:5558/message \
  -H "Content-Type: application/json" \
  -d '{"type":"navigate","payload":{"panel":"MCP"}}'
```

Expected: Desktop app switches to MCP panel.

- [ ] **Step 5: Commit**

```bash
git add src/components/NotificationToast.tsx src/App.tsx src/hooks/useNervSocket.ts
git commit -m "feat: mount toast renderer + wire useNervSocket into App"
```

---

### Task 6: Write `nerv-sdk.js`

> This is a standalone Node.js file that any agent (Aeon skill, GitHub Actions runner, OpenClaw) can import to communicate with the desktop app.

**Files:**
- Create: `nerv-sdk/nerv-sdk.js`
- Create: `nerv-sdk/package.json`
- Create: `nerv-sdk/README.md`

- [ ] **Step 1: Create `nerv-sdk/` directory**

```bash
mkdir -p ~/nerv-desktop/nerv-sdk
```

- [ ] **Step 2: Write `nerv-sdk/package.json`**

```json
{
  "name": "nerv-sdk",
  "version": "1.0.0",
  "description": "Client SDK for communicating with NERV Command Center desktop app",
  "main": "nerv-sdk.js",
  "dependencies": {
    "ws": "^8.0.0"
  }
}
```

- [ ] **Step 3: Write `nerv-sdk/nerv-sdk.js`**

```javascript
/**
 * nerv-sdk.js — Communicate with NERV Command Center desktop app
 *
 * Usage:
 *   const { NervClient } = require('./nerv-sdk')
 *   const nerv = new NervClient()
 *   await nerv.notify('hl-intel complete', 'success')
 *   await nerv.navigate('AGENCY')
 */

const http = require('http')

const NERV_PORT = 5558
const REST_ENDPOINT = `http://127.0.0.1:${NERV_PORT}/message`

async function postMessage(msg) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(msg)
    const options = {
      hostname: '127.0.0.1',
      port: NERV_PORT,
      path: '/message',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
      timeout: 2000,
    }

    const req = http.request(options, (res) => {
      let data = ''
      res.on('data', chunk => data += chunk)
      res.on('end', () => {
        try { resolve(JSON.parse(data)) }
        catch { resolve({ ok: true }) }
      })
    })

    req.on('error', (e) => {
      // Silently fail — desktop app may not be running
      resolve({ ok: false, error: e.message })
    })

    req.on('timeout', () => {
      req.destroy()
      resolve({ ok: false, error: 'timeout' })
    })

    req.write(body)
    req.end()
  })
}

class NervClient {
  /**
   * Send a notification toast to the desktop app
   * @param {string} message - The message to display
   * @param {'info'|'success'|'error'} severity - Toast style
   */
  async notify(message, severity = 'info') {
    return postMessage({ type: 'notify', payload: { message, severity } })
  }

  /**
   * Navigate the desktop app to a specific panel
   * @param {'CLI'|'SESSIONS'|'MCP'|'OPENCLAW'|'AEON'|'SUPERPOWERS'|'AGENCY'|'AIGENCY'|'MEMORY'|'CONFIG'} panel
   */
  async navigate(panel) {
    return postMessage({ type: 'navigate', payload: { panel } })
  }

  /**
   * Push data to a panel (for live updates)
   * @param {string} panel - Panel ID
   * @param {object} data - Data to push
   */
  async update(panel, data) {
    return postMessage({ type: 'update', payload: { panel, data } })
  }

  /**
   * Surface a critical alert
   * @param {string} message
   */
  async alert(message) {
    return postMessage({ type: 'alert', payload: { message, severity: 'error' } })
  }
}

module.exports = { NervClient, postMessage }
```

- [ ] **Step 4: Write `nerv-sdk/README.md`**

```markdown
# nerv-sdk

Communicate with NERV Command Center desktop app from any Node.js script.

## Install

```bash
npm install ws
```

Or copy `nerv-sdk.js` directly into your skill directory.

## Usage

```javascript
const { NervClient } = require('./nerv-sdk')
const nerv = new NervClient()

// Show a toast notification
await nerv.notify('hl-intel complete', 'success')

// Navigate to a panel
await nerv.navigate('AGENCY')

// Push data to a panel (for live updates)
await nerv.update('CLI', { output: 'Trade setup found: BTC long at 94200' })

// Show an error alert
await nerv.alert('MCP server qmd disconnected')
```

## Behavior

- If the desktop app is not running, calls silently succeed (no throw)
- Uses plain HTTP POST to `localhost:5558/message` — no WebSocket needed
- Zero dependencies beyond Node.js built-ins + optional `ws` for persistent connections

## Panel IDs

`CLI` · `SESSIONS` · `MCP` · `OPENCLAW` · `AEON` · `SUPERPOWERS` · `AGENCY` · `AIGENCY` · `MEMORY` · `CONFIG`
```

- [ ] **Step 5: Commit**

```bash
cd ~/nerv-desktop
git add nerv-sdk/
git commit -m "feat: add nerv-sdk.js agent communication SDK"
```

---

### Task 7: Wire nerv-sdk into an Aeon Skill (Integration Test)

> This task proves end-to-end agent→app communication works using an existing Aeon skill.

**Files:**
- Modify: `~/aeon/skills/heartbeat/SKILL.md` (add nerv notification at end)

- [ ] **Step 1: Copy nerv-sdk to aeon skills directory**

```bash
cp ~/nerv-desktop/nerv-sdk/nerv-sdk.js ~/aeon/nerv-sdk.js
```

- [ ] **Step 2: Write a test notification script**

Create `~/aeon/test-nerv-notify.js`:

```javascript
const { NervClient } = require('./nerv-sdk')

async function main() {
  const nerv = new NervClient()
  const results = await Promise.all([
    nerv.notify('Heartbeat: all systems nominal', 'success'),
    nerv.navigate('CLI'),
  ])
  console.log('Results:', results)
}

main().catch(console.error)
```

- [ ] **Step 3: Run desktop app + test**

Terminal 1: `cd ~/nerv-desktop/apps/desktop && npm run tauri dev`

Terminal 2:
```bash
cd ~/aeon && node test-nerv-notify.js
```

Expected:
- Green toast: "Heartbeat: all systems nominal"
- Desktop switches to CLI panel

- [ ] **Step 4: Commit test script**

```bash
cd ~/aeon
git add nerv-sdk.js test-nerv-notify.js
git commit -m "feat: add nerv-sdk.js and integration test script"
```

---

### Task 8: Add Token Auth to WS Server

> The current server accepts all connections. Add a simple token check for the REST endpoint.

**Files:**
- Modify: `apps/desktop/src-tauri/src/ws_server.rs`

- [ ] **Step 1: Add auth middleware to REST endpoint**

In `ws_server.rs`, update the `rest_message` handler to check authorization:

```rust
use axum::http::{HeaderMap, StatusCode};

async fn rest_message(
    headers: HeaderMap,
    State(state): State<AppState>,
    Json(msg): Json<NervMessage>,
) -> impl IntoResponse {
    // Check bearer token if NERV_SDK_TOKEN is set (non-empty)
    if !state.token.is_empty() {
        let auth = headers
            .get("authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");
        let expected = format!("Bearer {}", state.token);
        if auth != expected {
            return (StatusCode::UNAUTHORIZED, Json(serde_json::json!({ "error": "unauthorized" }))).into_response();
        }
    }

    broadcast(&state, &msg);
    println!("NERV_WS_MSG:{}", serde_json::to_string(&msg).unwrap_or_default());
    Json(serde_json::json!({ "ok": true })).into_response()
}
```

- [ ] **Step 2: Update `nerv-sdk.js` to send token if set**

In `nerv-sdk.js`, read token from env and add header:

```javascript
const NERV_TOKEN = process.env.NERV_SDK_TOKEN || ''

// In options object, add:
headers: {
  'Content-Type': 'application/json',
  'Content-Length': Buffer.byteLength(body),
  ...(NERV_TOKEN ? { 'Authorization': `Bearer ${NERV_TOKEN}` } : {}),
},
```

- [ ] **Step 3: Test with token env var**

```bash
NERV_SDK_TOKEN="" node ~/aeon/test-nerv-notify.js
```

Expected: Still works (token check skipped when empty).

```bash
NERV_SDK_TOKEN="wrong" node ~/aeon/test-nerv-notify.js
```

Expected: Returns `{ ok: false }` (401 from server, caught silently).

- [ ] **Step 4: Commit**

```bash
cd ~/nerv-desktop
git add apps/desktop/src-tauri/src/ws_server.rs nerv-sdk/nerv-sdk.js
git commit -m "feat: add bearer token auth to WS REST endpoint + sdk"
```

---

### Task 9: Final Integration Test for Plan 3

- [ ] **Step 1: Start all services**

```bash
cd ~/aeon && pm2 start ecosystem.config.cjs
cd ~/nerv-desktop/apps/desktop && npm run tauri dev
```

- [ ] **Step 2: Run full SDK test**

```bash
cd ~/aeon && node test-nerv-notify.js
```

Expected:
- ✅ Green toast: "Heartbeat: all systems nominal"
- ✅ Desktop navigates to CLI panel

- [ ] **Step 3: Test navigate to each panel**

```javascript
// From node REPL
const { NervClient } = require('./nerv-sdk')
const n = new NervClient()
await n.navigate('MCP')     // → MCP panel appears
await n.navigate('OPENCLAW')// → OpenClaw panel appears
await n.alert('test alert') // → red toast appears
```

- [ ] **Step 4: Verify graceful failure when app closed**

Close the desktop app, then:

```bash
node -e "const {NervClient}=require('./nerv-sdk'); new NervClient().notify('test').then(r=>console.log(r))"
```

Expected: `{ ok: false, error: 'connect ECONNREFUSED 127.0.0.1:5558' }` — no throw.

- [ ] **Step 5: Push all**

```bash
cd ~/nerv-desktop && git push
cd ~/aeon && git push
```

---

## What Plans 1–3 Deliver Together

| Feature | Plan |
|---------|------|
| Turborepo monorepo scaffold | 1 |
| Tauri shell + dark 3-column layout | 1 |
| Nav sidebar (10 panels) | 1 |
| Right status bar (MCP + OpenClaw health) | 1 |
| Shared `@nerv/ui` + `@nerv/core` packages | 1 |
| CLI panel (xterm + SSE job stream) | 2 |
| MCP Inspector (server list + tool browser) | 2 |
| OpenClaw Monitor (rate gauges + proxy status) | 2 |
| WebSocket server on :5558 | 3 |
| Toast notifications | 3 |
| Agent-driven navigation | 3 |
| `nerv-sdk.js` (zero-dep agent client) | 3 |

## Remaining Panels (Future Plans)

- Sessions Viewer (Claude Code process list + stdout streaming)
- Aeon Skills browser (dispatch to GitHub Actions)
- Superpowers panel (skill browser)
- Agency/NEXUS panel (mirrored from web dashboard)
- Aigency02 panel (156 agents catalog)
- Memory Browser (search + read memory files)
- Config panel (token management, port config)
