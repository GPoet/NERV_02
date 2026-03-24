// OpenClaw Proxy Sidecar — Express :5557
// Bridges HTTP POST /dispatch → persistent WebSocket connection to OpenClaw (:18789)
// Auth: Bearer OPENCLAW_PROXY_SECRET on all POST requests

const express = require('express')
const { WebSocket } = require('ws')

const PORT = parseInt(process.env.PORT || '5557', 10)
const WS_URL = process.env.OPENCLAW_WS_URL || 'ws://127.0.0.1:18789'
const SECRET = process.env.OPENCLAW_PROXY_SECRET || ''

const app = express()
app.use(express.json())

// --- Persistent WebSocket connection to OpenClaw ---

let ws = null
let pendingRequests = new Map() // id → { resolve, reject, timer }
let requestCounter = 0
let reconnectTimer = null

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  clearTimeout(reconnectTimer)

  console.log(`[openclaw-proxy] Connecting to ${WS_URL}`)
  ws = new WebSocket(WS_URL)

  ws.on('open', () => {
    console.log('[openclaw-proxy] Connected to OpenClaw')
  })

  ws.on('message', (data) => {
    let msg
    try { msg = JSON.parse(data.toString()) } catch { return }
    const pending = pendingRequests.get(msg.id)
    if (!pending) return
    clearTimeout(pending.timer)
    pendingRequests.delete(msg.id)
    if (msg.error) {
      pending.reject(new Error(msg.error))
    } else {
      pending.resolve(msg.result || msg.output || '')
    }
  })

  ws.on('close', () => {
    console.log('[openclaw-proxy] Disconnected — reconnecting in 3s')
    // Reject all pending requests
    for (const [id, pending] of pendingRequests) {
      clearTimeout(pending.timer)
      pending.reject(new Error('WebSocket disconnected'))
      pendingRequests.delete(id)
    }
    reconnectTimer = setTimeout(connect, 3000)
  })

  ws.on('error', (err) => {
    console.error('[openclaw-proxy] WS error:', err.message)
  })
}

connect()

// --- Auth middleware ---

function authMiddleware(req, res, next) {
  if (!SECRET) return next() // no secret configured — skip auth (dev mode)
  const auth = req.headers['authorization'] || ''
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : ''
  if (token !== SECRET) {
    return res.status(401).json({ error: 'Unauthorized' })
  }
  next()
}

// --- POST /dispatch ---

app.post('/dispatch', authMiddleware, async (req, res) => {
  const { agent, prompt } = req.body || {}
  if (!agent || !prompt) {
    return res.status(400).json({ error: 'Missing agent or prompt' })
  }

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return res.status(503).json({ error: 'OpenClaw not connected' })
  }

  const id = ++requestCounter
  const message = JSON.stringify({ id, agent, prompt })

  try {
    const result = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pendingRequests.delete(id)
        reject(new Error('Request timeout (30s)'))
      }, 30_000)
      pendingRequests.set(id, { resolve, reject, timer })
      ws.send(message)
    })
    return res.json({ ok: true, result })
  } catch (err) {
    return res.status(500).json({ error: err.message })
  }
})

// --- GET /health ---

app.get('/health', (req, res) => {
  res.json({
    ok: true,
    ws: ws ? ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState] : 'none',
    pending: pendingRequests.size,
  })
})

app.listen(PORT, () => {
  console.log(`[openclaw-proxy] Listening on :${PORT}`)
})
