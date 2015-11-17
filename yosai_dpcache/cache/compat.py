import sys

py3k = sys.version_info >= (3, 0)
py32 = sys.version_info >= (3, 2)

try:
    import threading
except ImportError:
    import dummy_threading as threading  # noqa


if py3k:  # pragma: no cover
    string_types = str,
    text_type = str
    string_type = str

    if py32:
        callable = callable
    else:
        def callable(fn):
            return hasattr(fn, '__call__')

    def u(s):
        return s

    def ue(s):
        return s

    import configparser
    import io
    import _thread as thread
else:
    raise Exception('Only py3 is supported.')


def timedelta_total_seconds(td):
    # used for float compatibility
    return (td.microseconds + (
        td.seconds + td.days * 24 * 3600) * 1e6) / 1e6
