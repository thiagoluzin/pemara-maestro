import assert from 'node:assert/strict'
import { mkdtemp, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { Readable } from 'node:stream'
import test from 'node:test'

import {
  MAX_ATTACHMENT_BYTES,
  createTaskRunner,
  normalizeTaskSubmission,
} from '../src/task-runner.mjs'

const PNG = Buffer.from('89504e470d0a1a0a0000000d49484452', 'hex')

test('task submission accepts bounded opaque attachment ids and supports attachment-only prompts', () => {
  assert.deepEqual(
    normalizeTaskSubmission({ task: '  O que aparece aqui?  ', attachmentIds: ['att-00000000-0000-4000-8000-000000000001'] }),
    { task: 'O que aparece aqui?', attachmentIds: ['att-00000000-0000-4000-8000-000000000001'] },
  )
  assert.deepEqual(
    normalizeTaskSubmission({ task: '', attachmentIds: ['att-00000000-0000-4000-8000-000000000001'] }),
    { task: 'Analise os anexos enviados e responda com base neles.', attachmentIds: ['att-00000000-0000-4000-8000-000000000001'] },
  )
  assert.throws(() => normalizeTaskSubmission({ task: '', attachmentIds: [] }), /tarefa/i)
  assert.throws(() => normalizeTaskSubmission({ task: 'ok', attachmentIds: ['fora-do-contrato'] }), /anexo/i)
  assert.throws(() => normalizeTaskSubmission({ task: 'ok', attachmentIds: Array(9).fill('att-00000000-0000-4000-8000-000000000001') }), /8 anexos/i)
  assert.throws(() => normalizeTaskSubmission({ task: 'ok', attachmentIds: [], command: 'pwsh' }), /campo/i)
})

test('runner streams image, audio and video into one durable job manifest', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-media-runner-'))
  const launches = []
  const runner = createTaskRunner({
    projectRoot: root,
    workspaceRoot: root,
    now: () => 1_787_330_000_000,
    launchDetached(entry, args, options) {
      launches.push({ entry, args, options })
      return { pid: 43210, unref() {} }
    },
  })

  const image = await runner.stageAttachment({
    stream: Readable.from([PNG]),
    filename: 'foto da obra.png',
    mediaType: 'image/png',
    contentLength: PNG.length,
  })
  const audio = await runner.stageAttachment({
    stream: Readable.from([Buffer.from('audio-fixture')]),
    filename: 'recado.webm',
    mediaType: 'audio/webm',
    contentLength: 13,
  })
  const video = await runner.stageAttachment({
    stream: Readable.from([Buffer.from('video-fixture')]),
    filename: 'teste.mp4',
    mediaType: 'video/mp4',
    contentLength: 13,
  })

  assert.deepEqual([image.kind, audio.kind, video.kind], ['image', 'audio', 'video'])
  assert.equal(image.name, 'foto da obra.png')
  assert.equal('path' in image, false)

  const job = await runner.start({
    task: 'Compare a foto, o áudio e o vídeo.',
    attachmentIds: [image.id, audio.id, video.id],
    workspace: root,
  })
  assert.equal(job.attachments.length, 3)
  assert.equal(launches.length, 1)
  const manifestIndex = launches[0].args.indexOf('--attachments-manifest')
  assert.ok(manifestIndex > 0)
  const manifestPath = launches[0].args[manifestIndex + 1]
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
  assert.equal(manifest.version, 1)
  assert.deepEqual(manifest.attachments.map(item => item.kind), ['image', 'audio', 'video'])
  assert.ok(manifest.attachments.every(item => item.relativePath.startsWith('attachments/')))
  assert.deepEqual(await readFile(join(manifestPath, '..', manifest.attachments[0].relativePath)), PNG)

  const snapshot = await runner.snapshot()
  assert.deepEqual(snapshot.attachments.map(item => item.name), ['foto da obra.png', 'recado.webm', 'teste.mp4'])
  assert.ok(snapshot.attachments.every(item => !('relativePath' in item) && !('path' in item)))
})

test('attachment admission rejects unsupported, oversized and repeated inputs before a task starts', async () => {
  const root = await mkdtemp(join(tmpdir(), 'pemara-media-deny-'))
  const runner = createTaskRunner({
    projectRoot: root,
    workspaceRoot: root,
    launchDetached() { throw new Error('must not launch') },
  })

  await assert.rejects(
    runner.stageAttachment({
      stream: Readable.from([Buffer.from('plain')]),
      filename: 'payload.txt',
      mediaType: 'text/plain',
      contentLength: 5,
    }),
    error => error?.code === 'UNSUPPORTED_MEDIA',
  )
  await assert.rejects(
    runner.stageAttachment({
      stream: Readable.from([]),
      filename: 'enorme.mp4',
      mediaType: 'video/mp4',
      contentLength: MAX_ATTACHMENT_BYTES + 1,
    }),
    error => error?.code === 'ATTACHMENT_TOO_LARGE',
  )

  const staged = await runner.stageAttachment({
    stream: Readable.from([PNG]),
    filename: '../foto.png',
    mediaType: 'image/png',
    contentLength: PNG.length,
  })
  assert.equal(staged.name, 'foto.png')
  await assert.rejects(
    runner.start({ task: 'Analise.', attachmentIds: [staged.id, staged.id], workspace: root }),
    /duplicado/i,
  )
})
