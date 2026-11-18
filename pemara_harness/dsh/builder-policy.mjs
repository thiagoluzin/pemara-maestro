import { randomUUID } from 'node:crypto'
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  rmSync,
} from 'node:fs'
import { isAbsolute, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  EXPECTED_BUILDER_TOOLS,
  SKILL_COUNT_MAX,
  SKILL_COUNT_MIN,
  checkToolSurface,
} from '../src/builder-contract.mjs'
import {
  EXPECTED_BUILDER_TOOLS_V2,
  checkBuilderV2ToolSurface,
} from '../src/builder-contract-v2.mjs'

export const name = 'pemara-builder-policy'
export const inject = ['tools', 'systemPrompt']

export const BUILDER_DSH_HOME_REL = join('.runtime', 'dsh-home-builder')
export const BUILDER_PROFILE_NAME = 'pemara-builder'
export const BUILDER_LEDGER_REL = 'pemara-builder/ledger.sqlite'
export const BUILDER_V2_PROFILE_NAME = 'pemara-builder-v2'
export const BUILDER_V2_LEDGER_REL = 'pemara-builder-v2/ledger.sqlite'
export const OPERATIONAL_LEDGER_REL = 'pemara/ledger.sqlite'
export const BUILDER_SKILL = 'qwen3.8-27b-uncensored-yarn-524k'
export const BUILDER_SKILL_BYTES_MAX = 128 * 1024

export const BUILDER_PROFILE_FILES = Object.freeze([
  'cordis.yml',
  'cordis.patch.yml',
  'package.json',
  'pnpm-workspace.yaml',
])

const PROFILE_INSTALL_ARTIFACTS = new Set(['node_modules', 'pnpm-lock.yaml'])
const SKILL_NAME_PATTERN = /^[a-z0-9][a-z0-9._-]{0,127}$/

export class BuilderPolicyError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'BuilderPolicyError'
    this.code = code
  }
}

function asPath(value) {
  return value instanceof URL ? fileURLToPath(value) : value
}

function isContained(root, target) {
  const rel = relative(root, target)
  return rel === '' || (!isAbsolute(rel) && rel !== '..' && !rel.startsWith(`..\\`) && !rel.startsWith('../'))
}

function validateSkillNames(skills) {
  if (!Array.isArray(skills) || skills.length < SKILL_COUNT_MIN || skills.length > SKILL_COUNT_MAX) {
    throw new BuilderPolicyError(
      'SKILLS_OUT_OF_RANGE',
      `skills must contain ${SKILL_COUNT_MIN} to ${SKILL_COUNT_MAX} names`,
    )
  }

  const seen = new Set()
  for (const name of skills) {
    if (typeof name !== 'string' || !SKILL_NAME_PATTERN.test(name) || name === '.' || name === '..') {
      throw new BuilderPolicyError('INVALID_SKILL_NAME', `invalid skill name: ${String(name)}`)
    }
    const key = name.toLowerCase()
    if (seen.has(key)) {
      throw new BuilderPolicyError('DUPLICATE_SKILLS', `duplicate skill name: ${name}`)
    }
    seen.add(key)
  }
  return [...skills]
}

function assertRegularSkillTree(path) {
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const child = join(path, entry.name)
    if (entry.isSymbolicLink()) {
      throw new BuilderPolicyError('SKILL_LINK_REJECTED', `skill tree contains a link: ${child}`)
    }
    if (entry.isDirectory()) assertRegularSkillTree(child)
    else if (!entry.isFile()) {
      throw new BuilderPolicyError('SKILL_ENTRY_REJECTED', `skill tree contains a non-file entry: ${child}`)
    }
  }
}

function resolveSkillSources(skills, sourceRoots) {
  if (!Array.isArray(sourceRoots) || sourceRoots.length === 0) {
    throw new BuilderPolicyError('SKILL_SOURCES_MISSING', 'at least one skill source root is required')
  }

  const roots = sourceRoots
    .map(asPath)
    .filter(root => existsSync(root))
    .map(root => realpathSync(root))
  const resolved = []
  const missing = []

  for (const skill of skills) {
    let source
    for (const root of roots) {
      const candidate = join(root, skill)
      if (!existsSync(candidate) || !existsSync(join(candidate, 'SKILL.md'))) continue
      const real = realpathSync(candidate)
      if (!isContained(root, real)) {
        throw new BuilderPolicyError('SKILL_SOURCE_ESCAPE', `skill escapes its source root: ${skill}`)
      }
      assertRegularSkillTree(real)
      source = real
      break
    }
    if (source === undefined) missing.push(skill)
    else resolved.push({ name: skill, source })
  }
  return { resolved, missing }
}

