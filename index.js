// whitebox-testing — host (cordis) half.
// The plugin is mostly a skill bundle; this entry does two jobs:
//   1. give the bundle a runtime presence so Plugin Manager can activate it;
//   2. serve GET/POST /whitebox/config — the loopback route the sidebar
//      settings card (dsh/client.js) reads and writes whitebox.config.json
//      through. Route shape and trust fence follow @liustack/modlens.
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { spawn } from 'node:child_process'

export const name = 'whitebox-testing'

const ROUTE = '/whitebox/config'
const ROUTE_REFUSAL = 'request refused: this route answers same-origin loopback only'
const CONFIG_NAME = 'whitebox.config.json'
const STATE_PATH = path.join(os.homedir(), '.dsh', 'whitebox-testing.json')
const MAX_BODY = 64 * 1024

function isLoopbackHost (hostname) {
  return hostname === 'localhost' || hostname === '127.0.0.1' ||
    hostname === '::1' || hostname === '[::1]'
}

// Same fence dsh puts in front of its own /api: Host must name a loopback
// authority (a DNS-rebound page carries its own domain there), then
// Sec-Fetch-Site / Origin rule out a cross-site page on this machine.
function isTrustedRequest (req) {
  const host = req.headers?.host
  if (typeof host !== 'string' || host === '') return false
  let hostUrl
  try {
    hostUrl = new URL(`http://${host}`)
  } catch {
    return false
  }
  if (!isLoopbackHost(hostUrl.hostname)) return false
  if (req.headers?.['sec-fetch-site'] === 'cross-site') return false
  const origin = req.headers?.origin
  if (origin === undefined) return true
  try {
    return new URL(origin).host === hostUrl.host
  } catch {
    return false
  }
}

function readState () {
  try {
    return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'))
  } catch {
    return {}
  }
}

function writeState (state) {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true })
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + '\n')
}

function configPathFor (workspace) {
  if (typeof workspace !== 'string' || workspace.trim() === '') {
    throw new Error('workspace is required: a directory holding whitebox.config.json')
  }
  const abs = path.resolve(workspace.trim())
  const st = fs.statSync(abs) // throws ENOENT when the directory is gone
  if (!st.isDirectory()) throw new Error(`not a directory: ${abs}`)
  return path.join(abs, CONFIG_NAME)
}

function readConfigFile (p) {
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'))
  } catch (error) {
    if (error?.code === 'ENOENT') return {}
    throw error
  }
}

function openConfigFile (p) {
  if (!fs.existsSync(p)) fs.writeFileSync(p, '{}\n')
  const cmd = process.platform === 'win32'
    ? ['cmd', ['/c', 'start', '', p]]
    : process.platform === 'darwin'
      ? ['open', [p]]
      : ['xdg-open', [p]]
  const child = spawn(cmd[0], cmd[1], { detached: true, stdio: 'ignore' })
  child.unref()
}

function registerConfigRoute (webServer) {
  webServer.register({
    name: 'whitebox-config',
    kind: 'exact',
    path: ROUTE,
    handler: async (req, res) => {
      const send = (status, body) => {
        res.writeHead(status, { 'content-type': 'application/json' })
        res.end(JSON.stringify(body))
      }
      if (!isTrustedRequest(req)) {
        send(403, { error: ROUTE_REFUSAL })
        return
      }
      try {
        if (req.method === 'GET') {
          const state = readState()
          const workspace = typeof state.workspace === 'string' ? state.workspace : ''
          let config = {}
          let exists = false
          if (workspace !== '') {
            try {
              const p = configPathFor(workspace)
              exists = fs.existsSync(p)
              if (exists) config = readConfigFile(p)
            } catch {
              // stale workspace entry: report empty and let the card re-point
            }
          }
          send(200, { workspace, config, exists })
          return
        }
        if (req.method !== 'POST') {
          res.writeHead(405).end()
          return
        }
        const chunks = []
        let total = 0
        for await (const chunk of req) {
          total += chunk.length
          if (total > MAX_BODY) {
            send(413, { error: 'config payload too large' })
            req.destroy()
            return
          }
          chunks.push(chunk)
        }
        const patch = JSON.parse(Buffer.concat(chunks).toString('utf8')) ?? {}
        const state = readState()
        const workspace = typeof patch.workspace === 'string' && patch.workspace.trim() !== ''
          ? patch.workspace.trim()
          : state.workspace
        const p = configPathFor(workspace)
        if (patch?.open === true) {
          openConfigFile(p)
          send(200, { opened: true })
          return
        }
        if (patch.config !== undefined) {
          if (typeof patch.config !== 'object' || Array.isArray(patch.config)) {
            throw new Error('config must be a JSON object')
          }
          fs.writeFileSync(p, JSON.stringify(patch.config, null, 2) + '\n')
        }
        if (workspace !== state.workspace) writeState({ ...state, workspace })
        send(200, { saved: true, workspace })
      } catch (error) {
        send(400, { error: String(error?.message ?? error) })
      }
    },
  })
}

export function apply (ctx, config = {}) {
  // webServer exists only under the web profile; ride a scoped inject so
  // headless runs stay untouched and the plugin never waits on it.
  if (typeof ctx.inject === 'function') {
    ctx.inject(['webServer'], (scope) => {
      try {
        registerConfigRoute(scope.webServer)
      } catch (error) {
        console.error(`[whitebox-testing] config route skipped: ${error}`)
      }
    })
  }
}

export default { name, apply }
