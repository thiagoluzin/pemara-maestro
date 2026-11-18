import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, realpathSync } from 'node:fs'
import { basename, dirname, isAbsolute, join, relative, resolve } from 'node:path'

import {
  EXPECTED_BUILDER_TOOLS,
  hashPackage,
  validateBuilderPackage,
  verifyFileHashes,
} from './builder-contract.mjs'
import {
  BUILDER_CONTRACT_VERSION_V2,
  EXPECTED_BUILDER_TOOLS_V2,
  validateBuilderPackageV2,
} from './builder-contract-v2.mjs'
import { verifyBuilderBaselines } from './builder-runtime.mjs'
import {
  BUILDER_V2_LEDGER_REL,
  BUILDER_V2_PROFILE_NAME,
  stageBuilderSkills,
  validateBuilderProfile,
} from '../dsh/builder-policy.mjs'

export class BuilderPreflightError extends Error {
  constructor(code, message, detail = undefined) {
    super(message)
    this.name = 'BuilderPreflightError'
    this.code = code
    this.detail = detail
  }
}

function real(path, code) {
  try {
    return realpathSync(resolve(path))
  }
  catch {
    throw new BuilderPreflightError(code, `path does not exist: ${path}`)
  }
}

function isContained(root, target) {
  const rel = relative(root, target)
  return rel === '' || (!isAbsolute(rel) && rel !== '..' && !rel.startsWith(`..\\`) && !rel.startsWith('../'))
}

function readJson(path, code) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  }
  catch (error) {
    throw new BuilderPreflightError(code, `invalid JSON at ${path}: ${error.message}`)
  }
}

function gitRead(workspace, args) {
  try {
    return execFileSync('git', [
      '-c', `safe.directory=${workspace}`,
      '-C', workspace,
      ...args,
    ], { encoding: 'utf8', windowsHide: true }).trim()
  }
  catch (error) {
    throw new BuilderPreflightError(
      'WORKTREE_GIT_INVALID',
      `cannot inspect Builder worktree: ${error.stderr?.toString().trim() || error.message}`,
    )
  }
}

