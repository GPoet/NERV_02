import { NextResponse } from 'next/server'
import { issueToken } from '@/lib/auth'

// No auth required — issues a signed JWT derived from DASHBOARD_SECRET.
// Security relies on DASHBOARD_SECRET strength + short TTL.
// Dashboard is localhost-only so open issuance is acceptable.
export async function POST() {
  const token = issueToken()
  return NextResponse.json({ token })
}
