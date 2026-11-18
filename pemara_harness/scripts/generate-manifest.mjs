#!/usr/bin/env node

import { checkManifest, writeManifest } from '../src/manifest.mjs'

if (process.argv.includes('--check')) {
  const result = checkManifest()
  if (result.status !== 'ok') {
    process.stderr.write('MANIFEST_SHA256.csv is stale; run npm run manifest.\n')
    process.exitCode = 1
  }
  else {
    process.stdout.write(`manifest=ok files=${result.detail.files}\n`)
  }
}
else {
  const result = writeManifest()
  process.stdout.write(`manifest=written files=${result.files}\n`)
}
