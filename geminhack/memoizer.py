import time
import functools
from threading import RLock


def memoize(lifespan=10, hasher=None, maxitems=100, cleanfrequency=100, fresharg='FRESH'):
    """Memoizer decorator with customizable lifespan

    :param lifespan: seconds of life of cached entry
    :param hasher: custom hash to create cache key
    :param maxitems: maximum items currently in cache
    :param cleanfrequency: how many access before checking and removing stale value from cache
    :param fresharg: optional function parameter to require fresh value
    """
    class _Memoizer(object):
        def __init__(self, func):
            self.lifespan = lifespan
            self.func = func
            self.cache = {}
            self.hasher = hasher if hasher is not None else lambda args, kwargs: "%s%s" % (args, kwargs)
            self.maxitems = maxitems
            self.cleanfrequency = cleanfrequency
            self.rlock = RLock()
            self.missed = 0

        @property
        def __name__(self):
            return self.func.__name__

        @property
        def __doc__(self):
            return self.func.__doc__

        def __call__(self, *args, **kwargs):
            k = self.hasher(args, kwargs)
            try:
                fresh = bool(kwargs.pop(fresharg))
            except KeyError:
                fresh = False
            cached = None if fresh else self.cache.get(k)
            if cached is not None and time.time()-cached[1] <= self.lifespan:
                value = cached[0]
            else:
                value = self.func(*args, **kwargs)
                with self.rlock:
                    self.cache[k] = (value, time.time())
                    self.missed += 1
                    if self.missed % self.cleanfrequency == 0:
                        self._clean()
            return value

        def _clean(self):
            # NB: Use with care and lock!
            now = time.time()
            chrono = sorted((now-c[1]-self.lifespan, k) for k, c in self.cache.items())
            for pos, entry in enumerate(chrono, 1):
                if pos > self.maxitems or entry[0] > 0:
                    del self.cache[entry[1]]

        def __repr__(self):
            return self.func.__doc__

        def __get__(self, obj, objtype):
            return functools.partial(self.__call__, obj)
    return _Memoizer
