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

#from abc import abstractmethod

#from yosai import (
#    LogManager,
#    cache_abcs,
#)

from yosai_dpcache import (
    make_region,
    cache_settings,
)


class DPCacheHandler:  #(cache_abcs.CacheHandler):

    def __init__(self):
        self.credentials_ttl = cache_settings.credentials_ttl
        self.authz_info_ttl = cache_settings.authz_info_ttl
        self.session_ttl = cache_settings.session_abs_ttl

        region_name = cache_settings.region_name
        self.cache_region = self.create_cache_region(name=region_name)

    def create_cache_region(self, name):

        cache_region = make_region(name=name)

        cache_region.configure(backend='yosai_dpcache.cache.redis',
                               expiration_time=cache_settings.absolute_ttl,
                               arguments=cache_settings.server_config,
                               wrap=SerializationProxy)

        return cache_region

    def get_ttl(self, key):
        return getattr(self, key + '_key', None)

    def generate_key(self, identifier, key):
        # simple for now yet TBD:
        return "yosai:{0}:{1}".format(identifier, key)

    def get(self, key, identifier):
        """
        :param obj:  a yosai object that contains an identifer
        :type obj:  Account, UsernamePasswordToken
        """
        full_key = self.generate_key(identifier, key)
        return self.cache_region.get(full_key)

    def get_or_create(self, key, identifier, creator_func):
        """
        This method will try to obtain an object from cache.  If the object is
        not available from cache, the creator_func function is called to generate
        a new Serializable object and then the object is cached.  get_or_create
        uses dogpile locking to avoid race condition among competing get_or_create
        threads where by the first requesting thread obtains exclusive privilege
        to generate the new object while other requesting threads wait for the
        value and then return it.

        :param obj:  a yosai object that contains an identifer
        :type obj:  Account, UsernamePasswordToken

        :param creator_func: the function called to generate a new
                             Serializable object for cache
        :type creator_func:  function
        """
        full_key = self.generate_key(identifier, key)
        ttl = self.get_ttl(key)
        return self.cache_region.get_or_create(key=full_key,
                                               creator=creator_func,
                                               expiration=ttl)

    def set(self, key, identifier, value):
        """
        :param obj:  a yosai object that contains the key identifer
        :type obj:  Account, UsernamePasswordToken

        :param value:  the Serializable object to cache
        """
        full_key = self.generate_key(identifier, key)
        ttl = self.get_ttl(key)
        self.cache_region.set(full_key, value, expiration=ttl)

    def delete(self, key, identifier):
        """
        Removes an object from cache

        :param obj:  a yosai object that contains an identifer
        :type obj:  Account, UsernamePasswordToken
        """
        full_key = self.generate_key(identifier key)
        self.cache_region.delete(full_key)
