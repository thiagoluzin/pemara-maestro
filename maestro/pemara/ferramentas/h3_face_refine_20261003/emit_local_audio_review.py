"""Read a local native-audio excerpt for tool audio inspection; no API or upload."""
import argparse
import base64
import subprocess

p = argparse.ArgumentParser()
p.add_argument('source')
p.add_argument('--start', type=float, default=0)
p.add_argument('--seconds', type=float, default=5)
args = p.parse_args()
result = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-v', 'error',
    '-ss', str(args.start), '-i', args.source, '-t', str(args.seconds),
    '-vn', '-ac', '1', '-ar', '32000', '-c:a', 'libmp3lame', '-b:a', '48k',
    '-f', 'mp3', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if result.returncode:
    raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
print(base64.b64encode(result.stdout).decode('ascii'))
