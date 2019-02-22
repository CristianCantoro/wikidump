"""Add timeout to function calls."""

import signal

class CallTimeout(Exception):
	pass


def handler(signum, frame):
	funcname = frame.f_code.co_name
	raise CallTimeout("{} timed out".format(funcname))


def wrap_timeout(func, timeout, args=None, kwargs=None):
    if args is None:
    	args = []

    if kwargs is None:
    	kwargs = {}

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)

    res = None
    # raises CallTimeout when timeout is reached
    res = func(*args, **kwargs)

    signal.alarm(0)

    return res