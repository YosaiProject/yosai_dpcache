from yosai_dpcache.cache import ProxyBackend


class SerializationProxy(ProxyBackend):

    def __init__(self, serialize, deserialize):
        """
        serialization and de-serialization functionality is injected
        """
        self.serialize = serialize
        self.deserialize = deserialize

    def get(self, key):
        serialized = self.proxied.get(key)
        return self.deserialize(serialized)

    def set(self, key, value, expiration):
        serialized = self.serialize(value)
        self.proxied.set(key, serialized, expiration)

    def get_multi(self, keys):
        multi_serialized = self.proxied.get_multi(keys)
        return {key: self.deserialize(value) for key, value in
                multi_serialized.items()}

    def set_multi(self, mapping, expiration):
        serialized_mapping = {key: self.serialize(value) for key, value in
                              mapping.items()}
        self.proxied.set_multi(serialized_mapping, expiration)

    def delete(self, key):
        self.proxied.delete(key)

    def keys(self, pattern):
        return self.proxied.keys(pattern)

    # delete, delete_multi, and get_mutext operations are inherited
