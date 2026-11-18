#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

import { prepareMediaContext } from '../src/media-context.mjs'

function argumentsMap(argv) {
  const values = {}
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index]
    const value = argv[index + 1]
    if (!key?.startsWith('--') || value === undefined) throw new Error(`Argumento inválido: ${key ?? ''}`)
    values[key.slice(2)] = value
  }
  for (const key of ['manifest', 'task-file', 'output', 'python', 'processor', 'bridge', 'whisper-model', 'qwen-url', 'qwen-model']) {
    if (!values[key]) throw new Error(`Argumento obrigatório ausente: --${key}`)
  }
  return values
}

function runProcessor(values, { attachment, path }) {
  return new Promise((resolveResult, reject) => {
    const child = spawn(resolve(values.python), [
      resolve(values.processor),
      '--bridge', resolve(values.bridge),
      '--whisper-model', resolve(values['whisper-model']),
      '--kind', attachment.kind,
      '--input', path,
      '--task-file', resolve(values['task-file']),
      '--qwen-url', values['qwen-url'],
      '--qwen-model', values['qwen-model'],
    ], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    let stdout = ''
    let stderr = ''
    const append = (current, chunk) => {
      if (Buffer.byteLength(current) + chunk.byteLength > 600 * 1024) {
        child.kill()
        reject(new Error('Processador excedeu o limite de saída.'))
        return current
      }
      return current + chunk.toString('utf8')
    }
    child.stdout.on('data', chunk => { stdout = append(stdout, chunk) })
    child.stderr.on('data', chunk => { stderr = append(stderr, chunk) })
    child.once('error', reject)
    child.once('close', code => {
      let parsed
      try { parsed = JSON.parse(stdout.trim()) }
      catch { return reject(new Error(`Processador retornou JSON inválido. ${stderr.slice(0, 1000)}`)) }
      if (code !== 0 || parsed?.ok !== true) return reject(new Error(parsed?.error ?? `Processador encerrou com código ${code}`))
      resolveResult(parsed)
    })
  })
}

async function main() {
  const values = argumentsMap(process.argv.slice(2))
  const result = await prepareMediaContext({
    manifestPath: values.manifest,
    taskPath: values['task-file'],
    outputPath: values.output,
    processAttachment: input => runProcessor(values, input),
  })
  process.stdout.write(`${JSON.stringify(result)}\n`)
}

main().catch(error => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`)
  process.exitCode = 1
})
