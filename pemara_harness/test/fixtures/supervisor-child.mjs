process.stdout.write(`fixture:${process.argv.at(-1).includes('TAREFA DURÁVEL PEMARA')}\n`)
process.exitCode = Number(process.env.PEMARA_FIXTURE_EXIT ?? 0)
