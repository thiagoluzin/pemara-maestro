import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { basename, join, resolve } from 'node:path'

function parseArguments(argv) {
  const options = {
    url: 'http://127.0.0.1:3080',
    edge: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    output: resolve(import.meta.dirname, '..', 'evidence'),
  }
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--url') options.url = argv[++index]
    else if (argument === '--edge') options.edge = argv[++index]
    else if (argument === '--output') options.output = resolve(argv[++index])
    else throw new Error(`unknown argument: ${argument}`)
  }
  const parsedUrl = new URL(options.url)
  if (parsedUrl.hostname !== '127.0.0.1' && parsedUrl.hostname !== 'localhost') {
    throw new Error('browser verification accepts only a loopback URL')
  }
  return options
}

function delay(milliseconds) {
  return new Promise(resolveDelay => setTimeout(resolveDelay, milliseconds))
}

async function waitForDevToolsPort(profile, child) {
  const activePortPath = join(profile, 'DevToolsActivePort')
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (child.exitCode !== null) throw new Error(`Edge exited before DevTools was ready: ${child.exitCode}`)
    try {
      const [port] = (await readFile(activePortPath, 'utf8')).trim().split(/\r?\n/u)
      if (/^\d+$/u.test(port)) return Number(port)
    }
    catch {}
    await delay(100)
  }
  throw new Error('DevTools endpoint did not become ready')
}

class CdpClient {
  constructor(url) {
    this.socket = new WebSocket(url)
    this.nextId = 1
    this.pending = new Map()
    this.listeners = new Map()
  }

  async open() {
    await new Promise((resolveOpen, reject) => {
      this.socket.addEventListener('open', resolveOpen, { once: true })
      this.socket.addEventListener('error', reject, { once: true })
    })
    this.socket.addEventListener('message', event => {
      const message = JSON.parse(String(event.data))
      if (message.id !== undefined) {
        const request = this.pending.get(message.id)
        if (request === undefined) return
        this.pending.delete(message.id)
        if (message.error !== undefined) request.reject(new Error(message.error.message))
        else request.resolve(message.result)
        return
      }
      const listeners = this.listeners.get(message.method) ?? []
      for (const listener of listeners) listener(message.params)
    })
  }

  send(method, params = {}) {
    const id = this.nextId++
    return new Promise((resolveSend, reject) => {
      this.pending.set(id, { resolve: resolveSend, reject })
      this.socket.send(JSON.stringify({ id, method, params }))
    })
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? []
    listeners.push(listener)
    this.listeners.set(method, listeners)
  }

  once(method, timeoutMs = 10000) {
    return new Promise((resolveEvent, reject) => {
      const listeners = this.listeners.get(method) ?? []
      const timeout = setTimeout(() => {
        const index = listeners.indexOf(handler)
        if (index >= 0) listeners.splice(index, 1)
        reject(new Error(`timed out waiting for ${method}`))
      }, timeoutMs)
      const handler = params => {
        clearTimeout(timeout)
        const index = listeners.indexOf(handler)
        if (index >= 0) listeners.splice(index, 1)
        resolveEvent(params)
      }
      listeners.push(handler)
      this.listeners.set(method, listeners)
    })
  }

  close() {
    this.socket.close()
  }
}

