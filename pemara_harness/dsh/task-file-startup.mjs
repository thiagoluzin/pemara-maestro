import { lstatSync, readFileSync, realpathSync } from 'node:fs'
import { isAbsolute, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'pemara-task-file-startup'
export const inject = ['cmdlineArgs']

function within(root, candidate) {
  const value = relative(resolve(root), resolve(candidate))
  return value === '' || (value !== '..' && !value.startsWith(`..${sep}`) && !isAbsolute(value))
}

export function readTaskFile(path = process.env.PEMARA_TASK_FILE) {
  if (typeof path !== 'string' || path.trim() === '' || !isAbsolute(path)) {
    throw new Error('PEMARA_TASK_FILE precisa apontar para a tarefa durável do monitor.')
  }
  const monitorRoot = realpathSync(fileURLToPath(new URL('../.runtime/monitor/', import.meta.url)))
  const details = lstatSync(path)
  const taskPath = realpathSync(path)
  if (!details.isFile() || details.isSymbolicLink() || !within(monitorRoot, taskPath) || details.size > 64 * 1024) {
    throw new Error('Arquivo de tarefa recusado pelo limite do monitor.')
  }
  const task = readFileSync(taskPath, 'utf8').trim()
  if (task.length < 3 || task.length > 16_000 || task.includes('\u0000')) {
    throw new Error('Conteúdo do arquivo de tarefa é inválido.')
  }
  return task
}

export function apply(ctx) {
  const taskFile = process.env.PEMARA_TASK_FILE
  if (typeof taskFile === 'string' && taskFile.trim() !== '') {
    ctx.provide('headlessStartup', { task: readTaskFile(taskFile) })
    return
  }
  const args = ctx.get('cmdlineArgs')?.get()
  if (!Array.isArray(args)) throw new Error('O launcher não forneceu cmdlineArgs.')
  if (args.includes('-h') || args.includes('--help')) {
    process.stdout.write('Pemara headless: forneça uma tarefa ou use o launcher visual.\n')
    ctx.get('appExit')?.(0)
    return
  }
  const task = args.join(' ').trim()
  if (task.length < 3 || task.length > 16_000 || task.includes('\u0000')) {
    throw new Error('Uma tarefa válida é obrigatória.')
  }
  ctx.provide('headlessStartup', { task })
}
