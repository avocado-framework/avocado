import json


class ConfigDecoder(json.JSONDecoder):
    """
    JSON Decoder for config options.
    """

    @staticmethod
    def decode_set(config_dict):
        for k, v in config_dict.items():
            if isinstance(v, dict):
                if '__encoded_set__' in v:
                    config_dict[k] = set(v['__encoded_set__'])
        return config_dict

    def decode(self, config_str):  # pylint: disable=W0221
        config_dict = json.JSONDecoder.decode(self, config_str)
        return self.decode_set(config_dict)


class ConfigEncoder(json.JSONEncoder):
    """
    JSON Encoder for config options.
    """

    def default(self, o):
        if isinstance(o, set):
            return {'__encoded_set__': list(o)}
        try:
            return json.JSONEncoder.default(self, o)
        except TypeError:
            # Probably this is a not JSON serializable data. To keep the same
            # behavior as before, lets return None
            return None
