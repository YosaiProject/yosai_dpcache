"""
Redis Backends
------------------

Provides backends for talking to `Redis <http://redis.io>`_.

"""

from __future__ import absolute_import
from yosai_dpcache.cache.api import CacheBackend
from yosai_dpcache.cache.compat import u

redis = None

__all__ = 'RedisBackend',


class RedisBackend(CacheBackend):
    """A `Redis <http://redis.io/>`_ backend, using the
    `redis-py <http://pypi.python.org/pypi/redis/>`_ backend.

    Example configuration::

        from yosai_dpcache.cache import make_region

        region = make_region().configure(
            'yosai_dpcache.cache.redis',
            arguments = {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'redis_expiration_time': 60*60*2,   # 2 hours
                'distributed_lock': True
                }
        )

    Arguments accepted in the arguments dictionary:

    :param url: string. If provided, will override separate host/port/db
     params.  The format is that accepted by ``StrictRedis.from_url()``.

    :param host: string, default is ``localhost``.

    :param password: string, default is no password.

    :param port: integer, default is ``6379``.

    :param db: integer, default is ``0``.

    :param distributed_lock: boolean, when True, will use a
     redis-lock as the dogpile lock.
     Use this when multiple
     processes will be talking to the same redis instance.
     When left at False, dogpile will coordinate on a regular
     threading mutex.

    :param lock_timeout: integer, number of seconds after acquiring a lock that
     Redis should expire it.  This argument is only valid when
     ``distributed_lock`` is ``True``.

    :param socket_timeout: float, seconds for socket timeout.
     Default is None (no timeout).

    :param lock_sleep: integer, number of seconds to sleep when failed to
     acquire a lock.  This argument is only valid when
     ``distributed_lock`` is ``True``.

    :param connection_pool: ``redis.ConnectionPool`` object.  If provided,
     this object supersedes other connection arguments passed to the
     ``redis.StrictRedis`` instance, including url and/or host as well as
     socket_timeout, and will be passed to ``redis.StrictRedis`` as the
     source of connectivity.

    """

    def __init__(self, arguments):
        self._imports()
        self.url = arguments.pop('url', None)
        self.host = arguments.pop('host', 'localhost')
        self.password = arguments.pop('password', None)
        self.port = arguments.pop('port', 6379)
        self.db = arguments.pop('db', 0)
        self.distributed_lock = arguments.get('distributed_lock', False)
        self.socket_timeout = arguments.pop('socket_timeout', None)

        self.lock_timeout = arguments.get('lock_timeout', None)
        self.lock_sleep = arguments.get('lock_sleep', 0.1)

        self.redis_expiration_time = arguments.pop('redis_expiration_time', 0)
        self.connection_pool = arguments.get('connection_pool', None)
        self.client = self._create_client()

    def _imports(self):
        # defer imports until backend is used
        global redis
        import redis  # noqa

    def _create_client(self):
        if self.connection_pool is not None:
            # the connection pool already has all other connection
            # options present within, so here we disregard socket_timeout
            # and others.
            return redis.StrictRedis(connection_pool=self.connection_pool)

        args = {}
        if self.socket_timeout:
            args['socket_timeout'] = self.socket_timeout

        if self.url is not None:
            args.update(url=self.url)
            return redis.StrictRedis.from_url(**args)
        else:
            args.update(
                host=self.host, password=self.password,
                port=self.port, db=self.db
            )
            return redis.StrictRedis(**args)

    def get_mutex(self, key):
        if self.distributed_lock:
            return self.client.lock(u('_lock{0}').format(key),
                                    self.lock_timeout, self.lock_sleep)
        else:
            return None

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value, expiration):
        self.client.set(key, value, ex=expiration)

    def delete(self, key):
        self.client.delete(key)

    def keys(self, pattern):
        """
        Returns a list of keys (bytestrings) matching pattern

        :param pattern: the string by which to search for keys with,
                        containing wildcards and expressions understood by
                        redis
        :returns: a list of bytestrings
        """
        return self.client.keys(pattern)
