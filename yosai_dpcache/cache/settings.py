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
    LazySettings,
)


class CacheSettings:

    def __init__(self):

        cache_config = LazySettings("YOSAI_CACHE_SETTINGS")

        region_init_config = cache_config.INIT_CONFIG
        self.region_name = region_init_config.get('region_name')
        self.backend = region_init_config.get('backend')

        server_config = cache_config.SERVER_CONFIG
        self.region_arguments = server_config.get('REDIS')

        ttl_config = cache_config.TTL_CONFIG
        self.absolute_ttl = ttl_config.get('absolute_ttl')
        self.credentials_ttl = ttl_config.get('credentials_ttl')
        self.authz_info_ttl = ttl_config.get('authz_info_ttl')
        self.session_abs_ttl = ttl_config.get('session_absolute_ttl')


def load_cache_settings():
    return CacheSettings()