/**
 * Atomically replace <home>/skills with exactly the host-approved skill pack.
 * Missing sources fail before mutation; temporary and backup trees stay on the
 * same volume so the final rename is atomic on Windows.
 */
export function stageBuilderSkills({ homeDir, skills, sourceRoots }) {
  const selected = validateSkillNames(skills)
  const { resolved, missing } = resolveSkillSources(selected, sourceRoots)
  if (missing.length > 0) return { ok: false, staged: [], missing }

  const home = resolve(asPath(homeDir))
  mkdirSync(home, { recursive: true })
  const suffix = `${process.pid}-${randomUUID()}`
  const destination = join(home, 'skills')
  const staging = join(home, `.skills-stage-${suffix}`)
  const backup = join(home, `.skills-backup-${suffix}`)
  let movedOld = false

  try {
    mkdirSync(staging)
    for (const { name: skillName, source } of resolved) {
      cpSync(source, join(staging, skillName), { recursive: true, force: false })
    }
    if (existsSync(destination)) {
      renameSync(destination, backup)
      movedOld = true
    }
    renameSync(staging, destination)
    if (movedOld) rmSync(backup, { recursive: true, force: true })
  }
  catch (error) {
    rmSync(staging, { recursive: true, force: true })
    if (movedOld && !existsSync(destination) && existsSync(backup)) {
      renameSync(backup, destination)
    }
    throw error
  }

  return { ok: true, staged: selected, missing: [] }
}

