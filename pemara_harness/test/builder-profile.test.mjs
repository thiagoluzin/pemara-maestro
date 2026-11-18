import assert from 'node:assert/strict'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import {
  BUILDER_LEDGER_REL,
  BUILDER_PROFILE_FILES,
  BUILDER_SKILL,
  BUILDER_V2_LEDGER_REL,
  BUILDER_V2_PROFILE_NAME,
  EXPECTED_BUILDER_TOOLS,
  EXPECTED_BUILDER_TOOLS_V2,
  OPERATIONAL_LEDGER_REL,
  buildStagedSkillSection,
  installBuilderRuntimePolicy,
  stageBuilderSkills,
  validateBuilderProfile,
  validateBuilderRequest,
} from '../dsh/builder-policy.mjs'

const projectRoot = new URL('..', import.meta.url)
const builderProfileDir = new URL(
  '../.runtime/dsh-home-builder/profiles/pemara-builder/',
  import.meta.url,
)
const operationalPatch = new URL(
  '../.runtime/dsh-home/profiles/pemara/cordis.patch.yml',
  import.meta.url,
)
const builderV2ProfileDir = new URL(
  '../.runtime/dsh-home-builder/profiles/pemara-builder-v2/',
  import.meta.url,
)

function makeSkill(root, name, body = `instructions for ${name}`) {
  const dir = join(root, name)
  mkdirSync(dir, { recursive: true })
  writeFileSync(
    join(dir, 'SKILL.md'),
    `---\nname: ${name}\ndescription: ${name} description\n---\n${body}\n`,
  )
}

test('the builder profile is isolated, loopback-only, and policy-enforced', () => {
  const result = validateBuilderProfile(builderProfileDir)
  assert.deepEqual(result.issues, [])
  assert.equal(result.ok, true)

  const patch = readFileSync(new URL('cordis.patch.yml', builderProfileDir), 'utf8')
  assert.match(patch, /baseURL: http:\/\/127\.0\.0\.1:11436\/v1/)
  assert.match(patch, /dshHomePath\('pemara-builder\/ledger\.sqlite'\)/)
  assert.match(patch, /@pemara\/harness\/dsh-builder-policy/)
  assert.match(patch, /rebindTaskId:.*PEMARA_SUPERVISOR_TASK_ID/)
  assert.doesNotMatch(patch, /dshHomePath\('pemara\/ledger\.sqlite'\)/)
})

test('Builder v2 profile is separately isolated and composes only contract-bound mutation tools', () => {
  const result = validateBuilderProfile(builderV2ProfileDir, {
    profileName: BUILDER_V2_PROFILE_NAME,
    ledgerRel: BUILDER_V2_LEDGER_REL,
    contractVersion: 2,
  })
  assert.deepEqual(result, { ok: true, issues: [] })
  const patch = readFileSync(new URL('cordis.patch.yml', builderV2ProfileDir), 'utf8')
  assert.match(patch, /dshHomePath\('pemara-builder-v2\/ledger\.sqlite'\)/)
  assert.match(patch, /builderPackagePath:.*PEMARA_BUILDER_PACKAGE/)
  assert.match(patch, /builderWorkspace:.*PEMARA_BUILDER_WORKSPACE/)
  assert.match(patch, /rebindTaskId:.*PEMARA_SUPERVISOR_TASK_ID/)
  assert.doesNotMatch(patch, /dshHomePath\('pemara\/ledger\.sqlite'\)/)

  assert.deepEqual(validateBuilderRequest({
    tools: [...EXPECTED_BUILDER_TOOLS_V2],
    skills: ['alpha', 'beta', 'gamma'],
    contractVersion: 2,
  }), { ok: true, issues: [] })
  const rawShell = validateBuilderRequest({
    tools: [...EXPECTED_BUILDER_TOOLS_V2, 'pwsh'],
    skills: ['alpha', 'beta', 'gamma'],
    contractVersion: 2,
  })
  assert.ok(rawShell.issues.some(issue => issue.code === 'TOOL_SURFACE'))
})