/** Host-only preflight. It validates and optionally stages; it never launches DSH. */
export function prepareBuilderRun({
  projectRoot,
  packagePath,
  workspace,
  stageSkills = true,
  worktreeRoot = join(dirname(projectRoot), 'worktrees', 'pemara-harness-qwen'),
  builderHome = join(projectRoot, '.runtime', 'dsh-home-builder'),
  skillRoots = [join(dirname(projectRoot), '.agents', 'skills')],
}) {
  const root = real(projectRoot, 'PROJECT_ROOT_MISSING')
  const packagesRoot = real(join(root, 'evidence', 'packages'), 'PACKAGE_ROOT_MISSING')
  const taskPackagePath = real(packagePath, 'PACKAGE_MISSING')
  if (!isContained(packagesRoot, taskPackagePath)) {
    throw new BuilderPreflightError(
      'PACKAGE_OUTSIDE_HOST_EVIDENCE',
      'Builder packages must come from the host-owned evidence/packages directory',
    )
  }

  const pkg = readJson(taskPackagePath, 'PACKAGE_INVALID_JSON')
  const contractVersion = pkg.contract_version === BUILDER_CONTRACT_VERSION_V2 ? 2 : 1
  const packageResult = contractVersion === 2
    ? validateBuilderPackageV2(pkg)
    : validateBuilderPackage(pkg)
  if (!packageResult.valid) {
    throw new BuilderPreflightError('PACKAGE_REJECTED', 'Builder package failed the protected contract', {
      issues: packageResult.issues,
    })
  }

  const approvedRoot = real(worktreeRoot, 'WORKTREE_ROOT_MISSING')
  const workspaceRoot = real(workspace, 'WORKSPACE_MISSING')
  if (!isContained(approvedRoot, workspaceRoot)) {
    throw new BuilderPreflightError(
      'WORKSPACE_OUTSIDE_BUILDER_ROOT',
      `workspace must stay under ${approvedRoot}`,
    )
  }
  if (basename(workspaceRoot).toLowerCase() !== pkg.task_id.toLowerCase()) {
    throw new BuilderPreflightError(
      'WORKSPACE_TASK_MISMATCH',
      `workspace leaf must match task id ${pkg.task_id}`,
    )
  }
  if (!existsSync(join(workspaceRoot, '.git'))) {
    throw new BuilderPreflightError('WORKTREE_GIT_MISSING', 'workspace is not a Git worktree')
  }
  const dirty = gitRead(workspaceRoot, ['status', '--porcelain'])
  if (dirty !== '') {
    throw new BuilderPreflightError('WORKTREE_DIRTY', 'Builder worktree must be clean before launch', {
      paths: dirty.split(/\r?\n/),
    })
  }
  const branch = gitRead(workspaceRoot, ['branch', '--show-current'])
  if (branch === '' || branch === 'main' || branch === 'master') {
    throw new BuilderPreflightError('WORKTREE_BRANCH_UNSAFE', `unsafe Builder branch: ${branch || '(detached)'}`)
  }

  const profileName = contractVersion === 2 ? BUILDER_V2_PROFILE_NAME : 'pemara-builder'
  const profileDir = join(builderHome, 'profiles', profileName)
  const profileResult = validateBuilderProfile(profileDir, contractVersion === 2 ? {
    profileName,
    ledgerRel: BUILDER_V2_LEDGER_REL,
    contractVersion,
  } : {})
  if (!profileResult.ok) {
    throw new BuilderPreflightError('BUILDER_PROFILE_REJECTED', 'Builder profile validation failed', {
      issues: profileResult.issues,
    })
  }

  const protectedEvidencePath = join(root, 'evidence', `protected-hashes-${pkg.task_id}.json`)
  let protectedFiles = { status: 'not-captured', violations: [] }
  if (existsSync(protectedEvidencePath)) {
    const protectedEvidence = readJson(protectedEvidencePath, 'PROTECTED_EVIDENCE_INVALID')
    // Hashes are captured from the exact task worktree handed to the Builder;
    // Windows line-ending policy can make a second checkout byte-different.
    const violations = verifyFileHashes(workspaceRoot, protectedEvidence.files ?? {})
    if (violations.length > 0) {
      throw new BuilderPreflightError('PROTECTED_FILES_CHANGED', 'protected file verification failed', { violations })
    }
    protectedFiles = { status: 'verified', violations: [] }
  }

  if (contractVersion === 2) {
    const baselineViolations = verifyBuilderBaselines(workspaceRoot, pkg)
    if (baselineViolations.length > 0) {
      throw new BuilderPreflightError(
        'BUILDER_BASELINE_MISMATCH',
        'Builder v2 file baselines do not match the clean worktree',
        { violations: baselineViolations },
      )
    }
  }

  let skillResult = { ok: true, staged: [...pkg.skills], missing: [] }
  if (stageSkills) {
    skillResult = stageBuilderSkills({
      homeDir: builderHome,
      skills: pkg.skills,
      sourceRoots: skillRoots,
    })
    if (!skillResult.ok) {
      throw new BuilderPreflightError('SKILLS_MISSING', 'one or more approved skills are unavailable', {
        missing: skillResult.missing,
      })
    }
  }

  return {
    status: 'ready',
    taskId: pkg.task_id,
    contractVersion,
    package: taskPackagePath,
    packageHash: hashPackage(pkg),
    workspace: workspaceRoot,
    branch,
    profile: profileName,
    builderHome: real(builderHome, 'BUILDER_HOME_MISSING'),
    tools: [...(contractVersion === 2 ? EXPECTED_BUILDER_TOOLS_V2 : EXPECTED_BUILDER_TOOLS)],
    skills: {
      names: [...pkg.skills],
      staged: stageSkills,
    },
    protectedFiles,
    controls: {
      network: pkg.network,
      serviceControl: pkg.service_control,
      gpuControl: pkg.gpu_control,
      commitOrPublish: pkg.commit_or_publish,
      maxRounds: pkg.max_rounds,
      maxFilesChanged: pkg.max_files_changed,
    },
  }
}
