
"""

Comments about the yosai_dpcache fork
-------------------------------------------------------------------------
- yosai's cache handlers interact with yosai_dpcache

- unlike yosai_dpcache.cache, yosai's cache handlers may specify expiration time for a
  set operation rather than use a global expiration.  This is done because
  credential caching used for authentication requires a much shorter TTL than
  authorization data, which lives in cache until event-driven invalidation or
  session expiration.

- yosai_dpcache uses a SerializationProxy that is injected with yosai's
  serialize and deserialize mechanisms, provided by a
  yosai.serialize.SerializationManager instance.  These mechanisms are
  responsible for:

    serializing
    ------------
    1) reducing (de-hydrating) object instances into their respective
       serializable dict form, facilitated by marshmallow
    2) appending cache metadata such as instance class name, version, and
       serialization creation datetime
    3) encoding the metadata-enriched dict (using MSGPack, JSON, etc)

    de-serializing
    --------------
    1) decoding a serialized object (obtained from cache) into its
       de-hydrated dict form
    2) validating metadata meets expectations (TBD)
    3) re-hydrating the dict into its respective yosai object instance

- As mentioned above, yosai's serializer creates serialization metadata.  The
  process of wrapping metadata replaces the process that was originally provided
  by yosai_dpcache.cache's CacheValue mechanism.

- expiration times are always set for cache entries
"""

from yosai_dpcache.dogpile.core import Lock, NeedRegenerationException
from yosai_dpcache.dogpile.core.nameregistry import NameRegistry
from . import exception
from .util import function_key_generator, PluginLoader, \
    memoized_property, coerce_string_conf, function_multi_key_generator
from .proxy import ProxyBackend
from . import compat
import time
import datetime
from numbers import Number
from functools import wraps
import threading

_backend_loader = PluginLoader("yosai_dpcache.cache")
register_backend = _backend_loader.register
from . import backends  # noqa


