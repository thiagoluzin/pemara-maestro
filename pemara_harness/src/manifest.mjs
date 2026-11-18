import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname.replace(/^\/(?:([A-Za-z]):)/, '$1:'))
const treeRoots = ['bin', 'docs', 'dsh', 'evidence', 'scripts', 'src', 'test']
const rootFiles = [
  '.gitignore', '.npmignore', 'FIXLOG.md', 'README.md', 'RULES.md', 'SPEC.md',
  'THIRD_PARTY_NOTICES.md', 'package.json',
]
const profileFiles = [
  '.runtime/dsh-home/profiles/pemara/cordis.patch.yml',
  '.runtime/dsh-home/profiles/pemara/cordis.yml',
  '.runtime/dsh-home/profiles/pemara/package.json',
  '.runtime/dsh-home/profiles/pemara/pnpm-workspace.yaml',
  '.runtime/dsh-home-builder/profiles/pemara-builder/cordis.patch.yml',
  '.runtime/dsh-home-builder/profiles/pemara-builder/cordis.yml',
  '.runtime/dsh-home-builder/profiles/pemara-builder/package.json',
  '.runtime/dsh-home-builder/profiles/pemara-builder/pnpm-workspace.yaml',
  '.runtime/dsh-home-builder/profiles/pemara-builder-v2/cordis.patch.yml',
  '.runtime/dsh-home-builder/profiles/pemara-builder-v2/cordis.yml',
  '.runtime/dsh-home-builder/profiles/pemara-builder-v2/package.json',
  '.runtime/dsh-home-builder/profiles/pemara-builder-v2/pnpm-workspace.yaml',
]

function walk(path, output) {
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const target = join(path, entry.name)
    if (entry.isDirectory()) walk(target, output)
    else if (entry.isFile()) output.push(target)
  }
}

function manifestFiles(base = root) {
  const files = rootFiles.map(path => join(base, path))
  if (existsSync(join(base, 'package-lock.json'))) files.push(join(base, 'package-lock.json'))
  for (const directory of treeRoots) walk(join(base, directory), files)
  files.push(...profileFiles.map(path => join(base, path)))
  return files
}

function manifestPathFor(base) {
  return join(base, 'MANIFEST_SHA256.csv')
}

function parseManifest(content) {
  const rows = new Map()
  for (const line of content.split('\n')) {
    const match = line.match(/^"([^"]+)","([0-9a-f]{64})"$/)
    if (match) rows.set(match[1], match[2])
  }
  return rows
}

/** Recompute the expected manifest content for the repository root. */
export function computeManifestContent(base = root) {
  const manifestPath = manifestPathFor(base)
  const rows = manifestFiles(base)
    .filter(path => path !== manifestPath && statSync(path).isFile())
    .map(path => {
      const name = relative(base, path).replaceAll('\\', '/')
      const hash = createHash('sha256').update(readFileSync(path)).digest('hex')
      return { name, hash }
    })
    .sort((left, right) => left.name.localeCompare(right.name, 'en'))
  return { content: `path,sha256\n${rows.map(row => `"${row.name}","${row.hash}"`).join('\n')}\n`, files: rows.length }
}

/**
 * Compare MANIFEST_SHA256.csv against disk without writing anything.
 * Stable codes: MANIFEST_OK | MANIFEST_STALE | MANIFEST_MISSING.
 */
export function checkManifest(base = root) {
  const manifestPath = manifestPathFor(base)
  let current
  try {
    current = readFileSync(manifestPath, 'utf8')
  }
  catch {
    return { status: 'fail', code: 'MANIFEST_MISSING', detail: { path: 'MANIFEST_SHA256.csv' } }
  }
  const expected = computeManifestContent(base).content
  if (current === expected) {
    return { status: 'ok', code: 'MANIFEST_OK', detail: { files: parseManifest(current).size } }
  }
  const currentRows = parseManifest(current)
  const expectedRows = parseManifest(expected)
  let changed = 0
  let missing = 0
  let unexpected = 0
  for (const [name, hash] of expectedRows) {
    if (!currentRows.has(name)) missing += 1
    else if (currentRows.get(name) !== hash) changed += 1
  }
  for (const name of currentRows.keys()) {
    if (!expectedRows.has(name)) unexpected += 1
  }
  return {
    status: 'fail',
    code: 'MANIFEST_STALE',
    detail: { files: expectedRows.size, changed, missing, unexpected },
  }
}

/** Write the manifest; returns the file count. */
export function writeManifest(base = root) {
  const { content, files } = computeManifestContent(base)
  writeFileSync(manifestPathFor(base), content)
  return { files }
}

export { manifestFiles }
