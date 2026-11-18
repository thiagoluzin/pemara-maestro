# Third-party notices

## Public research SDKs

- `@modelcontextprotocol/sdk@1.32.2` — MIT; `https://github.com/modelcontextprotocol/typescript-sdk`.
- Relationship: direct runtime dependencies for explicitly invoked public research. Their licenses remain in `node_modules`; exact transitive versions/integrities are in `package-lock.json`.

## Self-evolve — methodological reference

- Source: `https://github.com/DaizeDong/self-evolve`
- License: MIT
- Relationship: documentation consulted on 2026-11-02 for the fixed-evaluation method. No upstream source is copied and no runtime dependency is installed. The local gate is an independent Node implementation.

## DeepSeek Harness

- Source: `https://github.com/deepseek-ai/DeepSeek-Harness`
- Pinned commit: `141eb6fef83422698aef7a981029e843e8161534`
- License: MIT
- Relationship: composed at runtime through an out-of-tree profile and plugin; no upstream source is vendored into this project.

## Reversa

- Source: `https://github.com/sandeco/reversa`
- Pinned commit: `f3c36892e8aefa44f020f7ad74917089e67ddaa3`
- License: MIT
- Relationship: used as a development-time discovery/archaeology tool; it is not a runtime dependency.

The exact upstream license files remain in their respective checkouts under `E:\Pemara\third_party`.

## Inter Variable

- Source: `https://github.com/rsms/inter`
- Incorporated version: 4.001
- License: SIL Open Font License 1.1
- Relationship: local font used only by the web interface, with no external calls.
- Full text: `web-monitor/fonts/INTER-LICENSE.txt`.
