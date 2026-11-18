import { syncBuiltinESMExports } from 'node:module'
import dgram from 'node:dgram'
import dns from 'node:dns'
import http from 'node:http'
import http2 from 'node:http2'
import https from 'node:https'
import net from 'node:net'
import tls from 'node:tls'

function denied() {
  const error = new Error('Network access denied by Pemara Builder test sandbox.')
  error.code = 'PEMARA_NETWORK_DENIED'
  throw error
}

for (const [object, names] of [
  [net, ['connect', 'createConnection', 'createServer']],
  [tls, ['connect', 'createServer']],
  [http, ['request', 'get', 'createServer']],
  [https, ['request', 'get', 'createServer']],
  [http2, ['connect', 'createServer', 'createSecureServer']],
  [dgram, ['createSocket']],
  [dns, ['lookup', 'lookupService', 'resolve', 'resolve4', 'resolve6', 'resolveAny', 'resolveCaa',
    'resolveCname', 'resolveMx', 'resolveNaptr', 'resolveNs', 'resolvePtr', 'resolveSoa', 'resolveSrv',
    'resolveTxt', 'reverse', 'setServers']],
]) {
  for (const name of names) {
    if (typeof object[name] === 'function') object[name] = denied
  }
}

for (const name of Object.keys(dns)) {
  if (name !== 'Resolver' && /^(?:lookup|resolve|reverse|setServers)/u.test(name)
    && typeof dns[name] === 'function') dns[name] = denied
}

for (const prototype of [net.Socket?.prototype, net.Server?.prototype, dgram.Socket?.prototype]) {
  if (prototype === undefined) continue
  for (const name of ['connect', 'listen', 'bind', 'send']) {
    if (typeof prototype[name] === 'function') prototype[name] = denied
  }
}

if (dns.promises !== undefined) {
  for (const name of Object.keys(dns.promises)) {
    if (name !== 'Resolver' && typeof dns.promises[name] === 'function') {
      dns.promises[name] = async () => denied()
    }
  }
}

for (const initial of [dns.Resolver?.prototype, dns.promises?.Resolver?.prototype]) {
  let prototype = initial
  while (prototype !== undefined && prototype !== null && prototype !== Object.prototype) {
    for (const name of Object.getOwnPropertyNames(prototype)) {
      if (/^(?:cancel|lookup|resolve|reverse|setLocalAddress)/u.test(name)
        && typeof prototype[name] === 'function') prototype[name] = denied
    }
    prototype = Object.getPrototypeOf(prototype)
  }
}

const deniedBindings = /^(?:cares_wrap|fs|fs_dir|http2?|http_parser|pipe_wrap|process_wrap|quic|spawn_sync|tcp_wrap|tls_wrap|udp_wrap|worker)$/u
for (const name of ['binding', '_linkedBinding']) {
  const original = process[name]?.bind(process)
  if (original === undefined) continue
  Object.defineProperty(process, name, {
    configurable: false,
    enumerable: true,
    writable: false,
    value(bindingName) {
      if (deniedBindings.test(String(bindingName))) denied()
      return original(bindingName)
    },
  })
}

Object.defineProperty(globalThis, 'fetch', {
  configurable: false,
  enumerable: true,
  writable: false,
  value: async () => denied(),
})
if ('WebSocket' in globalThis) {
  Object.defineProperty(globalThis, 'WebSocket', {
    configurable: false,
    enumerable: true,
    writable: false,
    value: class PemaraDeniedWebSocket { constructor() { denied() } },
  })
}
for (const name of ['EventSource', 'WebTransport']) {
  if (!(name in globalThis)) continue
  Object.defineProperty(globalThis, name, {
    configurable: false,
    enumerable: true,
    writable: false,
    value: class PemaraDeniedNetworkClient { constructor() { denied() } },
  })
}

syncBuiltinESMExports()
