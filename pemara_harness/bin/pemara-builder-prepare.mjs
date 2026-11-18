#!/usr/bin/env node

import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { prepareBuilderRun } from '../src/builder-preflight.mjs'

function parseArgs(argv) {
  const values = { check: false }
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (arg === '--check') {
      values.check = true
      continue
    }
    if (arg !== '--package' && arg !== '--workspace') {
      throw Object.assign(new Error(`unknown argument: ${arg}`), { code: 'ARGUMENT_INVALID' })
    }
    const value = argv[index + 1]
    if (value === undefined || value.startsWith('--')) {
      throw Object.assign(new Error(`missing value for ${arg}`), { code: 'ARGUMENT_INVALID' })
    }
    values[arg.slice(2)] = value
    index += 1
  }
  if (values.package === undefined || values.workspace === undefined) {
    throw Object.assign(new Error('--package and --workspace are required'), { code: 'ARGUMENT_INVALID' })
  }
  return values
}

try {
  const args = parseArgs(process.argv.slice(2))
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
  const report = prepareBuilderRun({
    projectRoot,
    packagePath: args.package,
    workspace: args.workspace,
    stageSkills: !args.check,
  })
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
}
catch (error) {
  process.stderr.write(`${JSON.stringify({
    status: 'blocked',
    code: error?.code ?? 'BUILDER_PREFLIGHT_FAILED',
    message: error?.message ?? String(error),
    ...(error?.detail === undefined ? {} : { detail: error.detail }),
  }, null, 2)}\n`)
  process.exitCode = 2
}
