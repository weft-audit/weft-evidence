// DSH 连接层（Codex↔DSH ACP 桥）· 公开脱敏版（2026-10-19）
// 说明：与内部实现同源；所有机器相关路径改为环境变量注入，公开版不含任何本机路径。
// 用法：node bridge.mjs run --task "任务文本" [--cwd DIR] [--permission-mode read-only]
import { spawn } from 'node:child_process'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { Readable, Writable } from 'node:stream'
import {
  ClientSideConnection,
  ndJsonStream,
  PROTOCOL_VERSION,
} from '@zed-industries/agent-client-protocol'

const ROOT = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')
const DSH = process.env.DSH_BIN || '<your-dsh-bin.js 路径>'
const AGENTS = process.env.DSH_AGENTS || '<DSH_HOME>/AGENTS.md'
const DEFAULT_CWD = process.env.JARVIS_WORKSPACE || '<你的工作区绝对路径>'
const ALLOWLIST = ROOT + 'allowlist.json'
const STATE = ROOT + 'bridge-state.json'
const PROTOCOL_LOG = ROOT + 'bridge-protocol.log'
const SUMMARY_LOG = ROOT + 'bridge-summary.log'
const AUDIT_LOG = ROOT + 'bridge-audit.log'

function log(file, kind, text) {
  writeFileSync(file, `${new Date().toISOString()} [${kind}] ${text}\n`,
    { flag: 'a', encoding: 'utf-8' })
}
function audit(t) { log(AUDIT_LOG, 'AUDIT', t) }
function proto(t) { log(PROTOCOL_LOG, 'PROTO', t) }
function summ(t) { log(SUMMARY_LOG, 'SUM', t); console.log('[SUM] ' + t) }

function loadJson(path, fallback) {
  try { return existsSync(path) ? JSON.parse(readFileSync(path, 'utf-8')) : fallback }
  catch { return fallback }
}
function saveJson(path, obj) { writeFileSync(path, JSON.stringify(obj, null, 2), 'utf-8') }

function allowlisted(toolName) {
  const wl = loadJson(ALLOWLIST, { entries: [] })
  return (wl.entries || []).some((e) =>
    e.tool === '*' || String(e.tool).toLowerCase() === String(toolName).toLowerCase())
}

function argOf(name, def) {
  const i = process.argv.indexOf(name)
  return i >= 0 ? process.argv[i + 1] : def
}

function makeClient() {
  const textChunks = []
  return {
    client: () => ({
      sessionUpdate: async (n) => {
        try {
          const txt = JSON.stringify(n && n.update)
          for (const t of txt.match(/"text":"((?:[^"\\]|\\.)*)"/g) || []) {
            try { textChunks.push(JSON.parse('{' + t + '}').text) } catch { /* 容错 */ }
          }
        } catch (e) {
          proto('update 容错吞掉: ' + String(e && e.message).slice(0, 120))
        }
      },
      requestPermission: async (p) => {
        const toolName = p.toolCall && p.toolCall.name
        if (allowlisted(toolName)) {
          const opt = (p.options || []).find((o) => o.kind === 'allow_once') || (p.options || [])[0]
          if (opt) {
            audit(`APPROVED tool=${toolName} option=${opt.optionId} kind=${opt.kind}`)
            return { outcome: { outcome: 'selected', optionId: opt.optionId } }
          }
        }
        audit(`DENIED tool=${toolName} 原因=白名单未含`)
        textChunks.push(`[桥·权限拒绝] tool=${toolName} 处置=已取消；放行请向 allowlist.json 添加条目`)
        return { outcome: { outcome: 'cancelled' } }
      },
    }),
    textChunks,
  }
}

function withTimeout(p, ms, label, onTimeout) {
  let timer
  return Promise.race([
    p.finally(() => clearTimeout(timer)),
    new Promise((_, rej) => {
      timer = setTimeout(() => { if (onTimeout) onTimeout(); rej(new Error('TIMEOUT ' + label)) }, ms)
    }),
  ])
}

