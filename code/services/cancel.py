"""A single, process-wide "please stop" flag - set by the web UI's Stop button (web/progress.py),
checked between individual model calls in services/llm.py's retry loop and content/pipeline.py's
per-block loop. A plain flag, not asyncio cancellation: the actual model call runs in a real OS thread
(nicegui's run.io_bound), which asyncio-level cancellation can't interrupt once started - confirmed by
reading nicegui's own run.py: it catches asyncio.CancelledError internally and just returns None,
silently discarding whatever the thread eventually computes rather than propagating the cancellation.
Checking this flag BETWEEN blocks/retries, inside the thread itself, is what actually shortens the wait.

Cancelled inherits from BaseException, not Exception, on purpose - matching asyncio.CancelledError's
own convention - so the broad `except Exception` handlers throughout call_block()/the screen handlers
don't accidentally swallow it as an ordinary error."""
import threading

_event = threading.Event()


def request():
    _event.set()


def clear():
    _event.clear()


def requested():
    return _event.is_set()


def check():
    """Raise Cancelled if a stop has been requested - call between units of work."""
    if requested():
        raise Cancelled()


async def io_bound(func, *args, **kwargs):
    """Drop-in replacement for nicegui's `run.io_bound()` that a Stop click can actually be seen
    through. web/progress.py's Stop button calls both request() (this flag) AND task.cancel() on the
    awaiting task - and task.cancel() nearly always "wins": it interrupts run.io_bound()'s own internal
    await immediately, which its try/except catches and swallows, returning None as if the call simply
    produced no result, rather than raising anything - so `await run.io_bound(...)` returns None and the
    caller's code sails on into its normal success path (this is what caused a Stop click to show BOTH
    the "Stopping..." warning notify AND a false "success" one). Checking the flag again right after the
    await turns that swallowed None back into a real Cancelled for every call site at once."""
    from nicegui import run
    result = await run.io_bound(func, *args, **kwargs)
    check()
    return result


class Cancelled(BaseException):
    pass