class CacheRegion(object):
    """A front end to a particular cache backend.

    :param name: Optional, a string name for the region.
     This isn't used internally
     but can be accessed via the ``.name`` parameter, helpful
     for configuring a region from a config file.
    :param function_key_generator:  Optional.  A
     function that will produce a "cache key" given
     a data creation function and arguments, when using
     the :meth:`.CacheRegion.cache_on_arguments` method.
     The structure of this function
     should be two levels: given the data creation function,
     return a new function that generates the key based on
     the given arguments.  Such as::

        def my_key_generator(namespace, fn, **kw):
            fname = fn.__name__
            def generate_key(*arg):
                return namespace + "_" + fname + "_".join(str(s) for s in arg)
            return generate_key


        region = make_region(
            function_key_generator = my_key_generator
        ).configure(
            "yosai_dpcache.cache.dbm",
            expiration_time=300,
            arguments={
                "filename":"file.dbm"
            }
        )

     The ``namespace`` is that passed to
     :meth:`.CacheRegion.cache_on_arguments`.  It's not consulted
     outside this function, so in fact can be of any form.
     For example, it can be passed as a tuple, used to specify
     arguments to pluck from \**kw::

        def my_key_generator(namespace, fn):
            def generate_key(*arg, **kw):
                return ":".join(
                        [kw[k] for k in namespace] +
                        [str(x) for x in arg]
                    )
            return generate_key


     Where the decorator might be used as::

        @my_region.cache_on_arguments(namespace=('x', 'y'))
        def my_function(a, b, **kw):
            return my_data()

    :param function_multi_key_generator: Optional.
     Similar to ``function_key_generator`` parameter, but it's used in
     :meth:`.CacheRegion.cache_multi_on_arguments`. Generated function
     should return list of keys. For example::

        def my_multi_key_generator(namespace, fn, **kw):
            namespace = fn.__name__ + (namespace or '')

            def generate_keys(*args):
                return [namespace + ':' + str(a) for a in args]

            return generate_keys

    :param key_mangler: Function which will be used on all incoming
     keys before passing to the backend.  Defaults to ``None``,
     in which case the key mangling function recommended by
     the cache backend will be used.    A typical mangler
     is the SHA1 mangler found at :func:`.sha1_mangle_key`
     which coerces keys into a SHA1
     hash, so that the string length is fixed.  To
     disable all key mangling, set to ``False``.   Another typical
     mangler is the built-in Python function ``str``, which can be used
     to convert non-string or Unicode keys to bytestrings, which is
     needed when using a backend such as bsddb or dbm under Python 2.x
     in conjunction with Unicode keys.
    :param async_creation_runner:  A callable that, when specified,
     will be passed to and called by dogpile.lock when
     there is a stale value present in the cache.  It will be passed the
     mutex and is responsible releasing that mutex when finished.
     This can be used to defer the computation of expensive creator
     functions to later points in the future by way of, for example, a
     background thread, a long-running queue, or a task manager system
     like Celery.

     For a specific example using async_creation_runner, new values can
     be created in a background thread like so::

        import threading

        def async_creation_runner(cache, somekey, creator, mutex):
            ''' Used by dogpile.core:Lock when appropriate  '''
            def runner():
                try:
                    value = creator()
                    cache.set(somekey, value)
                finally:
                    mutex.release()

            thread = threading.Thread(target=runner)
            thread.start()


        region = make_region(
            async_creation_runner=async_creation_runner,
        ).configure(
            'yosai_dpcache.cache.memcached',
            expiration_time=5,
            arguments={
                'url': '127.0.0.1:11211',
                'distributed_lock': True,
            }
        )

     Remember that the first request for a key with no associated
     value will always block; async_creator will not be invoked.
     However, subsequent requests for cached-but-expired values will
     still return promptly.  They will be refreshed by whatever
     asynchronous means the provided async_creation_runner callable
     implements.

     By default the async_creation_runner is disabled and is set
     to ``None``.

     .. versionadded:: 0.4.2 added the async_creation_runner
        feature.

    """

    def __init__(
            self,
            name=None,
            function_key_generator=function_key_generator,
            function_multi_key_generator=function_multi_key_generator,
            key_mangler=None,
            async_creation_runner=None,
    ):
        """Construct a new :class:`.CacheRegion`."""
        self.name = name
        self.function_key_generator = function_key_generator
        self.function_multi_key_generator = function_multi_key_generator
        self.key_mangler = self._user_defined_key_mangler = key_mangler
        self.async_creation_runner = async_creation_runner

    def configure(
            self, backend,
            expiration_time,
            arguments=None,
            _config_argument_dict=None,
            _config_prefix=None,
            wrap=None,
            replace_existing_backend=False,
    ):
        """Configure a :class:`.CacheRegion`.

        The :class:`.CacheRegion` itself
        is returned.

        :param backend:   Required.  This is the name of the
         :class:`.CacheBackend` to use, and is resolved by loading
         the class from the ``yosai_dpcache.cache`` entrypoint.

        :param expiration_time:   Required.  The expiration time passed
         to the dogpile system.  May be passed as an integer number
         of seconds, or as a ``datetime.timedelta`` value.

            ``expiration_time`` may be optionally passed as a
            ``datetime.timedelta`` value.

        :param arguments: Optional.  The structure here is passed
         directly to the constructor of the :class:`.CacheBackend`
         in use, though is typically a dictionary.

        :param wrap: Optional.  A list of tuples, each that contains a
         :class:`.ProxyBackend` and any arguments required for ProxyBackend
         initialization, each of which will be applied
         in a chain to ultimately wrap the original backend,
         so that custom functionality augmentation can be applied.

        :param replace_existing_backend: if True, the existing cache backend
         will be replaced.  Without this flag, an exception is raised if
         a backend is already configured.

         """

        if "backend" in self.__dict__ and not replace_existing_backend:
            raise exception.RegionAlreadyConfigured(
                "This region is already "
                "configured with backend: %s.  "
                "Specify replace_existing_backend=True to replace."
                % self.backend)
        backend_cls = _backend_loader.load(backend)
        if _config_argument_dict:
            self.backend = backend_cls.from_config_dict(
                _config_argument_dict,
                _config_prefix
            )
        else:
            self.backend = backend_cls(arguments or {})

        if not expiration_time or isinstance(expiration_time, Number):
            self.expiration_time = expiration_time
        elif isinstance(expiration_time, datetime.timedelta):
            self.expiration_time = int(
                compat.timedelta_total_seconds(expiration_time))
        else:
            raise exception.ValidationError(
                'expiration_time is not a number or timedelta.')

        if not self._user_defined_key_mangler:
            self.key_mangler = self.backend.key_mangler

        self._lock_registry = NameRegistry(self._create_mutex)

        if getattr(wrap, '__iter__', False):
            for wrapper in reversed(wrap):
                self.wrap(wrapper)

        return self

    def wrap(self, proxy):
        ''' Takes a ProxyBackend instance or class and wraps the
        attached backend.

        proxy is a Tuple that looks like this:
            (ProxyClass, arg1, arg2, ...)
        '''

        # if we were passed a type rather than an instance then
        # initialize it.

        if not issubclass(proxy[0], ProxyBackend):
            raise TypeError("Type %s is not a valid ProxyBackend"
                            % type(proxy[0]))

        proxy = proxy[0](*proxy[1:])

        self.backend = proxy.wrap(self.backend)

    def _mutex(self, key):
        return self._lock_registry.get(key)

    class _LockWrapper(object):
        """weakref-capable wrapper for threading.Lock"""
        def __init__(self):
            self.lock = threading.Lock()

        def acquire(self, wait=True):
            return self.lock.acquire(wait)

        def release(self):
            self.lock.release()

    def _create_mutex(self, key):
        mutex = self.backend.get_mutex(key)
        if mutex is not None:
            return mutex
        else:
            return self._LockWrapper()

    def configure_from_config(self, config_dict, prefix):
        """Configure from a configuration dictionary
        and a prefix.

        Example::

            local_region = make_region()
            memcached_region = make_region()

            # regions are ready to use for function
            # decorators, but not yet for actual caching

            # later, when config is available
            myconfig = {
                "cache.local.backend":"yosai_dpcache.cache.dbm",
                "cache.local.arguments.filename":"/path/to/dbmfile.dbm",
                "cache.memcached.backend":"yosai_dpcache.cache.pylibmc",
                "cache.memcached.arguments.url":"127.0.0.1, 10.0.0.1",
            }
            local_region.configure_from_config(myconfig, "cache.local.")
            memcached_region.configure_from_config(myconfig,
                                                "cache.memcached.")

        """
        config_dict = coerce_string_conf(config_dict)
        return self.configure(
            config_dict["%sbackend" % prefix],
            expiration_time=config_dict.get(
                "%sexpiration_time" % prefix, None),
            _config_argument_dict=config_dict,
            _config_prefix="%sarguments." % prefix,
            wrap=config_dict.get(
                "%swrap" % prefix, None),
        )

    @memoized_property
    def backend(self):
        raise exception.RegionNotConfigured(
            "No backend is configured on this region.")

    @property
    def is_configured(self):
        """Return True if the backend has been configured via the
        :meth:`.CacheRegion.configure` method already.

        .. versionadded:: 0.5.1

        """
        return 'backend' in self.__dict__

    def get(self, key):
        """
        Return a value from the cache based on the given key

        If the value is not present, the method returns the token
        ``NO_VALUE``. ``NO_VALUE`` evaluates to False, but is separate from
        ``None`` to distinguish between a cached value of ``None``.

        :param key: Key to be retrieved. While it's typical for a key to be a
         string, it is ultimately passed directly down to the cache backend,
         before being optionally processed by the key_mangler function, so can
         be of any type recognized by the backend or by the key_mangler
         function, if present.
        """
        if self.key_mangler:
            key = self.key_mangler(key)
        return self.backend.get(key)

    def get_or_create(self, key, creator_func, creator, expiration):
        """
        Return a cached value based on the given key.

        If a previous value is available, that value is returned immediately
        and without blocking.

        If the requested value does not exist in cache, the provided creation
        function is used to re-create a value and persist it to cache.

        The creation function is used when a *dogpile lock* is acquired. If the
        *dogpile lock* cannot be acquired it is because another thread or process
        is already running a creation function against cache for the provided key.

        If no previous value is available and the dogpile lock cannot be acquired,
        get_or_create will block until the lock is released and a new value is
        available.

        :param key: Key to retrieve. While it's typical for a key to be a
         string, it is ultimately passed directly down to the cache backend,
         before being optionally processed by the key_mangler function, so can
         be of any type recognized by the backend or by the key_mangler
         function, if present.

        :param creator_func: function used to create a new value
        :param creator: the instance to run creator_func

        :param expiration: expiration time that will overide
         the expiration time already configured on this :class:`.CacheRegion`
        """

        if self.key_mangler:
            key = self.key_mangler(key)

        def get_value():
            value = self.backend.get(key)
            if value is None:
                raise NeedRegenerationException()
            return value

        def gen_value():
            created_value = creator_func(creator)
            self.backend.set(key, created_value, expiration)
            return created_value

        with Lock(self._mutex(key), gen_value, get_value) as value:
            return value

    def set(self, key, value, expiration=None):
        """Place a new value in the cache under the given key."""

        if self.key_mangler:
            key = self.key_mangler(key)

        exp = expiration if expiration else self.expiration_time

        self.backend.set(key, value, exp)

    def delete(self, key):
        """Remove a value from the cache.

        This operation is idempotent (can be called multiple times, or on a
        non-existent key, safely)
        """

        if self.key_mangler:
            key = self.key_mangler(key)

        self.backend.delete(key)

    def keys(self, pattern):
        """
        searches for keys matching pattern, returns accordingly

        :returns: list of bytestrings
        """
        return self.backend.keys(pattern)


def make_region(*arg, **kw):
    """Instantiate a new :class:`.CacheRegion`.

    Currently, :func:`.make_region` is a passthrough
    to :class:`.CacheRegion`.  See that class for
    constructor arguments.

    """
    return CacheRegion(*arg, **kw)
