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

from yosai.core import MisconfiguredException


class CacheSettings:
    def __init__(self, settings):

        try:
            cache_settings = settings.CACHE_HANDLER
            region_init_config = cache_settings['init_config']

            self.region_name = region_init_config['region_name']
            self.backend = region_init_config.get('backend')

            server_config = cache_settings['server_config']
            self.region_arguments = server_config.get('redis')

            ttl_config = cache_settings['ttl_config']
            self.absolute_ttl = ttl_config.get('absolute_ttl')
            self.credentials_ttl = ttl_config.get('credentials_ttl')
            self.authz_info_ttl = ttl_config.get('authz_info_ttl')
            self.session_abs_ttl = ttl_config.get('session_absolute_ttl')

        except (AttributeError, TypeError):
            msg = ('yosai_dpcache CacheSettings requires a LazySettings instance '
                   'with complete CACHE_HANDLER settings')
            raise MisconfiguredException(msg)