test('broken profile shapes are rejected with stable issue codes', () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-builder-profile-'))
  try {
    for (const file of BUILDER_PROFILE_FILES) {
      const source = new URL(file, builderProfileDir)
      writeFileSync(join(base, file), readFileSync(source))
    }

    rmSync(join(base, 'pnpm-workspace.yaml'))
    assert.ok(validateBuilderProfile(base).issues.some(issue => issue.code === 'PROFILE_FILE_MISSING'))

    writeFileSync(join(base, 'pnpm-workspace.yaml'), 'packages:\n  - .\n')
    const patchPath = join(base, 'cordis.patch.yml')
    writeFileSync(
      patchPath,
      readFileSync(patchPath, 'utf8').replaceAll(
        `dshHomePath('${BUILDER_LEDGER_REL}')`,
        `dshHomePath('${OPERATIONAL_LEDGER_REL}')`,
      ),
    )
    assert.ok(validateBuilderProfile(base).issues.some(issue => issue.code === 'PROFILE_LEDGER_NOT_DEDICATED'))

    writeFileSync(join(base, 'package.json'), '{invalid json')
    assert.ok(validateBuilderProfile(base).issues.some(issue => issue.code === 'PROFILE_PACKAGE_INVALID'))
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('the operational Pemara profile remains on its own ledger', () => {
  const source = readFileSync(operationalPatch, 'utf8')
  assert.match(source, /dshHomePath\('pemara\/ledger\.sqlite'\)/)
  assert.doesNotMatch(source, /dshHomePath\('pemara-builder\/ledger\.sqlite'\)/)
})

test('skill staging is exact and a missing skill leaves the prior catalog intact', () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-builder-skills-'))
  try {
    const source = join(base, 'source')
    const home = join(base, 'home')
    for (const name of ['alpha', 'beta', 'gamma']) makeSkill(source, name)

    const first = stageBuilderSkills({
      homeDir: home,
      skills: ['alpha', 'beta', 'gamma'],
      sourceRoots: [source],
    })
    assert.deepEqual(first, { ok: true, staged: ['alpha', 'beta', 'gamma'], missing: [] })
    assert.ok(existsSync(join(home, 'skills', 'alpha', 'SKILL.md')))

    const rejected = stageBuilderSkills({
      homeDir: home,
      skills: ['alpha', 'beta', 'missing'],
      sourceRoots: [source],
    })
    assert.deepEqual(rejected, { ok: false, staged: [], missing: ['missing'] })
    assert.ok(existsSync(join(home, 'skills', 'gamma', 'SKILL.md')),
      'an invalid replacement must not mutate the prior catalog')
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('skill staging rejects traversal, duplicates, and fewer than three skills', () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-builder-skill-policy-'))
  try {
    const source = join(base, 'source')
    for (const name of ['alpha', 'beta', 'gamma']) makeSkill(source, name)

    assert.throws(
      () => stageBuilderSkills({ homeDir: join(base, 'a'), skills: ['alpha', 'beta', '../gamma'], sourceRoots: [source] }),
      error => error?.code === 'INVALID_SKILL_NAME',
    )
    assert.throws(
      () => stageBuilderSkills({ homeDir: join(base, 'b'), skills: ['alpha', 'alpha', 'beta'], sourceRoots: [source] }),
      error => error?.code === 'DUPLICATE_SKILLS',
    )
    assert.throws(
      () => stageBuilderSkills({ homeDir: join(base, 'c'), skills: ['alpha', 'beta'], sourceRoots: [source] }),
      error => error?.code === 'SKILLS_OUT_OF_RANGE',
    )
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('staged skills become the exact embedded Builder instruction pack', () => {
  const base = mkdtempSync(join(tmpdir(), 'pemara-builder-skill-prompt-'))
  try {
    for (const name of ['alpha', 'beta', 'gamma']) makeSkill(base, name, `body-${name}`)
    const section = buildStagedSkillSection(base)

    assert.deepEqual(section.names, ['alpha', 'beta', 'gamma'])
    assert.match(section.text, /<available_skills>/)
    assert.match(section.text, /- `alpha`: alpha description/)
    assert.match(section.text, /body-alpha/)
    assert.doesNotMatch(section.text, /delta/)
  }
  finally {
    rmSync(base, { recursive: true, force: true })
  }
})

test('the runtime policy hides and denies every tool outside the protected five', () => {
  let guard
  let onCreated
  let restrictedTo
  let promptSection
  const disposed = []
  const ctx = {
    tools: {
      guard(callback) {
        guard = callback
        return () => disposed.push('guard')
      },
    },
    systemPrompt: {
      section(section) {
        promptSection = section
        return () => disposed.push('prompt')
      },
    },
    on(event, callback) {
      assert.equal(event, 'agent/created')
      onCreated = callback
      return () => disposed.push('listener')
    },
  }

  const dispose = installBuilderRuntimePolicy(ctx, {
    skillSectionText: '<available_skills>approved only</available_skills>',
  })
  onCreated({
    agent: {
      ctx: {
        tools: {
          restrict(filter) {
            restrictedTo = filter
            return () => disposed.push('restriction')
          },
        },
      },
    },
  })

  assert.deepEqual(restrictedTo, { allow: [...EXPECTED_BUILDER_TOOLS] })
  assert.equal(guard({ name: 'harness_task_checkpoint' }), undefined)
  assert.match(guard({ name: 'pwsh' }), /denied by Pemara Builder policy/)
  assert.match(guard({ name: 'web_search' }), /denied by Pemara Builder policy/)
  assert.equal(promptSection.name, 'pemara:builder-policy')
  assert.match(promptSection.text, /approved only/)

  dispose()
  assert.ok(disposed.includes('guard'))
  assert.ok(disposed.includes('listener'))
  assert.ok(disposed.includes('restriction'))
})

test('a Builder request contains exactly five ledger tools and 3 to 12 valid skills', () => {
  assert.deepEqual(validateBuilderRequest({
    tools: [...EXPECTED_BUILDER_TOOLS],
    skills: ['alpha', 'beta', 'gamma'],
  }), { ok: true, issues: [] })

  const extraTool = validateBuilderRequest({
    tools: [...EXPECTED_BUILDER_TOOLS, 'pwsh'],
    skills: ['alpha', 'beta', 'gamma'],
  })
  assert.ok(extraTool.issues.some(issue => issue.code === 'TOOL_SURFACE'))

  const invalidSkill = validateBuilderRequest({
    tools: [...EXPECTED_BUILDER_TOOLS],
    skills: ['alpha', 'beta', '../gamma'],
  })
  assert.ok(invalidSkill.issues.some(issue => issue.code === 'INVALID_SKILL_NAME'))
})

test('the profile declares the expected model and only four source files', () => {
  assert.equal(BUILDER_SKILL, 'qwen3.8-27b-uncensored-yarn-524k')
  assert.deepEqual(
    [...BUILDER_PROFILE_FILES].sort(),
    ['cordis.patch.yml', 'cordis.yml', 'package.json', 'pnpm-workspace.yaml'],
  )
  assert.ok(projectRoot)
})
