import base64
import json


class StatusMsgInvalidJSONError(Exception):
    """Status message does not contain valid JSON."""


def json_base64_decode(dct):
    """base64 decode object hook for custom JSON encoding."""
    key_name = '__base64_encoded__'
    if key_name in dct:
        return base64.b64decode(dct[key_name])
    return dct


def json_loads(data):
    """Loads and decodes JSON, with added base64 decoding.

    :param data: either bytes or a string. If bytes, will be decoded
                 using the current default encoding.
    :raises:
    :returns: decoded Python objects
    """
    if isinstance(data, bytes):
        data = data.decode()
    try:
        return json.loads(data, object_hook=json_base64_decode)
    except json.decoder.JSONDecodeError:
        raise StatusMsgInvalidJSONError(data)
