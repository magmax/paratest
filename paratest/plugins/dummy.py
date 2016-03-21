import time
from yapsy.IPlugin import IPlugin


class Dummy(IPlugin):
    def find(self, path, pattern):
        return ['foo', 'bar', 'bazz']

    def run(self, id, tid, workspace, output_path):
        if tid == 'bazz':
            raise Exception("Erroneous test")
        print("Worker %s: Running test %s" % (id, tid))
