"""Keep the Windows listener alive when a client disconnects during accept.

Only WinError 64 is retried. Cancellation and every other error retain the
standard asyncio behavior. Loaded before ComfyUI creates its event loop.
"""
import asyncio
import logging
import sys


def retrying_accept(original):
    def accept(proactor, sock):
        async def retry():
            while True:
                try:
                    return await original(proactor, sock)
                except OSError as exc:
                    if getattr(exc, 'winerror', None) != 64 or sock.fileno() < 0:
                        raise
                    logging.warning('PEMARA: client disconnected during accept; listener retained')
        return asyncio.ensure_future(retry(), loop=proactor._loop)
    return accept


def install():
    if sys.platform != 'win32':
        return
    from asyncio.windows_events import IocpProactor
    if not getattr(IocpProactor.accept, '_pemara_retry64', False):
        patched = retrying_accept(IocpProactor.accept)
        patched._pemara_retry64 = True
        IocpProactor.accept = patched
