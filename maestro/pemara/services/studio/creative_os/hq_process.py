"""Child-owned GPU lease around the existing finishing CLI; invoked only by Maestro."""
import argparse
import runpy
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gpu_lease import GpuLeaseRegistry


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--lease',required=True)
    parser.add_argument('--job',required=True)
    parser.add_argument('--parent',type=int,required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command and args.command[0]=='--' else args.command
    if not command: raise ValueError('Missing existing pipeline command')
    registry=GpuLeaseRegistry(Path(args.lease))
    registry.adopt_child_process(args.job,expected_parent_pid=args.parent)
    # Do not release here: the parent completes metadata handling and releases by job ID.
    # If the parent died, this PID stays authoritative until this process exits.
    sys.argv=command
    runpy.run_path(command[0],run_name='__main__')


if __name__=='__main__': main()
