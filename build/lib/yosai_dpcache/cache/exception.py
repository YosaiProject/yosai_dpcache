"""Exception classes for yosai_dpcache.cache."""


class DogpileCacheException(Exception):
    """Base Exception for yosai_dpcache.cache exceptions to inherit from."""


class RegionAlreadyConfigured(DogpileCacheException):
    """CacheRegion instance is already configured."""


class RegionNotConfigured(DogpileCacheException):
    """CacheRegion instance has not been configured."""


class ValidationError(DogpileCacheException):
    """Error validating a value or option."""