function skillDescription(content, fallback) {
  const frontmatter = content.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)
  const line = frontmatter?.[1].match(/^description:\s*(.+)$/m)?.[1]?.trim()
  if (line === undefined || line === '') return fallback
  return line.replace(/^(['"])(.*)\1$/, '$2')
}

/** Build the exact, deterministic skill catalog and bodies embedded in Builder requests. */
export function buildStagedSkillSection(skillsDir, {
  maxBytes = BUILDER_SKILL_BYTES_MAX,
  contractVersion = 1,
} = {}) {
  const root = resolve(asPath(skillsDir))
  if (!existsSync(root)) {
    throw new BuilderPolicyError('STAGED_SKILLS_MISSING', `staged skills directory does not exist: ${root}`)
  }

  const entries = readdirSync(root, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name, 'en'))
  const names = entries.map(entry => entry.name)
  validateSkillNames(names)

  const records = entries.map((entry) => {
    if (!entry.isDirectory() || entry.isSymbolicLink()) {
      throw new BuilderPolicyError('STAGED_SKILL_INVALID', `unexpected staged skill entry: ${entry.name}`)
    }
    const skillFile = join(root, entry.name, 'SKILL.md')
    if (!existsSync(skillFile)) {
      throw new BuilderPolicyError('STAGED_SKILL_INVALID', `missing SKILL.md for staged skill: ${entry.name}`)
    }
    assertRegularSkillTree(join(root, entry.name))
    const content = readFileSync(skillFile, 'utf8')
    return { name: entry.name, description: skillDescription(content, entry.name), content }
  })

  const catalog = records.map(record => `- \`${record.name}\`: ${record.description}`).join('\n')
  const bodies = records
    .map(record => `<skill name="${record.name}">\n${record.content.trimEnd()}\n</skill>`)
    .join('\n\n')
  const authorityText = contractVersion === 2
    ? 'The eight tools are the complete runtime surface. Use builder_file_read and builder_file_write only '
      + 'for exact contract paths, and builder_test_run only with a host-defined command id. You cannot use '
      + 'raw shell or Git, commit, publish, control services, use the GPU, or access the network.'
    : 'The five durable ledger tools are the complete runtime tool surface. Produce candidate content only; '
      + 'you cannot edit, execute, commit, publish, control services, use the GPU, or access the network.'
  const text = [
    'Pemara Builder is fail-closed. Only the host-selected skills below apply to this run.',
    '<available_skills>',
    catalog,
    '</available_skills>',
    '<builder_skill_instructions>',
    bodies,
    '</builder_skill_instructions>',
    authorityText,
  ].join('\n')
  const bytes = Buffer.byteLength(text)
  if (bytes > maxBytes) {
    throw new BuilderPolicyError('SKILL_PACK_TOO_LARGE', `staged skill pack is ${bytes} bytes; maximum is ${maxBytes}`)
  }
  return { names, text, bytes }
}

function issue(code, message) {
  return { code, message }
}

/** Validate the complete on-disk Builder profile without mutating it. */
export function validateBuilderProfile(profileDir, {
  profileName = BUILDER_PROFILE_NAME,
  ledgerRel = BUILDER_LEDGER_REL,
  contractVersion = 1,
} = {}) {
  const root = asPath(profileDir)
  const issues = []

  for (const file of BUILDER_PROFILE_FILES) {
    if (!existsSync(join(root, file))) issues.push(issue('PROFILE_FILE_MISSING', `missing profile file ${file}`))
  }
  if (!existsSync(root)) return { ok: false, issues }

  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (!BUILDER_PROFILE_FILES.includes(entry.name) && !PROFILE_INSTALL_ARTIFACTS.has(entry.name)) {
      issues.push(issue('PROFILE_UNEXPECTED_ENTRY', `unexpected profile entry ${entry.name}`))
    }
  }

  const patchPath = join(root, 'cordis.patch.yml')
  if (existsSync(patchPath)) {
    const patch = readFileSync(patchPath, 'utf8')
    if (!patch.includes(`model: ${BUILDER_SKILL}`)) {
      issues.push(issue('PROFILE_MODEL_MISMATCH', `profile must select ${BUILDER_SKILL}`))
    }
    if (!patch.includes('baseURL: http://127.0.0.1:11436/v1')) {
      issues.push(issue('PROFILE_ROUTE_NOT_LOOPBACK', 'builder profile must use the fixed loopback llama-server route'))
    }
    const urls = [...patch.matchAll(/https?:\/\/[^\s'"\]]+/g)].map(match => match[0])
    if (urls.some(url => url !== 'http://127.0.0.1:11436/v1')) {
      issues.push(issue('PROFILE_REMOTE_ROUTE', 'builder profile contains a non-approved URL'))
    }
    if (patch.includes(`dshHomePath('${OPERATIONAL_LEDGER_REL}')`)) {
      issues.push(issue('PROFILE_LEDGER_NOT_DEDICATED', 'builder profile must not use the operational ledger'))
    }
    if (!patch.includes(`dshHomePath('${ledgerRel}')`)) {
      issues.push(issue('PROFILE_LEDGER_MISSING', `builder profile must use ${ledgerRel}`))
    }
    if (!patch.includes("name: '@pemara/harness/dsh-builder-policy'")) {
      issues.push(issue('PROFILE_POLICY_MISSING', 'builder runtime policy plugin is not composed'))
    }
    for (const field of ['rebindTaskId', 'rebindAttemptId', 'rebindAuthority']) {
      if (!patch.includes(`${field}:`)) {
        issues.push(issue('PROFILE_REBIND_CONFIG_MISSING', `builder profile must configure ${field}`))
      }
    }
    if (contractVersion === 2) {
      for (const field of ['builderPackagePath', 'builderWorkspace', 'builderContractVersion']) {
        if (!patch.includes(`${field}:`)) {
          issues.push(issue('PROFILE_V2_CONFIG_MISSING', `builder v2 profile must configure ${field}`))
        }
      }
    }
  }

  const cordisPath = join(root, 'cordis.yml')
  if (existsSync(cordisPath)) {
    const rootRows = readFileSync(cordisPath, 'utf8')
      .split(/\r?\n/)
      .filter(line => !line.trimStart().startsWith('#'))
      .join('\n')
      .trim()
    if (rootRows !== '[]') {
      issues.push(issue('PROFILE_ROOT_NOT_EMPTY', 'cordis.yml must remain an empty profile root'))
    }
  }

  const workspacePath = join(root, 'pnpm-workspace.yaml')
  if (existsSync(workspacePath)) {
    const workspace = readFileSync(workspacePath, 'utf8')
    if (!/packages:\s*\r?\n\s*- \./.test(workspace)
      || !/nodeLinker:\s*hoisted/.test(workspace)
      || !/autoInstallPeers:\s*false/.test(workspace)) {
      issues.push(issue('PROFILE_WORKSPACE_INVALID', 'pnpm workspace policy is incomplete'))
    }
  }

  const packagePath = join(root, 'package.json')
  if (existsSync(packagePath)) {
    let pkg
    try {
      pkg = JSON.parse(readFileSync(packagePath, 'utf8'))
    }
    catch {
      issues.push(issue('PROFILE_PACKAGE_INVALID', 'package.json is not valid JSON'))
    }
    if (pkg !== undefined) {
      if (pkg.name !== `dsh-profile-${profileName}`) {
        issues.push(issue('PROFILE_PACKAGE_NAME', `package name must be dsh-profile-${profileName}`))
      }
      const dependencies = Object.keys(pkg.dependencies ?? {})
      if (dependencies.length !== 1 || dependencies[0] !== '@pemara/harness'
        || !pkg.dependencies['@pemara/harness'].startsWith('link:')) {
        issues.push(issue('PROFILE_DEPENDENCIES', 'profile must link only the local @pemara/harness package'))
      }
      const bundles = pkg.dsh?.profile?.bundles ?? []
      if (JSON.stringify(bundles) !== JSON.stringify(['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-headless'])) {
        issues.push(issue('PROFILE_BUNDLES', 'profile must compose only dsh-base and dsh-headless'))
      }
    }
  }

  return { ok: issues.length === 0, issues }
}

/** Validate the model-facing request as a closed five-tool, selected-skill surface. */
export function validateBuilderRequest({ tools, skills, contractVersion = 1 }) {
  const issues = []
  if (!Array.isArray(tools)) {
    issues.push(issue('TOOL_SURFACE', 'tools must be an array'))
  }
  else {
    const violations = contractVersion === 2
      ? checkBuilderV2ToolSurface(tools)
      : checkToolSurface(tools)
    for (const violation of violations) {
      issues.push({ code: 'TOOL_SURFACE', ...violation })
    }
  }
  try {
    validateSkillNames(skills)
  }
  catch (error) {
    issues.push(issue(error?.code ?? 'INVALID_SKILLS', error?.message ?? String(error)))
  }
  return { ok: issues.length === 0, issues }
}

/**
 * Runtime authority boundary for the isolated Builder profile. Restriction
 * removes inherited DSH tools from the request; the global monotonic guard
 * independently denies any hidden or late-registered tool at dispatch time.
 */
export function installBuilderRuntimePolicy(ctx, {
  skillSectionText,
  allowedTools = EXPECTED_BUILDER_TOOLS,
} = {}) {
  const allowed = new Set(allowedTools)
  const restrictions = new Set()
  const guardDispose = ctx.tools.guard(execution => allowed.has(execution.name)
    ? undefined
    : `Tool "${execution.name}" denied by Pemara Builder policy.`)
  const promptDispose = ctx.systemPrompt.section({
    name: 'pemara:builder-policy',
    order: 114,
    text: skillSectionText,
  })
  const listenerDispose = ctx.on('agent/created', ({ agent }) => {
    let active = true
    const lift = agent.ctx.tools.restrict({ allow: [...allowedTools] })
    const dispose = () => {
      if (!active) return
      active = false
      restrictions.delete(dispose)
      lift()
    }
    restrictions.add(dispose)
  })

  return () => {
    listenerDispose?.()
    for (const dispose of [...restrictions]) dispose()
    promptDispose?.()
    guardDispose?.()
  }
}

export function apply(ctx, config = {}) {
  const home = process.env.DSH_HOME
  if (typeof home !== 'string' || home.trim() === '') {
    throw new BuilderPolicyError('DSH_HOME_REQUIRED', 'DSH_HOME is required by the Builder policy')
  }
  const contractVersion = String(config.contractVersion ?? process.env.PEMARA_BUILDER_CONTRACT_VERSION ?? '1')
  if (!['1', '2'].includes(contractVersion)) {
    throw new BuilderPolicyError('CONTRACT_VERSION_INVALID', `unsupported Builder contract version: ${contractVersion}`)
  }
  const version = Number(contractVersion)
  const allowedTools = version === 2 ? EXPECTED_BUILDER_TOOLS_V2 : EXPECTED_BUILDER_TOOLS
  const section = buildStagedSkillSection(join(home, 'skills'), { contractVersion: version })
  return installBuilderRuntimePolicy(ctx, { skillSectionText: section.text, allowedTools })
}

export { EXPECTED_BUILDER_TOOLS, EXPECTED_BUILDER_TOOLS_V2 }
