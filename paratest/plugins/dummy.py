import time
from yapsy.IPlugin import IPlugin


class Dummy(IPlugin):
    def find(self, path, test_pattern, file_pattern, output_path):
        for item in {'foo': 'echo foo', 'bar': 'echo bar', 'bazz': 'echo bazz'}.items():
            yield item
