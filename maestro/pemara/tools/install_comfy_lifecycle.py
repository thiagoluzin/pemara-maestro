"""Install the local lifecycle adapter without contacting ComfyUI."""
from pathlib import Path
import shutil

BASE = Path('E:/Pemara/maestro/pemara')
SITE = BASE / 'ferramentas/comfy_mcp_runtime/Lib/site-packages'
BACKUP = BASE / 'dados/comfy_lifecycle/backup_20260907'
BACKUP.mkdir(parents=True, exist_ok=True)


def update(path, content):
    backup = BACKUP / path.name
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(content, encoding='utf-8')


path = SITE / 'comfy_cli/cmdline.py'
text = path.read_text(encoding='utf-8')
marker = '    renderer = get_renderer()\n\n    if port is not None:\n'
if '# Pemara shared lifecycle stop' not in text:
    assert marker in text
    text = text.replace(marker, '''    renderer = get_renderer()
    # Pemara shared lifecycle stop
    from comfy_cli.pemara_lifecycle_adapter import stop_if_canonical
    if stop_if_canonical(renderer, port, dry_run):
        return

    if port is not None:
''', 1)
if '# Pemara shared lifecycle launch' not in text:
    marker = '    launch_command(background, extra, frontend_pr)'
    assert marker in text
    text = text.replace(marker, '''    # Pemara shared lifecycle launch
    from comfy_cli.pemara_lifecycle_adapter import launch_if_canonical
    if launch_if_canonical(get_renderer(), background, extra, frontend_pr):
        return
    launch_command(background, extra, frontend_pr)''', 1)
update(path, text)

adapter = '''"""Installed adapter; lifecycle implementation is versioned in Pemara tools."""
import importlib.util
import os
from pathlib import Path
import typer

def load():
    path = Path('E:/Pemara/maestro/pemara/tools/comfy_lifecycle.py')
    spec = importlib.util.spec_from_file_location('pemara_comfy_lifecycle', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def canonical():
    from comfy_cli.local_address import resolve_local_host_port
    from comfy_cli.workspace_manager import WorkspaceManager
    workspace = WorkspaceManager().workspace_path
    host, port = resolve_local_host_port(None, None)
    return (host == '127.0.0.1' and int(port) == 8188 and workspace is not None
            and os.path.normcase(os.path.abspath(workspace)) == os.path.normcase(str(load().ROOT)))

def perform(renderer, action):
    try:
        data = load().operate(action)
        renderer.emit(data, command='launch' if action == 'start' else 'stop', changed=True)
    except Exception as exc:
        renderer.error(code='pemara_lifecycle_failed', message=str(exc), command=action)
        raise typer.Exit(code=1)

def stop_if_canonical(renderer, port, dry_run):
    if not canonical() or (port is not None and port != 8188):
        return False
    if dry_run:
        renderer.emit({'dry_run': True, 'pid': load().listener(), 'port': 8188}, command='stop', changed=False)
    else:
        perform(renderer, 'stop')
    return True

def launch_if_canonical(renderer, background, extra, frontend_pr):
    if not background or not canonical():
        return False
    # The permanent service has a fixed contract. Reject overrides explicitly.
    if frontend_pr or extra:
        renderer.error(code='pemara_fixed_runtime', message='Canonical service uses its fixed runtime arguments; omit extra_args.', command='launch')
        raise typer.Exit(code=1)
    perform(renderer, 'start')
    return True
'''
(SITE / 'comfy_cli/pemara_lifecycle_adapter.py').write_text(adapter, encoding='utf-8')

path = SITE / 'comfy_cli/utils.py'
text = path.read_text(encoding='utf-8')
old = '        for child in children:\n            child.kill()\n        return True'
new = '''        targets = list(reversed(children)) + [parent]
        for target in targets:
            try:
                target.kill()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(targets, timeout=10)
        return not alive'''
if old in text:
    text = text.replace(old, new, 1)
assert 'psutil.wait_procs(targets, timeout=10)' in text
update(path, text)

path = SITE / 'comfy_mcp/errors.py'
text = path.read_text(encoding='utf-8')
text = text.replace('if exc.code == _NO_RECORDED_SERVER_CODE:', 'if not exc.timed_out and exc.code in {_NO_RECORDED_SERVER_CODE, "no_background_server"}:')
update(path, text)

path = BASE / 'tools/start_comfy_runtime.ps1'
old = path.read_text(encoding='utf-8-sig')
header = old[:old.index("$ErrorActionPreference")]
body = '''$ErrorActionPreference = 'Stop'
if ($Port -ne 8188 -or $RuntimeRoot -ne 'D:\\PemaraRuntimes\\ComfyUI-v0.40.0-pemara' -or
    $Python -ne 'D:\\PemaraRuntimes\\comfyui-v0400-py311\\Scripts\\python.exe') {
    throw 'O servico central tem contrato fixo; use uma instalacao de laboratorio explicita.'
}
& 'E:\\Pemara\\maestro\\pemara\\ferramentas\\comfy_mcp_runtime\\Scripts\\python.exe' `
    'E:\\Pemara\\maestro\\pemara\\tools\\comfy_lifecycle.py' start --automatic
if ($LASTEXITCODE -ne 0) { throw 'Falha no controlador central do ComfyUI.' }
'''
update(path, header + body)

path = BASE / 'tools/watchdog_comfy_runtime.ps1'
text = path.read_text(encoding='utf-8-sig')
marker = '$ErrorActionPreference = \'Stop\''
if 'maintenance.hold' not in text:
    text = text.replace(marker, marker + '''
if (Test-Path -LiteralPath 'E:\\Pemara\\maestro\\pemara\\dados\\comfy_lifecycle\\maintenance.hold') {
    exit 0
}
''', 1)
update(path, text)

path = BASE / 'ferramentas/ComfyUI/restart_comfy.ps1'
update(path, '''param([int]$Port = 8188)
$ErrorActionPreference = 'Stop'
if ($Port -ne 8188) { throw 'Somente o runtime canonico 8188 e gerenciado aqui.' }
$python = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\comfy_mcp_runtime\\Scripts\\python.exe'
$controller = 'E:\\Pemara\\maestro\\pemara\\tools\\comfy_lifecycle.py'
$flag = 'E:\\Pemara\\maestro\\pemara\\dados\\flags\\comfy_restart_requested.flag'
$log = 'E:\\Pemara\\maestro\\pemara\\dados\\logs\\restart_comfy_admin.log'
try {
    $request = if (Test-Path -LiteralPath $flag) { Get-Content -LiteralPath $flag -Raw } else { '' }
    if ($request.StartsWith('pemara-lifecycle-stop:')) {
        & $python $controller broker-stop 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
        exit $LASTEXITCODE
    }
    # Legacy fixed restart requests use the same verified controller.
    & $python $controller stop 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Parada nao confirmada.' }
    # Consume the legacy request before the controller's explicit start.
    if (Test-Path -LiteralPath $flag) { Remove-Item -LiteralPath $flag }
    & $python $controller start 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
    exit $LASTEXITCODE
} catch {
    Add-Content -LiteralPath $log -Value $_.Exception.Message
    exit 1
}
''')

# Retire the per-session target override; configured MCP URL remains authoritative.
path = SITE / 'comfy_cli/local_address.py'
original = path.with_name('local_address.py.before_r17_8190')
if original.exists():
    update(path, original.read_text(encoding='utf-8'))
target = SITE / 'comfy_cli/pemara_local_target.txt'
if target.exists():
    shutil.copy2(target, BACKUP / target.name)
    target.unlink()
print('Lifecycle adapter installed. No service or generation operation executed.')
