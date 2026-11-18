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
import socket
import time
import uuid

import psutil
import requests

ROOT = Path('D:/PemaraRuntimes/ComfyUI-v0.40.0-pemara')
BASE = Path('E:/Pemara/maestro/pemara')
STATE = BASE / 'dados/comfy_lifecycle'
PYTHON = Path('D:/PemaraRuntimes/comfyui-v0400-py311/Scripts/python.exe')
USER = Path('D:/PemaraRuntimes/state/ComfyUI-v0.40.0-pemara/user')
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
    if (not found or found == {0}) and os.name == 'nt':
        # Windows may report the listening socket as PID0 while AcceptEx's
        # bound socket retains the real owner. Accept only our recorded
        # process or its verified startup child, never an arbitrary PID.
        bound = {c.pid for c in psutil.net_connections(kind='tcp')
                 if c.status == psutil.CONN_NONE and c.pid and c.laddr.port == 8188
                 and c.laddr.ip == '127.0.0.1'}
        # AcceptEx can expose only the bound socket, with no LISTEN row at all.
        # With neither socket present the port is genuinely not owned here.
        if not bound and not found:
            return None
        if len(bound) != 1:
            if not bound and found == {0}:
                # The OS can hide an elevated owner from this user. Let the
                # fixed administrative broker resolve it, with the same exact
                # runtime, idle-queue and process-identity checks before stop.
                raise psutil.AccessDenied(msg='Windows listener owner unresolved; administrative inspection required.')
            raise RuntimeError('Windows listener owner unresolved; preserved.')
        candidate = next(iter(bound))
        owned = False
        for record_name in ('runtime.json', 'starting.json'):
            record_path = STATE / record_name
            if not record_path.exists():
                continue
            data = json.loads(record_path.read_text(encoding='utf-8'))
            try:
                parent = psutil.Process(data['pid'])
                if parent.create_time() != data['created']:
                    continue
                owned = owned or candidate in {parent.pid, *[c.pid for c in parent.children(recursive=True)]}
            except psutil.NoSuchProcess:
                continue
        if not owned:
            raise RuntimeError('Windows bound owner is not a recorded runtime; preserved.')
        exact_process(candidate)
        return candidate
    if len(found) > 1 or None in found or 0 in found:
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
            or system['comfyui_version'] != '0.43.2'
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


def stop_owned_lost_listener(pid):
    """Explicit, one-shot recovery of a recorded runtime and our failed job.

    Default lost-listener protection remains intact without this scoped receipt.
    Recovery is invoked by MCP, never by the production scripts themselves.
    """
    path = STATE / 'owned_listener_recovery.json'
    request = json.loads(path.read_text(encoding='utf-8'))
    active = json.loads((STATE / 'runtime.json').read_text(encoding='utf-8'))
    proc = exact_process(pid)
    if (request.get('runtime') != active or active.get('pid') != pid
            or proc.create_time() != active['created']
            or not 0 <= time.time() - request['requested_at'] < 120
            or time.time() - request['observed_missing_at'] < 60):
        raise RuntimeError('Owned recovery identity/time mismatch; preserved.')
    progress = Path(request['progress']).resolve()
    allowed = (BASE.parents[1] / 'outputs/cupcake_lunar_gemeas_kpop_20261004/revisao_r05_animacao_narrativa/final_upscale_20261006/progress.json').resolve()
    if progress != allowed:
        raise RuntimeError('Recovery scope differs from the authorized finishing task.')
    stages = json.loads(progress.read_text(encoding='utf-8'))['stages']
    unfinished = [s for s in stages if s['status'] != 'completed']
    if (len(unfinished) != 1 or unfinished[0]['prompt_id'] != request['owned_prompt_id']
            or unfinished[0]['status'] != 'submitted'):
        raise RuntimeError('Owned in-flight job changed; preserved.')
    uuid.UUID(request['owned_prompt_id'])
    children = proc.children(recursive=True)
    if listener() is not None or proc.create_time() != active['created']:
        raise RuntimeError('Listener/identity changed during recovery; preserved.')
    archive = STATE / 'owned_listener_recovery_history' / (str(pid) + '-' + str(int(time.time())) + '.json')
    write_json(archive, {**request, 'child_pids': [c.pid for c in children],
                         'reason': 'Explicit recovery of owned finishing job after lost listener'})
    for target in list(reversed(children)) + [proc]:
        try:
            target.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(children + [proc], timeout=10)
    if alive or listener() is not None:
        raise RuntimeError('Owned recovery stop not confirmed; records retained.')
    path.unlink()
    register(None)
    return {'stopped': True, 'pid': pid, 'recovered_owned_lost_listener': True,
            'owned_prompt_id': request['owned_prompt_id'], 'evidence': str(archive)}


def stop_exact():
    pid = listener()
    if not pid:
        tracked = tracked_alive()
        if tracked:
            if (STATE / 'completed_ep03_recovery.json').exists():
                import sys
                sys.path.insert(0, str(BASE / 'tools'))
                from comfy_completed_recovery import recover
                from types import SimpleNamespace
                return recover(SimpleNamespace(**globals()), tracked)
            if (STATE / 'owned_listener_recovery.json').exists():
                return stop_owned_lost_listener(tracked)
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
            try:
                if listener():
                    validate_stats(get_json('/system_stats'))
                    idle()
                hold.write_text(str(time.time()), encoding='utf-8')
                result = stop_exact()
            except psutil.AccessDenied:
                hold.write_text(str(time.time()), encoding='utf-8')
                result = delegated_stop()
        elif action == 'start':
            if automatic and hold.exists():
                return {'started': False, 'maintenance': True, 'url': URL}
            if FLAG.exists():
                raise RuntimeError('Administrative request pending; start refused.')
            try:
                pid = listener()
            except psutil.AccessDenied:
                # Windows may retain a PID0 LISTEN row after our recorded
                # process has exited. A refused loopback connection confirms
                # it is not a usable listener. Do not kill/recycle anything:
                # the ordinary bind below still fails if another owner exists.
                if tracked_alive() is not None:
                    raise
                try:
                    with socket.create_connection(('127.0.0.1', 8188), timeout=1):
                        pass
                except ConnectionRefusedError:
                    pid = None
                else:
                    raise RuntimeError('Unresolved listener accepts connections; preserved.')
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
                        '--disable-dynamic-vram', '--disable-async-offload', '--disable-cuda-graphs',
                        '--reserve-vram', '4', '--max-upload-size', '2048']
                # GPU-lost recovery 2026-11-11: conservative synchronous model loading.
                # Do not re-enable fast FP16/dynamic offload without a stability retest.
                # One-shot, scoped low-memory start for the long finishing job.
                # The normal runtime launch policy remains unchanged.
                memory_request = STATE / 'cache_none_next_start.json'
                if memory_request.exists():
                    memory = json.loads(memory_request.read_text(encoding='utf-8'))
                    if (memory.get('scope') != 'cupcake_lunar_final20261006'
                            or not 0 <= time.time() - memory['requested_at'] < 120):
                        raise RuntimeError('Expired or unknown one-shot memory request; preserved.')
                    args.append('--cache-none')
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
                memory_request.unlink(missing_ok=True)
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