async function inspectViewport(client, url, outputPath, viewport) {
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: viewport.mobile,
    screenWidth: viewport.width,
    screenHeight: viewport.height,
  })
  const loaded = client.once('Page.loadEventFired')
  await client.send('Page.navigate', { url })
  await loaded
  await delay(2500)

  const evaluation = await client.send('Runtime.evaluate', {
    expression: `(() => ({
      title: document.title,
      heading: document.querySelector('#page-title')?.textContent?.trim(),
      runTitle: document.querySelector('#run-title')?.textContent?.trim(),
      activityTitle: document.querySelector('#activity-title')?.textContent?.trim(),
      sessionState: document.querySelector('#session-state')?.textContent?.trim(),
      sessionCount: document.querySelectorAll('.session-button').length,
      activityCount: document.querySelectorAll('.activity-row').length,
      healthStates: [...document.querySelectorAll('.health-card')].map(node => node.dataset.state),
      composerCount: document.querySelectorAll('#task-form').length,
      taskButtonEnabled: !document.querySelector('#run-task')?.disabled,
      technicalDetailsOpen: document.querySelector('#technical-details')?.open,
      viewportWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      bodyOverflowX: getComputedStyle(document.body).overflowX,
    }))()`,
    returnByValue: true,
  })
  const screenshot = await client.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
    captureBeyondViewport: false,
  })
  await writeFile(outputPath, Buffer.from(screenshot.data, 'base64'))
  return { ...evaluation.result.value, screenshot: basename(outputPath) }
}

async function main() {
  const options = parseArguments(process.argv.slice(2))
  const profile = await mkdtemp(join(tmpdir(), 'pemara-monitor-edge-'))
  const child = spawn(options.edge, [
    '--headless=new',
    '--disable-gpu',
    '--disable-background-networking',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-extensions',
    '--no-first-run',
    '--no-default-browser-check',
    '--remote-debugging-port=0',
    `--user-data-dir=${profile}`,
    'about:blank',
  ], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] })

  let stderr = ''
  child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk })
  let client
  try {
    const port = await waitForDevToolsPort(profile, child)
    const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json())
    const page = targets.find(target => target.type === 'page')
    if (page === undefined) throw new Error('Edge did not expose a page target')

    client = new CdpClient(page.webSocketDebuggerUrl)
    await client.open()
    const findings = { console: [], exceptions: [], failedRequests: [], badResponses: [] }
    client.on('Runtime.consoleAPICalled', event => {
      if (event.type === 'error' || event.type === 'warning') findings.console.push(event.type)
    })
    client.on('Runtime.exceptionThrown', event => findings.exceptions.push(event.exceptionDetails.text))
    client.on('Network.loadingFailed', event => findings.failedRequests.push(event.errorText))
    client.on('Network.responseReceived', event => {
      if (event.response.status >= 400) findings.badResponses.push({ url: event.response.url, status: event.response.status })
    })
    await Promise.all([
      client.send('Page.enable'),
      client.send('Runtime.enable'),
      client.send('Network.enable'),
      client.send('Accessibility.enable'),
    ])

    const desktop = await inspectViewport(
      client,
      options.url,
      join(options.output, 'monitor-ui-desktop.png'),
      { width: 1440, height: 900, mobile: false },
    )
    const mobile = await inspectViewport(
      client,
      options.url,
      join(options.output, 'monitor-ui-mobile.png'),
      { width: 390, height: 844, mobile: true },
    )
    const accessibility = await client.send('Accessibility.getFullAXTree')
    const namedButtons = accessibility.nodes
      .filter(node => node.role?.value === 'button')
      .map(node => node.name?.value)
      .filter(Boolean)

    const report = {
      verifiedAt: new Date().toISOString(),
      url: options.url,
      browser: await client.send('Browser.getVersion'),
      desktop,
      mobile,
      accessibility: { namedButtons, unnamedButtons: accessibility.nodes.filter(node => node.role?.value === 'button' && !node.name?.value).length },
      findings,
    }
    await writeFile(join(options.output, 'monitor-browser-verification.json'), `${JSON.stringify(report, null, 2)}\n`)
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
    await client.send('Browser.close')
  }
  finally {
    client?.close()
    if (child.exitCode === null) {
      const exited = new Promise(resolveExit => child.once('exit', resolveExit))
      child.kill()
      await Promise.race([exited, delay(5000)])
    }
    await rm(profile, { recursive: true, force: true })
    if (child.exitCode !== 0 && child.exitCode !== null && stderr.trim() !== '') {
      process.stderr.write(stderr.slice(-4000))
    }
  }
}

main().catch(error => {
  console.error(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
})
