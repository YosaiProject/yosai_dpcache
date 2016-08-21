"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from yosai.core import (
    CacheInitializationException,
    cache_abcs,
)

from yosai_dpcache.cache import (
    make_region,
    CacheSettings,
    SerializationProxy,
)


class DPCacheHandler(cache_abcs.CacheHandler):

    def __init__(self, settings=None, ttl=None, region_name=None, backend=None,
                 region_arguments=None, serialization_manager=None):
        """
        You may either explicitly configure the CacheHandler or default to
        settings defined in a yaml file.
        """
        if not all([ttl, region_name, region_arguments]):
            cache_settings = CacheSettings(settings)
            self.absolute_ttl = cache_settings.absolute_ttl
            self.credentials_ttl = cache_settings.credentials_ttl
            self.authz_info_ttl = cache_settings.authz_info_ttl
            self.session_ttl = cache_settings.session_abs_ttl
            self.region_name = cache_settings.region_name
            self.backend = cache_settings.backend
            self.region_arguments = cache_settings.region_arguments
        else:
            self.absolute_ttl = ttl.get('absolute_ttl', 60)
            self.credentials_ttl = ttl.get('credentials_ttl', 10)
            self.authz_info_ttl = ttl.get('authz_info_ttl', 60)
            self.session_ttl = ttl.get('session_abs_ttl', 60)
            self.region_name = region_name
            self.backend = backend
            self.region_arguments = region_arguments

        if serialization_manager:
            self.serialization_manager = serialization_manager
        else:
            self._serialization_manager = None
            self.cache_region = None  # initializes when serialization_manager is set

    @property
    def serialization_manager(self):
        return self._serialization_manager

    @serialization_manager.setter
    def serialization_manager(self, manager):
        self._serialization_manager = manager
        self.cache_region = self.create_cache_region(name=self.region_name)

    def create_cache_region(self, name):
        sm = self.serialization_manager

        try:
            cache_region = make_region(name=name)
            cache_region.configure(backend=self.backend,
                                   expiration_time=self.absolute_ttl,
                                   arguments=self.region_arguments,
                                   wrap=[(SerializationProxy,
                                          sm.serialize, sm.deserialize)])
        except AttributeError:
            msg = 'Failed to Initialize a CacheRegion. {one}'.\
                format(one='serialization_manager not set'
                       if not self.serialization_manager else '')
            raise CacheInitializationException(msg)

        return cache_region

    def get_ttl(self, key):
        return getattr(self, key + '_ttl', None)

    def generate_key(self, identifier, domain):
        # simple for now yet TBD:
        return "yosai:{0}:{1}".format(identifier, domain)

    def get(self, domain, identifier):
        if identifier is None:
            return
        full_key = self.generate_key(identifier, domain)
        return self.cache_region.get(full_key)

    def get_or_create(self, domain, identifier, creator_func, creator):
        """
        This method will try to obtain an object from cache.  If the object is
        not available from cache, the creator_func function is called to generate
        a new Serializable object and then the object is cached.  get_or_create
        uses dogpile locking to avoid race condition among competing get_or_create
        threads where by the first requesting thread obtains exclusive privilege
        to generate the new object while other requesting threads wait for the
        value and then return it.

        :param creator_func: the function called to generate a new
                             Serializable object for cache
        :type creator_func:  function

        :param creator: the object calling get_or_create
        """
        if identifier is None:
            return
        full_key = self.generate_key(identifier, domain)
        ttl = self.get_ttl(domain)
        return self.cache_region.get_or_create(key=full_key,
                                               creator_func=creator_func,
                                               creator=creator,
                                               expiration=ttl)

    def set(self, domain, identifier, value):
        """
        :param value:  the Serializable object to cache
        """
        if value is None:
            return
        full_key = self.generate_key(identifier, domain)
        ttl = self.get_ttl(domain)
        self.cache_region.set(full_key, value, expiration=ttl)

    def delete(self, domain, identifier):
        """
        Removes an object from cache
        """
        if identifier is None:
            return
        full_key = self.generate_key(identifier, domain)
        self.cache_region.delete(full_key)

    def keys(self, pattern):
        """
        obtains keys from cache that match pattern

        CAUTION:  use for debugging only as it is taxes redis hard and is slow

        :returns: list of bytestrings
        """
        return self.cache_region.keys(pattern)
