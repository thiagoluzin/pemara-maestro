'use strict'

// tsx asks Windows for the current user before it can load the DSH TypeScript
// entrypoint. Under severe commit pressure, uv_os_get_passwd can fail with
// ENOMEM even though Node can otherwise run. Preserve the native result and
// provide a minimal, non-sensitive fallback only for that one Windows failure.
const os = require('node:os')
const { syncBuiltinESMExports } = require('node:module')

const nativeUserInfo = os.userInfo.bind(os)

os.userInfo = function pemaraUserInfo(options) {
  try {
    return nativeUserInfo(options)
  }
  catch (error) {
    const isWindowsMemoryFailure = process.platform === 'win32'
      && error?.code === 'ERR_SYSTEM_ERROR'
      && error?.info?.code === 'ENOMEM'
      && error?.syscall === 'uv_os_get_passwd'
    if (!isWindowsMemoryFailure) throw error

    const username = String(process.env.USERNAME ?? 'pemara-user')
      .replace(/[^a-z0-9._-]/giu, '_')
      .slice(0, 64) || 'pemara-user'
    const homedir = process.env.USERPROFILE
      ?? `${process.env.HOMEDRIVE ?? 'C:'}${process.env.HOMEPATH ?? '\\'}`
    const fallback = {
      uid: -1,
      gid: -1,
      username,
      homedir,
      shell: null,
    }
    if (options?.encoding === 'buffer') {
      return {
        ...fallback,
        username: Buffer.from(username),
        homedir: Buffer.from(homedir),
        shell: Buffer.alloc(0),
      }
    }
    return fallback
  }
}

syncBuiltinESMExports()
