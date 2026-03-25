import { NextRequest, NextResponse } from 'next/server'
import { issueToken } from '@/lib/auth'

export async function POST(req: NextRequest) {
  const password = process.env.DASHBOARD_PASSWORD
  if (!password) {
    return NextResponse.json({ error: 'Server misconfigured: DASHBOARD_PASSWORD not set' }, { status: 503 })
  }

  let body: { password?: string } = {}
  try { body = await req.json() } catch { /* no body */ }

  if (!body.password || body.password !== password) {
    return NextResponse.json({ error: 'Invalid password' }, { status: 401 })
  }

  const token = issueToken()
  return NextResponse.json({ token })
}
