/**
 * nerv-sdk.js — Communicate with NERV Command Center desktop app
 *
 * Usage:
 *   const { NervClient } = require('./nerv-sdk')
 *   const nerv = new NervClient()
 *   await nerv.notify('hl-intel complete', 'success')
 *   await nerv.navigate('AGENCY')
 */

'use strict'

const http = require('http')

const NERV_PORT = 5558
const NERV_TOKEN = process.env.NERV_SDK_TOKEN || ''

function postMessage(msg) {
  return new Promise((resolve) => {
    const body = JSON.stringify(msg)
    const headers = {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(body),
    }
    if (NERV_TOKEN) {
      headers['Authorization'] = `Bearer ${NERV_TOKEN}`
    }

    const options = {
      hostname: '127.0.0.1',
      port: NERV_PORT,
      path: '/message',
      method: 'POST',
      headers,
      timeout: 2000,
    }

    const req = http.request(options, (res) => {
      let data = ''
      res.on('data', chunk => { data += chunk })
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
  notify(message, severity = 'info') {
    return postMessage({ type: 'notify', payload: { message, severity } })
  }

  /**
   * Navigate the desktop app to a specific panel
   * @param {'CLI'|'SESSIONS'|'MCP'|'OPENCLAW'|'AEON'|'SUPERPOWERS'|'AGENCY'|'AIGENCY'|'MEMORY'|'CONFIG'} panel
   */
  navigate(panel) {
    return postMessage({ type: 'navigate', payload: { panel } })
  }

  /**
   * Push data to a panel (for live updates)
   * @param {string} panel - Panel ID
   * @param {object} data - Data to push
   */
  update(panel, data) {
    return postMessage({ type: 'update', payload: { panel, data } })
  }

  /**
   * Surface a critical alert
   * @param {string} message
   */
  alert(message) {
    return postMessage({ type: 'alert', payload: { message, severity: 'error' } })
  }
}

module.exports = { NervClient, postMessage }
