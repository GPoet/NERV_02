import Anthropic from '@anthropic-ai/sdk'
import { NextResponse } from 'next/server'

const SYSTEM_PROMPT = `You are the NERV_02 AI Command Interface — an autonomous agent orchestration system.

You have access to the following agents that can be dispatched to GitHub Actions:

INTEL:
- morning-brief: Daily morning briefing with news, AI updates, and priorities
- rss-digest: RSS feed digest from curated sources
- hacker-news-digest: Top Hacker News stories
- paper-digest: AI/ML research paper summaries
- tweet-digest: Twitter/X digest

CRYPTO TRADING (Hyperliquid):
- hl-scan: Eagle Eye — scan all Hyperliquid perps for setups (funding extremes, volume spikes, momentum)
- hl-monitor: Radar — monitor open positions, PnL, liquidation risk, funding costs
- hl-trade: Execute a trade on Hyperliquid. Pass instruction as var, e.g. "BUY BTC 0.01" or "CLOSE ETH"
- hl-report: Portfolio report — positions, realized PnL, 7d funding, recent fills
- hl-alpha: The Engine — synthesise alpha from market data + news + on-chain signals into ranked trade ideas

CRYPTO MONITORING:
- token-alert: Crypto token price alerts
- wallet-digest: Crypto wallet summary
- on-chain-monitor: On-chain activity monitoring
- defi-monitor: DeFi protocol monitoring

GITHUB:
- issue-triage: GitHub issue triage and prioritization
- pr-review: Pull request review
- github-monitor: GitHub activity monitoring

BUILD:
- article: Write a long-form article
- digest: Create a digest report
- feature: Build a new feature
- code-health: Code health check
- changelog: Generate changelog
- build-skill: Build a new skill

SYSTEM:
- goal-tracker: Track and review goals
- skill-health: Check skill health
- self-review: Self-review and improvement
- reflect: Reflect on recent activity
- memory-flush: Consolidate memory
- weekly-review: Weekly review (Mondays)
- heartbeat: System heartbeat check

When the user asks you to run, trigger, or dispatch an agent, respond with exactly this on its own line (no extra text around it):
DISPATCH:{"skill":"<skill-name>"}

For hl-trade with a specific instruction, include the var:
DISPATCH:{"skill":"hl-trade","var":"BUY BTC 0.01"}

You understand Hyperliquid deeply: it's a high-performance on-chain perpetuals DEX. hl-scan finds setups, hl-alpha generates trade ideas with full intel synthesis, hl-trade executes them, hl-monitor watches risk, hl-report summarises performance.

Otherwise respond conversationally. Be concise, direct, and use a slightly military/technical tone that fits the NERV aesthetic. No fluff.`

type ChatMessage = { role: 'user' | 'assistant'; content: string }

export async function POST(request: Request) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      { error: 'ANTHROPIC_API_KEY is not configured.' },
      { status: 503 },
    )
  }

  let messages: ChatMessage[]
  try {
    const body = await request.json()
    if (!Array.isArray(body.messages)) {
      return NextResponse.json({ error: 'messages must be an array' }, { status: 400 })
    }
    messages = body.messages as ChatMessage[]
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
  }

  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

  // Convert to Anthropic message format
  const anthropicMessages = messages.map(m => ({
    role: m.role as 'user' | 'assistant',
    content: typeof m.content === 'string' ? m.content : String(m.content),
  }))

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const response = await client.messages.stream({
          model: 'claude-haiku-4-5',
          max_tokens: 1024,
          system: SYSTEM_PROMPT,
          messages: anthropicMessages,
        })

        for await (const chunk of response) {
          if (
            chunk.type === 'content_block_delta' &&
            chunk.delta.type === 'text_delta'
          ) {
            controller.enqueue(encoder.encode(chunk.delta.text))
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Stream error'
        controller.enqueue(encoder.encode(`\n[ERROR: ${msg}]`))
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Transfer-Encoding': 'chunked',
      'Cache-Control': 'no-cache',
    },
  })
}
