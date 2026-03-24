/**
 * test-nerv-notify.js — Integration test for nerv-sdk → NERV Desktop app
 *
 * Run: node test-nerv-notify.js
 * Expected: green toast + desktop navigates to CLI panel
 */

const { NervClient } = require('./nerv-sdk')

async function main() {
  const nerv = new NervClient()

  console.log('Sending test notifications to NERV Desktop...')

  const results = await Promise.all([
    nerv.notify('Heartbeat: all systems nominal', 'success'),
    nerv.navigate('CLI'),
  ])

  console.log('Results:', results)

  if (results.every(r => r.ok)) {
    console.log('✓ Desktop app responded successfully')
  } else {
    console.log('✗ Desktop app not running or token mismatch — this is expected if app is closed')
  }
}

main().catch(console.error)
