import json
import datetime


class MyEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that leverages an object's `__json__()` method,
    if available, to obtain its default JSON representation. 

    """
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if hasattr(obj, '__json__'):
            return obj.__json__()
        return json.JSONEncoder.default(self, obj)
