"""Single local ComfyUI lifecycle used by the MCP adapter and Windows launchers.

No generation API. Fixed installation, loopback address and broker operation.
"""
import configparser
import contextlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import time
import uuid

import psutil
import requests

ROOT = Path('D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara')
BASE = Path('E:/Pemara/maestro/pemara')
STATE = BASE / 'dados/comfy_lifecycle'
PYTHON = Path('D:/PemaraRuntimes/comfyui-v0360-py311/Scripts/python.exe')
USER = Path('D:/PemaraRuntimes/state/ComfyUI-v0.36.0-pemara/user')
CONFIG = Path('C:/Users/admin_remoto/AppData/Local/comfy-cli/config.ini')
FLAG = BASE / 'dados/flags/comfy_restart_requested.flag'
URL = 'http://127.0.0.1:8188'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(tmp, path)


@contextlib.contextmanager
def lock():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'lifecycle.lock').open('a+b') as stream:
        if os.fstat(stream.fileno()).st_size == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError('Another lifecycle operation is in progress; no action taken.') from exc
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def listener():
    found = {c.pid for c in psutil.net_connections(kind='tcp')
             if c.status == psutil.CONN_LISTEN and c.laddr.port == 8188
             and c.laddr.ip in {'127.0.0.1', '0.0.0.0', '::', '::ffff:127.0.0.1'}}
    if len(found) > 1 or None in found:
        raise RuntimeError('Ambiguous listener ownership; preserved.')
    return next(iter(found), None)


def get_json(endpoint):
    session = requests.Session()
    session.trust_env = False
    with session:
        result = session.get(URL + endpoint, timeout=5)
        result.raise_for_status()
        return result.json()


def validate_stats(data):
    system = data['system']
    argv = system['argv']
    if (os.path.normcase(os.path.abspath(argv[0])) != os.path.normcase(str(ROOT / 'main.py'))
            or system['comfyui_version'] != '0.37.0'
            or system['pytorch_version'] != '2.14.0+cu130'
            or data['devices'][0]['type'] != 'cuda'
            or '0.0.0.0' in argv or '::' in argv):
        raise RuntimeError('Listener differs from the fixed local runtime contract; preserved.')
    return data


def idle():
    queue = get_json('/queue')
    if not isinstance(queue.get('queue_running'), list) or not isinstance(queue.get('queue_pending'), list):
        raise RuntimeError('Queue could not be verified; preserved.')
    if queue['queue_running'] or queue['queue_pending']:
        raise RuntimeError('ComfyUI has running or pending jobs; restart refused.')


def register(pid):
    config = configparser.ConfigParser()
    config.read(CONFIG, encoding='utf-8-sig')
    if pid:
        config['DEFAULT']['background'] = repr(('127.0.0.1', 8188, pid))
        config['DEFAULT']['background_log'] = str(STATE / 'comfyui.log')
    else:
        config['DEFAULT'].pop('background', None)
    tmp = CONFIG.with_suffix('.lifecycle.tmp')
    with tmp.open('w', encoding='utf-8') as stream:
        config.write(stream)
    os.replace(tmp, CONFIG)


def record(pid):
    data = {'pid': pid, 'created': psutil.Process(pid).create_time(), 'url': URL,
            'runtime': str(ROOT), 'recorded_at': time.time()}
    write_json(STATE / 'runtime.json', data)
    register(pid)
    (STATE / 'starting.json').unlink(missing_ok=True)
    return data


def tracked_alive():
    for name in ('runtime.json', 'starting.json'):
        path = STATE / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        try:
            proc = psutil.Process(data['pid'])
            if proc.create_time() == data['created']:
                return proc.pid
        except psutil.NoSuchProcess:
            continue
    return None


