from yosai_dpcache.cache.region import register_backend

register_backend(
    "yosai_dpcache.redis", "yosai_dpcache.cache.backends.redis", "RedisBackend")
