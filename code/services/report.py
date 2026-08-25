"""Progress / status reporting that fans out to one or more sinks, so the SAME events appear in the
console AND (once the web UI adds its sink) the graphical UI - no duplicated code. Core modules call
the module-level functions (report.info / step / warn / progress); the default sink is the console.
The GUI does report.add_sink(UiSink(...)) around an operation (and removes it after). Stdlib only, so
it is importable before any dependency is installed."""
import sys


class ConsoleSink:
    def info(self, msg):
        print(msg)

    def step(self, msg):
        print(msg)

    def warn(self, msg):
        print(msg)

    def progress(self, done, total, label=""):
        filled = int(24 * done / total) if total else 24
        pct = int(100 * done / total) if total else 100
        sys.stdout.write(f"\r  [{'#' * filled}{'-' * (24 - filled)}] {pct:3d}%  {label:<16}")
        sys.stdout.flush()

    def progress_end(self):
        sys.stdout.write("\n")
        sys.stdout.flush()


class Reporter:
    def __init__(self, sinks=None):
        self.sinks = list(sinks) if sinks is not None else [ConsoleSink()]

    def _fan(self, name, *args):
        for sink in list(self.sinks):
            fn = getattr(sink, name, None)
            if fn:
                fn(*args)

    def info(self, msg):
        self._fan("info", msg)

    def step(self, msg):
        self._fan("step", msg)

    def warn(self, msg):
        self._fan("warn", msg)

    def progress(self, done, total, label=""):
        self._fan("progress", done, total, label)

    def progress_end(self):
        self._fan("progress_end")


_R = Reporter()


def reporter():
    return _R


def add_sink(sink):
    _R.sinks.append(sink)


def remove_sink(sink):
    if sink in _R.sinks:
        _R.sinks.remove(sink)


def info(msg):
    _R.info(msg)


def step(msg):
    _R.step(msg)


def warn(msg):
    _R.warn(msg)


def progress(done, total, label=""):
    _R.progress(done, total, label)


def progress_end():
    _R.progress_end()