def exact_process(pid):
    proc = psutil.Process(pid)
    cmd = proc.cmdline()  # AccessDenied is handled by the fixed Radar broker.
    expected = os.path.normcase(str(ROOT / 'main.py'))
    if not any(os.path.normcase(os.path.abspath(arg)) == expected for arg in cmd):
        raise RuntimeError('PID is not the expected ComfyUI main.py; preserved.')
    if '--port' not in cmd or cmd[cmd.index('--port') + 1] != '8188':
        raise RuntimeError('PID port does not match; preserved.')
    return proc


def stop_failed_start(pid):
    """Recover only our timed-out, recorded startup, never a lost live runtime."""
    path = STATE / 'starting.json'
    if not path.exists():
        raise RuntimeError('No matching startup record; living process preserved.')
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('pid') != pid:
        raise RuntimeError('Tracked PID differs from the startup record; preserved.')
    proc = exact_process(pid)
    if data['pid'] != pid or proc.create_time() != data['created']:
        raise RuntimeError('Startup process identity changed; preserved.')
    if time.time() - data['created'] < 300:
        raise RuntimeError('Startup is still within its recovery grace period; preserved.')
    active_path = STATE / 'runtime.json'
    if active_path.exists():
        active = json.loads(active_path.read_text(encoding='utf-8'))
        if active.get('pid') == pid and active.get('created') == data['created']:
            raise RuntimeError('Process was registered as a live runtime; preserved.')
    children = proc.children(recursive=True)
    # A newly available listener may have a real queue. Do not interrupt it.
    if listener() is not None:
        raise RuntimeError('Listener appeared during startup recovery; retry through the live queue.')
    if json.loads(path.read_text(encoding='utf-8')) != data or proc.create_time() != data['created']:
        raise RuntimeError('Startup record changed during recovery; preserved.')
    archive = STATE / 'startup_recovery_history' / (str(pid) + '-' + str(int(time.time())) + '.json')
    write_json(archive, {**data, 'recovery_requested_at': time.time(),
                         'reason': 'Recorded startup exceeded 300s without a listener',
                         'child_pids': [p.pid for p in children]})
    for target in list(reversed(children)) + [proc]:
        try:
            target.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(children + [proc], timeout=10)
    if alive or listener() is not None:
        raise RuntimeError('Startup recovery stop not confirmed; original record retained.')
    path.unlink()
    register(None)
    return {'stopped': True, 'pid': pid, 'url': URL, 'recovered_failed_startup': True,
            'evidence': str(archive)}


def stop_exact():
    pid = listener()
    if not pid:
        tracked = tracked_alive()
        if tracked:
            return stop_failed_start(tracked)
        register(None)
        return {'stopped': True, 'already_stopped': True, 'url': URL}
    validate_stats(get_json('/system_stats'))
    idle()
    proc = exact_process(pid)
    children = proc.children(recursive=True)
    # Recheck the PID/listener immediately before touching the process.
    if listener() != pid or not proc.is_running():
        raise RuntimeError('Listener changed during verification; retry with fresh state.')
    for target in list(reversed(children)) + [proc]:
        try:
            target.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(children + [proc], timeout=10)
    if alive or listener() is not None:
        raise RuntimeError('Stop not confirmed; process record retained.')
    register(None)
    return {'stopped': True, 'pid': pid, 'url': URL}


def broker_stop():
    request = STATE / 'broker_request.json'
    data = json.loads(request.read_text(encoding='utf-8'))
    uuid.UUID(data['id'])
    if data['action'] != 'stop' or not 0 <= time.time() - data['time'] < 120:
        raise RuntimeError('Invalid or expired fixed stop request.')
    # The requesting MCP process holds the global lock throughout this handoff.
    owner = psutil.Process(data['requester_pid'])
    if owner.create_time() != data['requester_created']:
        raise RuntimeError('Requesting process changed; request rejected.')
    try:
        result = stop_exact()
        result['ok'] = True
    except Exception as exc:
        result = {'ok': False, 'error': str(exc)}
    result['id'] = data['id']
    # Consume before acknowledgement, so Radar cannot repeat this stop.
    FLAG.unlink(missing_ok=True)
    write_json(STATE / 'broker_result.json', result)
    return result