async function spawnServer(permissionMode) {
  const env = { ...process.env }
  if (permissionMode) env.DSH_PERMISSION_MODE = permissionMode
  const child = spawn(process.execPath, [DSH, '--profile', 'acp'],
    { stdio: ['pipe', 'pipe', 'pipe'], env })
  let stderr = ''
  child.stderr.on('data', (d) => { stderr += String(d) })
  child.once('exit', (code) => { proto(`server exit code=${code} stderr_tail=${stderr.slice(-200)}`) })
  return { child, stream: ndJsonStream(Writable.toWeb(child.stdin), Readable.toWeb(child.stdout)) }
}

async function main() {
  const cmd = process.argv[2]
  if (cmd === 'state') { console.log(JSON.stringify(loadJson(STATE, {}), null, 2)); return }
  if (cmd !== 'run') { console.error('用法见文件头'); process.exit(2) }
  const taskText = argOf('--task', '')
  const cwd = argOf('--cwd', DEFAULT_CWD)
  const taskId = argOf('--task-id', 'default')
  const promptTimeout = Number(argOf('--prompt-timeout', '300000'))
  const cancelAfter = Number(argOf('--cancel-after-ms', '0'))
  const permissionMode = argOf('--permission-mode', 'read-only')
  if (!taskText) { console.error('缺 --task'); process.exit(2) }
  if (!existsSync(cwd + '/AGENTS.md') && !existsSync(AGENTS)) {
    audit('REFUSED cwd 无纪律锚点')
    console.error('[REFUSED] 纪律锚点缺失，拒绝起会话')
    process.exit(1)
  }
  const state = loadJson(STATE, { fuse: 0, tasks: {} })
  if (state.fuse >= 3) { audit('FUSE_OPEN 熔断中'); console.error('[FUSE_OPEN]'); process.exit(3) }
  const { child, stream } = await spawnServer(permissionMode)
  let exited = false
  child.once('exit', () => { exited = true })
  const kill = (sig) => { try { if (!exited) child.kill(sig) } catch { /* 忽略 */ } }
  const { client, textChunks } = makeClient()
  const conn = new ClientSideConnection(() => client(), stream)
  const t0 = Date.now()
  try {
    await withTimeout(conn.initialize({ protocolVersion: PROTOCOL_VERSION, clientCapabilities: {} }),
      60000, 'initialize', () => {})
    const ns = await withTimeout(conn.newSession({ cwd, mcpServers: [] }), 60000, 'newSession', () => {})
    const sessionId = ns.sessionId
    proto('newSession ok id=' + sessionId)
    state.tasks[taskId] = { sessionId, at: Date.now() }
    saveJson(STATE, state)
    let timer = null
    let cancelAt = 0
    if (cancelAfter > 0) {
      timer = setTimeout(async () => {
        audit(`CANCEL 试验钩子 ${cancelAfter}ms 触发`)
        cancelAt = Date.now()
        await withTimeout(conn.cancel({ sessionId }), 15000, 'cancel', () => {})
      }, cancelAfter)
    }
    const pr = await withTimeout(
      conn.prompt({ sessionId, prompt: [{ type: 'text', text: taskText }] }),
      promptTimeout, 'prompt', () => {})
    if (timer) clearTimeout(timer)
    if (pr.stopReason === 'cancelled' && cancelAt > 0) {
      audit(`CANCEL_OK stopReason=cancelled cancelToStop=${Date.now() - cancelAt}ms`)
    }
    state.tasks[taskId] = { sessionId, at: Date.now(), lastStop: pr.stopReason }
    state.fuse = 0
    saveJson(STATE, state)
    summ(`stopReason=${pr.stopReason} elapsed=${((Date.now() - t0) / 1000).toFixed(1)}s sessionId=${sessionId} 用量=未知`)
    console.log('[REPLY]\n' + textChunks.join('').slice(0, 4000))
  } catch (e) {
    state.fuse = (state.fuse || 0) + 1
    saveJson(STATE, state)
    audit(`FAIL fuse=${state.fuse} err=` + String(e && e.message).slice(0, 200))
    console.error('[BRIDGE-FAIL] ' + (e && e.message))
    process.exitCode = 1
  } finally {
    kill('SIGTERM')
    const exitRes = await Promise.race([
      new Promise((r) => child.once('exit', r)),
      new Promise((r) => setTimeout(() => r('timeout'), 15000)),
    ])
    if (exitRes === 'timeout') { kill('SIGKILL'); audit('ORPHAN SIGKILL 已补刀') }
    else proto('server 已退出')
  }
}

main()
