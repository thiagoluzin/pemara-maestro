import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import {
  MEDIA_CONTEXT_VERSION,
  loadMediaContext,
  prepareMediaContext,
} from '../src/media-context.mjs'

function sha256(value) { return createHash('sha256').update(value).digest('hex') }

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), 'pemara-media-context-'))
  const attachmentsRoot = join(root, 'attachments')
  await mkdir(attachmentsRoot)
  const rows = [
    { id: 'att-00000000-0000-4000-8000-000000000001', name: 'foto.png', kind: 'image', mediaType: 'image/png', bytes: 5, sha256: sha256('image'), relativePath: 'attachments/image.media' },
    { id: 'att-00000000-0000-4000-8000-000000000002', name: 'voz.webm', kind: 'audio', mediaType: 'audio/webm', bytes: 5, sha256: sha256('audio'), relativePath: 'attachments/audio.media' },
    { id: 'att-00000000-0000-4000-8000-000000000003', name: 'video.mp4', kind: 'video', mediaType: 'video/mp4', bytes: 5, sha256: sha256('video'), relativePath: 'attachments/video.media' },
  ]
  await Promise.all([
    writeFile(join(attachmentsRoot, 'image.media'), 'image'),
    writeFile(join(attachmentsRoot, 'audio.media'), 'audio'),
    writeFile(join(attachmentsRoot, 'video.media'), 'video'),
  ])
  const manifestPath = join(root, 'attachments.json')
  const taskPath = join(root, 'task.txt')
  const outputPath = join(root, 'media-context.json')
  await writeFile(manifestPath, JSON.stringify({ version: 1, jobId: 'job-test', attachments: rows }))
  await writeFile(taskPath, 'Explique tudo que aparece e é dito.')
  return { root, manifestPath, taskPath, outputPath, rows }
}

test('media context processes image, audio and video into bounded untrusted evidence', async () => {
  const files = await fixture()
  const calls = []
  const report = await prepareMediaContext({
    manifestPath: files.manifestPath,
    taskPath: files.taskPath,
    outputPath: files.outputPath,
    async processAttachment({ attachment, path, task }) {
      calls.push({ attachment, path, task })
      if (attachment.kind === 'image') return { ok: true, kind: 'vision', observation: 'uma parede vermelha' }
      if (attachment.kind === 'audio') return { ok: true, kind: 'transcription', text: 'áudio compreendido' }
      return { ok: true, kind: 'video-analysis', visual: { timeline: ['movimento'] }, transcription: { text: 'fala do vídeo' } }
    },
  })

  assert.equal(report.ok, true)
  assert.equal(report.attachments, 3)
  assert.deepEqual(calls.map(call => call.attachment.kind), ['image', 'audio', 'video'])
  assert.ok(calls.every(call => call.task === 'Explique tudo que aparece e é dito.'))
  const context = await loadMediaContext(files.outputPath)
  assert.equal(context.pemaraMediaContext, MEDIA_CONTEXT_VERSION)
  assert.equal(context.trust, 'media-untrusted-data')
  assert.deepEqual(context.attachments.map(item => item.kind), ['image', 'audio', 'video'])
  assert.match(JSON.stringify(context), /áudio compreendido/u)
  assert.equal(JSON.stringify(context).includes(files.root), false)
})

test('media context fails closed on traversal and hash drift', async () => {
  const files = await fixture()
  const outside = join(files.root, '..', 'outside.media')
  await writeFile(outside, 'outside')
  await writeFile(files.manifestPath, JSON.stringify({
    version: 1,
    jobId: 'job-test',
    attachments: [{ ...files.rows[0], relativePath: '../outside.media', bytes: 7, sha256: sha256('outside') }],
  }))
  await assert.rejects(
    prepareMediaContext({
      manifestPath: files.manifestPath,
      taskPath: files.taskPath,
      outputPath: files.outputPath,
      async processAttachment() { throw new Error('must not run') },
    }),
    error => error?.code === 'MEDIA_PATH_DENIED',
  )

  await writeFile(files.manifestPath, JSON.stringify({
    version: 1,
    jobId: 'job-test',
    attachments: [{ ...files.rows[0], sha256: '0'.repeat(64) }],
  }))
  await assert.rejects(
    prepareMediaContext({
      manifestPath: files.manifestPath,
      taskPath: files.taskPath,
      outputPath: files.outputPath,
      async processAttachment() { throw new Error('must not run') },
    }),
    error => error?.code === 'MEDIA_HASH_MISMATCH',
  )
})

test('media context refuses malformed output instead of teaching the model invented content', async () => {
  const files = await fixture()
  await assert.rejects(
    prepareMediaContext({
      manifestPath: files.manifestPath,
      taskPath: files.taskPath,
      outputPath: files.outputPath,
      async processAttachment({ attachment }) {
        return attachment.kind === 'audio' ? { ok: false, error: 'Whisper offline' } : { ok: true }
      },
    }),
    error => error?.code === 'MEDIA_PROCESSING_FAILED' && /Whisper offline/u.test(error.message),
  )
  await assert.rejects(readFile(files.outputPath), error => error?.code === 'ENOENT')
})