def delegated_stop():
    if FLAG.exists():
        raise RuntimeError('An administrative restart is already pending; preserved.')
    token = str(uuid.uuid4())
    write_json(STATE / 'broker_request.json', {
        'id': token, 'action': 'stop', 'time': time.time(),
        'requester_pid': os.getpid(), 'requester_created': psutil.Process().create_time()})
    FLAG.parent.mkdir(parents=True, exist_ok=True)
    FLAG.write_text('pemara-lifecycle-stop:' + token, encoding='utf-8')
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        receipt = STATE / 'broker_result.json'
        if receipt.exists():
            data = json.loads(receipt.read_text(encoding='utf-8'))
            if data.get('id') == token:
                if not data['ok']:
                    raise RuntimeError(data['error'])
                return data
        time.sleep(0.5)
    raise RuntimeError('Radar did not acknowledge stop within 50s; no replacement launched.')


def operate(action, automatic=False):
    with lock():
        hold = STATE / 'maintenance.hold'
        if action == 'stop':
            # Check the live queue before setting maintenance intent.
            if listener():
                validate_stats(get_json('/system_stats'))
                idle()
            hold.write_text(str(time.time()), encoding='utf-8')
            try:
                result = stop_exact()
            except psutil.AccessDenied:
                result = delegated_stop()
        elif action == 'start':
            if automatic and hold.exists():
                return {'started': False, 'maintenance': True, 'url': URL}
            if FLAG.exists():
                raise RuntimeError('Administrative request pending; start refused.')
            pid = listener()
            if pid:
                validate_stats(get_json('/system_stats'))
                result = record(pid) | {'started': False, 'already_running': True}
            else:
                if tracked_alive():
                    raise RuntimeError('Recorded process is still alive without a listener; duplicate start refused.')
                io = BASE / 'ferramentas/ComfyUI'
                args = [str(PYTHON), str(ROOT / 'main.py'), '--listen', '127.0.0.1',
                        '--port', '8188', '--cuda-device', '0', '--user-directory', str(USER),
                        '--input-directory', str(io / 'input'), '--output-directory', str(io / 'output'),
                        '--temp-directory', str(io / 'temp'), '--disable-auto-launch', '--enable-manager',
                        '--fast', 'fp16_accumulation']
                # Keep unrelated per-user Python installs out of this dedicated runtime.
                # This does not alter the parent environment or the installed packages.
                runtime_env = os.environ.copy()
                runtime_env['PYTHONNOUSERSITE'] = '1'
                with (STATE / 'comfyui.log').open('ab', buffering=0) as log:
                    proc = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL,
                                            stdout=log, stderr=log,
                                            env=runtime_env,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                write_json(STATE / 'starting.json', {
                    'pid': proc.pid, 'created': psutil.Process(proc.pid).create_time()})
                deadline = time.monotonic() + 115
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        raise RuntimeError('ComfyUI exited during startup; consult comfyui.log.')
                    try:
                        validate_stats(get_json('/system_stats'))
                        pid = listener()
                        if pid not in {proc.pid, *[p.pid for p in psutil.Process(proc.pid).children(recursive=True)]}:
                            raise RuntimeError('Unexpected process acquired port during startup.')
                        exact_process(pid)
                        result = record(pid) | {'started': True}
                        break
                    except requests.RequestException:
                        time.sleep(0.5)
                else:
                    raise RuntimeError('Startup timeout; preserved for diagnosis, no second instance.')
            hold.unlink(missing_ok=True)
        else:
            raise ValueError('Only start and stop are supported.')
        write_json(STATE / 'last_operation.json', {'action': action, 'time': time.time(), **result})
        return result


if __name__ == '__main__':
    import sys
    action = sys.argv[1]
    if action == 'broker-stop':
        print(json.dumps(broker_stop()))
    else:
        print(json.dumps(operate(action, automatic='--automatic' in sys.argv)))

