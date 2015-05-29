import os
import threading
import yaml

_local = threading.local()

class Scopes(object):
    def __init__(self, filename):
        self.filename = filename

    @property
    def _data(self):
        mtime = os.stat(self.filename).st_mtime
        if mtime > getattr(_local, 'mtime', 0):
            with open(self.filename, 'rb') as f:
                _local.data = yaml.load(f)
            _local.mtime = mtime
        return _local.data

    def __iter__(self):
        return iter(self._data)
    
    def __getitem__(self, key):
        return self._data[key]