import time
# import logging

# log = logging.getLogger(__name__)

class NeedRegenerationException(Exception):
    """An exception that when raised in the 'with' block,
    forces the 'has_value' flag to False and incurs a
    regeneration of the value.

    """

NOT_REGENERATED = object()

class Lock(object):
    """Dogpile lock class.

    Provides an interface around an arbitrary mutex
    that allows one thread/process to be elected as
    the creator of a new value, while other threads/processes
    continue to return the previous version
    of that value.

    .. versionadded:: 0.4.0
        The :class:`.Lock` class was added as a single-use object
        representing the dogpile API without dependence on
        any shared state between multiple instances.

    :param mutex: A mutex object that provides ``acquire()``
     and ``release()`` methods.

    :param creator: Callable which returns a tuple of the form
     (new_value, creation_time).  "new_value" should be a newly
     generated value representing completed state.  "creation_time"
     should be a floating point time value which is relative
     to Python's ``time.time()`` call, representing the time
     at which the value was created.  This time value should
     be associated with the created value.

    :param value_and_created_fn: Callable which returns
     a tuple of the form (existing_value, creation_time).  This
     basically should return what the last local call to the ``creator()``
     callable has returned, i.e. the value and the creation time,
     which would be assumed here to be from a cache.  If the
     value is not available, the :class:`.NeedRegenerationException`
     exception should be thrown.

    """

    def __init__(self, mutex, creator, value_and_created_fn):
        self.mutex = mutex
        self.creator = creator
        self.value_and_created_fn = value_and_created_fn

    def _no_value(self, createdtime):
        """Return true if no value is available."""
        return not self._has_value(createdtime)

    def _has_value(self, createdtime):
        """Return true if the creation function has proceeded
        at least once."""
        return createdtime > 0

    def _enter(self):
        value_fn = self.value_and_created_fn
        createdtime = 1
        try:
            value = value_fn()
        except NeedRegenerationException:
            # when cache returns a None value, the cache region raises this
            # log.debug("NeedRegenerationException")
            value = NOT_REGENERATED
            createdtime = -1

        generated = self._enter_create(createdtime)

        if generated is not NOT_REGENERATED:
            return generated
        elif value is NOT_REGENERATED:
            try:
                value = value_fn()
                return value
            except NeedRegenerationException:
                raise Exception("Generation function should have just been"
                                " called by a concurrent thread.")
        else:
            return value

    def _enter_create(self, createdtime):
        if not self._no_value(createdtime):
            return NOT_REGENERATED

        if self._has_value(createdtime):
            if not self.mutex.acquire(False):
                # log.debug("creation function in progress elsewhere, returning")
                return NOT_REGENERATED
        else:
            # log.debug("no value, waiting for create lock")
            self.mutex.acquire()

        try:
            # log.debug("value creation lock %r acquired" % self.mutex)

            # see whether another thread created the value already
            try:
                value = self.value_and_created_fn()
            except NeedRegenerationException:
                pass
            else:
                # log.debug("value already present")
                return value

            # log.debug("Calling creation function")
            created = self.creator()
            return created
        finally:
            self.mutex.release()
            # log.debug("Released creation lock")

    def __enter__(self):
        return self._enter()

    def __exit__(self, type, value, traceback):
        pass
