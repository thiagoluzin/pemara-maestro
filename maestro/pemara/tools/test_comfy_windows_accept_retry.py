import asyncio
import unittest
from unittest.mock import Mock
from comfy_windows_accept_retry import retrying_accept


class AcceptRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_win64_retries_and_retains_result(self):
        calls = []
        error = OSError(22, 'network disconnected'); error.winerror = 64
        async def original(proactor, sock):
            calls.append(1)
            if len(calls) == 1: raise error
            return ('accepted', 'address')
        proactor = Mock(_loop=asyncio.get_running_loop())
        sock = Mock(); sock.fileno.return_value = 10
        self.assertEqual(await retrying_accept(original)(proactor, sock), ('accepted', 'address'))
        self.assertEqual(len(calls), 2)

    async def test_unrelated_error_preserved(self):
        error = OSError(22, 'other'); error.winerror = 5
        async def original(proactor, sock): raise error
        with self.assertRaises(OSError):
            await retrying_accept(original)(Mock(_loop=asyncio.get_running_loop()), Mock())

    async def test_cancellation_preserved(self):
        async def original(proactor, sock): await asyncio.Future()
        task = retrying_accept(original)(Mock(_loop=asyncio.get_running_loop()), Mock())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task

    async def test_closed_listener_not_retried(self):
        error = OSError(22, 'closed'); error.winerror = 64
        async def original(proactor, sock): raise error
        sock = Mock(); sock.fileno.return_value = -1
        with self.assertRaises(OSError):
            await retrying_accept(original)(Mock(_loop=asyncio.get_running_loop()), sock)


if __name__ == '__main__': unittest.main()
