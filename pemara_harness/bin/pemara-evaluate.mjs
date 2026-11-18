#!/usr/bin/env node
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { freezeEvaluation, compareEvaluation } from '../src/fixed-evaluation.mjs'

const defaultRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const [command, ...args] = process.argv.slice(2)
const options = {}
for (let index = 0; index < args.length; index += 2) {
  if (!['--root', '--output', '--contract', '--sha'].includes(args[index]) || !args[index + 1]) throw new Error('Invalid option')
  options[args[index].slice(2)] = args[index + 1]
}
try {
  if (command === 'freeze' && options.output) {
    console.log(JSON.stringify(await freezeEvaluation({ root: options.root ?? defaultRoot, output: options.output }), null, 2))
  } else if (command === 'compare' && options.contract && options.sha) {
    const result = await compareEvaluation({ root: options.root ?? defaultRoot, contractPath: options.contract, expectedSha: options.sha })
    console.log(JSON.stringify({ status: result.status, accepted: false, sameSource: result.sameSource,
      baseline: result.baseline, candidate: result.candidate.summary, receiptPath: result.receiptPath }, null, 2))
    if (['REGRESSION', 'INVALID_EVIDENCE'].includes(result.status)) process.exitCode = 1
  } else {
    throw new Error('Usage: freeze --output <new-dir> [--root <repo>] | compare --contract <contract.json> --sha <sha256> [--root <candidate>]')
  }
} catch (error) {
  console.error(error.message)
  process.exitCode = 1
}
